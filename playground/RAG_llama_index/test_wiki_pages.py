import wikipedia
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core import VectorStoreIndex, Settings
from llama_index.core.node_parser import SentenceSplitter
from llama_index.llms.groq import Groq
from llama_index.core import Document
from utils import get_apikey

def load_wiki_content_direct(pages):
    print(f"Loading Wikipedia content directly for: {pages}")
    documents = []
    for page_title in pages:
        try:
            wiki_page = wikipedia.page(page_title, auto_suggest=False, redirect=True)
            content = wiki_page.content
            metadata = {"title": wiki_page.title, "source": "wikipedia"}
            documents.append(Document(text=content, metadata=metadata))
            print(f"Successfully loaded content for '{page_title}'.")
        except wikipedia.exceptions.PageError:
            print(f"Error: Wikipedia page '{page_title}' not found.")
        except wikipedia.exceptions.DisambiguationError as e:
            print(f"Error: '{page_title}' has multiple meanings: {e.options}")
        except Exception as e:
            print(f"An unexpected error occurred while loading '{page_title}': {e}")
    return documents

def create_index_from_docs(documents):
    text_splits = SentenceSplitter(chunk_size=150, chunk_overlap=45)
    nodes = text_splits.get_nodes_from_documents(documents)
    embed_model = HuggingFaceEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")
    Settings.embed_model = embed_model
    index = VectorStoreIndex(nodes, embed_model=embed_model)
    print("Index created from documents.")
    return index

def query_index_simple(index, query):
    llm = Groq(api_key=get_apikey(), model="llama3-8b-8192")
    query_engine = index.as_query_engine(response_mode="compact", verbose=True, similarity_top_k=3, llm=llm)
    print(f"\nQuerying index: '{query}'")
    response = query_engine.query(query)
    return response

if __name__ == "__main__":
    pages_to_index = ["Paris"]
    documents = load_wiki_content_direct(pages_to_index)
    if documents:
        index = create_index_from_docs(documents)
        query = "Where is Paris located?"
        response = query_index_simple(index, query)
        print("\n--- Query Response ---")
        print(response)
    else:
        print("No documents were loaded.")