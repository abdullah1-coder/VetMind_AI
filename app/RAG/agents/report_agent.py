# app/RAG/agents/report_agent.py

import os
import re
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

from app.services.logging_config import logger


class ReportGenerationAgent:
    def __init__(self, groq_api_key: str = None, output_dir: str = None):
        if output_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            output_dir = os.path.join(base_dir, "generated_reports")
            
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def _sanitize_utf8_text(self, text: str) -> str:
        """Removes characters that trigger Helvetica missing-glyph boxes."""
        replacements = {
            "–": "-",
            "—": "-",
            "“": '"',
            "”": '"',
            "‘": "'",
            "’": "'",
            "½": "1/2",
            "¼": "1/4",
            "¾": "3/4",
            "…": "...",
            "\u00a0": " ",
            "\u25a0": "",
        }
        for bad_char, clean_char in replacements.items():
            text = text.replace(bad_char, clean_char)
        return text

    def convert_to_pdf(self, report_text: str, filename: str = "case_summary.pdf") -> str:
        pdf_path = os.path.join(self.output_dir, filename)
        
        # 1. Initialize Document Template
        doc = SimpleDocTemplate(
            pdf_path, 
            pagesize=letter, 
            rightMargin=36, 
            leftMargin=36, 
            topMargin=36, 
            bottomMargin=36,
            title="VetMind AI Report",  # <--- FIXES BROWSER TAB TITLE FROM (anonymous) TO VetMind AI Report
            author="VetMind AI"
        )
        
        styles = getSampleStyleSheet()
        
        # --- APP BUTTON GREEN PALETTE ---
        PRIMARY_GREEN = colors.HexColor("#059669")    # Darker Green for Headings
        HEADER_GREEN = colors.HexColor("#10B981")     # VetMind Button Green for Table Headers
        TEXT_DARK = colors.HexColor("#1F2937")        # Clean Dark Text
        
        # 2. Heading Styles with VetMind Green
        title_style = ParagraphStyle(
            'PDFTitle', parent=styles['Heading1'], fontSize=16, leading=20, 
            textColor=PRIMARY_GREEN, spaceAfter=12, fontName='Helvetica-Bold'
        )
        h2_style = ParagraphStyle(
            'PDFH2', parent=styles['Heading2'], fontSize=12, leading=16, 
            textColor=PRIMARY_GREEN, spaceBefore=10, spaceAfter=4, fontName='Helvetica-Bold'
        )
        body_style = ParagraphStyle(
            'PDFBody', parent=styles['Normal'], fontSize=9, leading=13, 
            textColor=TEXT_DARK, spaceAfter=4
        )
        table_cell_style = ParagraphStyle(
            'TableCell', parent=styles['Normal'], fontSize=8, leading=11, 
            textColor=TEXT_DARK
        )
        table_header_style = ParagraphStyle(
            'TableHeader', parent=styles['Normal'], fontSize=8, leading=11, 
            fontName='Helvetica-Bold', textColor=colors.white
        )

        story = []
        
        # Main Header
        story.append(Paragraph("VetMind AI — Clinical Case Summary Report", title_style))
        story.append(Spacer(1, 8))

        cleaned_text = self._sanitize_utf8_text(report_text)
        lines = cleaned_text.split('\n')
        
        table_buffer = []
        
        def flush_table_buffer(buffer, story_list):
            if not buffer:
                return
            
            table_data = []
            for row_idx, row_str in enumerate(buffer):
                cells = [c.strip() for c in row_str.split('|')[1:-1]]
                if not cells:
                    continue
                formatted_row = []
                for cell_text in cells:
                    cell_text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', cell_text)
                    style = table_header_style if row_idx == 0 else table_cell_style
                    formatted_row.append(Paragraph(cell_text, style))
                table_data.append(formatted_row)
            
            if table_data:
                num_cols = max(len(row) for row in table_data)
                col_width = 540 / max(num_cols, 1)
                
                t = Table(table_data, colWidths=[col_width] * num_cols)
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), HEADER_GREEN),  # Table Header matches App Green
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                    ('TOPPADDING', (0, 0), (-1, -1), 5),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F3F4F6")]),
                ]))
                story_list.append(Spacer(1, 4))
                story_list.append(t)
                story_list.append(Spacer(1, 6))

        for line in lines:
            clean_line = line.strip()
            
            if clean_line.startswith("|") and clean_line.endswith("|"):
                if "---" in clean_line or "|---" in clean_line:
                    continue
                table_buffer.append(clean_line)
                continue
            else:
                if table_buffer:
                    flush_table_buffer(table_buffer, story)
                    table_buffer = []

            if not clean_line or clean_line == "---":
                continue

            clean_line = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', clean_line)

            if clean_line.startswith("## ") or clean_line.startswith("### ") or (clean_line.endswith(":") and len(clean_line) < 40 and not clean_line.startswith("-")):
                heading_text = clean_line.replace("#", "").strip()
                story.append(Paragraph(heading_text, h2_style))
            elif clean_line.startswith("-") or clean_line.startswith("*") or re.match(r'^\d+\.', clean_line):
                bullet_text = re.sub(r'^[-*\d.]+\s*', '', clean_line).strip()
                story.append(Paragraph(f"&bull; {bullet_text}", body_style))
            else:
                story.append(Paragraph(clean_line, body_style))

        if table_buffer:
            flush_table_buffer(table_buffer, story)

        doc.build(story)
        logger.info(f"PDF compiled successfully at: {pdf_path}")
        return pdf_path