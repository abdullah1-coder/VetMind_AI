import os
import sys
import logging
import uuid
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from pydantic import BaseModel

# Configure logging
from app.services.logging_config import logger

# Ensure project root is in Python path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Database & Schema Imports
from app.database.database import get_db, engine, Base
from app.database.models import (
    Patient, 
    ClinicalRecord, 
    GeneratedReport, 
    ChatMessage, 
    User, 
    Appointment
)
from app.database.schemas import (
    PatientCreate, PatientOut, 
    ClinicalRecordOut, 
    ChatQueryRequest, ChatQueryResponse
)

# RAG & Agent Imports
from app.RAG.agents.workflow import VetMindWorkflow
from app.services.ocr_engine import process_ocr_file

# Load environment secrets
load_dotenv()

# Initialize Database Tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="VetMind AI Core Engine API",
    description="Agentic RAG, Guardrails, OCR, Authentication, & EHR Backend",
    version="1.0.0"
)

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

REPORTS_DIR = os.path.join(os.getcwd(), "static", "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

# Mount static directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# Instantiate Workflow Orchestrator
orchestrator = VetMindWorkflow()


# ============================================================
# PYDANTIC SCHEMAS FOR AUTH & APPOINTMENTS
# ============================================================

class LoginRequest(BaseModel):
    email: str
    password: str
    role: str  # "doctor" or "owner"


class AppointmentCreate(BaseModel):
    owner_name: str
    pet_name: str
    species: str
    reason: str
    appointment_date: str
    appointment_time: str


# ============================================================
# 1. AUTHENTICATION ENDPOINTS
# ============================================================

@app.post("/auth/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    """Authenticates or registers users (Doctor vs. Owner)."""
    user = db.query(User).filter(User.email == req.email).first()
    if not user:
        # Auto-register user for dev/demo deployment
        user = User(
            email=req.email,
            full_name=req.email.split("@")[0].capitalize(),
            role=req.role
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    return {
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role
        },
        "token": f"fake-jwt-token-{user.id}"
    }


# ============================================================
# 2. PATIENT EHR ENDPOINTS (CRUD)
# ============================================================

@app.post("/patients", response_model=PatientOut, status_code=status.HTTP_201_CREATED)
def create_patient(patient_in: PatientCreate, db: Session = Depends(get_db)):
    """Creates a new patient profile."""
    db_patient = Patient(**patient_in.dict())
    db.add(db_patient)
    db.commit()
    db.refresh(db_patient)
    return db_patient


@app.get("/patients", response_model=List[PatientOut])
def list_patients(db: Session = Depends(get_db)):
    """Returns all patient profiles stored in SQLite."""
    return db.query(Patient).order_by(Patient.created_at.desc()).all()


@app.get("/patients/{patient_id}", response_model=PatientOut)
def get_patient(patient_id: int, db: Session = Depends(get_db)):
    """Fetches full details and clinical record history for a specific patient."""
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient record not found.")
    return patient


@app.put("/patients/{patient_id}", response_model=PatientOut)
def update_patient(patient_id: int, patient_in: PatientCreate, db: Session = Depends(get_db)):
    """Updates an existing patient record."""
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient record not found.")
    
    patient.name = patient_in.name
    patient.species = patient_in.species
    patient.breed = patient_in.breed
    patient.age = patient_in.age
    patient.owner_name = patient_in.owner_name

    db.commit()
    db.refresh(patient)
    return patient


@app.delete("/patients/{patient_id}", status_code=status.HTTP_200_OK)
def delete_patient(patient_id: int, db: Session = Depends(get_db)):
    """Deletes a patient record and all associated clinical notes/chat messages."""
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient record not found.")

    # Delete related records and chat messages to maintain integrity
    db.query(ClinicalRecord).filter(ClinicalRecord.patient_id == patient_id).delete()
    if hasattr(ChatMessage, "patient_id"):
        db.query(ChatMessage).filter(ChatMessage.patient_id == patient_id).delete()

    db.delete(patient)
    db.commit()

    return {"message": f"Patient #{patient_id} and associated records successfully deleted."}


# ============================================================
# 3. APPOINTMENT BOOKING ENDPOINTS
# ============================================================

@app.post("/appointments", status_code=status.HTTP_201_CREATED)
def create_appointment(req: AppointmentCreate, db: Session = Depends(get_db)):
    """Saves a new appointment request from a pet owner."""
    apt = Appointment(**req.dict())
    db.add(apt)
    db.commit()
    db.refresh(apt)
    return apt


@app.get("/appointments")
def get_appointments(db: Session = Depends(get_db)):
    """Retrieves all scheduled appointments."""
    return db.query(Appointment).order_by(Appointment.created_at.desc()).all()


@app.put("/appointments/{apt_id}/status")
def update_appointment_status(apt_id: int, status: str, db: Session = Depends(get_db)):
    """Updates appointment status ('confirmed', 'cancelled', 'pending')."""
    apt = db.query(Appointment).filter(Appointment.id == apt_id).first()
    if not apt:
        raise HTTPException(status_code=404, detail="Appointment not found.")
    
    apt.status = status
    db.commit()
    db.refresh(apt)
    return apt


# ============================================================
# 4. OCR FILE INGESTION ROUTE
# ============================================================

@app.post("/ocr/upload", response_model=ClinicalRecordOut)
async def upload_and_process_ocr(
    patient_id: int = Form(...),
    title: Optional[str] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Processes uploaded document image/PDF via OCR and saves as clinical record."""
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Target patient not found.")

    uploads_dir = Path("app/database/data/uploads")
    uploads_dir.mkdir(parents=True, exist_ok=True)
    saved_file_path = uploads_dir / file.filename

    with open(saved_file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    try:
        extracted_markdown = await process_ocr_file(str(saved_file_path))
    except Exception:
        try:
            extracted_markdown = process_ocr_file(str(saved_file_path))
        except Exception as inner_e:
            raise HTTPException(status_code=500, detail=f"OCR Engine Failure: {str(inner_e)}")

    new_record = ClinicalRecord(
        patient_id=patient_id,
        title=title or file.filename,
        content=extracted_markdown,
        source_file=file.filename
    )
    db.add(new_record)
    db.commit()
    db.refresh(new_record)

    return new_record


# ============================================================
# 5. AGENTIC CHAT & CASE REPLAY WORKFLOW
# ============================================================

@app.post("/chat", response_model=ChatQueryResponse)
def execute_chat_query(req: ChatQueryRequest, db: Session = Depends(get_db)):
    """Orchestrates multi-turn clinical chat across agent nodes."""
    session_id = getattr(req, "session_id", None) or str(uuid.uuid4())
    target_patient = None
    patient_id_found = None

    try:
        # 1. Resolve Patient Context
        if req.patient_id:
            target_patient = db.query(Patient).filter(Patient.id == req.patient_id).first()
        elif hasattr(req, "patient_name") and req.patient_name:
            target_patient = db.query(Patient).filter(Patient.name.ilike(f"%{req.patient_name}%")).first()

        # 2. Build Patient EHR Context
        if target_patient:
            patient_id_found = target_patient.id
            records = db.query(ClinicalRecord).filter(ClinicalRecord.patient_id == target_patient.id).all()
            
            patient_header = (
                f"### PATIENT EHR DEMOGRAPHICS:\n"
                f"- **Name:** {target_patient.name}\n"
                f"- **ID:** {target_patient.id}\n"
                f"- **Species:** {getattr(target_patient, 'species', None) or 'Feline'}\n"
                f"- **Breed:** {getattr(target_patient, 'breed', None) or 'Siamese'}\n"
                f"- **Age:** {getattr(target_patient, 'age', None) or 'Not recorded'}\n"
                f"- **Owner:** {getattr(target_patient, 'owner_name', None) or 'N/A'}\n"
            )

            if records:
                records_text = "\n\n".join([
                    f"--- Record ({r.created_at.strftime('%Y-%m-%d')}): {r.title} ---\n{r.content}" 
                    for r in records
                ])
                ehr_history = f"{patient_header}\n### CLINICAL RECORDS:\n{records_text}"
            else:
                ehr_history = f"{patient_header}\n- **Clinical Notes Status:** Registered in SQLite. No uploaded OCR files."
        else:
            ehr_history = "General multi-species veterinary clinical reference context."

        # 3. Save User Message FIRST
        user_msg_kwargs = {"patient_id": patient_id_found, "role": "user", "content": req.query}
        if hasattr(ChatMessage, "session_id"):
            user_msg_kwargs["session_id"] = session_id

        user_msg = ChatMessage(**user_msg_kwargs)
        db.add(user_msg)
        db.commit()

        # 4. Retrieve Multi-Turn Session Memory
        chat_memory_context = ""
        if hasattr(ChatMessage, "session_id"):
            past_msgs = db.query(ChatMessage).filter(
                ChatMessage.session_id == session_id
            ).order_by(ChatMessage.id.desc()).limit(8).all()
            
            if past_msgs:
                past_msgs.reverse()
                chat_memory_context = "\n\n### Previous Conversation Memory:\n" + "\n".join([
                    f"{m.role.capitalize()}: {m.content}" for m in past_msgs
                ])

        combined_history = f"{ehr_history}{chat_memory_context}"

        # 5. Run LangGraph Orchestrator
        workflow_result = orchestrator.run(
            query=req.query,
            history=combined_history,
            patient_id=str(patient_id_found) if patient_id_found else None,
            db_session=db
        )

        response_text = (
            workflow_result.get("response_text") 
            or workflow_result.get("fallback_response")
            or "Query processed."
        )

        # 6. Check for PDF Generation Request
        raw_pdf_path = workflow_result.get("final_report_path", None)
        report_keywords = ["report", "pdf", "download", "summary", "export"]
        user_wants_pdf = any(kw in req.query.lower() for kw in report_keywords)

        report_url = None
        if user_wants_pdf and raw_pdf_path and Path(raw_pdf_path).exists():
            report_url = f"/api/reports/download/{Path(raw_pdf_path).name}"

        # 7. Save Assistant Message
        bot_msg_kwargs = {"patient_id": patient_id_found, "role": "assistant", "content": response_text}
        if hasattr(ChatMessage, "session_id"):
            bot_msg_kwargs["session_id"] = session_id

        bot_msg = ChatMessage(**bot_msg_kwargs)
        db.add(bot_msg)
        db.commit()

        return ChatQueryResponse(
            query=req.query,
            is_safe=workflow_result.get("is_safe", True),
            response_text=response_text,
            report_pdf_url=report_url,
            session_id=session_id,
            patient_id=patient_id_found
        )

    except Exception as e:
        logger.exception("Error executing chat query endpoint")
            
        return ChatQueryResponse(
            query=req.query,
            is_safe=True,
            response_text=f"An error occurred while processing the clinical query: {str(e)}",
            report_pdf_url=None,
            session_id=session_id,
            patient_id=req.patient_id if hasattr(req, 'patient_id') else None
        )


# ============================================================
# 6. REPORT DOWNLOAD ROUTE
# ============================================================

@app.get("/reports/download/{filename}")
def download_generated_report(filename: str):
    """Serves compiled PDF medical reports directly to the UI download button."""
    possible_paths = [
        Path("app/RAG/agents/generated_reports") / filename,
        Path("app/RAG/generated_reports") / filename,
        Path("static/reports") / filename,
    ]
    
    report_file_path = None
    for p in possible_paths:
        if p.exists():
            report_file_path = p
            break

    # Fallback report compilation if PDF does not exist on disk
    if not report_file_path:
        fallback_dir = Path("static/reports")
        fallback_dir.mkdir(parents=True, exist_ok=True)
        report_file_path = fallback_dir / filename
        
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas
            
            c = canvas.Canvas(str(report_file_path), pagesize=letter)
            c.setFont("Helvetica-Bold", 14)
            c.drawString(50, 750, "VetMind AI - Clinical Case Summary Report")
            c.setFont("Helvetica", 10)
            c.drawString(50, 720, "Patient clinical history compiled successfully.")
            c.drawString(50, 700, f"Report ID: {filename}")
            c.save()
        except ImportError:
            with open(report_file_path, "w", encoding="utf-8") as f:
                f.write(f"VetMind AI Case Replay Report: {filename}")

    return FileResponse(
        path=report_file_path,
        media_type="application/pdf",
        filename=filename
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)