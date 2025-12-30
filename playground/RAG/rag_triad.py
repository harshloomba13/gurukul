import warnings
warnings.filterwarnings('ignore')

import rag_utils as utils

import os
import openai
openai.api_key = utils.get_openai_api_key()

from trulens_eval import Tru

tru = Tru()
tru.reset_database()

from llama_index.core import SimpleDirectoryReader, Document, VectorStoreIndex, Settings

documents = SimpleDirectoryReader(
    input_files=["./eBook-How-to-Build-a-Career-in-AI.pdf"]
).load_data()

from llama_index.core import Document

document = Document(text="\n\n".\
                    join([doc.text for doc in documents]))

#print(document)

from rag_utils import build_sentence_window_index
from llama_index.llms.openai import OpenAI

llm = OpenAI(model="gpt-3.5-turbo", temperature=0.1)

sentence_index = build_sentence_window_index(
    document,
    llm,
    embed_model="local:BAAI/bge-small-en-v1.5",
    save_dir="sentence_index"
)

from rag_utils import get_sentence_window_query_engine

sentence_window_engine = \
get_sentence_window_query_engine(sentence_index)

output = sentence_window_engine.query(
    "How do you create your AI portfolio?")

#print(output.response)

import nest_asyncio

nest_asyncio.apply()

from trulens.providers.openai import OpenAI as fOpenAI

provider = fOpenAI()

from trulens_eval import Feedback

f_qa_relevance = Feedback(
    provider.relevance_with_cot_reasons,
    name="Answer Relevance"
).on_input_output()

from trulens_eval import TruLlama

context_selection = TruLlama.select_source_nodes().node.text

import numpy as np

f_qs_relevance = (
    Feedback(provider.qs_relevance,
             name="Context Relevance")
    .on_input()
    .on({"context": context_selection})
    .aggregate(np.mean)
)

import numpy as np

f_qs_relevance = (
    Feedback(provider.qs_relevance_with_cot_reasons,
             name="Context Relevance")
    .on_input()
    .on(context_selection)
    .aggregate(np.mean)
)

from trulens_eval.feedback import Groundedness

grounded = Groundedness(groundedness_provider=provider)

f_groundedness = (
    Feedback(grounded.groundedness_measure_with_cot_reasons,
             name="Groundedness"
            )
    .on(context_selection)
    .on_output()
    .aggregate(grounded.grounded_statements_aggregator)
)

from trulens_eval import TruLlama
from trulens_eval import FeedbackMode

tru_recorder = TruLlama(
    sentence_window_engine,
    app_id="App_1",
    feedbacks=[
        f_qa_relevance,
        f_qs_relevance,
        f_groundedness
    ]
)

eval_questions = []
with open('eval_questions.txt', 'r') as file:
    for line in file:
        # Remove newline character and convert to integer
        item = line.strip()
        eval_questions.append(item)

print(eval_questions)