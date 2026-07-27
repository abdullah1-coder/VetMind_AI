#%%
from app.services.logging_config import logger

class ClinicalContextAgent:
    def __init__(self, hybrid_retriever_func):
        self.retriever = hybrid_retriever_func
        logger.info("ClinicalContextAgent initialized.")

    def assemble_grounding_context(self, user_query: str) -> str:
        try:
            logger.info(f"Querying retriever: {user_query}")
            
            # Pass user_query positionally so it works with search_query parameter name
            retrieved_chunks = self.retriever(user_query)
            
            if not retrieved_chunks:
                logger.warning("No chunks returned from retriever.")
                return "No verified context found."

            # Safe extraction regardless of whether chunks are strings or LangChain document objects
            context_strings = []
            for doc in retrieved_chunks:
                if hasattr(doc, 'page_content'):
                    context_strings.append(doc.page_content)
                elif isinstance(doc, dict):
                    context_strings.append(doc.get("content", str(doc)))
                else:
                    context_strings.append(str(doc))

            return "\n\n".join(context_strings)
            
        except Exception:
            logger.exception("CRITICAL ERROR in assemble_grounding_context")
            return "An internal system error occurred during context assembly."
# %%
# Create dummy data/retriever function to test
def mock_retriever(query):
    return ["Feline Panleukopenia virus requires a solid primary series...", "MDA declines by 10-12 weeks."]

# Initialize your agent
agent = ClinicalContextAgent(hybrid_retriever_func=mock_retriever)

# Run a test query
context = agent.assemble_grounding_context("Kitten vaccination timeline")
print("\n--- AGENT OUTPUT ---")
print(context)
# %%
