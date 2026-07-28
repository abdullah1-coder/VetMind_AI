# %%
import os
import sys
import sqlite3
import torch
from dotenv import load_dotenv
import pymupdf4llm
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_community.retrievers import BM25Retriever
from langchain_classic.retrievers import EnsembleRetriever
import nest_asyncio
import logging
from pathlib import Path
from langchain_community.embeddings import FastEmbedEmbeddings
# Resolve project runtime search directory pathways
current_dir = os.path.abspath(os.getcwd())
root_dir = current_dir
logger = logging.getLogger("VetMindAI.RAG")
while os.path.basename(root_dir) != "VetMind AI" and os.path.dirname(root_dir) != root_dir:
    root_dir = os.path.dirname(root_dir)

if os.path.basename(root_dir) == "VetMind AI":
    sys.path.insert(0, root_dir)
else:
    sys.path.insert(0, r"C:\VetMind AI")

# Load environment configuration variables and security modules
load_dotenv()
from app.config import settings

nest_asyncio.apply()

# Configure the root system log formatting for all imported modules/agents to use line numbers
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s.%(funcName)s:%(lineno)d - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

RAW_DATA_DIR = r"C:\VetMind AI\data"
SQLITE_DB_PATH = r"C:\VetMind AI\data\vetmind_records.db"

BASE_DIR = Path(__file__).resolve().parent.parent.parent
VECTOR_DB_DIR = os.getenv("VECTOR_DB_DIR", str(BASE_DIR / "app" / "data" / "vector_store"))

os.makedirs(RAW_DATA_DIR, exist_ok=True)
os.makedirs(VECTOR_DB_DIR, exist_ok=True)

def init_registry():
    """Initializes the persistent tracking database schema for processed documents."""
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS global_reference_registry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT UNIQUE,
            total_pages INTEGER,
            ingestion_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_registry()
print("System registry connection established.")

# %% Agent Pipeline Instantiations
# Import your verified standalone agents safely
from agents.context_agent import ClinicalContextAgent
from agents.generation_agent import ClinicalGenerationAgent

# Initialize the modular Generation Agent with the operational production model
generation_agent = ClinicalGenerationAgent(
    api_key=os.getenv("GROQ_API_KEY"),
    model="openai/gpt-oss-120b"
)

# %% PDF Processing Functions
def extract_pdf_pages(file_path: str):
    """
    Parses and streams markdown schema nodes from a target PDF page-by-page.
    Yields: tuple (page_number, total_pages, text_content)
    """
    filename = os.path.basename(file_path)
    file_extension = os.path.splitext(filename)[1].lower()
    
    if file_extension != ".pdf":
        raise ValueError(f"Invalid file extension context: {file_extension}")

    page_data = pymupdf4llm.to_markdown(file_path, page_chunks=True)
    
    for page_index, page_dict in enumerate(page_data):
        page_text = page_dict.get("text", "")
        metadata = page_dict.get("metadata", {})
        
        page_num = metadata.get("page_number", page_index + 1)
        total_pages = metadata.get("page_count", 0)
        
        yield page_num, total_pages, page_text

def configure_text_splitter() -> RecursiveCharacterTextSplitter:
    """Configures structural text boundaries optimized for clinical reference material."""
    return RecursiveCharacterTextSplitter(
        chunk_size=700,
        chunk_overlap=100,
        length_function=len,
        is_separator_regex=False
    )

# %% Engine Core Hybrid Retriever
# %% Engine Core Hybrid Retriever
os.environ["HF_HUB_OFFLINE"] = "0"  # Allow initial download on Railway if needed

device_target = "cuda" if torch.cuda.is_available() else "cpu"

logger.info("Initializing high-speed ONNX FastEmbed engine...")
GLOBAL_EMBEDDINGS = FastEmbedEmbeddings(model_name="BAAI/bge-small-en-v1.5")

logger.info(f"Connecting to persistent Chroma Vector Store at: {VECTOR_DB_DIR}")
GLOBAL_VECTOR_DB = Chroma(
    persist_directory=VECTOR_DB_DIR,
    embedding_function=GLOBAL_EMBEDDINGS
)

def ensure_vector_store_populated():
    """Checks if vector store is populated; auto-ingests reference data if empty."""
    try:
        # Check if vector DB contains any collections or documents
        existing_count = GLOBAL_VECTOR_DB._collection.count()
        if existing_count > 0:
            logger.info(f"Vector database verified with {existing_count} existing chunks.")
            return
        
        logger.info("Empty vector store detected. Initiating automated document ingestion...")
        
        # Check for raw PDF documents in data directories
        pdf_sources = []
        for search_path in [RAW_DATA_DIR, str(BASE_DIR / "data"), str(BASE_DIR / "app" / "RAG" / "data")]:
            if os.path.exists(search_path):
                for f in os.listdir(search_path):
                    if f.lower().endswith(".pdf"):
                        pdf_sources.append(os.path.join(search_path, f))

        if not pdf_sources:
            logger.warning("No PDF reference files found to auto-ingest.")
            return

        splitter = configure_text_splitter()
        documents_to_add = []

        for pdf_path in pdf_sources:
            logger.info(f"Ingesting reference document: {os.path.basename(pdf_path)}")
            try:
                for page_num, total_pages, page_text in extract_pdf_pages(pdf_path):
                    if not page_text.strip():
                        continue
                    
                    chunks = splitter.split_text(page_text)
                    for chunk in chunks:
                        documents_to_add.append({
                            "text": chunk,
                            "metadata": {
                                "source_document": os.path.basename(pdf_path),
                                "page": page_num
                            }
                        })
            except Exception as e:
                logger.error(f"Error reading {pdf_path}: {e}")

        if documents_to_add:
            texts = [d["text"] for d in documents_to_add]
            metadatas = [d["metadata"] for d in documents_to_add]
            
            # Batch add documents to Chroma
            GLOBAL_VECTOR_DB.add_texts(texts=texts, metadatas=metadatas)
            logger.info(f"Successfully ingested {len(texts)} chunks into ChromaDB.")

    except Exception as e:
        logger.error(f"Vector store auto-population check failed: {e}")

# Run check on module load
ensure_vector_store_populated()


def get_hybrid_retriever(search_query: str = None, k: int = 4, **kwargs):
    if search_query is None:
        search_query = kwargs.get("query", "")

    search_query = search_query.strip()
    if not search_query:
        return []

    # 1. Fetch top 5 vector candidates using ONNX fast embeddings
    try:
        candidates = GLOBAL_VECTOR_DB.similarity_search(search_query, k=5)
    except Exception as e:
        logger.error(f"ChromaDB lookup error: {e}")
        candidates = []

    if not candidates:
        return []

    # 2. In-memory BM25 reranking on top 5 candidates
    try:
        bm25_retriever = BM25Retriever.from_documents(candidates)
        bm25_retriever.k = min(k, len(candidates))

        vector_retriever = GLOBAL_VECTOR_DB.as_retriever(search_kwargs={"k": k})

        ensemble_retriever = EnsembleRetriever(
            retrievers=[vector_retriever, bm25_retriever],
            weights=[0.6, 0.4]
        )

        return ensemble_retriever.invoke(search_query)
    except Exception as e:
        logger.error(f"Error executing ensemble retrieval: {e}")
        return candidates[:k]
# %% Standalone Script Execution Verification Block
if __name__ == "__main__":
    test_query = "What is the recommended feline parvovirus vaccination schedule?"
    print(f"\nExecuting hybrid semantic query lookup: '{test_query}'...")
    
    try:
        results = get_hybrid_retriever(test_query, k=3)
        print("\n--- Hybrid Retrieval Results ---")
        for idx, doc in enumerate(results, 1):
            source = doc.metadata.get('source_document', 'Unknown')
            page = doc.metadata.get('page', 'Unknown')
            print(f"\n[Match {idx}] Source: {source} (Page {page})")
            print(f"Content: {doc.page_content[:200]}...")
            print("-" * 50)
            
        # Hook up the operationalized context agent to confirm end-to-end functionality
        context_agent = ClinicalContextAgent(get_hybrid_retriever)
        assembled_context = context_agent.assemble_grounding_context(test_query)
        
        print("\nExecuting standalone Generation Agent tracking test via Groq...")
        final_report = generation_agent.execute_grounded_generation(
            user_query=test_query,
            structured_context=assembled_context
        )
        print("\n" + "="*20 + " END-TO-END PIPELINE REPORT " + "="*20)
        print(final_report)
        print("="*68 + "\n")
        
    except Exception as e:
        print(f"Pipeline runtime execution failed: {str(e)}")
# %%
