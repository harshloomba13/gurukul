# rag_triad_fixed.py
# End-to-end: Sentence-window RAG (LlamaIndex) + TruLens (Answer Rel, Context Rel, Groundedness)
# Exports: trulens_expanded_results.csv with columns: input, output, Answer Relevance, Context Relevance, Groundedness

import os
import time
import logging
import warnings
warnings.filterwarnings("ignore")
os.environ["TRULENS_DATABASE_URL"] = "sqlite://///Users/harshloomba/Documents/gurukul/playground/RAG/default.sqlite"


os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

# Avoid HF tokenizers fork/parallelism warnings
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

# ---- logging: keep it readable (optional) ----
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
for noisy in ["httpx", "openai", "urllib3"]:
    logging.getLogger(noisy).setLevel(logging.WARNING)

# ---- OpenAI key ----
# Prefer env var; fallback to rag_utils.get_openai_api_key() if you have it
if not os.getenv("OPENAI_API_KEY"):
    try:
        import rag_utils as utils
        os.environ["OPENAI_API_KEY"] = utils.get_openai_api_key()
    except Exception:
        raise RuntimeError("Set OPENAI_API_KEY env var (or provide rag_utils.get_openai_api_key()).")

# =========================
# LlamaIndex: build/load index
# =========================
from llama_index.core import (
    SimpleDirectoryReader,
    Document,
    VectorStoreIndex,
    Settings,
    StorageContext,
    load_index_from_storage,
)

from llama_index.llms.openai import OpenAI

# --- embeddings: use local HF if available, else OpenAI embeddings ---
def get_embed_model():
    # Local embedding (dim 384) - matches your BGE local setup
    try:
        from llama_index.embeddings.huggingface import HuggingFaceEmbedding
        return HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")
    except Exception:
        # fallback to OpenAI (dim 1536/3072 depending model) - OK but MUST stay consistent forever
        from llama_index.embeddings.openai import OpenAIEmbedding
        return OpenAIEmbedding(model="text-embedding-3-small")  # pick one and keep it fixed


# postprocessors imports differ a bit across llama-index versions
try:
    from llama_index.core.postprocessor import MetadataReplacementPostProcessor, SentenceTransformerRerank
except Exception:
    from llama_index.core.indices.postprocessor import MetadataReplacementPostProcessor, SentenceTransformerRerank

from llama_index.core.node_parser import SentenceWindowNodeParser


def build_or_load_sentence_window_index(
    pdf_path: str,
    persist_dir: str = "sentence_index",
    sentence_window_size: int = 3,
):
    # LLM + Embeddings MUST be set before building/loading
    Settings.llm = OpenAI(model="gpt-3.5-turbo", temperature=0.1)
    Settings.embed_model = get_embed_model()

    docs = SimpleDirectoryReader(input_files=[pdf_path]).load_data()
    full_doc = Document(text="\n\n".join(d.text for d in docs))

    node_parser = SentenceWindowNodeParser.from_defaults(
        window_size=sentence_window_size,
        window_metadata_key="window",
        original_text_metadata_key="original_text",
    )

    def _build():
        nodes = node_parser.get_nodes_from_documents([full_doc])
        idx = VectorStoreIndex(nodes)
        idx.storage_context.persist(persist_dir=persist_dir)
        return idx

    # Try load, then do a tiny query to detect embedding mismatch (384 vs 1536)
    if os.path.isdir(persist_dir):
        try:
            logging.info(f"[index] loading from {persist_dir} ...")
            idx = load_index_from_storage(StorageContext.from_defaults(persist_dir=persist_dir))
            _ = idx.as_query_engine(similarity_top_k=1).query("ping")
            return idx
        except Exception as e:
            logging.warning(f"[index] load/query failed (likely embedding mismatch): {e}")
            logging.warning(f"[index] deleting {persist_dir} and rebuilding ...")
            import shutil
            shutil.rmtree(persist_dir, ignore_errors=True)
            return _build()
    else:
        logging.info("[index] building new index ...")
        return _build()


def get_sentence_window_query_engine(index, similarity_top_k: int = 6, rerank_top_n: int = 2):
    postproc = MetadataReplacementPostProcessor(target_metadata_key="window")
    rerank = SentenceTransformerRerank(top_n=rerank_top_n, model="BAAI/bge-reranker-base")

    return index.as_query_engine(
        similarity_top_k=similarity_top_k,
        node_postprocessors=[postproc, rerank],
    )


# =========================
# TruLens: feedback + recording
# =========================
from trulens.core import TruSession, Feedback, Select
from trulens.apps.llamaindex import TruLlama
from trulens.dashboard.run import run_dashboard
from trulens.providers.openai import OpenAI as TruOpenAIProvider
import numpy as np
import pandas as pd


def _join_contexts(ctx):
    if ctx is None:
        return ""
    if isinstance(ctx, list):
        return "\n\n".join(str(x) for x in ctx)
    return str(ctx)


def main():
    pdf_path = "./eBook-How-to-Build-a-Career-in-AI.pdf"
    persist_dir = "sentence_index"

    # ---- Build/load index + engine ----
    index = build_or_load_sentence_window_index(
        pdf_path=pdf_path,
        persist_dir=persist_dir,
        sentence_window_size=3,
    )
    engine = get_sentence_window_query_engine(index)

    # quick sanity query
    sanity_q = "How do you create your AI portfolio?"
    sanity_resp = engine.query(sanity_q)
    print(f"\n[sanity]\nQ: {sanity_q}\nA: {sanity_resp.response}\n")

    # ---- Tru session ----
    import os
    os.environ["TRULENS_DATABASE_URL"] = "sqlite://///Users/harshloomba/Documents/gurukul/playground/RAG/default.sqlite"
    tru = TruSession()
    tru.reset_database()

    provider = TruOpenAIProvider()

    # Lens for retrieved contexts
    context_sel = TruLlama.select_source_nodes().node.text

    # Answer relevance: question vs answer
    f_answer_rel = (
        Feedback(provider.relevance_with_cot_reasons, name="Answer Relevance")
        .on_input_output()
    )

    # Context relevance: question vs retrieved context (JOIN the list!)
    def context_relevance(question: str, ctx):
        return provider.qs_relevance_with_cot_reasons(question, _join_contexts(ctx))

    f_context_rel = (
        Feedback(context_relevance, name="Context Relevance")
        .on_input()
        .on(context_sel)
        .aggregate(np.mean)
    )

    # Groundedness: answer vs context (JOIN the list!)
    def groundedness(ctx, answer: str):
        return provider.groundedness_measure_with_cot_reasons(_join_contexts(ctx), answer)

    f_grounded = (
        Feedback(groundedness, name="Groundedness")
        .on(context_sel)
        .on(Select.RecordOutput)
        .aggregate(np.mean)
    )

    tru_recorder = TruLlama(
        engine,
        app_name="sentence_window_engine",
        app_version="v1",
        feedbacks=[f_answer_rel, f_context_rel, f_grounded],
    )

    # ---- Eval questions ----
    default_questions = [
        "What are the keys to building a career in AI?",
        "How can teamwork contribute to success in AI?",
        "What is the importance of networking in AI?",
        "What are some good habits to develop for a successful career?",
        "How can altruism be beneficial in building a career?",
        "What is imposter syndrome and how does it relate to AI?",
        "Who are some accomplished individuals who have experienced imposter syndrome?",
        "What is the first step to becoming good at AI?",
        "What are some common challenges in AI?",
        "Is it normal to find parts of AI challenging?",
    ]

    eval_questions = []
    if os.path.exists("eval_questions.txt"):
        with open("eval_questions.txt", "r") as f:
            eval_questions = [line.strip() for line in f if line.strip()]
    else:
        eval_questions = default_questions

    print(f"Eval questions ({len(eval_questions)}):")
    for q in eval_questions:
        print("-", q)

    # IMPORTANT: record using tru_recorder.app.query(...)
    for q in eval_questions:
        with tru_recorder:
            tru_recorder.app.query(q)

    # ---- Poll until feedback columns appear ----
    t0 = time.time()
    feedback_cols = []
    records = None

    while True:
        records, feedback_cols = tru.get_records_and_feedback(app_ids=[])
        cols = list(feedback_cols)
        if len(records) > 0 and ("Context Relevance" in cols) and ("Answer Relevance" in cols):
            break
        if time.time() - t0 > 180:
            print("[warn] Timed out waiting for feedback; exporting what exists.")
            break
        time.sleep(2)

    # ---- Export clean CSV ----
    records, feedback_cols = tru.get_records_and_feedback(app_ids=[])

    if len(records) == 0:
        print("\nNo records captured. If this happens, confirm you're calling tru_recorder.app.query(...)")
        return

    in_col = "input" if "input" in records.columns else "main_input"
    out_col = "output" if "output" in records.columns else "main_output"

    desired = [in_col, out_col, "Answer Relevance", "Context Relevance", "Groundedness"]
    desired = [c for c in desired if c in records.columns]

    expanded = records[desired].copy()
    expanded.rename(columns={in_col: "input", out_col: "output"}, inplace=True)

    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 220)
    pd.set_option("display.max_colwidth", 200)

    print("\nColumns:", list(expanded.columns))
    print(expanded.head(10))

    expanded.to_csv("trulens_expanded_results.csv", index=False)
    print("\nSaved trulens_expanded_results.csv")
    tru.get_leaderboard(app_ids=[])
    run_dashboard(session=tru)


if __name__ == "__main__":
    main()
