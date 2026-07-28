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
        """Strips unicode characters that trigger missing-glyph black boxes in Helvetica."""
        # 1. Strip raw code blocks, Base64 strings, and download link noise
        text = re.sub(r'```(?:text|bash)?[\s\S]*?```', '', text)
        text = re.sub(r'\[.*?\]\(data:application/pdf;base64,[\s\S]*?\)', '', text)
        text = re.sub(r'JVBERi0x[\s\S]*', '', text)
        text = re.sub(r'A PDF version of this report[\s\S]*', '', text, flags=re.IGNORECASE)

        # 2. Fix ReportLab paraparser <br> syntax errors
        text = re.sub(r'<br\s*/?>', '<br/>', text, flags=re.IGNORECASE)

        # 3. Comprehensive dictionary replacement for bad Unicode characters
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
            "\u25a0": "-",
            "■": "-",
            "•": "-",
            "≥": ">=",
            "≤": "<=",
            "±": "+/-",
            "~": "-",
            "α": "alpha",
            "β": "beta",
            "γ": "gamma",
            "μ": "u",
            "|": "",  # Strip stray pipes outside tables
        }
        for bad_char, clean_char in replacements.items():
            text = text.replace(bad_char, clean_char)

        # 4. Remove any remaining non-ASCII characters to guarantee clean Helvetica rendering
        text = re.sub(r'[^\x00-\x7F]+', '', text)
            
        return text.strip()

    def convert_to_pdf(self, report_text: str, filename: str = "case_summary.pdf") -> str:
        pdf_path = os.path.join(self.output_dir, filename)
        
        # Initialize Document Template with precise 0.5-inch margins
        doc = SimpleDocTemplate(
            pdf_path, 
            pagesize=letter, 
            rightMargin=36, 
            leftMargin=36, 
            topMargin=36, 
            bottomMargin=36,
            title="VetMind AI Report",
            author="VetMind AI"
        )
        
        styles = getSampleStyleSheet()
        
        # Brand Colors
        PRIMARY_GREEN = colors.HexColor("#059669")
        HEADER_GREEN = colors.HexColor("#10B981")
        TEXT_DARK = colors.HexColor("#1F2937")
        BORDER_GRAY = colors.HexColor("#D1D5DB")
        ALT_BG = colors.HexColor("#F9FAFB")
        
        # Paragraph Styles
        title_style = ParagraphStyle(
            'PDFTitle', parent=styles['Heading1'], fontSize=15, leading=19, 
            textColor=PRIMARY_GREEN, spaceAfter=8, fontName='Helvetica-Bold'
        )
        h2_style = ParagraphStyle(
            'PDFH2', parent=styles['Heading2'], fontSize=11, leading=15, 
            textColor=PRIMARY_GREEN, spaceBefore=8, spaceAfter=4, fontName='Helvetica-Bold'
        )
        body_style = ParagraphStyle(
            'PDFBody', parent=styles['Normal'], fontSize=8.5, leading=12, 
            textColor=TEXT_DARK, spaceAfter=3
        )
        bullet_style = ParagraphStyle(
            'PDFBullet', parent=body_style, leftIndent=12, firstLineIndent=-8, spaceAfter=2
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
        
        # Title Banner
        story.append(Paragraph("VetMind AI - Clinical Case Summary Report", title_style))
        story.append(Spacer(1, 4))

        cleaned_text = self._sanitize_utf8_text(report_text)
        lines = cleaned_text.split('\n')
        
        table_buffer = []
        
        def flush_table_buffer(buffer, story_list):
            if not buffer:
                return
            
            table_data = []
            for row_idx, row_str in enumerate(buffer):
                raw_cells = row_str.strip().strip('|').split('|')
                cells = [c.strip() for c in raw_cells]
                if not cells or all(c == "" for c in cells):
                    continue
                
                formatted_row = []
                for cell_text in cells:
                    # Clean markdown tags inside table cells
                    cell_text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', cell_text)
                    cell_text = re.sub(r'<br\s*/?>', '<br/>', cell_text, flags=re.IGNORECASE)
                    cell_text = cell_text.replace("■", "-").replace("•", "-")
                    
                    style = table_header_style if row_idx == 0 else table_cell_style
                    formatted_row.append(Paragraph(cell_text, style))
                
                table_data.append(formatted_row)
            
            if table_data:
                num_cols = max(len(row) for row in table_data)
                total_printable_width = 540
                
                # Column sizing based on column count
                if num_cols == 2:
                    col_widths = [140, 400]
                elif num_cols == 3:
                    col_widths = [110, 210, 220]
                elif num_cols == 4:
                    col_widths = [110, 150, 140, 140]
                elif num_cols == 5:
                    col_widths = [100, 110, 110, 100, 120]
                else:
                    col_widths = [total_printable_width / max(num_cols, 1)] * num_cols
                
                t = Table(table_data, colWidths=col_widths)
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), HEADER_GREEN),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                    ('TOPPADDING', (0, 0), (-1, -1), 4),
                    ('LEFTPADDING', (0, 0), (-1, -1), 5),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                    ('GRID', (0, 0), (-1, -1), 0.5, BORDER_GRAY),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, ALT_BG]),
                ]))
                story_list.append(Spacer(1, 4))
                story_list.append(t)
                story_list.append(Spacer(1, 4))

        for line in lines:
            clean_line = line.strip()
            
            # Detect Markdown tables
            if "|" in clean_line and (clean_line.startswith("|") or clean_line.endswith("|")):
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

            # Strip out download link noise
            if "Downloadable PDF" in clean_line or "data:application/pdf" in clean_line or "base64" in clean_line:
                continue

            # Bold tags
            clean_line = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', clean_line)

            # Headings
            if clean_line.startswith("## ") or clean_line.startswith("### ") or (clean_line.endswith(":") and len(clean_line) < 45 and not clean_line.startswith("-")):
                heading_text = clean_line.replace("#", "").strip()
                story.append(Paragraph(heading_text, h2_style))
            # Bullet points
            elif clean_line.startswith("-") or clean_line.startswith("*") or re.match(r'^\d+\.', clean_line):
                bullet_text = re.sub(r'^[-*\d.]+\s*', '', clean_line).strip()
                story.append(Paragraph(f"- {bullet_text}", bullet_style))
            # Body text
            else:
                story.append(Paragraph(clean_line, body_style))

        if table_buffer:
            flush_table_buffer(table_buffer, story)

        doc.build(story)
        logger.info(f"PDF compiled successfully at: {pdf_path}")
        return pdf_path

