from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


# --- Clinical Visit Schemas ---
class ClinicalVisitBase(BaseModel):
    primary_complaint: str
    clinical_findings: str
    diagnosis: Optional[str] = None
    treatment_plan: str
    weight_kg: Optional[float] = None
    pruritus_score: Optional[int] = None
    follow_up_date: Optional[str] = None
    notes: Optional[str] = None

class ClinicalVisitCreate(ClinicalVisitBase):
    doctor_id: Optional[int] = None
    appointment_id: Optional[int] = None

class ClinicalVisitOut(ClinicalVisitBase):
    id: int
    patient_id: int
    doctor_id: Optional[int] = None
    appointment_id: Optional[int] = None
    visit_date: datetime
    created_at: datetime

    class Config:
        from_attributes = True


# --- Clinical Record Schemas ---
class ClinicalRecordBase(BaseModel):
    title: Optional[str] = None
    content: str
    source_file: Optional[str] = None

class ClinicalRecordCreate(ClinicalRecordBase):
    patient_id: int

class ClinicalRecordOut(ClinicalRecordBase):
    id: int
    patient_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# --- Patient Schemas ---
class PatientBase(BaseModel):
    name: str
    species: Optional[str] = "Feline"
    breed: Optional[str] = None
    age: Optional[str] = None
    owner_name: Optional[str] = None

class PatientCreate(PatientBase):
    pass

class PatientOut(PatientBase):
    id: int
    created_at: datetime
    records: List[ClinicalRecordOut] = []
    visits: List[ClinicalVisitOut] = []

    class Config:
        from_attributes = True


# --- Chat & Query Schemas ---
class ChatQueryRequest(BaseModel):
    query: str
    patient_id: Optional[int] = None
    patient_name: Optional[str] = None
    session_id: Optional[str] = None

class ChatQueryResponse(BaseModel):
    query: str
    is_safe: bool
    response_text: str
    report_pdf_url: Optional[str] = None
    session_id: Optional[str] = None  
    patient_id: Optional[int] = None