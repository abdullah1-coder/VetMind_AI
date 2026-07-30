# 🐾 VetMind AI — Agentic RAG, Guardrails & Intelligent EHR System

[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18.0-61DAFB?style=flat&logo=react)](https://react.dev/)
[![TailwindCSS](https://img.shields.io/badge/TailwindCSS-3.0-38B2AC?style=flat&logo=tailwindcss)](https://tailwindcss.com/)
[![SQLite/PostgreSQL](https://img.shields.io/badge/Database-SQLite%2FPostgreSQL-4479A1?style=flat&logo=postgresql)](https://www.postgresql.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**VetMind AI** is a state-of-the-art clinical intelligence and electronic health record (EHR) platform built for veterinary practices and pet owners. Powered by an **Agentic RAG (Retrieval-Augmented Generation)** pipeline, safety guardrails, OCR file ingestion, and multi-tenant isolation, VetMind AI allows clinical doctors to query rich patient histories, log structured consultation sessions, and generate instant medical summary reports.

---

## 🌟 Key Features

### 🩺 1. Veterinary Clinical Workspace (Doctor & Owner Portals)
- **Multi-Tenant Isolation:** Role-based access control (RBAC) separating Veterinary Doctors from Pet Owners using custom `X-User-ID` context headers.
- **Dynamic Patient Selector:** Instant access to patient EHR histories, species/breed details, and longitudinal clinical notes.
- **Appointment Booking Engine:** Allows pet owners to request visits and enables doctors to confirm or decline appointments in real time.

### 📝 2. Clinical Visit Session Logger
- **Structured Consultation Entry:** Log vital parameters including primary complaint, physical exam findings, weight (kg), diagnosis, treatment plan, pruritus itch scores (1–10), and follow-up dates.
- **Automated RAG Synchronization:** Submitting a doctor visit session automatically summarizes the encounter into searchable clinical notes, keeping the AI assistant instantly up to date.

### 📄 3. Multimodal OCR Document Ingestion
- **Automated Document Extraction:** Supports PDF and Word (`.docx`) file uploads containing clinical lab reports, bloodwork panels, and handwritten notes.
- **Collapsible Inspection View:** Clean Markdown rendering in the UI with accordion drawers to inspect raw extracted OCR text.

### 🤖 4. Agentic RAG & Guardrail Orchestration
- **Longitudinal Memory Retrieval:** Synthesizes multi-turn conversation memory, active patient demographics, and past visit logs to answer complex medical queries.
- **Clinical Safety Guardrails:** Implements query safety evaluation to block out-of-scope or unsafe requests.
- **Automated PDF Case Summaries:** Generates downloadable, structured PDF medical reports on demand whenever requested in chat.

---

## 🏗️ System Architecture
                   +-------------------------------+
                   |   React 18 + Tailwind UI      |
                   | (Axios + Custom Headers)      |
                   +---------------+---------------+
                                   |
                                   v
                   +-------------------------------+
                   |     FastAPI Backend Router    |
                   |  (CORS, Middleware, Auth)     |
                   +---------------+---------------+
                                   |
         +-------------------------+-------------------------+
         |                                                   |
         v                                                   v
     +-------------------------+                         +-------------------------+
     |   SQLite / PostgreSQL   |                         |  VetMind RAG Engine     |
     | (Patients, Records,     |                         | (Agentic Workflow,      |
     |  Visits, Appointments)  |                         |  Guardrails, OCR)       |
     +-------------------------+                         +-------------------------+
---

## 🚀 Tech Stack

- **Backend:** Python 3.10+, FastAPI, SQLAlchemy, Pydantic v2, ReportLab, PyPDF / Python-Docx
- **Frontend:** React 18, Axios, Lucide React Icons, Tailwind CSS, React Markdown, Remark-GFM
- **Deployment:** Railway Cloud Platform (Docker containerized)

---

## 💻 Local Setup & Installation

### Prerequisites
- Python 3.10+
- Node.js 18+ & npm

### 1. Clone Repository
```bash
git clone [https://github.com/your-username/VetMind-AI.git](https://github.com/your-username/VetMind-AI.git)
cd VetMind-AI
```
### 2. Backend Setup (FastAPI)
```
# Create and activate virtual environment
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create environment configuration (.env)
cp .env.example .env
```
### 3. Frontend Setup (React)
```
cd frontend

# Install node modules
npm install

# Start Vite development server
npm run dev
```
## 📜 License
Distributed under the MIT License. See LICENSE for details.
