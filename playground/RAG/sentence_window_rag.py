# sentence_window_rag.py
# End-to-end: build/load sentence-window index, run eval questions under TruLlama recorder,
# then export expanded records+feedback to CSV.

import os
import warnings
warnings.filterwarnings("ignore")

import pandas as pd
import numpy as np

import rag_utils as utils

# -----------------------------
# OpenAI key (your helper)
# -----------------------------
import openai
openai.api_key = utils.get_openai_api_key()

# -----------------------------
# LlamaIndex imports (modern)
# -----------------------------
from llama_index.core import (
    SimpleDirectoryReader,
    Document,
    VectorStoreIndex,
    Settings,
    StorageContext,
    load_index_from_storage,
)

from llama_index.core.node_parser import SentenceWindowNodeParser
from llama_index.core.postprocessor import MetadataReplacementPostProcessor, SentenceTransformerRerank

from llama_index.llms.openai import OpenAI  # correct path for your env

# -----------------------------
# TruLens imports (v2 style)
# -----------------------------
from trulens_eval import Tru, Feedback
from trulens.apps.llamaindex import TruLlama
from trulens.providers.openai import OpenAI as fOpenAI  # feedback provider


# =============================
# Config
# =============================
PDF_PATH = "./eBook-How-to-Build-a-Career-in-AI.pdf"
PERSIST_DIR = "./sentence_index_1"
APP_NAME = "sentence window engine 1"
APP_VERSION = "v1"
QUESTIONS_FILE = "generated_questions.text"  # <-- keep your filename
CSV_OUT = "trulens_records_expanded.csv"

# Retrieval settings
SIMILARITY_TOP_K = 6
RERANK_TOP_N = 2
SENTENCE_WINDOW_SIZE = 1

# LLM config
LLM_MODEL = "gpt-3.5-turbo"
LLM_TEMP = 0.1


# =============================
# Helpers
# =============================
def load_pdf_as_single_document(pdf_path: str) -> Document:
    docs = SimpleDirectoryReader(input_files=[pdf_path]).load_data()
    return Document(text="\n\n".join([d.text for d in docs]))


def build_or_load_sentence_window_index(
    document: Document,
    llm,
    persist_dir: str,
    sentence_window_size: int = 3,
) -> VectorStoreIndex:
    """
    Key point: to get sentence-window behavior, you must pass a SentenceWindowNodeParser
    as transformations when building the index.
    """
    node_parser = SentenceWindowNodeParser.from_defaults(
        window_size=sentence_window_size,
        window_metadata_key="window",
        original_text_metadata_key="original_text",
    )

    Settings.llm = llm

    if not os.path.exists(persist_dir):
        index = VectorStoreIndex.from_documents(
            [document],
            transformations=[node_parser],  # IMPORTANT
        )
        index.storage_context.persist(persist_dir=persist_dir)
        return index

    storage = StorageContext.from_defaults(persist_dir=persist_dir)
    return load_index_from_storage(storage)


def make_query_engine(index: VectorStoreIndex, similarity_top_k: int, rerank_top_n: int):
    postproc = MetadataReplacementPostProcessor(target_metadata_key="window")
    rerank = SentenceTransformerRerank(top_n=rerank_top_n, model="BAAI/bge-reranker-base")

    return index.as_query_engine(
        similarity_top_k=similarity_top_k,
        node_postprocessors=[postproc, rerank],
    )


def load_eval_questions(path: str) -> list[str]:
    questions = []
    with open(path, "r") as f:
        for line in f:
            q = line.strip()
            if q:
                questions.append(q)
    return questions


def run_evals(eval_questions: list[str], tru_recorder: TruLlama, query_engine):
    """
    Important: run the query INSIDE the `with tru_recorder` block,
    otherwise TruLens may capture nothing.
    """
    for q in eval_questions:
        with tru_recorder as recording:
            _ = query_engine.query(q)


def export_expanded_results(tru: Tru, app_name: str, csv_out: str):
    """
    DO NOT filter by app_ids=["some human name"].
    Fetch all, then filter by app_name.
    """
    records, feedback_cols = tru.get_records_and_feedback(app_ids=[])

    print("\nfeedback cols:", feedback_cols)
    print("record count (all):", len(records))

    # show app_name/app_id pairs to debug if needed
    if len(records) > 0 and "app_name" in records.columns and "app_id" in records.columns:
        print("\nDistinct apps captured:")
        print(records[["app_name", "app_id", "app_version"]].drop_duplicates().head(20))

    # Filter by app_name
    if "app_name" in records.columns:
        records = records[records["app_name"] == app_name]

    print("record count (filtered by app_name):", len(records))

    # Set pandas print options globally (DataFrame has no set_option)
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 220)
    pd.set_option("display.max_colwidth", None)

    # Choose useful columns that exist
    base_candidates = [
        "app_name", "app_version", "app_id",
        "main_input", "main_output",
        "input", "output",
        "ts", "record_id",
    ]
    base_cols = [c for c in base_candidates if c in records.columns]
    fb_cols = list(feedback_cols) if isinstance(feedback_cols, (list, tuple)) else []
    cols = base_cols + [c for c in fb_cols if c in records.columns]

    if len(records) > 0:
        print("\n=== Expanded (head) ===")
        print(records[cols].head(10) if cols else records.head(10))
    else:
        print("\nNo records captured for this app_name. If this happens, ensure run_evals() is called and queries run inside `with tru_recorder:`.")

    records.to_csv(csv_out, index=False)
    print(f"\nSaved {csv_out}")


# =============================
# Main
# =============================
def main():
    llm = OpenAI(model=LLM_MODEL, temperature=LLM_TEMP)
    Settings.llm = llm

    # 1) Load PDF into one Document
    document = load_pdf_as_single_document(PDF_PATH)

    # 2) Build/load sentence-window index
    index = build_or_load_sentence_window_index(
        document=document,
        llm=llm,
        persist_dir=PERSIST_DIR,
        sentence_window_size=SENTENCE_WINDOW_SIZE,
    )

    # 3) Create query engine with postprocessors
    query_engine = make_query_engine(
        index=index,
        similarity_top_k=SIMILARITY_TOP_K,
        rerank_top_n=RERANK_TOP_N,
    )

    # Quick sanity query (optional)
    sanity_q = "What are the keys to building a career in AI?"
    sanity_resp = query_engine.query(sanity_q)
    print(str(sanity_resp))

    # 4) Tru session + feedbacks
    tru = Tru()
    tru.reset_database()

    provider = fOpenAI()

    f_qa_relevance = Feedback(
        provider.relevance_with_cot_reasons,
        name="Answer Relevance",
    ).on_input_output()

    # This selector is based on TruLlama's record schema for llamaindex
    # (you saw TruLens auto-setting these in your logs)
    context_selection = TruLlama.select_source_nodes().node.text

    f_ctx_relevance = (
        Feedback(provider.qs_relevance_with_cot_reasons, name="Context Relevance")
        .on_input()
        .on(context_selection)
        .aggregate(np.mean)
    )

    # Groundedness: use provider's groundedness measure (no trulens_eval.feedback.Groundedness import)
    f_groundedness = (
        Feedback(provider.groundedness_measure_with_cot_reasons, name="Groundedness")
        .on(context_selection)          # context
        .on_output()                   # answer (record main_output)
        .aggregate(np.mean)
    )

    # 5) Recorder
    tru_recorder = TruLlama(
        query_engine,
        app_name=APP_NAME,
        app_version=APP_VERSION,
        feedbacks=[f_qa_relevance, f_ctx_relevance, f_groundedness],
    )

    # 6) Load questions + run evals
    eval_questions = load_eval_questions(QUESTIONS_FILE)
    print("\neval quest -", eval_questions)

    run_evals(eval_questions, tru_recorder, query_engine)

    # 7) Export expanded results
    export_expanded_results(tru, APP_NAME, CSV_OUT)


if __name__ == "__main__":
    main()
