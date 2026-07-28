import os
import sys

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from app.RAG.agents.report_agent import ReportGenerationAgent

sample_report_text = """
## Bella - Feline (Domestic Shorthair) - Comprehensive PDF Report

### 1. Diagnostic Evaluation
| Date | Key Findings | Interpretation |
|---|---|---|
| 2024-06-12 | Weight 4.8 kg, BCS 5/9, mild dental tartar. Serum Creatinine 1.4 mg/dL, BUN 22 mg/dL. | Baseline senior wellness; kidneys within normal limits. |
| 2025-09-04 | Weight 3.9 kg (-18.7%), PU/PD, dull coat. Serum Creatinine 2.8 mg/dL, BUN 45 mg/dL, SDMA 18 ug/dL. Urine USG 1.018, microalbuminuria positive. | IRIS Stage 2 CKD (moderate azotemia) with proteinuria. |
| 2026-02-18 | Weight 4.0 kg (+0.1 kg). Serum Creatinine 2.5 mg/dL. | Slight improvement in renal function; CKD remains Stage 2. |

### 2. Treatment & Pharmaceutical Protocol
| Intervention | Start Date | Dose / Frequency | Rationale |
|---|---|---|---|
| Prescription Renal Diet | 2025-09-04 | Canned 1-1.5 cans/day | Reduces phosphorus load, supports renal function. |
| Telmisartan | 2025-09-04 | 1 mg/kg PO q24h | Decreases intraglomerular pressure, mitigates proteinuria. |
| Sub-Q Lactated Ringer's (LRS) | 2026-02-18 | 100 mL BID weekly | Supplemental hydration, improves renal perfusion. |

### 3. Monitoring & Case Management
- Body Weight: Re-check every 2-4 weeks. Target: >= 4.0 kg.
- Serum Creatinine & SDMA: Every 3 months. Target: Creatinine < 3.0 mg/dL.
- Blood Pressure: Every 6 months. Target: Systolic < 150 mmHg.
"""

def test_report_compilation():
    print("?? Initializing ReportGenerationAgent...")
    agent = ReportGenerationAgent()
    output_filename = "test_bella_report_final.pdf"
    print(f"?? Compiling sample report to PDF ({output_filename})...")
    
    pdf_path = agent.convert_to_pdf(sample_report_text, filename=output_filename)
    
    if os.path.exists(pdf_path):
        print(f"? SUCCESS! PDF compiled at: {pdf_path}")
    else:
        print("? FAILED! PDF file was not created.")

if __name__ == "__main__":
    test_report_compilation()
