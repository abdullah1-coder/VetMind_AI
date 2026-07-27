#%%
import sys
from pathlib import Path

# Ensure ROOT_DIR is in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.database.database import engine, Base
from app.database.models import Patient, ClinicalRecord, GeneratedReport, ChatMessage

def init_database():
    print("Creating database tables in vetmind_records.db if they don't exist...")
    Base.metadata.create_all(bind=engine)
    print("Database tables initialized successfully!")

if __name__ == "__main__":
    init_database()
# %%
