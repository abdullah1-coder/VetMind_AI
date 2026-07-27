import sys
import os
import datetime

# Ensure project root is in Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.database.database import SessionLocal, engine, Base
from app.database.models import Patient, ClinicalRecord

def seed_all_demo_patients():
    # 1. Ensure all database tables exist
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        print("Clearing old patient records...")
        # Delete existing records to wipe old patient profiles clean
        db.query(ClinicalRecord).delete()
        db.query(Patient).delete()
        db.commit()

        print("Seeding database with updated patient data...")

        patients_data = [
            # -------------------------------------------------------------
            # PATIENT 1: Rocky (Cockatiel / Avian Chlamydiosis)
            # -------------------------------------------------------------
            {
                "name": "Rocky",
                "species": "Avian",
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
            # -------------------------------------------------------------
            # PATIENT 2: Bella (Cat / Chronic Kidney Disease)
            # -------------------------------------------------------------
            {
                "name": "Bella",
                "species": "Feline",
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
            # -------------------------------------------------------------
            # PATIENT 3: Rosie (Cat / Feline Idiopathic Cystitis)
            # -------------------------------------------------------------
            {
                "name": "Rosie",
                "species": "Feline",
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
            # -------------------------------------------------------------
            # PATIENT 4: Milo (Dog / Canine Atopic Dermatitis)
            # -------------------------------------------------------------
            {
                "name": "Milo",
                "species": "Canine",
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
            # -------------------------------------------------------------
            # PATIENT 5: Simba (Dog / BOAS & Weight Management)
            # -------------------------------------------------------------
            {
                "name": "Simba",
                "species": "Canine",
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
            # Add Patient row
            patient = Patient(
                name=p_data["name"],
                species=p_data["species"],
                breed=p_data["breed"],
                age=p_data["age"],
                owner_name=p_data["owner_name"]
            )
            db.add(patient)
            db.flush()  # Populates patient.id

            # Add associated Clinical Records
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
        print("Database successfully wiped and re-seeded with updated patients (Rocky, Bella, Rosie, Milo, Simba)!")

    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_all_demo_patients()