# app/RAG/agents/guardrail_agent.py


from typing import Dict, Any

from app.services.logging_config import logger

class GuardrailAgent:
    def __init__(self, groq_api_key: str = None):
        # Ensure you have raw_llm initialized
        from langchain_groq import ChatGroq
        import os
        
        self.groq_api_key = groq_api_key or os.getenv("GROQ_API_KEY")
        self.raw_llm = ChatGroq(
            model_name="openai/gpt-oss-safeguard-20b",
            groq_api_key=self.groq_api_key,
            temperature=0.0
        )

    def validate_input(self, user_query: str) -> Dict[str, Any]:
        """
        Executes Guardrail input validation pass.
        Dynamic Intent Audit: Rejects ANY prompt outside veterinary clinical medicine.
        """
        logger.info(f"Auditing user query domain relevance: '{user_query}'")

        try:
            classifier_prompt = f"""You are the strict domain guardrail for VetMind AI, a specialized clinical veterinary decision support system.

Your job is to classify if the query is strictly within the domain of veterinary medicine, animal healthcare, OR clinical report generation requests.

ALLOWED DOMAIN (VET_CLINICAL):
- Veterinary clinical cases, animal diseases, symptoms, diagnosis, treatment, pharmacology, or animal surgery.
- Pet medical history, longitudinal trends, EHR lab notes, or animal preventive care/nutrition.
- Meta-questions about the active clinical conversation (e.g., "what were we talking about?", "what is the patient's name?").
- Requests for clinical reports, PDF exports, treatment summaries, or downloads for a patient (e.g., "give downloadable pdf report for Simba", "export report as pdf", "generate summary").

DISALLOWED DOMAIN (OFF_TOPIC):
- ANY subject completely unrelated to animal health or clinical case management.
- Examples: politics, sports, general history (e.g. "who founded Microsoft?"), coding, travel, entertainment, math, cooking, or general trivia.

DISALLOWED DOMAIN (HARMFUL):
- Intent to intentionally poison, fatally overdose, or harm an animal at home.

USER QUERY: "{user_query}"

Respond with EXACTLY ONE word: VET_CLINICAL, OFF_TOPIC, or HARMFUL."""

            # Execute classification call
            response = self.raw_llm.invoke(classifier_prompt)
            verdict = response.content.strip().upper()

            if "OFF_TOPIC" in verdict:
                logger.warning(f"Guardrail Intercept: Off-topic query detected ('{user_query}')")
                refusal_text = (
                    "I am sorry, but as VetMind AI, I am strictly configured to assist with "
                    "veterinary clinical cases and animal health guidelines. I cannot assist with non-veterinary topics."
                )
                return {
                    "is_safe": False,
                    "reason": "Dynamic Guardrail: Non-veterinary query intercepted.",
                    "response_text": refusal_text,
                    "fallback_response": refusal_text
                }

            if "HARMFUL" in verdict:
                logger.warning(f"Guardrail Intercept: Harmful query detected ('{user_query}')")
                refusal_text = (
                    "I am VetMind AI. I cannot provide instructions on lethal dosages, toxicity thresholds, or home euthanasia."
                )
                return {
                    "is_safe": False,
                    "reason": "Dynamic Guardrail: Harmful/Lethal query intercepted.",
                    "response_text": refusal_text,
                    "fallback_response": refusal_text
                }

            logger.info("Guardrail Pass: Query validated as safe clinical input.")
            return {
                "is_safe": True,
                "reason": "Passed safety checks.",
                "response_text": None,
                "fallback_response": None
            }

        except Exception as e:
            logger.exception(f"Error during dynamic guardrail pass: {str(e)}")
            # Fallback to prevent breaking pipeline on API errors
            return {
                "is_safe": True,
                "reason": f"Guardrail execution fallback: {str(e)}",
                "response_text": None,
                "fallback_response": None
            }