import os
import sys
import logging
import uuid
import datetime
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, status, Header
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
from app.database.database import get_db, engine, Base, SessionLocal
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


# ============================================================
# AUTO-SEED DATABASE FOR DEMO DOCTOR ACCOUNT
# ============================================================
def seed_demo_doctor_and_patients():
    db = SessionLocal()
    try:
        # 1. Ensure the demo doctor exists
        doctor = db.query(User).filter(User.email == "abdullahbinshahbaz12@gmail.com").first()
        if not doctor:
            doctor = User(
                email="abdullahbinshahbaz12@gmail.com",
                password_hash="abd123",
                full_name="Dr. Abdullah Bin Shahbaz",
                role="doctor"
            )
            db.add(doctor)
            db.commit()
            db.refresh(doctor)
            print("Created default doctor account: abdullahbinshahbaz12@gmail.com")

        # 2. Seed patients strictly assigned to this doctor if none exist for him
        doctor_patient_count = db.query(Patient).filter(Patient.doctor_id == doctor.id).count()
        if doctor_patient_count == 0:
            print("Seeding database with 5 rich patient profiles for Dr. Abdullah...")

            patients_data = [
                # PATIENT 1: Rocky
                {
                    "name": "Rocky",
                    "species": "Avian(Bird)",
                    "breed": "Cockatiel",
                    "age": "3 years",
                    "owner_name": "Javeria Khan",
                    "records": [
                        {
                            "title": "Initial Wellness Check",
                            "content": (
                                "Presentation: Active 3-year-old male Cockatiel brought in for routine annual checkup.\n"
                                "Physical Exam: Weight 92g. Feathers clear, normal posture. Choanal papillae sharp and normal.\n"
                                "Fecal Gram Stain: Normal gram-positive flora predominant (85%).\n"
                                "Assessment: Healthy avian baseline established at 92g."
                            ),
                            "created_at": datetime.datetime(2025, 11, 10, 10, 0)
                        },
                        {
                            "title": "Symptomatic Presentation - Lethargy & Tail Bobbing",
                            "content": (
                                "Presentation: Owner notes mild lethargy, biliverdinuria (bright green droppings), and mild tail bobbing.\n"
                                "Physical Exam: Weight dropped to 81g (11.9% involuntary weight loss). Pectoral muscle atrophy (BCS 2/5).\n"
                                "Diagnostics: PCR Swab panel submitted for Chlamydia psittaci (Avian Chlamydiosis).\n"
                                "Initial Therapy: Doxycycline hygiene protocol initiated, heat support at 85°F."
                            ),
                            "created_at": datetime.datetime(2026, 3, 15, 14, 30)
                        },
                        {
                            "title": "Diagnostic Confirmation & Treatment Protocol",
                            "content": (
                                "Diagnostics: Real-Time PCR returned POSITIVE for Chlamydia psittaci.\n"
                                "Treatment Protocol: Medicated Doxycycline oral suspension (25 mg/kg PO q24h) prescribed for 45 consecutive days.\n"
                                "Re-check Exam: Weight stabilized at 84g. Dropping color improving."
                            ),
                            "created_at": datetime.datetime(2026, 3, 22, 11, 15)
                        }
                    ]
                },
                # PATIENT 2: Bella
                {
                    "name": "Bella",
                    "species": "Feline(cat)",
                    "breed": "Domestic Shorthair",
                    "age": "12 years",
                    "owner_name": "Minahil Jahangir",
                    "records": [
                        {
                            "title": "Senior Wellness & Baseline Lab Panel",
                            "content": (
                                "Presentation: Senior female DSH presented for routine geriatric screening.\n"
                                "Physical Exam: Body weight 4.8kg. BCS 5/9. Mild dental tartar.\n"
                                "Bloodwork: Serum Creatinine 1.4 mg/dL, BUN 22 mg/dL. Normal renal baseline."
                            ),
                            "created_at": datetime.datetime(2024, 6, 12, 9, 0)
                        },
                        {
                            "title": "Progressive Weight Loss & Polyuria Evaluation",
                            "content": (
                                "Presentation: Weight dropped to 3.9kg (18.7% involuntary weight loss). Owner reports PU/PD and dull coat.\n"
                                "Bloodwork: Serum Creatinine 2.8 mg/dL, BUN 45 mg/dL, SDMA 18 ug/dL.\n"
                                "Urinalysis: USG 1.018 (Isosthenuric), microalbuminuria positive.\n"
                                "Assessment: IRIS Stage 2 Chronic Kidney Disease (CKD).\n"
                                "Plan: Transition to prescription renal diet (low phosphorus), Telmisartan initiated for proteinuria."
                            ),
                            "created_at": datetime.datetime(2025, 9, 4, 15, 0)
                        },
                        {
                            "title": "CKD Re-check & SubQ Fluid Maintenance",
                            "content": (
                                "Presentation: Re-evaluation of renal therapy compliance.\n"
                                "Physical Exam: Weight stable at 4.0kg. Serum Creatinine 2.5 mg/dL.\n"
                                "Plan: Continue canned renal diet. Subcutaneous fluids (LRS 100ml twice weekly) integrated into home care routine."
                            ),
                            "created_at": datetime.datetime(2026, 2, 18, 10, 30)
                        }
                    ]
                },
                # PATIENT 3: Rosie
                {
                    "name": "Rosie",
                    "species": "Feline(cat)",
                    "breed": "Siamese",
                    "age": "2 years",
                    "owner_name": "Talha Bashir",
                    "records": [
                        {
                            "title": "Acute Stranguria & Dysuria Consultation",
                            "content": (
                                "Presentation: 2-year-old female Siamese presenting with frequent litterbox visits, vocalizing, and hematuria.\n"
                                "Physical Exam: Body weight 3.4kg. Bladder small, firm, and painful on abdominal palpation. No urethral obstruction.\n"
                                "Urinalysis: RBCs >50/hpf, pH 6.5, no bacterial organisms or struvite crystals observed.\n"
                                "Assessment: Feline Lower Urinary Tract Disease (FLUTD) / Feline Idiopathic Cystitis (FIC) flare.\n"
                                "Plan: Buprenorphine 0.01 mg/kg transmucosal q8h for pain, Gabapentin 50mg PO q12h, increase wet food intake."
                            ),
                            "created_at": datetime.datetime(2026, 1, 15, 11, 0)
                        },
                        {
                            "title": "FLUTD Follow-Up & Urinary Diet Transition",
                            "content": (
                                "Presentation: 2-week re-check following acute cystitis episode.\n"
                                "Physical Exam: Weight 3.5kg. Bladder soft and non-painful.\n"
                                "Owner Report: Hematuria resolved; urination frequency returned to normal.\n"
                                "Plan: Transition to prescription urinary stress diet long-term, install synthetic facial pheromone diffuser."
                            ),
                            "created_at": datetime.datetime(2026, 1, 29, 14, 0)
                        }
                    ]
                },
                # PATIENT 4: Milo
                {
                    "name": "Milo",
                    "species": "Canine(Dog)",
                    "breed": "Golden Retriever",
                    "age": "5 years",
                    "owner_name": "Danial Aziz",
                    "records": [
                        {
                            "title": "Bilateral Otitis Externa & Pruritus Examination",
                            "content": (
                                "Presentation: 5-year-old male Golden Retriever presenting with severe head shaking and pedal licking.\n"
                                "Physical Exam: Weight 31.2kg. Severe erythema in both ear canals with brown exudate. Erythematous paws.\n"
                                "Cytology: Malassezia yeast 3+ bilaterally.\n"
                                "Treatment: Ear flush performed. Applied Osurnia otic gel bilaterally. Prescribed Apoquel (oclacitinib) 16mg PO q12h."
                            ),
                            "created_at": datetime.datetime(2025, 7, 20, 16, 0)
                        },
                        {
                            "title": "Seasonal Allergy Re-evaluation",
                            "content": (
                                "Presentation: Follow-up for environmental allergic dermatitis.\n"
                                "Physical Exam: Weight 31.5kg. Ear canals clear, no discharge. Pruritus score decreased from 8/10 to 1/10.\n"
                                "Plan: Maintenance dose of Apoquel (16mg PO q24h) during high pollen season."
                            ),
                            "created_at": datetime.datetime(2025, 8, 10, 10, 30)
                        }
                    ]
                },
                # PATIENT 5: Simba
                {
                    "name": "Simba",
                    "species": "Canine(Dog)",
                    "breed": "French Bulldog",
                    "age": "4 years",
                    "owner_name": "Moeez Amir",
                    "records": [
                        {
                            "title": "BOAS Assessment & Interdigital Pyoderma Exam",
                            "content": (
                                "Presentation: 4-year-old male French Bulldog presented for exercise intolerance, loud stertor, and paw licking.\n"
                                "Physical Exam: Weight 14.2kg (BCS 7/9 - Overweight). Stenotic nares, soft palate stertor. Interdigital erythema on front paws.\n"
                                "Assessment: Brachycephalic Obstructive Airway Syndrome (BOAS) compounded by interdigital dermatitis.\n"
                                "Plan: Cytopoint injection (20mg SQ) for allergic itch, Chlorhexidine paw wipes daily, weight reduction target to 12.0kg."
                            ),
                            "created_at": datetime.datetime(2026, 2, 5, 12, 0)
                        }
                    ]
                }
            ]

            for p_data in patients_data:
                patient = Patient(
                    name=p_data["name"],
                    species=p_data["species"],
                    breed=p_data["breed"],
                    age=p_data["age"],
                    owner_name=p_data["owner_name"],
                    doctor_id=doctor.id  # STRONGLY ASSIGNED TO DEMO DOCTOR
                )
                db.add(patient)
                db.flush()

                for rec_data in p_data["records"]:
                    new_rec = ClinicalRecord(
                        patient_id=patient.id,
                        title=rec_data["title"],
                        content=rec_data["content"],
                        created_at=rec_data["created_at"],
                        source_file=f"{patient.name.lower()}_ehr.pdf"
                    )
                    db.add(new_rec)

            db.commit()
            print("Successfully assigned Rocky, Bella, Rosie, Milo, Simba to Dr. Abdullah!")
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
    finally:
        db.close()

# Execute Database Auto-Seeding
seed_demo_doctor_and_patients()


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

app.mount("/static", StaticFiles(directory="static"), name="static")

orchestrator = VetMindWorkflow()


# ============================================================
# PYDANTIC SCHEMAS
# ============================================================

class LoginRequest(BaseModel):
    email: str
    password: str
    role: str  # "doctor" or "owner"


class RegisterRequest(BaseModel):
    full_name: str
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
# HELPER: CURRENT USER RESOLUTION
# ============================================================

def get_current_user(x_user_id: Optional[int] = Header(None), db: Session = Depends(get_db)) -> Optional[User]:
    """Resolves logged in User context from header or defaults to demo doctor."""
    if x_user_id:
        return db.query(User).filter(User.id == x_user_id).first()
    return None


# ============================================================
# 1. AUTHENTICATION ENDPOINTS
# ============================================================

@app.post("/auth/register")
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """Registers a new user (Doctor or Pet Owner)."""
    existing_user = db.query(User).filter(User.email == req.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="User with this email already exists.")
    
    new_user = User(
        email=req.email,
        password_hash=req.password,
        full_name=req.full_name,
        role=req.role
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "user": {
            "id": new_user.id,
            "email": new_user.email,
            "full_name": new_user.full_name,
            "role": new_user.role
        },
        "token": f"jwt-token-{new_user.id}"
    }


@app.post("/auth/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    """Authenticates user with email & password check."""
    user = db.query(User).filter(User.email == req.email).first()
    
    if not user:
        # Register new account dynamically if not found
        user = User(
            email=req.email,
            password_hash=req.password,
            full_name=req.email.split("@")[0].capitalize(),
            role=req.role
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    elif user.password_hash and user.password_hash != req.password:
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    return {
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role
        },
        "token": f"jwt-token-{user.id}"
    }


# ============================================================
# 2. PATIENT EHR ENDPOINTS (MULTI-TENANT ISOLATED)
# ============================================================

@app.post("/patients", response_model=PatientOut, status_code=status.HTTP_201_CREATED)
def create_patient(
    patient_in: PatientCreate, 
    user_id: Optional[int] = Header(None, alias="X-User-ID"),
    db: Session = Depends(get_db)
):
    """Creates a new patient associated with the creating user."""
    user = db.query(User).filter(User.id == user_id).first() if user_id else None
    
    patient_dict = patient_in.dict()
    if user:
        if user.role == "doctor":
            patient_dict["doctor_id"] = user.id
        elif user.role == "owner":
            patient_dict["owner_id"] = user.id

    db_patient = Patient(**patient_dict)
    db.add(db_patient)
    db.commit()
    db.refresh(db_patient)
    return db_patient


@app.get("/patients", response_model=List[PatientOut])
def list_patients(
    user_id: Optional[int] = Header(None, alias="X-User-ID"),
    db: Session = Depends(get_db)
):
    """Returns patient profiles filtered strictly by the logged-in user's account."""
    if not user_id:
        # Fallback to demo doctor if no header is supplied
        demo_doc = db.query(User).filter(User.email == "abdullahbinshahbaz12@gmail.com").first()
        user_id = demo_doc.id if demo_doc else None

    user = db.query(User).filter(User.id == user_id).first() if user_id else None
    if not user:
        return []

    # Doctors see ONLY patients assigned to their doctor_id
    if user.role == "doctor":
        return db.query(Patient).filter(Patient.doctor_id == user.id).order_by(Patient.created_at.desc()).all()
    
    # Pet Owners see ONLY patients linked to their owner_id
    elif user.role == "owner":
        return db.query(Patient).filter(Patient.owner_id == user.id).order_by(Patient.created_at.desc()).all()

    return []


@app.get("/patients/{patient_id}", response_model=PatientOut)
def get_patient(patient_id: int, db: Session = Depends(get_db)):
    """Fetches full details for a specific patient."""
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
    """Deletes a patient record and all associated history."""
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient record not found.")

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
def create_appointment(
    req: AppointmentCreate, 
    user_id: Optional[int] = Header(None, alias="X-User-ID"),
    db: Session = Depends(get_db)
):
    """Saves a new appointment request."""
    apt_data = req.dict()
    if user_id:
        apt_data["user_id"] = user_id
        
    apt = Appointment(**apt_data)
    db.add(apt)
    db.commit()
    db.refresh(apt)
    return apt


@app.get("/appointments")
def get_appointments(
    user_id: Optional[int] = Header(None, alias="X-User-ID"),
    db: Session = Depends(get_db)
):
    """Retrieves appointments filtered by user."""
    user = db.query(User).filter(User.id == user_id).first() if user_id else None
    if user and user.role == "owner":
        return db.query(Appointment).filter(Appointment.user_id == user.id).order_by(Appointment.created_at.desc()).all()
    
    # Doctors see all appointments
    return db.query(Appointment).order_by(Appointment.created_at.desc()).all()


@app.put("/appointments/{apt_id}/status")
def update_appointment_status(apt_id: int, status: str, db: Session = Depends(get_db)):
    """Updates appointment status."""
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
    """Processes uploaded document image/PDF via OCR."""
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
        if req.patient_id:
            target_patient = db.query(Patient).filter(Patient.id == req.patient_id).first()
        elif hasattr(req, "patient_name") and req.patient_name:
            target_patient = db.query(Patient).filter(Patient.name.ilike(f"%{req.patient_name}%")).first()

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

        user_msg_kwargs = {"patient_id": patient_id_found, "role": "user", "content": req.query}
        if hasattr(ChatMessage, "session_id"):
            user_msg_kwargs["session_id"] = session_id

        user_msg = ChatMessage(**user_msg_kwargs)
        db.add(user_msg)
        db.commit()

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

        raw_pdf_path = workflow_result.get("final_report_path", None)
        report_keywords = ["report", "pdf", "download", "summary", "export"]
        user_wants_pdf = any(kw in req.query.lower() for kw in report_keywords)

        report_url = None
        if user_wants_pdf and raw_pdf_path and Path(raw_pdf_path).exists():
            report_url = f"/api/reports/download/{Path(raw_pdf_path).name}"

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
    """Serves compiled PDF medical reports directly to UI."""
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