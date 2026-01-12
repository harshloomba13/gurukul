# llama_rag.py
import os
import time

# ✅ MUST be set before importing anything from trulens / utils
os.environ["TRULENS_OTEL"] = "0"
os.environ["TRULENS_OTEL_TRACING"] = "0"

# Optional but strongly recommended so dashboard + script point to same DB file
# (use an absolute path if you want zero ambiguity)
os.environ.setdefault("TRULENS_DB_URL", "sqlite:///trulens.sqlite")

import rag_utils as utils
print("RAG_UTILS FILE:", utils.__file__)
print("UTILS FILE:", utils.__file__)
print("UTILS DIR :", os.path.dirname(utils.__file__))
print("HAS build_sentence_window_index:", hasattr(utils, "build_sentence_window_index"))

from llama_index.core import SimpleDirectoryReader, Document, VectorStoreIndex, Settings
from llama_index.llms.openai import OpenAI as LlamaOpenAI
from llama_index.embeddings.openai import OpenAIEmbedding

# If you still use openai==0.x SDK elsewhere, this is fine; otherwise you can remove it.
import openai
openai.api_key = utils.get_openai_api_key()

# --- Load PDF ---
documents = SimpleDirectoryReader(
    input_files=["./eBook-How-to-Build-a-Career-in-AI.pdf"]
).load_data()

print(type(documents), "\n")
print(len(documents), "\n")
print(type(documents[0]))
print(documents[0])

# LlamaIndex expects a list of Documents; we also build one "combined" document for some indices
combined_document = Document(text="\n\n".join([doc.text for doc in documents]))

# --- LlamaIndex Settings (modern; no ServiceContext) ---
Settings.llm = LlamaOpenAI(model="gpt-4o-mini", temperature=0.1)
Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-small")

# --- Helper: load eval questions ---
def load_eval_questions(path: str) -> list[str]:
    qs: list[str] = []
    try:
        with open(path, "r") as f:
            for line in f:
                item = line.strip()
                if item:
                    qs.append(item)
    except FileNotFoundError:
        # Safe fallback if file isn't present
        qs = []
    qs.append("What is the right AI job for me?")
    return qs

eval_questions = load_eval_questions("eval_questions.txt")
print(eval_questions)

# --- TruLens session ---
from trulens.core import TruSession
tru = TruSession()

# Uncomment if you want a clean slate each run (do this BEFORE recording)
# tru.reset_database()

# -----------------------------
# 1) Baseline VectorStoreIndex
# -----------------------------
print("\n=== Baseline VectorStoreIndex ===")
index = VectorStoreIndex.from_documents([combined_document])
query_engine = index.as_query_engine()

baseline_q = "What are steps to take when finding projects to build your experience?"
print("Q:", baseline_q)
print("A:", str(query_engine.query(baseline_q)))

baseline_recorder = utils.get_prebuilt_trulens_recorder(
    query_engine,
    app_name="Baseline VectorStoreIndex",
    app_version="v1",
)

with baseline_recorder:
    for q in eval_questions:
        _ = query_engine.query(q)

# Force TruLens to materialize results before moving on / exiting (prevents shutdown race)
records, feedback = tru.get_records_and_feedback(app_ids=[])
print("Baseline records:", len(records))

# -----------------------------
# 2) Sentence Window Index
# -----------------------------
print("\n=== Sentence Window Index ===")
# Use a cheaper model for experimentation if you like
llm_small = LlamaOpenAI(model="gpt-3.5-turbo", temperature=0.1)

sentence_index = utils.build_sentence_window_index(
    combined_document,
    llm_small,
    embed_model="local:BAAI/bge-small-en-v1.5",
    save_dir="sentence_index",
)

sentence_window_engine = utils.get_sentence_window_query_engine(sentence_index)

window_q = "how do I get started on a personal project in AI?"
print("Q:", window_q)
print("A:", str(sentence_window_engine.query(window_q)))

sentence_recorder = utils.get_prebuilt_trulens_recorder(
    sentence_window_engine,
    app_name="Sentence Window Query Engine",
    app_version="v1",
)

with sentence_recorder:
    for q in eval_questions:
        _ = sentence_window_engine.query(q)

records, feedback = tru.get_records_and_feedback(app_ids=[])
print("After sentence-window records:", len(records))

# -----------------------------
# 3) AutoMerging Index
# -----------------------------
print("\n=== AutoMerging Index ===")
automerging_index = utils.build_automerging_index(
    documents,  # IMPORTANT: build_automerging_index expects a list of docs
    llm_small,
    embed_model="local:BAAI/bge-small-en-v1.5",
    save_dir="merging_index",
)

automerging_query_engine = utils.get_automerging_query_engine(
    automerging_index,
)

auto_q = "How do I build a portfolio of AI projects?"
print("Q:", auto_q)
print("A:", str(automerging_query_engine.query(auto_q)))

automerging_recorder = utils.get_prebuilt_trulens_recorder(
    automerging_query_engine,
    app_name="Automerging Query Engine",
    app_version="v1",
)

with automerging_recorder:
    for q in eval_questions:
        _ = automerging_query_engine.query(q)

# Final materialization + small wait to avoid groundedness shutdown race
records, feedback = tru.get_records_and_feedback(app_ids=[])
print("Final records:", len(records))

time.sleep(10)

# Leaderboard (prints a dataframe-like object depending on your environment)
try:
    lb = tru.get_leaderboard(app_ids=[])
    print("\n=== Leaderboard ===")
    print(lb)
except Exception as e:
    print("Leaderboard fetch failed:", e)

print("\nDone. To view dashboard, run in a new terminal:")
print("  export TRULENS_DB_URL='sqlite:///trulens.sqlite'")
print("  streamlit run /Users/harshloomba/Documents/gurukul/.venv/lib/python3.12/site-packages/trulens/dashboard/main.py")
