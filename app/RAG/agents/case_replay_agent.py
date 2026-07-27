# app/RAG/agents/case_replay_agent.py
#%%
import logging
import os
import sys
from typing import Dict, Any
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from app.services.logging_config import logger


class CaseReplayAgent:
    """
    Case Replay Agent.
    Transforms raw, multi-visit patient records into a structured, chronological 
    clinical timeline, acting like a documentary of the patient's medical history.
    """
    def __init__(self, groq_api_key: str):
        # Utilizing the highly efficient model for structured layout extraction
        self.llm = ChatGroq(
            model="openai/gpt-oss-120b",
            groq_api_key=groq_api_key,
            temperature=0.1
        )
        self.parser = JsonOutputParser()
        logger.info("CaseReplayAgent initialized successfully.")

    def replay_case(self, raw_patient_history: str) -> Dict[str, Any]:
        """
        Parses messy medical histories and extracts structured milestone events 
        for timeline rendering.
        """
        logger.info("Parsing longitudinal patient history for chronological replay...")

        system_instruction = (
            "You are an expert veterinary medical historian.\n"
            "Your task is to analyze the raw patient medical history and break it down into "
            "a chronological list of distinct visits or milestones.\n"
            "For each visit/milestone, extract the following fields strictly if present:\n"
            "- date: The exact date or time anchor.\n"
            "- title: e.g., 'Initial Presentation', 'Follow-up Check', 'Emergency Visit'.\n"
            "- symptoms: Summary of clinical signs.\n"
            "- labs: Key diagnostic tests, bloodwork, or imaging findings.\n"
            "- treatment: Medications prescribed or procedures performed.\n"
            "- progression: How the patient responded or deteriorated.\n\n"
            "Return the output strictly as a JSON object with a single key 'events' containing an array of these objects.\n"
            "Do not wrap the JSON in markdown code blocks, do not include any explanatory prose."
        )

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_instruction),
            ("user", "Analyze this medical history and extract the chronological timeline:\n\n{history}")
        ])

        try:
            chain = prompt | self.llm | self.parser
            structured_data = chain.invoke({"history": raw_patient_history})
            logger.info("Successfully extracted structured case replay timeline matrix.")
            return structured_data
        except Exception:
            logger.exception("CRITICAL ERROR during Case Replay timeline extraction")
            return {"events": []}
# %%
