# rag_utils.py
import os
from dotenv import load_dotenv, find_dotenv

def get_openai_api_key() -> str | None:
    _ = load_dotenv(find_dotenv())
    return os.getenv("OPENAI_API_KEY")


# -----------------------------
# TruLens recorder (no groundedness)
# -----------------------------
_trulens_modules = None

def _import_trulens():
    import numpy as np
    from trulens.core import Feedback
    from trulens.apps.llamaindex import TruLlama
    from trulens.providers.openai import OpenAI as TruOpenAI
    return {"np": np, "Feedback": Feedback, "TruLlama": TruLlama, "TruOpenAI": TruOpenAI}

def _get_trulens_modules():
    global _trulens_modules
    if _trulens_modules is None:
        _trulens_modules = _import_trulens()
    return _trulens_modules

def get_prebuilt_trulens_recorder(query_engine, app_name="llamaindex_rag", app_version="v1"):
    m = _get_trulens_modules()
    np = m["np"]
    Feedback = m["Feedback"]
    TruLlama = m["TruLlama"]
    TruOpenAI = m["TruOpenAI"]

    provider = TruOpenAI()
    context = TruLlama.select_context(query_engine)

    f_answer_relevance = (
        Feedback(provider.relevance_with_cot_reasons, name="Answer Relevance")
        .on_input()
        .on_output()
    )

    f_context_relevance = (
        Feedback(provider.context_relevance_with_cot_reasons, name="Context Relevance")
        .on_input()
        .on(context.collect())
        .aggregate(np.mean)
    )

    return TruLlama(
        query_engine,
        app_name=app_name,
        app_version=app_version,
        feedbacks=[f_answer_relevance, f_context_relevance],
    )


# -----------------------------
# Sentence window helpers
# -----------------------------
from llama_index.core import Settings, VectorStoreIndex, StorageContext, load_index_from_storage
from llama_index.core.node_parser import SentenceWindowNodeParser
from llama_index.core.indices.postprocessor import MetadataReplacementPostProcessor, SentenceTransformerRerank

def build_sentence_window_index(
    document,
    llm,
    embed_model="local:BAAI/bge-small-en-v1.5",
    save_dir="sentence_index",
):
    node_parser = SentenceWindowNodeParser.from_defaults(
        window_size=3,
        window_metadata_key="window",
        original_text_metadata_key="original_text",
    )

    Settings.llm = llm
    Settings.embed_model = embed_model
    Settings.node_parser = node_parser

    if not os.path.exists(save_dir):
        idx = VectorStoreIndex.from_documents([document])
        idx.storage_context.persist(persist_dir=save_dir)
    else:
        idx = load_index_from_storage(StorageContext.from_defaults(persist_dir=save_dir))

    return idx


def get_sentence_window_query_engine(sentence_index, similarity_top_k=6, rerank_top_n=2):
    postproc = MetadataReplacementPostProcessor(target_metadata_key="window")
    rerank = SentenceTransformerRerank(top_n=rerank_top_n, model="BAAI/bge-reranker-base")

    return sentence_index.as_query_engine(
        similarity_top_k=similarity_top_k,
        node_postprocessors=[postproc, rerank],
    )

import os
from llama_index.core import Settings, VectorStoreIndex, StorageContext, load_index_from_storage
from llama_index.core.node_parser import HierarchicalNodeParser, get_leaf_nodes
from llama_index.core.retrievers import AutoMergingRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.indices.postprocessor import SentenceTransformerRerank


def build_automerging_index(
    documents,
    llm,
    embed_model,
    save_dir="merging_index",
    chunk_sizes=None,
):
    """
    Builds/loads a hierarchical auto-merging index (NO ServiceContext).
    `embed_model` can be an embedding object (recommended) or a supported string.
    """
    chunk_sizes = chunk_sizes or [2048, 512, 128]

    # Parse documents into hierarchical nodes
    node_parser = HierarchicalNodeParser.from_defaults(chunk_sizes=chunk_sizes)
    nodes = node_parser.get_nodes_from_documents(documents)
    leaf_nodes = get_leaf_nodes(nodes)

    # Configure global Settings for index construction
    Settings.llm = llm
    Settings.embed_model = embed_model

    # Keep the full node hierarchy in docstore
    storage_context = StorageContext.from_defaults()
    storage_context.docstore.add_documents(nodes)

    # Build or load
    if not os.path.exists(save_dir):
        idx = VectorStoreIndex(leaf_nodes, storage_context=storage_context)
        idx.storage_context.persist(persist_dir=save_dir)
    else:
        idx = load_index_from_storage(StorageContext.from_defaults(persist_dir=save_dir))

    return idx


def get_automerging_query_engine(
    automerging_index,
    similarity_top_k=12,
    rerank_top_n=2,
    rerank_model="BAAI/bge-reranker-base",
    verbose=True,
):
    base_retriever = automerging_index.as_retriever(similarity_top_k=similarity_top_k)

    retriever = AutoMergingRetriever(
        base_retriever,
        automerging_index.storage_context,
        verbose=verbose,
    )

    rerank = SentenceTransformerRerank(top_n=rerank_top_n, model=rerank_model)

    return RetrieverQueryEngine.from_args(
        retriever,
        node_postprocessors=[rerank],
    )
