'''
Patient Timeline Agent
Maintains the complete medical history.
Finds patterns like:
Weight loss over 3 years
Recurring ear infections
Diabetes progression
Medication changes 
'''
#%%
# app/RAG/agents/timeline_agent.py
# app/RAG/agents/timeline_agent.py


from typing import List, Dict, Any

from app.services.logging_config import logger

class PatientTimelineAgent:
    def __init__(self, db_path: str, groq_api_key: str):
        self.db_path = db_path
        from groq import Groq
        self.client = Groq(api_key=groq_api_key)
        self.model = "openai/gpt-oss-120b"

    def fetch_patient_history(self, patient_id: str, db_session=None) -> List[Dict[str, Any]]:
        """Queries database for chronological logs using active SQLAlchemy session or direct SQLite."""
        if not patient_id:
            return []

        # 1. Use ORM session if available (Prevents file path mismatch)
        if db_session:
            try:
                from app.database.models import ClinicalRecord
                records = db_session.query(ClinicalRecord).filter(
                    ClinicalRecord.patient_id == int(patient_id)
                ).order_by(ClinicalRecord.created_at.asc()).all()

                return [
                    {
                        "created_at": r.created_at.strftime('%Y-%m-%d') if r.created_at else "Undated",
                        "title": r.title or "Clinical Entry",
                        "content": r.content or "",
                        "source_file": r.source_file or "EHR"
                    }
                    for r in records
                ]
            except Exception as e:
                logger.warning(f"ORM fetch failed, falling back to SQLite connection: {e}")

        # 2. Direct SQLite Fallback
        import sqlite3
        query = """
            SELECT created_at, title, content, source_file 
            FROM clinical_records 
            WHERE patient_id = ? 
            ORDER BY created_at ASC
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(query, (str(patient_id),))
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception:
            logger.exception("CRITICAL ERROR inside fetch_patient_history database layer")
            return []

    def analyze_timeline_patterns(self, patient_id: str, db_session=None) -> str:
        """Processes raw chronological records through an analytical LLM inference pass."""
        try:
            raw_history = self.fetch_patient_history(patient_id, db_session)
            if not raw_history:
                logger.warning(f"No longitudinal records found for patient ID: {patient_id}")
                return "No historical longitudinal data available for this patient."

            history_serialized = ""
            for record in raw_history:
                history_serialized += (
                    f"### Date: {record.get('created_at')} | Title: {record.get('title')}\n"
                    f"Notes:\n{record.get('content')}\n"
                    f"{'-'*50}\n"
                )

            system_instruction = (
                "You are an expert veterinary medical data analyst representing VetMind AI.\n"
                "Evaluate the historical timeline of the patient to uncover multi-year patterns:\n"
                "1. Weight Variations\n"
                "2. Recurring Conditions\n"
                "3. Chronic Disease Progression\n"
                "4. Medication Efficacy & Changes\n\n"
                "CRITICAL: Rely strictly on facts present in the logs without hallucinating."
            )

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": f"CHRONOLOGICAL PATIENT LOG DATA:\n{history_serialized}"}
                ],
                temperature=0.1
            )
            return response.choices[0].message.content

        except Exception:
            logger.exception("CRITICAL ERROR inside analyze_timeline_patterns pass")
            return "An internal system tracking error occurred during timeline evaluation."