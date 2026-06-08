#!/usr/bin/env python
# coding: utf-8

# # Measuring What Matters: Benchmarking and Evaluation
# 
# In this notebook, you'll learn how to:
# 1. Run a real **GuideLLM** benchmark against your vLLM server and interpret the results
# 2. Evaluate model quality with **lm_eval** on a standardized task
# 3. Read **published model card data** to understand quantization 
# 4. Reason about whether a quantization tradeoff is worth deploying

# ## Setup

# In this notebook, you're also provided with the **same vLLM server** you used in the previous lesson to query the model Qwen3-0.6B. Now you'll answer: **how good is this deployment, really?** You'll measure two dimensions:
# 
# | Dimension | Question | Tool |
# |:--|:--|:--|
# | **Performance** | How fast and efficiently does the system serve requests? | GuideLLM |
# | **Quality** | How well does the model perform on real tasks? | lm_eval |

# Let's send a quick test request to confirm everything is working.

# In[ ]:


import warnings
warnings.filterwarnings("ignore")

import time, requests, json, os, glob, sys
from openai import OpenAI

VLLM_URL = "http://localhost:8000"

for _ in range(12):
    try:
        r = requests.get(f"{VLLM_URL}/v1/models", timeout=5)
        if r.status_code == 200:
            MODEL = r.json()["data"][0]["id"]
            break
    except requests.ConnectionError:
        time.sleep(5)
else:
    raise RuntimeError("vLLM server not reachable.")

print(f"Connected to {VLLM_URL} — model: {MODEL}")


# In[ ]:


client = OpenAI(base_url=f"{VLLM_URL}/v1", api_key="unused")
resp = client.chat.completions.create(
    model=MODEL,
    messages=[{"role": "user", 
               "content": "What is model quantization in one sentence."}],
    max_tokens=30, temperature=0.7,
    extra_body={"chat_template_kwargs": {"enable_thinking": False}},
)
print(f"{MODEL}: {resp.choices[0].message.content.strip()}")


# ## Benchmarking with GuideLLM

# [GuideLLM](https://github.com/neuralmagic/guidellm) is a benchmarking tool from the vLLM project for evaluating inference performance. It sends requests at controlled rates and records per-request timing.
# 
# | Metric | What it measures |
# |:--|:--|
# | **TTFT** | Time to first token: perceived responsiveness |
# | **ITL** | Inter-token latency: smoothness of streaming |
# | **E2E latency** | Total request time |
# | **Throughput** | Requests/sec and tokens/sec |
# 
# You'll run a **synchronous** profile (one request at a time) with 10 requests.
# 
# > **Note:** `10 requests` is deliberately tiny so the cell finishes quickly in this environment; a real benchmark would use a few hundred to a few thousand requests, or switch to a time-bounded run with --max-seconds.

# In[ ]:


os.makedirs("outputs", exist_ok=True)


# In[ ]:


import subprocess

cmd = [
    sys.executable, "-m", "guidellm", "benchmark",
    "--target", "http://localhost:8000",
    "--model", MODEL,
    "--processor", "Qwen/Qwen3-0.6B",
    "--profile", "synchronous",
    "--max-requests", "10",
    "--data", "prompt_tokens=32,output_tokens=16,samples=32",
    "--output-dir", "./outputs",
]

print(f"Running: {' '.join(cmd)}\n")

result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

if result.returncode == 0:
    print("Benchmark complete!")
    tail = result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout
    print(tail)
else:
    print(f"GuideLLM exited with code {result.returncode}")
    print(f"STDOUT:\n{result.stdout[-1000:]}")
    print(f"STDERR:\n{result.stderr[-1000:]}")


# ## Interpreting Benchmark Results

# GuideLLM saves results as JSON with pre-computed statistics for every metric (means, percentiles, min/max) so you can load the file directly and read the numbers you need.

# In[ ]:


with open("outputs/benchmarks.json") as f:
    report = json.load(f)

bench = report["benchmarks"][0]
metrics = bench["metrics"]
n_requests = metrics["request_totals"]["successful"]

profile_type = bench.get("type") 
print(f"Profile: {profile_type}  |  Requests: {n_requests}\n")

display_metrics = {
    "TTFT (ms)":       "time_to_first_token_ms",
    "ITL (ms)":        "inter_token_latency_ms",
    "E2E Latency (s)": "request_latency",
    "Output tokens":   "output_token_count",
}

print(f"{'Metric':<20} {'Mean':>8} {'p50':>8} {'p95':>8} {'p99':>8}")
print("-" * 55)
for label, key in display_metrics.items():
    dist = metrics[key]["successful"]
    p = dist["percentiles"]
    print(f"{label:<20} {dist['mean']:>8.2f} {p['p50']:>8.2f} "
          f"{p['p95']:>8.2f} {p['p99']:>8.2f}")

throughput = metrics["output_tokens_per_second"]["successful"]
req_rate = metrics["requests_per_second"]["successful"]
print(f"\nThroughput: {req_rate['mean']:.2f} req/s  |  "
      f"{throughput['mean']:.1f} output tokens/s")


# **Why Percentiles Matter**
# 
# Averages hide outliers. A system with 100ms average latency but 2-second p99 means **1 in 100 users** waits 20x longer than typical.
# 
# | Percentile | Meaning |
# |:--|:--|
# | **p50 (median)** | Half of requests are faster |
# | **p95** | 95% are faster — the remaining 5% are your "tail" |
# | **p99** | 99% are faster — only 1 in 100 is slower |
# 
# When evaluating a deployment, always look at **p95 and p99**, not just the average. The GuideLLM metrics above include percentile breakdowns so you can compare the mean to p95 to gauge consistency.

# ## Evaluating Model Quality with lm_eval

# Performance benchmarks tell you how fast a deployment is, but not whether it gives **good answers**.
# 
# [lm_eval](https://github.com/EleutherAI/lm-evaluation-harness) measures **task performance**: how well a model answers on standardized academic benchmarks.
# 
# | | GuideLLM | lm_eval |
# |:--|:--|:--|
# | **Measures** | Serving speed, latency, throughput | Task accuracy, quality |
# | **Target** | A running inference server | A model (local or API) |
# | **Question** | "How well does this *deployment* perform?" | "How well does this *model* answer?" |
# 
# You'll point lm_eval at the same running vLLM server using the `local-completions` backend — this uses the OpenAI-compatible **completions** endpoint, which supports the log-probability scoring that multiple-choice benchmarks require. You'll run [**Hellaswag**](https://rowanzellers.com/hellaswag/): a benchmark that's also in the model's [quantization paper](https://arxiv.org/html/2505.02214v1), so you can compare your result directly.
# 
# > **Note:** You'll use lm_evals `simple_evaluate` function on 20 examples to keep it quick, but in production, you'd run the full test set once or multiple times.

# In[ ]:


import lm_eval

os.environ.setdefault("OPENAI_API_KEY", "unused")

TASK = "hellaswag"
print(f"Running lm_eval on {MODEL} via vLLM server ({TASK}, 20 examples)...\n")

results = lm_eval.simple_evaluate(
    model="local-completions",
    model_args=(
        f"model={MODEL},"
        f"base_url={VLLM_URL}/v1/completions,"
        "tokenized_requests=False,"
        "tokenizer=Qwen/Qwen3-0.6B,"
        "num_concurrent=1"
    ),
    tasks=[TASK],
    limit=20,
)


# In[ ]:


task_results = results["results"][TASK]

print(f"Model: {MODEL}")
print(f"Task: {TASK}  |  Examples: 20\n")
for metric, value in task_results.items():
    if isinstance(value, (int, float)):
        print(f"  {metric}: {value:.4f}")


# ## Reading Published Benchmark Data

# In a previous lesson, you learned how to quantize a model with `llm-compressor` using GPTQ. In practice, quantized model publishers include **accuracy tables** on their model cards so users can evaluate the tradeoff without running every benchmark themselves.
# 
# Here's the accuracy table from the [RedHatAI/Qwen3-0.6B-quantized.w4a16 model card](https://huggingface.co/RedHatAI/Qwen3-0.6B-quantized.w4a16) — the W4A16 variant of the model you've been working with:
# 
# | Category | Benchmark | Qwen3-0.6B | W4A16 (this model) | Recovery |
# |:--|:--|--:|--:|--:|
# | **OpenLLM v1** | MMLU (5-shot) | 42.82 | 39.80 | 93.0% |
# | | ARC Challenge (25-shot) | 32.85 | 30.72 | 93.5% |
# | | GSM-8K (5-shot) | 1.82 | 2.20 | — |
# | | Hellaswag (10-shot) | 43.04 | 41.02 | 95.3% |
# | | Winogrande (5-shot) | 54.54 | 54.62 | 100.1% |
# | | TruthfulQA (0-shot) | 51.61 | 48.77 | 94.5% |
# | | **Average** | **37.78** | **36.19** | **95.8%** |
# | **OpenLLM v2** | MMLU-Pro (5-shot) | 17.25 | 14.27 | — |
# | | IFEval (0-shot) | 62.83 | 55.81 | 88.8% |
# | | BBH (3-shot) | 4.23 | 1.63 | — |
# | | Math-lvl-5 (4-shot) | 18.26 | 10.26 | — |
# | | GPQA (0-shot) | 0.00 | 0.00 | — |
# | | MuSR (0-shot) | 0.00 | 0.00 | — |
# | | **Average** | **17.10** | **13.66** | — |
# | **Multilingual** | MGSM (0-shot) | 19.70 | 19.90 | — |
# | **Reasoning** | AIME 2024 | 9.69 | 3.44 | — |
# | | AIME 2025 | 13.13 | 6.98 | — |
# | | GPQA diamond | 29.29 | 27.78 | 94.8% |
# | | Math-lvl-5 | 71.60 | 70.60 | 98.6% |
# | | LiveCodeBench | 12.83 | 8.35 | — |
# 
# The **recovery** column shows how much of the base model's accuracy the quantized version retains. Most benchmarks with meaningful base scores show 97–100% recovery, a strong result for a major model size reduction.

# ## Making the Decision

# You now have three sources of evidence:
# 
# | Source | What it tells you |
# |:--|:--|
# | **GuideLLM** | How the deployment *performs* (latency, throughput, consistency) |
# | **lm_eval** | How the model *answers* (accuracy on a task you ran yourself) |
# | **Model card** | How the model performs across many benchmarks, evaluated by the publisher |
# 
# When deciding whether to deploy a quantized model, you need **both** dimensions. An optimization that doubles throughput but drops accuracy by 15% may not be worth it. An accurate model that can't meet latency SLOs isn't deployable either.
# 
# For this W4A16 model: **~50% model size reduction** for **~4% average accuracy loss** on OpenLLM v1. The answer depends on your use case — check recovery on the tasks that matter to you.

# ## Summary
# 

# In this notebook, you:
# 
# - Ran a real **GuideLLM benchmark** against your vLLM server, measuring TTFT, ITL, end-to-end latency, and throughput
# - Evaluated model quality with **lm_eval** on the Hellaswag benchmark, pointing it at the running server
# - Read published accuracy data from a **model card** to understand the full quantization tradeoff
# - Combined performance and quality evidence to reason about a deployment decision

# ## Resources

# - [GuideLLM GitHub](https://github.com/vllm-project/guidellm)
# - [lm_eval](https://github.com/EleutherAI/lm-evaluation-harness)
