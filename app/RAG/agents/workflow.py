# %%
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any, TypedDict, Literal, List
from dotenv import load_dotenv
from langchain_core.messages import BaseMessage
from langchain_core.runnables import RunnableConfig

load_dotenv()

# --- EXACT DIRECTORY PATH RESOLUTION ---
current_file = Path(__file__).resolve() if "__file__" in globals() else Path.cwd()

if current_file.name == "agents":
    agents_dir = current_file
    rag_dir = current_file.parent
elif (current_file / "agents").exists():
    rag_dir = current_file
    agents_dir = current_file / "agents"
else:
    agents_dir = next((p for p in current_file.parents if p.name == "agents"), current_file)
    rag_dir = agents_dir.parent

project_root = next((p for p in rag_dir.parents if (p / "app").exists()), rag_dir.parent)

for path_dir in [str(agents_dir), str(rag_dir), str(project_root)]:
    if path_dir not in sys.path:
        sys.path.insert(0, path_dir)
# ---------------------------------------

from langgraph.graph import StateGraph, END

# Direct imports since workflow.py is inside the agents/ directory
from guardrail_agent import GuardrailAgent
from context_agent import ClinicalContextAgent
from timeline_agent import PatientTimelineAgent
from generation_agent import ClinicalGenerationAgent
from case_replay_agent import CaseReplayAgent
from report_agent import ReportGenerationAgent

from RAG import get_hybrid_retriever

from app.services.logging_config import logger


# 1. State Schema tracking data across all agents
class AgentState(TypedDict):
    user_query: str
    patient_id: str | None
    db_session: Any | None
    chat_history: List[BaseMessage] | str
    patient_history_raw: str
    retrieved_textbook_context: str
    patient_timeline_analysis: str
    fused_clinical_advice: str
    is_safe: bool
    fallback_response: str | None
    timeline_replay: Dict[str, Any] | None
    final_report_path: str | None


class VetMindWorkflow:
    """
    Central LangGraph Orchestrator fusing 6 specialized agents:
    Guardrail -> (Context + Timeline) -> Generation -> Case Replay/Report
    """
    def __init__(self, groq_api_key: str = None, db_path: str = None):
        self.groq_api_key = groq_api_key or os.getenv("GROQ_API_KEY")
        self.db_path = db_path or r"C:\VetMind AI\data\vetmind_records.db"

        # Instantiate all 6 agents
        self.guardrail_agent = GuardrailAgent(groq_api_key=self.groq_api_key)
        self.context_agent = ClinicalContextAgent(hybrid_retriever_func=get_hybrid_retriever)
        self.timeline_agent = PatientTimelineAgent(db_path=self.db_path, groq_api_key=self.groq_api_key)
        self.generation_agent = ClinicalGenerationAgent(api_key=self.groq_api_key, model="openai/gpt-oss-120b")
        self.replay_agent = CaseReplayAgent(groq_api_key=self.groq_api_key)
        self.report_agent = ReportGenerationAgent(groq_api_key=self.groq_api_key)

        self.workflow_graph = self._initialize_graph()

    # Node 1: Fast Guardrail Audit with RunnableConfig
    def _guardrail_node(self, state: AgentState, config: RunnableConfig = None) -> Dict[str, Any]:
        logger.info("Node 1 [Guardrail]: Auditing query safety...")
        verdict = self.guardrail_agent.validate_input(state["user_query"])
        
        is_safe = verdict.get("is_safe", True)
        fallback_text = (
            verdict.get("fallback_response") 
            or verdict.get("response_text") 
            or "This query violates safety policies or is off-topic."
        ) if not is_safe else None

        return {
            "is_safe": is_safe,
            "fallback_response": fallback_text
        }

    # Node 2: Hybrid Vector DB & BM25 Knowledge Retrieval with RunnableConfig
    # Node 2: Hybrid Vector DB & BM25 Knowledge Retrieval with RunnableConfig
    def _textbook_context_node(self, state: AgentState, config: RunnableConfig = None) -> Dict[str, Any]:
        logger.info("Node 2 [ContextAgent]: Fetching hybrid vector/BM25 chunks...")
        
        # FIX: Pass ONLY the raw user query into the retriever. 
        # Do NOT concatenate history_str here!
        search_query = state["user_query"]
        
        textbook_context = self.context_agent.assemble_grounding_context(search_query)
        return {"retrieved_textbook_context": textbook_context}
    # Node 3: SQLite Longitudinal Timeline Analysis with RunnableConfig
    def _timeline_node(self, state: AgentState, config: RunnableConfig = None) -> Dict[str, Any]:
        patient_id = state.get("patient_id")
        db_session = state.get("db_session")

        if not patient_id:
            return {"patient_timeline_analysis": "No patient context selected."}

        try:
            timeline_result = self.timeline_agent.analyze_timeline_patterns(str(patient_id), db_session)
            logger.info(f"Successfully extracted timeline analysis for Patient #{patient_id}")
            return {"patient_timeline_analysis": timeline_result}

        except Exception as e:
            logger.exception(f"Timeline node execution failed for patient_id: {patient_id}")
            return {"patient_timeline_analysis": f"Timeline analysis unavailable: {str(e)}"}

    # Node 4: Grounded Clinical Generation with Callback Propagation
    def _clinical_generation_node(self, state: AgentState, config: RunnableConfig = None) -> Dict[str, Any]:
        logger.info("Node 4 [GenerationAgent]: Synthesizing grounded clinical advice...")
        
        chat_history_str = state.get("chat_history") or "No previous conversation history."
    
        fused_context = (
            f"=== CONVERSATION HISTORY (PAST TURNS) ===\n{chat_history_str}\n\n"
            f"=== TEXTBOOK REFERENCE GUIDELINES ===\n{state['retrieved_textbook_context']}\n\n"
            f"=== PATIENT LONGITUDINAL TRENDS ===\n{state['patient_timeline_analysis']}\n\n"
            f"=== RAW EHR NOTES ===\n{state['patient_history_raw']}"
        )
        
        clinical_response = self.generation_agent.execute_grounded_generation(
            user_query=state["user_query"],
            structured_context=fused_context,
            config=config
        )
        return {"fused_clinical_advice": clinical_response}

    # Node 5: Conditional Case Replay & PDF Generation with RunnableConfig
    def _case_replay_and_report_node(self, state: AgentState, config: RunnableConfig = None) -> Dict[str, Any]:
        user_query = state.get("user_query", "").lower()
        
        explicit_export_keywords = [
            "download report", "export report", "pdf report", 
            "download pdf", "generate report", "export pdf"
        ]
        
        user_wants_pdf = any(kw in user_query for kw in explicit_export_keywords)

        if not user_wants_pdf:
            logger.info("Node 5 [Report/CaseReplay]: Skipping PDF report compilation for standard chat query.")
            return {"final_report_path": None, "timeline_replay": None}

        logger.info("Node 5 [Report/CaseReplay]: Compiling PDF artifact...")
        
        replay_data = self.replay_agent.replay_case(state["patient_history_raw"])
        dynamic_report_text = state.get("fused_clinical_advice") or state.get("patient_history_raw")
        
        patient_tag = state.get("patient_id") or "clinical"
        pdf_filename = f"case_summary_{patient_tag}.pdf"

        pdf_path = self.report_agent.convert_to_pdf(
            report_text=dynamic_report_text,
            filename=pdf_filename
        )
        return {"final_report_path": pdf_path, "timeline_replay": replay_data}

    # Conditional Router
    def _router_logic(self, state: AgentState) -> Literal["continue", "halt"]:
        if not state.get("is_safe", True):
            logger.warning("Router: Unsafe query detected. Halting pipeline.")
            return "halt"
        return "continue"

    def _initialize_graph(self):
        builder = StateGraph(AgentState)

        # Register nodes
        builder.add_node("guardrail", self._guardrail_node)
        builder.add_node("textbook_context", self._textbook_context_node)
        builder.add_node("patient_timeline", self._timeline_node)
        builder.add_node("clinical_generation", self._clinical_generation_node)
        builder.add_node("case_replay_report", self._case_replay_and_report_node)

        # Define topology
        builder.set_entry_point("guardrail")

        builder.add_conditional_edges(
            "guardrail",
            self._router_logic,
            {
                "continue": "textbook_context",
                "halt": END
            }
        )

        builder.add_edge("textbook_context", "patient_timeline")
        builder.add_edge("patient_timeline", "clinical_generation")
        builder.add_edge("clinical_generation", "case_replay_report")
        builder.add_edge("case_replay_report", END)

        return builder.compile()

    def run(
    self, 
    query: str, 
    history: Any = None,  
    patient_id: str = None, 
    db_session: Any = None,
    config: RunnableConfig = None
) -> Dict[str, Any]:
    
        initial_state: AgentState = {
            "user_query": query,
            "patient_id": patient_id,
            "db_session": db_session,
            "chat_history": history or "", 
            "patient_history_raw": "",
            "retrieved_textbook_context": "",
            "patient_timeline_analysis": "",
            "fused_clinical_advice": "",
            "is_safe": True,
            "fallback_response": None,
            "timeline_replay": None,
            "final_report_path": None
        }

        results = self.workflow_graph.invoke(initial_state, config=config)
        
        final_text = results.get("fallback_response") if not results.get("is_safe") else results.get("fused_clinical_advice")

        return {
            "is_safe": results.get("is_safe", True),
            "response_text": final_text,
            "patient_timeline_analysis": results.get("patient_timeline_analysis"),
            "final_report_path": results.get("final_report_path")
        }
# %%