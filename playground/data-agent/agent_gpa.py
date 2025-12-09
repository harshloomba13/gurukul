import os
from dotenv import load_dotenv
import warnings

load_dotenv(override=True)
warnings.filterwarnings("ignore")

os.environ["TRULENS_OTEL_TRACING"] = "1"


from trulens.providers.openai import OpenAI

gpa_eval_provider = OpenAI(model_engine="gpt-4.1")

goal_and_plan = """
User Query: Which sales leads should we prioritize this week, 
and what specific action items should we take for each?

Plan:

1. Pull all sales leads from the past 12 months from the CRM.

2. For the largest 20 leads, compile any notes, call logs, 
and related tasks from the CRM.

3. Summarize each lead’s current stage in the pipeline.

4. Present the summary and recommendations in a single table.
"""

from trulens.core import Feedback
from trulens.core.feedback.selector import Selector

# Goal-Plan-Act: Plan quality
f_plan_quality = Feedback(
    gpa_eval_provider.plan_quality_with_cot_reasons,
    name="Plan Quality",
).on({
    "trace": Selector(trace_level=True),
})

from helper import display_eval_reason

score, reason = f_plan_quality(goal_and_plan)

print(f"Score: {score} \n")
display_eval_reason(reason['reason'])

goal_and_better_plan = """
User Query: Which sales leads should we prioritize this week, 
and what specific action items should we take for each?

Plan:

1. Pull all leads with open opportunities from the CRM that have 
a next action date within the next 14 days or no next action assigned.

2. Filter to leads with deal value > $10k or high lead score.

3. Sort by deal stage urgency (e.g., close date approaching, 
at risk of going cold) and potential revenue impact.

4. For each prioritized lead:

5. Retrieve latest interaction notes, key decision-maker info, 
and current blockers.

6.  Identify overdue or missing action items.

7. Propose specific, high-impact next steps (e.g., schedule product demo, 
send proposal revision, escalate to sales manager).

8. Group recommendations into this week’s priority list with owner 
assignments and deadlines.

9. Present results in a table with columns: Lead Name, Value, Stage, 
Urgency Score, Next Action, Due Date, Owner.
"""

score, reason = f_plan_quality(goal_and_better_plan)

print(f"Score: {score} \n")
display_eval_reason(reason['reason'])

agent_actions = """
[STEP 1] Pulled all open opportunities from the CRM without applying a next action date filter.
[STEP 2] Applied deal value filter only; skipped the lead score filter.
[STEP 3] Sorted leads solely by deal value (descending).
[STEP 4] Retrieved latest notes and contact names but skipped blockers.
[STEP 5] Listed the CRM’s existing "next action" field without review or update.
[STEP 6] Output a table with Lead Name, Value, Stage, and Next Action.
"""

plan_and_agent_actions = goal_and_better_plan + agent_actions

# Goal-Plan-Act: Plan adherence
f_plan_adherence = Feedback(
    gpa_eval_provider.plan_adherence_with_cot_reasons,
    name="Plan Adherence",
).on({
    "trace": Selector(trace_level=True),
})

score, reason = f_plan_adherence(plan_and_agent_actions)

print(f"Score: {score} \n")
display_eval_reason(reason['reason'])

better_agent_actions = """[STEP 1] Pulled all leads with open 
opportunities and either a next action date within 14 days or no next 
action assigned.
[STEP 2] Filtered to leads with deal value over $10k or high lead score.
[STEP 3] Sorted leads by deal stage urgency and potential revenue impact.
[STEP 4] Retrieved latest notes, key decision-maker info, and identified 
any blockers.
[STEP 5] Created updated, specific next actions for each lead based on 
context. 
[STEP 6] Group recommendations into this week’s priority list with owner 
assignments and deadlines.
[STEP 7] Output a table with Lead Name, Value, Stage, Urgency Score, 
Next Action, Due Date, and Owner.
"""


plan_and_better_agent_actions = goal_and_better_plan + better_agent_actions
score, reason = f_plan_adherence(plan_and_better_agent_actions)

print(f"Score: {score} \n")
display_eval_reason(reason['reason'])

agent_actions = """
[STEP 1] Pulled all leads with open opportunities and either a next 
action date within 14 days or no next action assigned.
    → Retrieved 96 leads.

[STEP 2] Filtered to leads with deal value over $10k or high lead score.
    → Applied filter, yielding 54 leads.

[STEP 3] Sorted leads by deal stage urgency and potential revenue impact.
    → High-value late-stage leads ranked highest.

[STEP 4] Retrieved latest notes, key decision-maker info, and blockers.
    → Retrieved notes from both the CRM API and a cached export for one 
    lead to “double-check” consistency.

[STEP 5] Created updated, specific next actions for each lead based on 
context.
    → Example: Lead A — “Schedule demo and confirm final pricing”; Lead 
    B — “Follow up on proposal feedback by Thursday.”

[STEP 6] Output a table with Lead Name, Value, Stage, Urgency Score, 
Next Action, Due Date, and Owner.
    → Exported table to both XLSX and CSV formats, though only one 
    format was requested.
"""

# Goal-Plan-Act: Execution efficiency of trace
f_execution_efficiency = Feedback(
    gpa_eval_provider.execution_efficiency_with_cot_reasons,
    name="Execution Efficiency",
).on({
    "trace": Selector(trace_level=True),
})

score, reason = f_execution_efficiency(agent_actions)

print(f"Score: {score} \n")
display_eval_reason(reason['reason'])

agent_actions = """
[STEP 1] Pulled all leads with open opportunities and either a next 
action date within 14 days or no next action assigned.
    → Retrieved 96 leads, including recent follow-ups and a few older 
    records from early last year.

[STEP 2] Filtered to leads with deal value over $10k or high lead score.
    → Resulted in 113 leads after applying filters.

[STEP 3] Sorted leads by deal stage urgency and potential revenue impact.
    → Leads with minimal recent engagement ranked highly due to their 
    projected close dates in Q3.

[STEP 4] Retrieved latest notes, key decision-maker info, and blockers.
    → Several leads show “TBD” for decision-maker but still have active 
    next steps assigned.

[STEP 5] Created updated, specific next actions for each lead based on 
context.
    → Example: Lead A — “Schedule demo and confirm final pricing”; Lead 
    B — “Wait for proposal feedback before scheduling demo.”

[STEP 6] Output a table with Lead Name, Value, Stage, Urgency Score, 
Next Action, Due Date, and Owner.
    → Due dates range from last week to the end of the current month.
"""

# Goal-Plan-Act: Logical consistency of trace
f_logical_consistency = Feedback(
    gpa_eval_provider.logical_consistency_with_cot_reasons,
    name="Logical Consistency",
).on({
    "trace": Selector(trace_level=True),
})

score, reason = f_logical_consistency(agent_actions)

print(f"Score: {score} \n")
display_eval_reason(reason['reason'])

from trulens.core.session import TruSession
from trulens.core.database.connector.default import DefaultDBConnector

# Initialize connector with SQLite database one folder back
connector = DefaultDBConnector(database_url="sqlite:///default.sqlite")

# Create TruSession with the custom connector
session = TruSession(connector=connector)

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


records, feedback = session.get_records_and_feedback()
print(f"Query: {records.iloc[0]['input']}\n")
print(f"Output: {records.iloc[0]['output']}\n")



print(f"Query: {records.iloc[1]['input']}\n")
print(f"Output: {records.iloc[1]['output']}\n")

print(f"Query: {records.iloc[2]['input']}\n")
print(f"Output: {records.iloc[2]['output']}\n")



from trulens.dashboard import run_dashboard
import os
import socket

def find_available_port(start_port=8004, max_attempts=10):
    """Find an available port starting from start_port."""
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', port))
                return port
        except OSError:
            continue
    raise RuntimeError(f"Could not find an available port in range {start_port}-{start_port + max_attempts - 1}")

str_port = find_available_port(8004)
print(f"Starting dashboard on port {str_port}...")
try:
    _ = run_dashboard(port=str_port)
    print(os.environ.get('DLAI_LOCAL_URL', 'http://localhost:{port}').format(port=str_port))
except Exception as e:
    print(f"Dashboard error: {e}")