#!/usr/bin/env python
# coding: utf-8

# # L4: Memory Operations: Extraction, Consolidation, and Self-Updating Memory

# <div style="background-color:#fff6e4; padding:15px; border-width:3px; border-color:#f5ecda; border-style:solid; border-radius:6px"> <p>⏳ <b>Note <code>(Database Starting)</code>:</b> This notebook takes about 30-60 seconds to be ready to use. You may start and watch the video while you wait.</p>
# <p>If you see <tt>Admin connection failed</tt> after running the first cell, simply wait and re-run — it is not a credentials issue.</p>
# </div>

# This lesson explores advanced memory operations that enable AI agents to manage long-running conversations efficiently. As conversations grow, they consume valuable context window space. Without proper management, agents lose important historical context or fail due to token limits.
# 
# **Lesson Objectives**
# 
# By the end of this lesson, you will understand how to:
# - Monitor context window utilization and detect when summarization is needed
# - Extract and consolidate conversation history into structured summaries
# - Implement self-updating memory that preserves technical details, emotional context, and entity information
# - Build tools that allow agents to expand summaries back to original conversations when needed
# 
# **Key Concepts**
# 
# | Concept | Description |
# |---------|-------------|
# | **Context Window Management** | Tracking token usage to prevent overflow and trigger timely summarization |
# | **Memory Consolidation** | Compressing verbose conversations into structured summaries while preserving critical information |
# | **Summary Expansion** | Retrieving original conversation content from summary references when detail is needed |
# | **Self-Updating Memory** | Automatic marking of summarized messages to prevent re-processing |

# <div style="background-color:#fff6ff; padding:13px; border-width:3px; border-color:#efe6ef; border-style:solid; border-radius:6px">
# <p> 💻 &nbsp; <b>Access <code>requirements.txt</code> and <code>helper.py</code> files:</b> 1) click on the <em>"File"</em> option on the top menu of the notebook and then 2) click on <em>"Open"</em>.
# 
# <p> ⬇ &nbsp; <b>Download Notebooks:</b> 1) click on the <em>"File"</em> option on the top menu of the notebook and then 2) click on <em>"Download as"</em> and select <em>"Notebook (.ipynb)"</em>.</p>
# 
# </div>

# ## Part 1: Setup and Configuration
# 
# This section establishes the foundational infrastructure needed for memory operations.
# 
# ### What We're Setting Up
# 
# | Component | Purpose |
# |-----------|---------|
# | **Database Connection** | Oracle Database stores all memory persistently |
# | **Embedding Model** | Converts text to vectors for semantic search |
# | **Memory Stores** | Separate vector stores for different memory types |
# | **MemoryManager** | Unified interface for all memory operations |
# 
# ### Database Connection

# <!-- edu-bridge:2f7cb99e -->
# ### Oracle Bootstrap
# 
# Oracle setup runs first to verify the database runtime is ready for memory operations. It establishes the infrastructure foundation that every later step depends on.

# <!-- edu-bridge:b0119a96 -->
# ### Connection Session
# 
# A live Oracle connection is created here and shared across all memory components. With infrastructure ready from the previous step, this turns setup into an active session.

# In[ ]:


from helper import suppress_warnings

# Warning control
suppress_warnings()

from helper import load_env, setup_oracle_database, connect_to_oracle

load_env()

# One-time admin setup: configures tablespace, vector memory, and VECTOR user
setup_oracle_database()

# Connect as the VECTOR user for all subsequent operations
database_connection = connect_to_oracle(
    user="VECTOR",
    password="VectorPwd_2025",
    dsn="127.0.0.1:1521/FREEPDB1",
    program="devrel.deeplearning.course_1",
)

print("Using user:", database_connection.username)


# ### Models and Embedding

# <!-- edu-bridge:3282ebc3 -->
# ### LLM And Embeddings
# 
# The OpenAI client and embedding model are initialized to power summarization and vector retrieval. After database connectivity, this adds the model-side capabilities for memory intelligence.

# In[ ]:


from openai import OpenAI
from langchain_huggingface import HuggingFaceEmbeddings

client = OpenAI()

# Initialize the embedding model
embedding_model = HuggingFaceEmbeddings(
    model_name="sentence-transformers/paraphrase-mpnet-base-v2"
)


# ### Memory Stores and Managers

# <!-- edu-bridge:9add47ef -->
# ### Memory Table Names
# 
# Canonical names are defined for each memory store so setup and queries stay consistent. This prepares the storage schema used throughout the notebook.

# In[ ]:


# Table names for each memory type
CONVERSATIONAL_TABLE = "CONVERSATIONAL_MEMORY"
KNOWLEDGE_BASE_TABLE = "SEMANTIC_MEMORY"
WORKFLOW_TABLE = "WORKFLOW_MEMORY"
TOOLBOX_TABLE = "TOOLBOX_MEMORY"
ENTITY_TABLE = "ENTITY_MEMORY"
SUMMARY_TABLE = "SUMMARY_MEMORY"
TOOL_LOG_TABLE = "TOOL_LOG_MEMORY"


# ### Clean Slate: Drop Existing Tables
# 
# <p style="background-color:#ff9a94; padding:15px; border-width:3px; border-color:#f5ecda; border-style:solid; border-radius:6px"> ⏳ <b>Note:</b> To ensure this lesson runs correctly regardless of whether previous lessons have been executed, we drop all memory tables before recreating them by running the cell below. This guarantees a clean starting state with consistent distance strategy and no stale data for the lesson.</p>

# In[ ]:


ALL_TABLES = [
    CONVERSATIONAL_TABLE,
    KNOWLEDGE_BASE_TABLE,
    WORKFLOW_TABLE,
    TOOLBOX_TABLE,
    ENTITY_TABLE,
    SUMMARY_TABLE,
    TOOL_LOG_TABLE]

# Drop existing tables to start fresh
for table in ALL_TABLES:
    try:
        with database_connection.cursor() as cur:
            cur.execute(f"DROP TABLE {table} PURGE")
            print(f"  - {table} (dropped)")
    except Exception as e:
        if "ORA-00942" in str(e):
            print(f"  - {table} (not exists)")
        else:
            print(f"  ✗ {table}: {e}")

database_connection.commit()


# <!-- edu-bridge:39b83051 -->
# ### Conversation Table Setup
# 
# The conversational SQL table is created or reused for thread-level message persistence. It applies the naming decisions from the previous step to a concrete memory component.

# In[ ]:


# Create or retrieve the conversational history table
from helper import create_conversational_history_table, create_tool_log_table
CONVERSATION_HISTORY_TABLE = create_conversational_history_table(database_connection, CONVERSATIONAL_TABLE)
TOOL_LOG_HISTORY_TABLE = create_tool_log_table(database_connection, TOOL_LOG_TABLE)


# <!-- edu-bridge:35a5c92e -->
# ### Store Manager Wiring
# 
# Vector stores are wired through `StoreManager`, then handles are retrieved for downstream use. The storage layer now expands from conversation memory into multi-memory support.

# In[ ]:


from langchain_oracledb.vectorstores import OracleVS
from langchain_community.vectorstores.utils import DistanceStrategy
from helper import StoreManager

# Create StoreManager instance
store_manager = StoreManager(
    client=database_connection,
    embedding_function=embedding_model,
    table_names={
        'knowledge_base': KNOWLEDGE_BASE_TABLE,
        'workflow': WORKFLOW_TABLE,
        'toolbox': TOOLBOX_TABLE,
        'entity': ENTITY_TABLE,
        'summary': SUMMARY_TABLE,
    },
    distance_strategy=DistanceStrategy.EUCLIDEAN_DISTANCE,
    conversational_table=CONVERSATION_HISTORY_TABLE,
    tool_log_table=TOOL_LOG_HISTORY_TABLE,
)

# Get all stores via the manager
conversation_table = store_manager.get_conversational_table()
knowledge_base_vs = store_manager.get_knowledge_base_store()
workflow_vs = store_manager.get_workflow_store()
toolbox_vs = store_manager.get_toolbox_store()
entity_vs = store_manager.get_entity_store()
summary_vs = store_manager.get_summary_store()
tool_log_table = store_manager.get_tool_log_table()

print("✅ All stores loaded via StoreManager")


# <!-- edu-bridge:0c3f0546 -->
# ### Memory Runtime Assembly
# 
# `MemoryManager` and `Toolbox` are composed into the working runtime. Raw stores from the prior step become high-level operations the agent can call consistently.

# In[ ]:


from helper import MemoryManager, Toolbox

# Initialize the MemoryManager instance
memory_manager = MemoryManager(
    conn=database_connection,
    conversation_table=conversation_table,
    knowledge_base_vs=knowledge_base_vs,
    workflow_vs=workflow_vs,
    toolbox_vs=toolbox_vs,
    entity_vs=entity_vs,
    summary_vs=summary_vs,
    tool_log_table=TOOL_LOG_HISTORY_TABLE
)

# Initialize Toolbox with embedding function
toolbox = Toolbox(memory_manager, client, embedding_model)

print("✅ MemoryManager and Toolbox initialized")


# **Part 1 Takeaway:** We now have a complete infrastructure with database connectivity, embedding capabilities, and organized memory stores. The `MemoryManager` provides a clean interface to read/write different memory types, while the `Toolbox` allows us to register functions that the agent can discover and call.
# 
# ---
# 
# ## Part 2: Context Window Management and Summarization
# 
# Large Language Models have finite context windows. When conversations grow long, we face a critical challenge: how do we preserve important information while staying within token limits?
# 
# This section implements the core memory consolidation pipeline:
# 
# ```
# Long Conversation → Monitor Usage → Summarize → Store Summary → Mark Original as Processed
# ```
# 
# ### Why This Matters
# 
# | Problem | Solution |
# |---------|----------|
# | Context overflow crashes the agent | Monitor token usage and summarize proactively |
# | Summaries lose important details | Capture technical, emotional, and entity information |
# | Can't access original conversation | Store summary ID links back to original messages |
# | Re-summarizing already processed messages | Mark messages with summary_id after processing |
# 
# ### Token Counting and Monitoring

# <!-- edu-bridge:c16580e7 -->
# ### Token Budget Definition
# 
# Model context limits are declared to frame when compaction should occur. This starts the transition from setup to context-window management.

# In[ ]:


# Model token limits (for context management)
MODEL_TOKEN_LIMITS = {
    "gpt-5-mini": 256000,
}


# <!-- edu-bridge:3c626cd9 -->
# ### Usage Calculator
# 
# A usage estimator converts context length into token utilization percentage. It relies on the token budget above and provides the trigger signal for summarization.

# In[ ]:


# Context window calculator - returns percentage used
def calculate_context_usage(context: str, model: str = "gpt-5-mini") -> dict:
    """Calculate context window usage as percentage."""
    estimated_tokens = len(context) // 4  # ~4 chars per token
    max_tokens = MODEL_TOKEN_LIMITS.get(model, 128000)
    percentage = (estimated_tokens / max_tokens) * 100
    return {"tokens": estimated_tokens, "max": max_tokens, "percent": round(percentage, 1)}


# ### Summarization Functions
# 
# The summarization pipeline captures four types of information:
# 1. **Technical Information** — Facts, code, configurations, solutions
# 2. **Emotional Context** — Tone, sentiment, urgency levels
# 3. **Entities & References** — People, systems, projects mentioned
# 4. **Action Items & Decisions** — Next steps, agreements, pending tasks

# <!-- edu-bridge:758e267b -->
# ### Summary Generation Function
# 
# Summary generation is defined with parsing and fallback behavior for robust outputs. This is the core compaction mechanism used when context becomes too large.

# In[ ]:


import uuid

def summarise_context_window(content: str, memory_manager, llm_client, model: str = "gpt-5-mini") -> dict:
    """
    Summarise content using an LLM and store in summary memory.
    """
    cleaned = (content or "").strip()
    if not cleaned:
        return {"status": "nothing_to_summarize"}

    def _message_text(resp) -> str:
        msg = resp.choices[0].message
        payload = getattr(msg, "content", None)
        if isinstance(payload, str):
            return payload.strip()
        if isinstance(payload, list):
            parts = []
            for item in payload:
                if isinstance(item, dict):
                    txt = item.get("text")
                    if isinstance(txt, str) and txt.strip():
                        parts.append(txt.strip())
            return "\n".join(parts).strip()
        return ""

    summary_prompt = f"""You are creating durable memory for an AI research assistant.
Summarize this conversation so it can be resumed accurately later.

Output with exactly these headings:
### Technical Information
### Emotional Context
### Entities & References
### Action Items & Decisions

Rules:
- Keep concrete details (names, dates, APIs, errors, decisions).
- Separate confirmed facts from open questions where relevant.
- Do not invent information.
- Keep it concise and useful for continuation.

Conversation:
{cleaned[:6000]}"""

    response = llm_client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": summary_prompt}],
        max_completion_tokens=4000
    )
    summary = _message_text(response)

    # Retry once with a simpler prompt if output is empty.
    if not summary:
        retry_prompt = f"""Summarize this conversation in <= 180 words using these headings:
### Technical Information
### Emotional Context
### Entities & References
### Action Items & Decisions

Conversation:
{cleaned[:6000]}"""
        retry = llm_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": retry_prompt}],
            max_completion_tokens=4000
        )
        summary = _message_text(retry)

    if not summary:
        excerpt = cleaned[:500].replace("\n", " ").strip()
        summary = (
            "### Technical Information\n"
            f"{excerpt or '(No content provided.)'}\n\n"
            "### Emotional Context\n"
            "Not available from model output.\n\n"
            "### Entities & References\n"
            "Not available from model output.\n\n"
            "### Action Items & Decisions\n"
            "Not available from model output."
        )

    desc_prompt = f"""Create a short 8-12 word label for this summary.
Return ONLY the label.

Summary:
{summary}"""

    desc_response = llm_client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": desc_prompt}],
        max_completion_tokens=2000
    )
    description = _message_text(desc_response) or "Conversation summary"

    summary_id = str(uuid.uuid4())[:8]
    memory_manager.write_summary(summary_id, cleaned, summary, description)

    return {"id": summary_id, "description": description, "summary": summary}


# ### Agent Tools for Memory Operations
# 
# These tools are registered with the Toolbox so the agent can call them during execution.

# <!-- edu-bridge:3718c3b7 -->
# ### Summary Expansion Tool
# 
# `expand_summary` is registered so compressed context can be expanded on demand. Compaction and recoverability stay paired, which is critical for agent reliability.

# In[ ]:


# Summary tools for the agent
@toolbox.register_tool(augment=True)
def expand_summary(summary_id: str) -> str:
    """
    Expand a summary reference to retrieve the original conversations.

    Use when you need more details from a [Summary ID: xxx] reference.
    Returns all original messages that were summarized, in chronological order with timestamps.
    """
    # Get the summary text for context
    summary_text = memory_manager.read_summary_memory(summary_id)

    # Get the original conversations that were summarized
    original_conversations = memory_manager.read_conversations_by_summary_id(summary_id)

    return f"""
            ## Summary Context
                {summary_text}

                {original_conversations}
        """


# <!-- edu-bridge:936738a1 -->
# ### Conversation Summarizer
# 
# Thread-level summarization is implemented over unsummarized rows and tagged with `summary_id`. This provides precise consolidation and traceability back to source units.

# In[ ]:


def summarize_conversation(thread_id: str) -> dict:
    """
    Summarize all unsummarized messages in a thread and mark those exact units.

    This function:
    1. Reads unsummarized message rows from the thread
    2. Generates a structured summary via LLM
    3. Stores the summary in summary memory
    4. Marks the exact source rows with summary_id
    5. Returns the summary object for continued context
    """
    thread_id = str(thread_id)

    # Read raw unsummarized conversation units (IDs + content)
    with memory_manager.conn.cursor() as cur:
        cur.execute(f"""
            SELECT id, role, content, timestamp
            FROM {memory_manager.conversation_table}
            WHERE thread_id = :thread_id AND summary_id IS NULL
            ORDER BY timestamp ASC
        """, {"thread_id": thread_id})
        rows = cur.fetchall()

    if not rows:
        return {"status": "nothing_to_summarize"}

    # Build transcript from unsummarized units only
    message_ids = []
    transcript_lines = []
    for msg_id, role, content, timestamp in rows:
        message_ids.append(msg_id)
        ts_str = timestamp.strftime('%Y-%m-%d %H:%M:%S') if timestamp else "Unknown"
        transcript_lines.append(f"[{ts_str}] [{str(role).upper()}] {content}")

    transcript = "\n".join(transcript_lines)

    # Summarize the exact transcript
    result = summarise_context_window(transcript, memory_manager, client)
    if result.get("status") == "nothing_to_summarize":
        return result

    summary_id = result["id"]

    # Mark the exact source rows with the generated summary_id
    with memory_manager.conn.cursor() as cur:
        cur.executemany(f"""
            UPDATE {memory_manager.conversation_table}
            SET summary_id = :summary_id
            WHERE id = :id AND summary_id IS NULL
        """, [{"summary_id": summary_id, "id": msg_id} for msg_id in message_ids])
    memory_manager.conn.commit()

    result["num_messages_summarized"] = len(message_ids)

    print(f"✅ Conversation summarized: [Summary ID: {summary_id}]")
    print(f"   Description: {result['description']}")
    print(f"   Messages marked summarized: {len(message_ids)}")

    return result


# <!-- edu-bridge:16abf75a -->
# ### Offload Policy
# 
# A simple offload policy compacts conversation-heavy context into summary references. It keeps the context window lean while preserving a retrieval path to details.

# In[ ]:


def offload_to_summary(context: str, memory_manager, llm_client, thread_id: str = None) -> tuple:
    """
    Simple context compaction:
    - If thread_id is provided, summarize unsummarized conversation units for that thread.
    - Otherwise, summarize the provided context string.
    - Replace only conversation-heavy context and keep other memory segments.
    """
    raw_context = (context or "").strip()

    if thread_id:
        result = summarize_conversation(thread_id)
    else:
        result = summarise_context_window(raw_context, memory_manager, llm_client)

    if result.get("status") == "nothing_to_summarize":
        return raw_context, []

    summary_ref = f"[Summary ID: {result['id']}] {result['description']}"
    conversation_stub = (
        "## Conversation Memory\n"
        "Older conversation content was summarized to reduce context size.\n"
        "Use Summary Memory references + expand_summary(id) for full detail."
    )

    # Replace only conversation section, preserve other memory sections.
    compact_context = raw_context
    if "## Conversation Memory" in compact_context:
        lines = compact_context.splitlines()
        rebuilt = []
        in_conversation = False
        inserted_stub = False

        for line in lines:
            if line.startswith("## "):
                heading = line.strip()
                if heading == "## Conversation Memory":
                    in_conversation = True
                    if not inserted_stub:
                        if rebuilt and rebuilt[-1].strip():
                            rebuilt.append("")
                        rebuilt.extend(conversation_stub.splitlines())
                        rebuilt.append("")
                        inserted_stub = True
                    continue
                in_conversation = False

            if not in_conversation:
                rebuilt.append(line)

        compact_context = "\n".join(rebuilt).strip()
    else:
        compact_context = f"{conversation_stub}\n\n{compact_context}".strip()

    if "## Summary Memory" in compact_context:
        compact_context = f"{compact_context}\n{summary_ref}".strip()
    else:
        compact_context = (
            f"{compact_context}\n\n"
            "## Summary Memory\n"
            "Use expand_summary(id) to retrieve full underlying content.\n"
            f"{summary_ref}"
        ).strip()

    return compact_context, [result]


# <!-- edu-bridge:bf92accc -->
# ### Agent Summarize Tool
# 
# `summarize_and_store` exposes summarization as an agent-callable tool. The offload capability now becomes available during autonomous execution.

# In[ ]:


@toolbox.register_tool(augment=True)
def summarize_and_store(text: str, thread_id: str = None) -> str:
    """
    Summarize long text and store in memory.

    If thread_id is provided, summarize unsummarized conversation units from that thread
    and mark exactly those units with the generated summary_id.
    """
    if thread_id:
        result = summarize_conversation(thread_id)
        if result.get("status") == "nothing_to_summarize":
            return f"No unsummarized messages found for thread {thread_id}."
        return f"Stored as [Summary ID: {result['id']}] {result['description']}"

    result = summarise_context_window(text, memory_manager, client)
    if result.get("status") == "nothing_to_summarize":
        return "No content to summarize."
    return f"Stored as [Summary ID: {result['id']}] {result['description']}"


# <!-- edu-bridge:8315929b -->
# ### Context Monitor Utility
# 
# A monitor function maps usage into `ok`, `warning`, and `critical` states. This closes the helper pipeline with clear operational thresholds.

# In[ ]:


def monitor_context_window(context: str, model: str = "gpt-5-mini") -> dict:
    """
    Monitor the current context window and return capacity utilization.

    Args:
        context: The current context string to measure
        model: The model being used (to determine max tokens)

    Returns:
        dict with:
        - tokens: Estimated token count
        - max: Maximum tokens for the model
        - percent: Percentage of capacity used
        - status: 'ok', 'warning', or 'critical' based on usage
    """
    result = calculate_context_usage(context, model)

    # Add status indicator
    if result['percent'] < 50:
        result['status'] = 'ok'
    elif result['percent'] < 80:
        result['status'] = 'warning'
    else:
        result['status'] = 'critical'

    return result


# **Part 2 Takeaway:** We've built a complete summarization pipeline that monitors context usage, generates structured summaries, and provides tools for the agent to expand summaries when needed.
# 
# ---
# 
# ## Part 3: Testing the Memory Pipeline
# 
# Now let's verify that our memory consolidation system works end-to-end.
# 
# ### Test Workflow
# 
# | Step | Action | Verification |
# |------|--------|--------------|
# | 1 | Create test conversation | Messages stored in conversational memory |
# | 2 | Monitor context usage | Token count and percentage calculated |
# | 3 | Summarize conversation | Summary captures key information |
# | 4 | Expand summary | Original messages retrievable |
# | 5 | Verify marking | Summarized messages marked as processed |
# 
# ### Step 1: Create Test Conversation

# <!-- edu-bridge:025b1d47 -->
# ### Test Thread Creation
# 
# A realistic multi-turn conversation is seeded to validate the full summarization lifecycle. The environment and utilities are now exercised end to end.

# In[ ]:


# Step 1: Create a test thread with sample conversations
import time
from helper import SAMPLE_RESEARCH_CONVERSATION

TEST_THREAD_ID = f"test_summary_{int(time.time())}"

# Use the sample conversation from helper.py (30 messages about research papers)
test_messages = SAMPLE_RESEARCH_CONVERSATION

print(f"📝 Creating test thread: {TEST_THREAD_ID}")
print("-" * 50)

for role, content in test_messages:
    memory_manager.write_conversational_memory(content, role, TEST_THREAD_ID)
    print(f"[{role.upper()}] {content[:70]}...")
    time.sleep(0.05)  # Small delay to ensure distinct timestamps

print(f"✅ Added {len(test_messages)} messages to thread")


# ### Step 2: Monitor Context Usage

# <!-- edu-bridge:85f1bddd -->
# ### Pre-Summary Measurement
# 
# Baseline context usage is measured before any compression. This creates a reference point for evaluating the effect of summarization.

# In[ ]:


# Step 2: Monitor context usage before summarization
current_context = memory_manager.read_conversational_memory(TEST_THREAD_ID, limit=100)

print("📊 CONTEXT WINDOW MONITOR (Before Summarization)")
print("=" * 50)
usage = monitor_context_window(current_context)
print(f"  Tokens: {usage['tokens']:,}")
print(f"  Max: {usage['max']:,}")
print(f"  Usage: {usage['percent']}%")
print(f"  Status: {usage['status'].upper()}")
print()
print("📄 Current conversation content:")
print("-" * 50)
print(current_context)


# ### Step 3: Summarize the Conversation

# <!-- edu-bridge:99c09821 -->
# ### Summarization Execution
# 
# The summarization pipeline runs and produces a durable summary artifact. This demonstrates how verbose history is compacted for continued reasoning.

# In[ ]:


# Step 3: Summarize the conversation
print("🔄 SUMMARIZING CONVERSATION")
print("=" * 50)

summary_result = summarize_conversation(TEST_THREAD_ID)

print(f"\n📋 Summary Result:")
print(f"  ID: {summary_result['id']}")
print(f"  Description: {summary_result['description']}")
print(f"\n📝 Full Summary (for new context window):")
print("-" * 50)
print(summary_result['summary'])


# ### Step 4: Expand the Summary

# <!-- edu-bridge:be6ba99c -->
# ### Summary Expansion Check
# 
# The new summary reference is expanded to recover original chronology and detail. It confirms that compact memory remains reversible when precision is needed.

# In[ ]:


# Step 4: Expand the summary to retrieve original conversations
print("🔍 EXPANDING SUMMARY - Retrieving Original Conversations")
print("=" * 50)
print(f"Summary ID: {summary_result['id']}")
print()

# Access the function via toolbox._tools_by_name (since decorator returns ID, not function)
expand_fn = toolbox._tools_by_name['expand_summary']
expanded = expand_fn(summary_result['id'])
print(expanded)


# ### Step 5: Verify the Pipeline

# <!-- edu-bridge:d74e0d45 -->
# ### Post-Summary Verification
# 
# API-level and DB-level checks verify that summarized rows are tagged and omitted from unsummarized reads. The consolidation loop is validated with explicit evidence.

# In[ ]:


# Step 5: Verify - After summarization, unsummarized messages should be empty
print("✅ VERIFICATION - Thread After Summarization")
print("=" * 50)

# High-level check via memory API (should show no unsummarized messages)
remaining = memory_manager.read_conversational_memory(TEST_THREAD_ID, limit=100)
print("Unsummarized messages in thread (memory API):")
print(remaining)

# Ground-truth check at DB row level
with memory_manager.conn.cursor() as cur:
    cur.execute(f"""
        SELECT COUNT(*)
        FROM {memory_manager.conversation_table}
        WHERE thread_id = :thread_id AND summary_id IS NULL
    """, {"thread_id": TEST_THREAD_ID})
    unsummarized_count = cur.fetchone()[0]

    cur.execute(f"""
        SELECT COUNT(*)
        FROM {memory_manager.conversation_table}
        WHERE thread_id = :thread_id AND summary_id IS NOT NULL
    """, {"thread_id": TEST_THREAD_ID})
    summarized_count = cur.fetchone()[0]

    cur.execute(f"""
        SELECT DISTINCT summary_id
        FROM {memory_manager.conversation_table}
        WHERE thread_id = :thread_id AND summary_id IS NOT NULL
        ORDER BY summary_id
    """, {"thread_id": TEST_THREAD_ID})
    summary_ids = [row[0] for row in cur.fetchall()]

print(f"\nDB verification:")
print(f"  Unsummarized rows: {unsummarized_count}")
print(f"  Summarized rows: {summarized_count}")
print(f"  Summary IDs applied: {summary_ids}")

if unsummarized_count == 0 and summarized_count > 0:
    print("✅ PASS: conversation units summarized and tagged with summary_id")
else:
    print("⚠️ CHECK: expected 0 unsummarized rows and >0 summarized rows")

print("\n" + "=" * 50)
print("🎉 TEST COMPLETE!")
print("=" * 50)
print("""
Summary of what happened:
1. ✅ Created test conversation with 30 messages
2. ✅ Monitored context window usage
3. ✅ Summarized conversation with a structured LLM prompt
4. ✅ Expanded summary to retrieve original messages with timestamps
5. ✅ Verified source conversation rows are marked with summary_id
""")


# **Part 3 Takeaway:** The test demonstrates the complete memory consolidation cycle: conversations are stored, monitored, summarized when needed, and marked to prevent reprocessing.
# 
# ---
# 
# ## Lesson Summary
# 
# In this lesson, you learned how to build a self-managing memory system for AI agents:
# 
# | Capability | Implementation |
# |------------|----------------|
# | **Monitor** | `calculate_context_usage()` tracks token consumption |
# | **Summarize** | `summarise_context_window()` extracts structured information |
# | **Store** | Summaries persist in `SUMMARY_MEMORY` with links to originals |
# | **Expand** | `expand_summary()` tool retrieves original conversations |
# | **Self-Update** | `mark_as_summarized()` prevents re-processing |
# 
# **Key Insight:** Memory consolidation isn't just about compression—it's about *structured extraction* that preserves technical details, emotional context, entities, and action items.
