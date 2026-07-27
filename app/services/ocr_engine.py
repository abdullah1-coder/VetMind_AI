#%%
# app/services/ocr_engine.py
import os
import sys
import base64
from pathlib import Path

# Anchor project root (C:\VetMind AI) into sys.path for interactive cell execution
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import pymupdf4llm
from groq import Groq
from app.config import settings
from app.services.logging_config import logger

def encode_image(image_path: str) -> str:
    """Encodes an image file into base64 format for vision model ingestion."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


def process_ocr_file(file_path: str) -> str:
    """
    Core OCR engine:
    - Uses PyMuPDF4LLM for PDFs to preserve layout & structural markdown.
    - Uses Groq Llama Scout for image/scanned document vision extraction.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Target file not found at path: {file_path}")

    ext = path.suffix.lower()

    # Route 1: Native PDF markdown extraction
    if ext == ".pdf":
        return pymupdf4llm.to_markdown(str(path))

    # Route 2: Image / Vision OCR via Groq Llama Scout
    api_key = settings.groq_api_key or os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY is required for image OCR extraction.")

    client = Groq(api_key=api_key)

    if ext in [".png", ".jpg", ".jpeg", ".webp"]:
        base64_image = encode_image(str(path))
        mime_type = f"image/{ext.replace('.', '')}"
        if ext == ".jpg":
            mime_type = "image/jpeg"

        response = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Extract all veterinary clinical text, lab values, dates, and medical notes from this image into structured markdown."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            temperature=0.1
        )
        return response.choices[0].message.content

    # Route 3: Plain text file fallback
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


if __name__ == "__main__":
    test_image = r"C:\VetMind AI\data\Abdullah_Bin_Shahbaz_Resume.pdf"
    if Path(test_image).exists():
        result = process_ocr_file(test_image)
        print("OCR Result:\n", result)
    else:
        print("Test file path does not exist.")



# %%
