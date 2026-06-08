#!/usr/bin/env python
# coding: utf-8

# # Serving LLMs Efficiently with vLLM - Part II
# 
# In this notebook, you'll learn how to:
# 1. Launch a **vLLM inference server** serving a real model
# 2. Query it using the OpenAI-compatible API
# 3. **Explore model behavior** with logprobs and sampling parameters
# 4. Observe **continuous batching** and **KV cache** usage via live Prometheus metrics
# 5. Demonstrate **prefix caching**

# ## From Quantization to Serving

# In an earlier lesson, you used `llm-compressor` to quantize a model's weights from 16-bit to 4-bit using GPTQ. Now you'll **serve** a model with vLLM and interact with it through its OpenAI-compatible API.
# 
# [vLLM](https://github.com/vllm-project/vllm) is an open-source LLM inference engine that integrates key serving optimizations:
# 
# | Feature | Benefit |
# |:--|:--|
# | **Continuous batching** | Schedules at the token level: no wasted compute waiting for the longest request |
# | **PagedAttention** | Manages KV cache in fixed-size blocks: near-zero memory waste |
# | **Prefix caching** | Reuses KV cache for shared prompt prefixes across requests |
# | **Quantization support** | Natively serves GPTQ, AWQ, and compressed-tensors models |
# | **OpenAI-compatible API** | Drop-in replacement for applications already using the OpenAI client |

# ## Step 1: Start Your vLLM Server

# In this learning environment, a pre-warmed vLLM server is provided to you to use with Qwen3-0.6B, so the server is already running and you'll use the code cells in this notebook to interact with it.

# **How to serve a model with vLLM?**
# 
# To serve your model with vLLM, you'd need to run this command in the terminal. 
# 
# ```bash
# vllm serve Qwen/Qwen3-0.6B --dtype=bfloat16 --max-model-len 4096
# ```
# 
# You can find the installation details [here](https://docs.vllm.ai/en/latest/getting_started/installation/).
# 
# - **`vllm serve`**: launches vLLM's built-in inference server. It loads the model weights into the engine (with PagedAttention, continuous batching, and prefix caching enabled by default) and exposes it over HTTP on port 8000.
# - **`Qwen/Qwen3-0.6B`**: the model identifier on the [Hugging Face Hub](https://huggingface.co/Qwen/Qwen3-0.6B). On first run, vLLM downloads the weights, tokenizer, and config from Hugging Face into the local cache (`~/.cache/huggingface/hub`), then loads them into memory. Subsequent runs reuse the cached files.
# - **`--dtype=bfloat16`**: loads the weights in BF16 precision. 
# - **`--max-model-len 4096`**: caps the context window (prompt + generation) at 4096 tokens. 
# 
# > **Note:** You can also serve the quantized model from the previous lesson, but that requires a GPU because its W4A16 format only has optimized runtime support on GPUs. Since this learning environment runs on CPU, the original model is the one served through vLLM.
# 
# vLLM wraps the model in an **OpenAI-compatible HTTP API**. It implements the same routes the OpenAI SDK calls (`/v1/models`, `/v1/chat/completions`, `/v1/completions`, `/v1/embeddings`) with the same request and response shapes.

# So here let's check if it's running. 

# In[ ]:


import warnings
warnings.filterwarnings("ignore")

import time, requests, json, os, math, sys

VLLM_URL = "http://localhost:8000"
os.makedirs("outputs", exist_ok=True)

print("Waiting for vLLM server...")
for attempt in range(60):
    try:
        r = requests.get(f"{VLLM_URL}/v1/models", timeout=5)
        if r.status_code == 200:
            MODEL = r.json()["data"][0]["id"]
            break
    except requests.ConnectionError:
        pass
    time.sleep(5)
    if attempt % 6 == 5:
        print(f"  Still waiting... ({(attempt + 1) * 5}s elapsed)")
else:
    raise RuntimeError(
        "vLLM server not reachable after 5 minutes."
    )

print(f"Connected to {VLLM_URL} — model: {MODEL}")


# > **Note:** The vLLM server might need 1 or 2 minutes to be ready.

# ## Your First Local LLM Request

# vLLM exposes an OpenAI-compatible API, so we use the standard `openai` Python client.

# In[ ]:


from openai import OpenAI
client = OpenAI(base_url=f"{VLLM_URL}/v1", api_key="unused")


# Qwen3 supports a *thinking mode* that generates chain-of-thought reasoning before answering. We disable it with `enable_thinking: False` to keep responses short and predictable.

# In[ ]:


start = time.time()
resp = client.chat.completions.create(
    model=MODEL,
    messages=[{"role": "user", 
               "content": "What is PagedAttention in one sentence?"}],
    max_tokens=80,
    temperature=0.7,
    top_p=0.8,
    extra_body={"top_k": 20, 
                "chat_template_kwargs": {"enable_thinking": False}},
)
elapsed = time.time() - start

print(f"Response ({elapsed:.2f}s, {resp.usage.completion_tokens} tokens):")
print(resp.choices[0].message.content)
print(f"\nUsage: {resp.usage.prompt_tokens} prompt + "
      f"{resp.usage.completion_tokens} completion = {resp.usage.total_tokens} total")


# ## Exploring Model Behavior

# Beyond simple chat, the vLLM API lets you inspect model internals and control generation. For example, **Logprobs:** allows you to see the model's confidence in each token it generates, plus the alternatives it considered

# In[ ]:


resp = client.chat.completions.create(
    model=MODEL,
    messages=[{"role": "user", "content": "The capital of France is"}],
    max_tokens=15,
    temperature=0.0,
    logprobs=True,
    top_logprobs=5,
    extra_body={"chat_template_kwargs": {"enable_thinking": False}},
)

print(f"Response: {resp.choices[0].message.content.strip()}\n")
print("Token-by-token probabilities:\n")

for tok in resp.choices[0].logprobs.content[:8]:
    print(f"  Chosen: '{tok.token}'  (logprob {tok.logprob:.2f})")
    if tok.top_logprobs:
        for alt in tok.top_logprobs[:5]:
            pct = math.exp(alt.logprob) * 100
            bar = "\u2588" * min(20, max(1, int(pct / 5)))
            print(f"    {pct:5.1f}%  {bar}  '{alt.token}'")
    print()


# ## Observing vLLM Under the Hood

# vLLM exposes a Prometheus-compatible **`/metrics`** endpoint (it's a format that is easy to scrape). Key metrics to watch:
# 
# - **`num_requests_running / waiting`**: how many requests are active vs queued
# - **`gpu_cache_usage_perc`** (or `cpu_cache_usage_perc`): KV cache memory pressure
# - **`prompt_tokens_total / generation_tokens_total`**: cumulative token counts
# 

# In[ ]:


def get_vllm_metrics(base_url=VLLM_URL):
    """Scrape vLLM Prometheus /metrics and return {name: value}."""
    r = requests.get(f"{base_url}/metrics")
    metrics = {}
    for line in r.text.split("\n"):
        if line.startswith("#") or not line.strip():
            continue
        name = line.split("{")[0].split()[0]
        try:
            metrics[name] = float(line.split()[-1])
        except (ValueError, IndexError):
            continue
    return metrics

metrics = get_vllm_metrics()
print("Current vLLM Metrics:")
for key in ["vllm:num_requests_running", "vllm:num_requests_waiting",
            "vllm:gpu_cache_usage_perc", "vllm:cpu_cache_usage_perc",
            "vllm:prompt_tokens_total", "vllm:generation_tokens_total"]:
    if key in metrics:
        print(f"  {key.replace('vllm:', '')}: {metrics[key]:g}")

with open("outputs/metrics_snapshot.json", "w") as f:
    json.dump(metrics, f, indent=2)
print(f"\nFull metrics saved to outputs/metrics_snapshot.json")


# ## Continuous Batching in Action

# vLLM uses **continuous batching** (iteration-level scheduling): when a request finishes generating, its slot is immediately filled by the next waiting request.
# 
# Let's send 5 requests **concurrently** and watch the metrics while they run.

# In[ ]:


import concurrent.futures

prompts = [
    "What is quantization?",
    "Explain KV caching briefly.",
    "What is continuous batching?",
    "Why is LLM inference memory-bound?",
    "What is PagedAttention?",
]

def _ask(prompt):
    return client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=60, temperature=0.7,
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
    )

before = get_vllm_metrics()
print(f"Sending {len(prompts)} concurrent requests...\n")
start = time.time()

with concurrent.futures.ThreadPoolExecutor(
    max_workers=len(prompts)) as pool:
    futures = {pool.submit(_ask, p): p for p in prompts}
    time.sleep(0.5)
    during = get_vllm_metrics()
    running = during.get("vllm:num_requests_running", "--")
    waiting = during.get("vllm:num_requests_waiting", "--")
    print(f"  [mid-flight]  running: {running}  |  waiting: {waiting}")

    for f in concurrent.futures.as_completed(futures):
        resp = f.result()
        print(f"  done: \"{futures[f][:40]}\" -> {resp.usage.completion_tokens} tokens")

elapsed = time.time() - start
after = get_vllm_metrics()
tokens = after.get("vllm:generation_tokens_total", 0) - before.get(
    "vllm:generation_tokens_total", 0)

print(f"\nAll {len(prompts)} completed in {elapsed:.2f}s")
if tokens > 0:
    print(f"Tokens generated: {tokens:g}  |  ~{tokens / elapsed:.1f} tokens/s")


# >**Note**: The first time you run this cell, you may see running: 0 or running: 1 instead of 5. Run the cell again and it will show 5. The metric is checked just once, a fraction of a second after sending the requests. That single reading is taken so soon that the requests may not have reached the server yet, so it can show 0 (nothing running and nothing queued) even though all five are about to run together. Sampling repeatedly instead shows the true peak of 5.

# **What Just Happened**
# 
# vLLM's scheduler received all 5 requests and processed them using **continuous batching**. Each generation step produces tokens for every request in the batch, and completed requests free their slots immediately.
# 
# vLLM's **PagedAttention** is key to making this work at scale: the KV cache is divided into fixed-size blocks that can be placed anywhere in memory. When a request finishes, its blocks are immediately available for reuse — no fragmentation.

# ## Prefix Caching

# Many applications share a long **system prompt** across requests. Without prefix caching, vLLM recomputes the KV cache for the shared prefix every time.
# 
# With **prefix caching**, vLLM detects shared prefixes and **reuses cached KV entries**. The first request pays the full prefill cost; subsequent requests skip it.
# 
# Let's send 5 requests with the same system prompt and compare timing.

# In[ ]:


SYSTEM_PROMPT = (
    "You are a helpful AI teaching assistant for a course on "
    "LLM optimization. You specialize in explaining concepts like "
    "quantization, inference optimization, and model serving. Keep "
    "answers concise -- one or two sentences."
)

questions = [
    "What is weight quantization?",
    "How does vLLM handle memory?",
    "What is continuous batching?",
    "Why use prefix caching?",
    "What is GPTQ?",
]

before = get_vllm_metrics()
timings = []
tok_counts = []

print("Sending 5 requests with the SAME system prompt...\n")
for i, q in enumerate(questions):
    t0 = time.time()
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": q},
        ],
        max_tokens=60, temperature=0.7,
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
    )
    dt = time.time() - t0
    timings.append(dt)
    tok_counts.append(resp.usage.completion_tokens)
    tokens = resp.usage.completion_tokens
    ms_per_tok = (dt / tokens * 1000) if tokens > 0 else 0.0
    print(f"  [{i+1}] {q:<35} {dt:.2f}s  ({tokens} tok, {ms_per_tok:.0f} ms/tok)")

after = get_vllm_metrics()

prefix_before = before.get("vllm:prefix_cache_queries_total", 0)
prefix_after = after.get("vllm:prefix_cache_queries_total", 0)

print(f"\nPrefix cache queries: {prefix_before:g} -> {prefix_after:g}  (+{prefix_after - prefix_before:g})")

cache_keys = [k for k in after if "prefix" in k.lower() 
              or "cache_hit" in k.lower()]
for k in sorted(cache_keys):
    b, a = before.get(k, 0), after.get(k, 0)
    if a != b and k != "vllm:prefix_cache_queries_total":
        print(f"  {k}: {b:g} -> {a:g}")

print("\n The increasing prefix_cache_queries count confirms vLLM is ")
print("checking and reusing cached KV blocks for the shared system prompt.")


# **Why Prefix Caching Matters**
# 
# The `prefix_cache_queries` metric increasing confirms that vLLM is reusing cached KV entries for the shared system prompt. With your short system prompt (~50 tokens), the savings are small compared to total generation time. But in production with **long** system prompts (thousands of tokens of instructions or few-shot examples), prefix caching eliminates a large chunk of prefill compute on every request.

# ---
# 
# ## (Optional) KV Cache Size Visualization for Qwen3-0.6B

# The KV cache stores key and value tensors from the attention mechanism. It grows **linearly** with sequence length and concurrent requests.

# In[ ]:


num_layers = 28
num_kv_heads = 8     # GQA: 16 Q heads, 8 KV heads
head_dim = 128
dtype_bytes = 2      # BF16

per_token = 2 * num_layers * num_kv_heads * head_dim * dtype_bytes

print(f"KV Cache -- Qwen3-0.6B")
print(f"Per token: 2 x {num_layers} x {num_kv_heads} x {head_dim} x {dtype_bytes}"
      f" = {per_token:,} bytes ({per_token // 1024} KB)\n")
print(f"  {'Context':>8}  {'KV Cache':>10}")
print(f"  {'-'*8}  {'-'*10}")
for ctx in [1, 64, 256, 1024, 4096]:
    size = per_token * ctx
    label = f"{size / 1024:.0f} KB" if size < 1024**2 else f"{size / 1024**2:.0f} MB"
    print(f"  {ctx:>7}t  {label:>10}")

print(f"\n  10 concurrent x 4096 ctx = {per_token * 4096 * 10 / 1024**3:.1f} GB")


# ---
# 
# ## (Optional) Thinking Mode

# Qwen3 supports a *thinking mode* where the model generates internal chain-of-thought reasoning (`<think>...</think>`) before the visible answer. This produces better answers but uses **significantly more tokens** — more KV cache, more compute, longer response.
# 
# Let's stream both modes side by side on the same prompt.

# In[ ]:


prompt = "What makes continuous batching better than static batching?"

for label, thinking, max_tok in [
    ("Thinking OFF", False, 80), ("Thinking ON", True, 200)]:
    print(f"=== {label} ===\n")
    start = time.time()
    tokens = 0
    stream = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tok, temperature=0.7, stream=True,
        extra_body={"chat_template_kwargs": {"enable_thinking": thinking}},
    )
    for chunk in stream:
        if chunk.choices[0].delta.content:
            sys.stdout.write(chunk.choices[0].delta.content)
            sys.stdout.flush()
            tokens += 1
    elapsed = time.time() - start
    print(f"\n  [{tokens} tokens, {elapsed:.2f}s]\n")


# ## Summary
# 
# In this notebook, you:
# 
# - Launched a **vLLM server** serving Qwen3-0.6B and connected with the OpenAI client
# - Explored model internals with **logprobs** (token probabilities)
# - Used the **`/metrics` endpoint** to observe KV cache usage and request counts
# - Demonstrated **continuous batching**: sending concurrent requests
# - Demonstrated **prefix caching**: shared system prompts reuse cached KV entries
# - Streamed **thinking mode** to see chain-of-thought reasoning live

# ## Resources

# - [vLLM Github](https://github.com/vllm-project/vllm)
# - [vLLM Docs](https://docs.vllm.ai/en/latest/)
# - [vLLM Installation Instructions](https://docs.vllm.ai/en/latest/getting_started/installation/)
