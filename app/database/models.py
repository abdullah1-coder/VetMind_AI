import os
import sys
import enum
from datetime import datetime
from pathlib import Path

# Ensure project root is in Python path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database.database import Base


# ============================================================
# ENUM DEFINITIONS
# ============================================================

class UserRole(str, enum.Enum):
    DOCTOR = "doctor"
    OWNER = "owner"


class AppointmentStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


# ============================================================
# PATIENT EHR & CLINICAL MODELS
# ============================================================

class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)   # e.g. "Bella"
    species = Column(String(50), default="Feline")            # e.g. "Cat / Feline"
    breed = Column(String(100), nullable=True)               # e.g. "Domestic Shorthair"
    age = Column(String(20), nullable=True)                  # e.g. "4 years"
    owner_name = Column(String(100), nullable=True)
    
    # User isolation
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    doctor = relationship("User", foreign_keys=[doctor_id])
    owner = relationship("User", foreign_keys=[owner_id])
    records = relationship("ClinicalRecord", back_populates="patient", cascade="all, delete-orphan")
    visits = relationship("ClinicalVisit", back_populates="patient", cascade="all, delete-orphan")
    reports = relationship("GeneratedReport", back_populates="patient", cascade="all, delete-orphan")
    chats = relationship("ChatMessage", back_populates="patient", cascade="all, delete-orphan")


class ClinicalVisit(Base):
    """Dedicated table for storing doctor-patient consultation sessions."""
    __tablename__ = "clinical_visits"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    appointment_id = Column(Integer, ForeignKey("appointments.id"), nullable=True)

    visit_date = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    primary_complaint = Column(Text, nullable=False)          # e.g. "Polyuria and polydipsia for 2 weeks"
    clinical_findings = Column(Text, nullable=False)          # e.g. "Dull coat, mild dehydration, soft bladder"
    diagnosis = Column(String(255), nullable=True)            # e.g. "IRIS Stage 2 Chronic Kidney Disease"
    treatment_plan = Column(Text, nullable=False)             # e.g. "Telmisartan 1mg/kg q24h, Renal Diet"
    
    # Vitals & Metrics
    weight_kg = Column(Float, nullable=True)                  # e.g. 4.0
    pruritus_score = Column(Integer, nullable=True)           # e.g. 1-10 scale for dermatology cases
    follow_up_date = Column(String(50), nullable=True)        # e.g. "2026-08-15"
    
    notes = Column(Text, nullable=True)                       # Internal doctor notes
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    patient = relationship("Patient", back_populates="visits")
    doctor = relationship("User", foreign_keys=[doctor_id])
    appointment = relationship("Appointment")


class ClinicalRecord(Base):
    __tablename__ = "clinical_records"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    title = Column(String(255), nullable=True)               # e.g. "Blood Panel OCR Extraction"
    content = Column(Text, nullable=False)                   # Markdown extracted from OCR engine
    source_file = Column(String(255), nullable=True)          # e.g. "bella_lab_results.pdf"
    created_at = Column(DateTime, default=datetime.utcnow)

    patient = relationship("Patient", back_populates="records")


class GeneratedReport(Base):
    __tablename__ = "generated_reports"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    report_title = Column(String(255), default="Case Replay Summary")
    pdf_path = Column(String(500), nullable=False)            # e.g. "app/RAG/generated_reports/case_summary_replay.pdf"
    created_at = Column(DateTime, default=datetime.utcnow)

    patient = relationship("Patient", back_populates="reports")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=True)
    session_id = Column(String(100), index=True, nullable=True)  # Essential for multi-turn conversation memory
    role = Column(String(20), nullable=False)                # "user" or "assistant"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    patient = relationship("Patient", back_populates="chats")


# ============================================================
# USER AUTHENTICATION & APPOINTMENT MODELS
# ============================================================

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=True)       # Null if logged in via Google OAuth
    full_name = Column(String(255), nullable=False)
    role = Column(String(50), default=UserRole.OWNER.value)  # "doctor" or "owner"
    google_id = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    appointments = relationship("Appointment", back_populates="user", cascade="all, delete-orphan")


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Links to User if logged in
    owner_name = Column(String(255), nullable=False)
    pet_name = Column(String(255), nullable=False)
    species = Column(String(50), nullable=False)
    reason = Column(Text, nullable=False)
    appointment_date = Column(String(50), nullable=False)   # e.g. "2026-08-01"
    appointment_time = Column(String(50), nullable=False)   # e.g. "10:30 AM"
    status = Column(String(50), default=AppointmentStatus.PENDING.value)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="appointments")