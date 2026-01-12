import os
from dotenv import load_dotenv
import warnings

# Set matplotlib to use non-interactive backend to avoid GUI issues
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend

load_dotenv(override=True)
warnings.filterwarnings("ignore")

os.environ["TRULENS_OTEL_TRACING"] = "1"

from trulens.providers.openai import OpenAI

# Use GPT-4o for RAG Triad Evaluations
provider = OpenAI(model_engine="gpt-4o")

import numpy as np
from trulens.core import Feedback
from trulens.core.feedback.selector import Selector
from trulens.otel.semconv.trace import SpanAttributes

# Define a groundedness feedback function
f_groundedness = (
    Feedback(
        provider.groundedness_measure_with_cot_reasons, 
        name="Groundedness"
    )
    .on({
            "source": Selector(
                span_type=SpanAttributes.SpanType.RETRIEVAL,
                span_attribute=SpanAttributes.RETRIEVAL.RETRIEVED_CONTEXTS,
                collect_list=True
            )
        }
    )
    .on_output()
)

# Question/answer relevance between overall question and answer.
f_answer_relevance = (
    Feedback(provider.relevance_with_cot_reasons, name="Answer Relevance")
    .on_input()
    .on_output()
)

# Context relevance between question and each context chunk.
f_context_relevance = (
    Feedback(provider.context_relevance_with_cot_reasons, 
             name="Context Relevance")
    .on({
            "question": Selector(
                span_type=SpanAttributes.SpanType.RETRIEVAL,
                span_attribute=SpanAttributes.RETRIEVAL.QUERY_TEXT,
            )
        }
    )
    .on({
            "context": Selector(
                span_type=SpanAttributes.SpanType.RETRIEVAL,
                span_attribute=SpanAttributes.RETRIEVAL.RETRIEVED_CONTEXTS,
                collect_list=False
            )
        }
    )
    .aggregate(np.mean)
)

from trulens.core.session import TruSession
from trulens.core.database.connector.default import DefaultDBConnector

# Initialize connector with SQLite database one folder back
connector = DefaultDBConnector(database_url="sqlite:///default.sqlite")

# Create TruSession with the custom connector
session = TruSession(connector=connector)
session.reset_database()

from helper import cortex_agent, State
from trulens.core.otel.instrument import instrument
from langchain_core.messages import HumanMessage
from langgraph.graph import END
from langgraph.types import Command
from typing import Literal

@instrument(
    span_type=SpanAttributes.SpanType.RETRIEVAL,
    attributes=lambda ret, exception, *args, **kwargs: {
        SpanAttributes.RETRIEVAL.QUERY_TEXT: args[0].get("agent_query") if args[0].get("agent_query") else None,
        SpanAttributes.RETRIEVAL.RETRIEVED_CONTEXTS: [
            ret.update["messages"][-1].content
        ] if hasattr(ret, "update") else "No tool call",
    },
)
def cortex_agents_research_node(
    state: State,
) -> Command[Literal["executor"]]:
    query = state.get("agent_query", state.get("user_query", ""))
    # Call the tool with the string query
    agent_response = cortex_agent.invoke({"messages":query})
    # Compose a message content string with all results new HumanMessage with the result
    new_message = HumanMessage(content=agent_response['messages'][-1].content, name="cortex_researcher")
    # Append to the message history
    goto = "executor"
    return Command(
        update={"messages": [new_message]},
        goto=goto,
    )


from helper import web_search_agent

@instrument(
    span_type=SpanAttributes.SpanType.RETRIEVAL,
    attributes=lambda ret, exception, *args, **kwargs: {
        SpanAttributes.RETRIEVAL.QUERY_TEXT: args[0].get("agent_query") if args[0].get("agent_query") else None,
        SpanAttributes.RETRIEVAL.RETRIEVED_CONTEXTS: [
            ret.update["messages"][-1].content
        ] if hasattr(ret, "update") else "No tool call",
    },
)
def web_research_node(
    state: State,
) -> Command[Literal["executor"]]:
    agent_query = state.get("agent_query")
    result = web_search_agent.invoke({"messages":agent_query})
    goto = "executor"
    # wrap in a human message, as not all providers allow
    # AI message at the last position of the input messages list
    result["messages"][-1] = HumanMessage(
        content=result["messages"][-1].content, name="web_researcher"
    )
    return Command(
        update={
            # share internal message history of research agent with other agents
            "messages": result["messages"],
        },
        goto=goto,
    )

from langgraph.graph import START, StateGraph
from helper import State, planner_node, executor_node, cortex_agents_research_node, web_research_node, chart_node, chart_summary_node, synthesizer_node

workflow = StateGraph(State)
workflow.add_node("planner", planner_node)
workflow.add_node("executor", executor_node)
workflow.add_node("web_researcher", web_research_node)
workflow.add_node("cortex_researcher", cortex_agents_research_node)
workflow.add_node("chart_generator", chart_node)
workflow.add_node("chart_summarizer", chart_summary_node)
workflow.add_node("synthesizer", synthesizer_node)

workflow.add_edge(START, "planner")

graph = workflow.compile()

from trulens.apps.langgraph import TruGraph

tru_recorder = TruGraph(
    graph,
    app_name="Sales Data Agent",
    app_version="L4: Base",
    feedbacks=[
        f_answer_relevance,
        f_context_relevance,
        f_groundedness,
    ],
)

from langchain_core.messages import HumanMessage

with tru_recorder as recording:
    query = "What are our top 3 client deals? Chart the deal value for each."
    print(f"Query: {query}")
    state = {
                "messages": [HumanMessage(content=query)],
                "user_query": query,
                "enabled_agents": ["cortex_researcher", "web_researcher", 
                                   "chart_generator", "chart_summarizer", 
                                   "synthesizer"],
            }
    graph.invoke(state)

    print("--------------------------------")


with tru_recorder as recording:
    query = "Identify our pending deals, research if they may be experiencing regulatory changes, and using the meeting notes for each customer, provide a new value proposition for each given the regulatory changes."
    print(f"Query: {query}")
    state = {
                "messages": [HumanMessage(content=query)],
                "user_query": query,
                "enabled_agents": ["cortex_researcher", "web_researcher", 
                                   "chart_generator", "chart_summarizer", 
                                   "synthesizer"],
            }
    graph.invoke(state)

    print("--------------------------------")

with tru_recorder as recording:
    query = "Identify our largest client deal, then find important topics in the meeting notes with that company, and find a news article related to the important topics discussed."
    print(f"Query: {query}")
    state = {
                "messages": [HumanMessage(content=query)],
                "user_query": query,
                "enabled_agents": ["cortex_researcher", "web_researcher", 
                                   "chart_generator", "chart_summarizer", 
                                   "synthesizer"],
            }
    graph.invoke(state)

    print("--------------------------------")


from trulens.dashboard import run_dashboard
import os
import socket

def find_available_port(start_port=8001, max_attempts=10):
    """Find an available port starting from start_port."""
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', port))
                return port
        except OSError:
            continue
    raise RuntimeError(f"Could not find an available port in range {start_port}-{start_port + max_attempts - 1}")

str_port = find_available_port(8001)
print(f"Starting dashboard on port {str_port}...")
try:
    _ = run_dashboard(port=str_port)
    print(os.environ.get('DLAI_LOCAL_URL', 'http://localhost:{port}').format(port=str_port))
except Exception as e:
    print(f"Dashboard error: {e}")