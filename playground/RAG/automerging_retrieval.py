import warnings
warnings.filterwarnings('ignore')


import rag_utils as utils

import os
import openai
openai.api_key = utils.get_openai_api_key()

from llama_index.core import (
    SimpleDirectoryReader,
    Document,
    VectorStoreIndex,
    Settings,
    StorageContext,
    load_index_from_storage,
)

documents = SimpleDirectoryReader(
    input_files=["./eBook-How-to-Build-a-Career-in-AI.pdf"]
).load_data()

print(documents[0])



document = Document(text="\n\n".join([doc.text for doc in documents]))

from llama_index.core.node_parser import HierarchicalNodeParser

# create the hierarchical node parser w/ default settings
node_parser = HierarchicalNodeParser.from_defaults(
    chunk_sizes=[2048, 512, 128]
)

nodes = node_parser.get_nodes_from_documents([document])

from llama_index.core.node_parser import get_leaf_nodes

leaf_nodes = get_leaf_nodes(nodes)
print(leaf_nodes[30].text)

nodes_by_id = {node.node_id: node for node in nodes}

parent_node = nodes_by_id[leaf_nodes[30].parent_node.node_id]
print(parent_node.text)

from llama_index.llms.openai import OpenAI

llm = OpenAI(model="gpt-3.5-turbo", temperature=0.1)
Settings.llm = llm

# ---- Build index using the parser as a transformation ----
index = VectorStoreIndex.from_documents(
    [document],
    transformations=[node_parser],  # important: ensures hierarchical chunks used
)

# Now you can query:
qe = index.as_query_engine(similarity_top_k=5)
resp = qe.query("How much math do you need to know to be a machine learning engineer?")
print(resp)

from llama_index.core.retrievers import AutoMergingRetriever
from llama_index.core.indices.postprocessor import SentenceTransformerRerank
from llama_index.core.query_engine import RetrieverQueryEngine


def build_automerging_index(
    documents,
    llm,
    embed_model="local:BAAI/bge-small-en-v1.5",
    save_dir="merging_index",
    chunk_sizes=None,
):
    chunk_sizes = chunk_sizes or [2048, 512, 128]
    node_parser = HierarchicalNodeParser.from_defaults(chunk_sizes=chunk_sizes)
    nodes = node_parser.get_nodes_from_documents(documents)
    leaf_nodes = get_leaf_nodes(nodes)
    Settings.llm = llm
    storage_context = StorageContext.from_defaults()
    storage_context.docstore.add_documents(nodes)

    if not os.path.exists(save_dir):
        # ---- Build index using the parser as a transformation ----
        automerging_index = VectorStoreIndex.from_documents(
            [document],
            transformations=[node_parser],  # important: ensures hierarchical chunks used
        )
        automerging_index.storage_context.persist(persist_dir=save_dir)
    else:
        automerging_index = load_index_from_storage(
            StorageContext.from_defaults(persist_dir=save_dir)
        )
    return automerging_index


def get_automerging_query_engine(
    automerging_index,
    similarity_top_k=12,
    rerank_top_n=6,
):
    base_retriever = automerging_index.as_retriever(similarity_top_k=similarity_top_k)
    retriever = AutoMergingRetriever(
        base_retriever, automerging_index.storage_context, verbose=True
    )
    rerank = SentenceTransformerRerank(
        top_n=rerank_top_n, model="BAAI/bge-reranker-base"
    )
    auto_merging_engine = RetrieverQueryEngine.from_args(
        retriever, node_postprocessors=[rerank]
    )
    return auto_merging_engine

from llama_index.llms.openai import OpenAI

index = build_automerging_index(
    [document],
    llm=OpenAI(model="gpt-3.5-turbo", temperature=0.1),
    save_dir="./merging_index",
)
query_engine = get_automerging_query_engine(index, similarity_top_k=6)

from trulens_eval import Tru

Tru().reset_database()

auto_merging_index_0 = build_automerging_index(
    documents,
    llm=OpenAI(model="gpt-3.5-turbo", temperature=0.1),
    embed_model="local:BAAI/bge-small-en-v1.5",
    save_dir="merging_index_0",
    chunk_sizes=[2048,512],
)

auto_merging_engine_0 = get_automerging_query_engine(
    auto_merging_index_0,
    similarity_top_k=12,
    rerank_top_n=6,
)

from rag_utils import get_prebuilt_trulens_recorder

tru_recorder = get_prebuilt_trulens_recorder(
    auto_merging_engine_0,
    app_name ='app_0'
)

eval_questions = []
with open('generated_questions.text', 'r') as file:
    for line in file:
        # Remove newline character and convert to integer
        item = line.strip()
        eval_questions.append(item)


def run_evals(eval_questions, tru_recorder, query_engine):
    for question in eval_questions:
        with tru_recorder as recording:
            response = query_engine.query(question)

run_evals(eval_questions, tru_recorder, auto_merging_engine_0)

from trulens_eval import Tru

Tru().get_leaderboard(app_ids=[])