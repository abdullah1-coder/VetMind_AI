# %%

import sys
from typing import Dict, Any
from groq import Groq
from langchain_core.runnables import RunnableConfig

from app.services.logging_config import logger

class ClinicalGenerationAgent:
    """
    Agent 2: Clinical Generation Pass.
    Responsible for engineering the clinical prompt layout, executing the 
    generation pass via Groq, and ensuring adherence to textbook contexts.
    """
    def __init__(self, base_url: str = "https://api.groq.com/openai/v1", api_key: str = None, model: str = "openai/gpt-oss-120b"):
        self.client = Groq(api_key=api_key)
        self.model = model
        logger.info(f"ClinicalGenerationAgent initialized with model: {model}")

    def execute_grounded_generation(
        self, 
        user_query: str, 
        structured_context: str, 
        config: RunnableConfig = None,
        history: str = "", 
        patient_timeline_analysis: str = ""
    ) -> str:
        """
        Sends the compiled context framework and query to Groq for a structured clinical response.
        """
        try:
            logger.info("Drafting clinical evaluation prompt payload...")
            
            # 1. Format System Prompt with dynamic context variables
            system_prompt = f"""You are VetMind AI, an elite veterinary decision support assistant.

### RESPONSE FORMATTING RULES (STRICTLY ENFORCED):

1. **DIRECT / CONVERSATIONAL QUERIES:**
   - IF the user asks a direct question (e.g., "Is Luna a dog or cat?", "What is Oliver's weight?", "What dosage was given?"):
   - **DO NOT** use structured section headers (1. Diagnostic Evaluation, 2. Treatment...).
   - Answer directly and concisely in 1–2 brief paragraphs.

2. **REPORTS & COMPREHENSIVE SUMMARIES:**
   - **ONLY** use the 4-part structured format (1. Diagnostic Evaluation, 2. Treatment, 3. Monitoring, 4. Direct Citation Mapping) if explicitly instructed below.

3. **PATIENT DATA TRUTH:**
   - Use PATIENT EHR HISTORY and PATIENT TIMELINE ANALYSIS as the single source of truth for patient species, breed, and medical history.

4. **STRICT SPECIES ISOLATION:**
   - Always verify the patient's target species from the PATIENT EHR HISTORY demographics header (e.g., Avian, Feline, Canine).
   - ONLY provide diagnostic insights, side effects, and pharmaceutical guidelines applicable to THAT SPECIFIC SPECIES.
   - **NEVER** mention or compare other species in your explanation (e.g., DO NOT write "as seen in dogs and cats" or "more common in cats" when answering about an avian patient).
   - Ensure clinical advice respects avian anatomy (e.g., cautioning against excessive fluid flushing to prevent aspiration).
5. **NO META-TALKING OR CONTEXT APOLOGIES:**
   - **NEVER** use meta-phrases such as "Given the explicit request", "Based on the provided context", "The retrieved information discusses...", "The database shows...", or "There is limited specific data on avian species".
   - Synthesize all clinical insights seamlessly, authoritatively, and naturally as an expert system.

### PATIENT EHR HISTORY:
{history or 'No raw EHR history provided.'}

### PATIENT TIMELINE ANALYSIS:
{patient_timeline_analysis or 'No longitudinal timeline analysis available.'}

### TEXTBOOK REFERENCE CONTEXT:
{structured_context or 'No textbook context retrieved.'}"""

            # 2. Check if user query explicitly seeks a comprehensive report
            REPORT_KEYWORDS = ["report", "summary", "pdf", "timeline", "case replay", "treatment plan", "protocol"]
            is_report_requested = any(kw in user_query.lower() for kw in REPORT_KEYWORDS)
            
            if is_report_requested:
                format_instruction = (
                    "Provide a comprehensive, structured response covering:\n"
                    "1. Diagnostic Evaluation\n"
                    "2. Treatment & Pharmaceutical Protocol\n"
                    "3. Monitoring & Case Management\n"
                    "4. Direct Citation Mapping"
                )
            else:
                format_instruction = (
                    "Answer the user query directly, concisely, and conversationally in 1-2 paragraphs. "
                    "DO NOT use numbered section headings."
                )

            # 3. Build user content payload dynamically
            user_content = (
                f"CLINICAL USER QUERY: {user_query}\n\n"
                f"INSTRUCTION: {format_instruction}"
            )

            logger.info(f"Dispatching API inference call to Groq endpoint for query: {user_query[:40]}...")
            
            # 4. Dispatch Groq API Call
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                temperature=0.1
            )
            
            logger.info("Generation pass successfully completed.")
            return response.choices[0].message.content

        except Exception:
            logger.exception("CRITICAL ERROR inside execute_grounded_generation")
            return "An internal system error occurred during the clinical generation phase."



