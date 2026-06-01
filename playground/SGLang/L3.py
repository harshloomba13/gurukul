"""L3: Prefix caching with RadixAttention as a Python module."""

from __future__ import annotations

import copy
import random
import time
import warnings
from dataclasses import dataclass
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch

try:
    from .helper import TinyLLM, sample
except ImportError:
    from helper import TinyLLM, sample  # type: ignore


warnings.filterwarnings("ignore")


def calculate_speedup(total_tokens: int, cached_tokens: int) -> float:
    """Prefill speedup from prefix caching."""
    tokens_to_compute = total_tokens - cached_tokens
    return total_tokens / tokens_to_compute


class CacheEntry:
    """Pairs a token sequence with its precomputed KV cache."""

    def __init__(self, token_ids: list[int], kv_cache: Any) -> None:
        self.token_ids = list(token_ids)
        self.kv_cache = kv_cache

    def get_seq_length(self, layer_idx: int = 0) -> int:
        if self.kv_cache is None:
            return 0
        return self.kv_cache.get_seq_length(layer_idx)


class FlatRadixTree:
    """Simplified radix tree for prefix matching and KV cache reuse."""

    def __init__(self) -> None:
        self.entries: list[CacheEntry] = []

    def insert(self, token_ids: list[int], kv_cache: Any) -> None:
        self.entries.append(CacheEntry(token_ids, kv_cache))

    def search(self, token_ids: list[int]) -> CacheEntry | None:
        best_len = 0
        best_entry: CacheEntry | None = None

        for entry in self.entries:
            match_len = 0
            for a, b in zip(entry.token_ids, token_ids):
                if a != b:
                    break
                match_len += 1
            if match_len > best_len:
                best_len = match_len
                best_entry = entry

        if best_entry is None or best_len == 0:
            return None

        trimmed_kv = copy.deepcopy(best_entry.kv_cache)
        trimmed_kv.crop(best_len)
        return CacheEntry(best_entry.token_ids[:best_len], trimmed_kv)


def construct_prompt(article: str, question: str) -> str:
    """Build a RAG-style prompt."""
    return f"Article:\n{article.strip()}\n\nQuestion: {question}\nAnswer:"


def _tokenize(self: TinyLLM, text: str) -> list[int]:
    return self.tokenizer.encode(text)


def _detokenize(self: TinyLLM, token_ids: list[int]) -> str:
    return self.tokenizer.decode(token_ids, skip_special_tokens=True)


@torch.inference_mode()
def _generate(
    self: TinyLLM,
    prompt: str,
    max_new_tokens: int = 16,
    stop_strs: list[str] | None = None,
    temperature: float = 0.0,
) -> tuple[str, CacheEntry]:
    """Full prefill + decode."""
    input_ids = self.tokenize(prompt)
    token_ids = list(input_ids)

    inp = torch.tensor([token_ids], device=self.model.device)
    out = self.model(inp, use_cache=True)
    past = out.past_key_values
    next_id = sample(out.logits[:, -1, :], temperature).item()
    token_ids.append(next_id)

    for _ in range(max_new_tokens - 1):
        inp_t = torch.tensor([[token_ids[-1]]], device=self.model.device)
        out = self.model(inp_t, past_key_values=past, use_cache=True)
        past = out.past_key_values
        next_id = sample(out.logits[:, -1, :], temperature).item()
        token_ids.append(next_id)
        if stop_strs:
            tail = self.detokenize(token_ids[len(input_ids) :])
            if any(stop_str in tail for stop_str in stop_strs):
                break

    return self.detokenize(token_ids), CacheEntry(token_ids, past)


@torch.inference_mode()
def _generate_with_prefix_cache(
    self: TinyLLM,
    prompt: str,
    max_new_tokens: int = 16,
    stop_strs: list[str] | None = None,
    prefix_cache: CacheEntry | None = None,
    temperature: float = 0.0,
) -> tuple[str, CacheEntry]:
    """Generate with optional prefix KV reuse."""
    input_ids = self.tokenize(prompt)
    token_ids = list(input_ids)

    if prefix_cache is not None and prefix_cache.get_seq_length(0) > 0:
        cached_len = prefix_cache.get_seq_length(0)
        suffix = token_ids[cached_len:] or [token_ids[-1]]
        inp = torch.tensor([suffix], device=self.model.device)
        out = self.model(
            inp,
            past_key_values=prefix_cache.kv_cache,
            use_cache=True,
        )
    else:
        inp = torch.tensor([token_ids], device=self.model.device)
        out = self.model(inp, use_cache=True)

    past = out.past_key_values
    next_id = sample(out.logits[:, -1, :], temperature).item()
    token_ids.append(next_id)

    for _ in range(max_new_tokens - 1):
        inp_t = torch.tensor([[token_ids[-1]]], device=self.model.device)
        out = self.model(inp_t, past_key_values=past, use_cache=True)
        past = out.past_key_values
        next_id = sample(out.logits[:, -1, :], temperature).item()
        token_ids.append(next_id)
        if stop_strs:
            tail = self.detokenize(token_ids[len(input_ids) :])
            if any(stop_str in tail for stop_str in stop_strs):
                break

    return self.detokenize(token_ids), CacheEntry(token_ids, past)


TinyLLM.tokenize = _tokenize
TinyLLM.detokenize = _detokenize
TinyLLM.generate = _generate
TinyLLM.generate_with_prefix_cache = _generate_with_prefix_cache


ARTICLE0 = """\
Serving large language models in production requires careful orchestration of compute, memory, and scheduling resources. A single user request triggers a two-phase process: prefill, where the model processes the entire input prompt in parallel to build the initial KV cache, and decode, where new tokens are generated one at a time using that cache. The prefill phase is compute-bound because it processes many tokens simultaneously through the transformer layers, while the decode phase is memory-bandwidth-bound because each step loads the full KV cache from GPU memory to produce just one token.

SGLang is a high-performance serving framework designed to make LLM inference fast and efficient. One of its core techniques is continuous batching, which allows new requests to join a running batch as soon as a slot opens, rather than waiting for the entire batch to finish. This keeps GPU utilization high even when individual requests have different lengths. SGLang also manages KV cache memory in fixed-size blocks to eliminate fragmentation and enable larger batch sizes on the same GPU.

The key innovation in SGLang is RadixAttention, which uses a radix tree to store and reuse KV caches across requests. Instead of discarding the KV cache after each request, SGLang indexes it by token sequence. When a new request shares a prefix with a previous one, the cached KV tensors are loaded directly - no recomputation needed. This is particularly effective for workloads with shared context: RAG applications where the same document appears in many queries, chatbots where every request begins with the same system prompt, and few-shot learning where identical examples precede each API call.

SGLang further optimizes inference through efficient scheduling. The scheduler decides which requests to process next, how to form batches, and when to preempt lower-priority requests to meet latency targets. It considers factors like estimated output length, prefix cache hit rates, and SLA deadlines. Interactive chat requests get lower latency than batch processing jobs, even when running on the same GPU cluster. Together, these optimizations allow SGLang to achieve significantly higher throughput and lower latency than naive serving approaches.
"""

ARTICLE0_QUESTIONS = [
    "What are the two phases of LLM inference and how do they differ?",
    "How does continuous batching improve GPU utilization in SGLang?",
    "What is RadixAttention and how does it reuse KV cache across requests?",
    "How does SGLang manage KV cache memory to avoid fragmentation?",
    "What factors does SGLang's scheduler consider when forming batches?",
    "Why is the decode phase memory-bandwidth-bound rather than compute-bound?",
]

ARTICLE1 = """\
The key-value cache is the single most important optimization in autoregressive language model inference. During text generation, a transformer model produces one token at a time. At each step, the self-attention mechanism computes Query, Key, and Value projections for the new token and compares the Query against all previous Keys to determine attention weights. Without caching, every previous token's Key and Value would be recomputed from scratch at every step, leading to O(n-squared) total computation for generating n tokens.

The KV cache stores the Key and Value tensors for all previously processed tokens. When generating token n+1, only the new token's Q, K, and V need to be computed. The attention scores are then calculated between the new Query and all cached Keys, the result is multiplied by all cached Values, and the new K and V are appended to the cache. This reduces total computation from O(n-squared) to O(n), a dramatic improvement for long sequences.

However, the KV cache introduces its own challenges. Each transformer layer stores Key and Value tensors whose size grows with sequence length. For a large model with many layers and attention heads, a single sequence of several thousand tokens can require gigabytes of KV cache memory. When serving many concurrent requests, KV cache memory often becomes the binding constraint rather than model weights or compute. SGLang addresses this with intelligent memory management that allocates cache in fixed-size blocks and reclaims memory from completed requests immediately.

Grouped Query Attention (GQA), used in models like DeepSeek, addresses the KV cache memory problem by sharing Key and Value heads across multiple Query heads. Instead of giving every Query head its own independent KV head, a model might use only 8 KV heads shared among 64 Query heads, reducing KV cache size by 8x. This trades a small amount of model quality for significant memory savings, enabling much larger batch sizes in production. SGLang takes full advantage of GQA by only caching the reduced set of KV heads, so prefix caching with RadixAttention is even more memory-efficient.

Beyond single-request caching, the real power comes from reusing KV tensors across requests. When many users ask different questions about the same document, the KV cache for that document is computed once and shared via the radix tree. This combination of within-request KV caching and across-request prefix caching is what makes SGLang's inference pipeline so effective in production.
"""

ARTICLE1_QUESTIONS = [
    "Why does autoregressive generation without KV cache lead to O(n-squared) computation?",
    "How does the KV cache reduce the computational complexity of text generation?",
    "Why does KV cache memory become the binding constraint in production serving?",
    "What is Grouped Query Attention and how does it reduce KV cache size?",
    "How does SGLang manage KV cache memory with fixed-size blocks?",
    "How does across-request prefix caching combine with within-request KV caching?",
]

MIN_PREFIX_MATCH = 20


@dataclass
class LessonArtifacts:
    baseline_df: pd.DataFrame | None = None
    radix_df: pd.DataFrame | None = None
    multi_df: pd.DataFrame | None = None
    comparison_df: pd.DataFrame | None = None


class PrefixCachingLesson:
    """Class wrapper for the Lesson 3 notebook workflow."""

    def __init__(
        self,
        model_path: str = "../models/deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B",
        max_new_tokens: int = 16,
    ) -> None:
        self.model_path = model_path
        self.max_new_tokens = max_new_tokens
        self.tiny_llm = TinyLLM(model_path)
        self.artifacts = LessonArtifacts()

    def speedup_demo(self, total: int = 500, cached: int = 450) -> float:
        compute = total - cached
        speedup = calculate_speedup(total, cached)
        print(f"Total: {total}  Cached: {cached} ({cached / total * 100:.0f}%)")
        print(f"Compute: {compute}  ->  Speedup: {speedup:.0f}x")
        return speedup

    def run_baseline_experiment(self) -> pd.DataFrame:
        print("Baseline: No Caching")
        print("=" * 55)

        baseline_results: list[dict[str, Any]] = []

        for i, question in enumerate(ARTICLE0_QUESTIONS):
            prompt = construct_prompt(ARTICLE0, question)

            tic = time.time()
            output, _cached_req = self.tiny_llm.generate(
                prompt,
                max_new_tokens=self.max_new_tokens,
                stop_strs=["\n", "Answer:"],
                temperature=0,
            )
            elapsed = time.time() - tic

            answer = output.split("Answer:")[-1].strip()
            baseline_results.append(
                {
                    "question_id": i,
                    "time": elapsed,
                    "answer": answer,
                }
            )
            print(f"  Q{i + 1}: {elapsed:.3f}s  |  {answer[:70]}...")

        baseline_df = pd.DataFrame(baseline_results)
        print(f"\nAverage: {baseline_df['time'].mean():.3f}s/question")
        print(f"Total:   {baseline_df['time'].sum():.3f}s")
        self.artifacts.baseline_df = baseline_df
        return baseline_df

    def run_radix_experiment(self) -> pd.DataFrame:
        print("RadixAttention: Prefix Caching")
        print("=" * 55)

        radix = FlatRadixTree()
        radix_results: list[dict[str, Any]] = []

        for i, question in enumerate(ARTICLE0_QUESTIONS):
            prompt = construct_prompt(ARTICLE0, question)
            token_ids = self.tiny_llm.tokenize(prompt)

            prefix_cache = radix.search(token_ids)
            matched = prefix_cache.get_seq_length(0) if prefix_cache is not None else 0

            tic = time.time()
            output, cached_req = self.tiny_llm.generate_with_prefix_cache(
                prompt,
                max_new_tokens=self.max_new_tokens,
                stop_strs=["\n", "Answer:"],
                prefix_cache=prefix_cache,
                temperature=0,
            )
            elapsed = time.time() - tic

            radix.insert(cached_req.token_ids, cached_req.kv_cache)

            status = "MISS" if matched == 0 else f"HIT ({matched} tokens)"
            radix_results.append(
                {
                    "question_id": i,
                    "time": elapsed,
                    "cached_tokens": matched,
                    "answer": output.split("Answer:")[-1].strip(),
                }
            )
            print(f"  Q{i + 1}: {elapsed:.3f}s  [{status}]")

        radix_df = pd.DataFrame(radix_results)
        baseline_df = self._require_baseline_df()
        avg_baseline = baseline_df["time"].mean()
        avg_radix = radix_df["time"].mean()
        speedup = avg_baseline / avg_radix
        saved = baseline_df["time"].sum() - radix_df["time"].sum()

        print(f"\nAverage: {avg_radix:.3f}s/question")
        print(f"Total:   {radix_df['time'].sum():.3f}s")
        print(f"Speedup: {speedup:.2f}x")
        print(f"Saved:   {saved:.1f}s")

        self.artifacts.radix_df = radix_df
        return radix_df

    def plot_radix_vs_baseline(self) -> None:
        baseline_df = self._require_baseline_df()
        radix_df = self._require_radix_df()

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

        x = np.arange(len(ARTICLE0_QUESTIONS))
        width = 0.35
        bars1 = ax1.bar(
            x - width / 2,
            baseline_df["time"],
            width,
            label="No Cache",
            color="#e74c3c",
            alpha=0.85,
        )
        bars2 = ax1.bar(
            x + width / 2,
            radix_df["time"],
            width,
            label="RadixAttention",
            color="#2ecc71",
            alpha=0.85,
        )
        ax1.set(
            xlabel="Question",
            ylabel="Time (s)",
            title="Per-Question Inference Time",
        )
        ax1.set_xticks(x, [f"Q{i + 1}" for i in x])
        ax1.legend()

        for bars in (bars1, bars2):
            for bar in bars:
                height = bar.get_height()
                ax1.text(
                    bar.get_x() + bar.get_width() / 2.0,
                    height,
                    f"{height:.2f}s",
                    ha="center",
                    va="bottom",
                    fontsize=8,
                )

        prompt_lens = [
            len(self.tiny_llm.tokenize(construct_prompt(ARTICLE0, question)))
            for question in ARTICLE0_QUESTIONS
        ]
        cache_rates = [
            (matched / total * 100) if total > 0 else 0
            for matched, total in zip(radix_df["cached_tokens"], prompt_lens)
        ]
        ax2.bar(x, cache_rates, color="#9b59b6", alpha=0.85)
        ax2.set(
            xlabel="Question",
            ylabel="Cache Hit Rate (%)",
            title="Prompt Tokens Reused from Cache",
        )
        ax2.set_xticks(x, [f"Q{i + 1}" for i in x])
        ax2.set_ylim(0, 105)
        for i, rate in enumerate(cache_rates):
            ax2.text(i, rate + 1, f"{rate:.0f}%", ha="center", fontsize=9)

        plt.tight_layout()
        plt.show()

    def run_mixed_workload_experiment(self) -> pd.DataFrame:
        print("Mixed Workload: Two Articles, Random Order")
        print("=" * 55)

        all_prompts: list[tuple[str, str, str]] = []
        for question in ARTICLE0_QUESTIONS:
            all_prompts.append(
                ("article0", "SGLang Serving", construct_prompt(ARTICLE0, question))
            )
        for question in ARTICLE1_QUESTIONS:
            all_prompts.append(("article1", "KV Cache", construct_prompt(ARTICLE1, question)))

        random.seed(42)
        random.shuffle(all_prompts)

        radix_multi = FlatRadixTree()
        multi_results: list[dict[str, Any]] = []

        for i, (tag, article_name, prompt) in enumerate(all_prompts):
            token_ids = self.tiny_llm.tokenize(prompt)

            prefix_cache = radix_multi.search(token_ids)
            matched = prefix_cache.get_seq_length(0) if prefix_cache is not None else 0
            effective_cache = prefix_cache if matched >= MIN_PREFIX_MATCH else None

            tic = time.time()
            out, cached_req = self.tiny_llm.generate_with_prefix_cache(
                prompt,
                max_new_tokens=self.max_new_tokens,
                stop_strs=["\n", "Answer:"],
                prefix_cache=effective_cache,
                temperature=0,
            )
            elapsed = time.time() - tic

            radix_multi.insert(cached_req.token_ids, cached_req.kv_cache)

            is_hit = matched >= MIN_PREFIX_MATCH
            multi_results.append(
                {
                    "request_num": i + 1,
                    "article": tag,
                    "article_name": article_name,
                    "time": elapsed,
                    "matched_tokens": matched if is_hit else 0,
                    "answer": out.split("Answer:")[-1].strip(),
                }
            )

            status = f"HIT ({matched})" if is_hit else "MISS"
            print(f"  {i + 1:2d}. [{article_name:14s}] {elapsed:.3f}s  {status}")

        multi_df = pd.DataFrame(multi_results)
        cache_hits = (multi_df["matched_tokens"] > 0).sum()
        hit_pct = cache_hits / len(multi_df) * 100
        print(f"\nCache hits: {cache_hits}/{len(multi_df)} ({hit_pct:.0f}%)")
        print(f"Average time: {multi_df['time'].mean():.3f}s")

        self.artifacts.multi_df = multi_df
        return multi_df

    def plot_mixed_workload(self) -> None:
        multi_df = self._require_multi_df()
        cache_hits = (multi_df["matched_tokens"] > 0).sum()
        cache_misses = len(multi_df) - cache_hits

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

        colors = [
            "#e74c3c" if article == "article0" else "#3498db"
            for article in multi_df["article"]
        ]
        ax1.scatter(
            multi_df["request_num"],
            multi_df["time"],
            c=colors,
            s=120,
            edgecolors="black",
            lw=1.5,
        )
        ax1.set(
            xlabel="Request Number",
            ylabel="Time (s)",
            title="Request Timeline",
        )
        ax1.legend(
            handles=[
                plt.Line2D(
                    [0],
                    [0],
                    marker="o",
                    color="w",
                    markerfacecolor="#e74c3c",
                    markersize=10,
                    label="SGLang Serving",
                    markeredgecolor="black",
                ),
                plt.Line2D(
                    [0],
                    [0],
                    marker="o",
                    color="w",
                    markerfacecolor="#3498db",
                    markersize=10,
                    label="KV Cache",
                    markeredgecolor="black",
                ),
            ]
        )

        ax2.pie(
            [cache_hits, cache_misses],
            labels=[f"Hit ({cache_hits})", f"Miss ({cache_misses})"],
            autopct="%1.0f%%",
            colors=["#2ecc71", "#e74c3c"],
            wedgeprops=dict(edgecolor="black", lw=1.5),
            textprops=dict(fontweight="bold"),
        )
        ax2.set_title("Cache Hit Rate")

        plt.tight_layout()
        plt.show()

    def summarize_mixed_workload(self) -> None:
        multi_df = self._require_multi_df()
        hits_df = multi_df[multi_df["matched_tokens"] > 0]
        misses_df = multi_df[multi_df["matched_tokens"] == 0]

        avg_hit_time = hits_df["time"].mean()
        avg_miss_time = misses_df["time"].mean()
        hit_vs_miss_speedup = avg_miss_time / avg_hit_time

        print("Per-Article Breakdown")
        print("=" * 55)
        for article_name in ["SGLang Serving", "KV Cache"]:
            article_df = multi_df[multi_df["article_name"] == article_name]
            article_hits = (article_df["matched_tokens"] > 0).sum()
            article_total = len(article_df)
            article_avg = article_df["time"].mean()
            print(
                f"  {article_name:16s}  "
                f"{article_hits}/{article_total} hits  "
                f"avg {article_avg:.3f}s"
            )

        print(f"\nCache Miss (cold start):  avg {avg_miss_time:.3f}s  ({len(misses_df)} requests)")
        print(f"Cache Hit  (reuse):      avg {avg_hit_time:.3f}s  ({len(hits_df)} requests)")
        print(f"Hit vs Miss speedup:     {hit_vs_miss_speedup:.2f}x")
        print(f"\nTotal requests:  {len(multi_df)}")
        print(f"Total time:      {multi_df['time'].sum():.2f}s")
        print(f"Amortized cost:  {multi_df['time'].mean():.3f}s/request")
        print(f"\nKey insight: {len(misses_df)} cold starts amortized across {len(multi_df)} requests.")
        print(f"As traffic grows, the miss ratio -> 0 and average time -> {avg_hit_time:.3f}s")

    def build_summary_comparison(self) -> pd.DataFrame:
        baseline_df = self._require_baseline_df()
        radix_df = self._require_radix_df()

        prompt_lens = [
            len(self.tiny_llm.tokenize(construct_prompt(ARTICLE0, question)))
            for question in ARTICLE0_QUESTIONS
        ]
        cache_rates = [
            (matched / total * 100) if total > 0 else 0
            for matched, total in zip(radix_df["cached_tokens"], prompt_lens)
        ]

        comparison_df = pd.DataFrame(
            {
                "Question": [f"Q{i + 1}" for i in range(len(ARTICLE0_QUESTIONS))],
                "No Cache (s)": baseline_df["time"].values,
                "With Cache (s)": radix_df["time"].values,
                "Cached Tokens": radix_df["cached_tokens"].values,
                "Cache Rate (%)": cache_rates,
                "Speedup": baseline_df["time"].values / radix_df["time"].values,
            }
        )

        print(comparison_df.to_string(index=False, float_format=lambda x: f"{x:.3f}"))
        print(f"\nAverage speedup:    {comparison_df['Speedup'].mean():.2f}x")
        print(f"Average cache rate: {comparison_df['Cache Rate (%)'].mean():.1f}%")
        print(f"Total time saved:   {baseline_df['time'].sum() - radix_df['time'].sum():.1f}s")

        self.artifacts.comparison_df = comparison_df
        return comparison_df

    def run_all(self, plot: bool = False) -> LessonArtifacts:
        self.speedup_demo()
        self.run_baseline_experiment()
        self.run_radix_experiment()
        if plot:
            self.plot_radix_vs_baseline()
        self.run_mixed_workload_experiment()
        if plot:
            self.plot_mixed_workload()
        self.summarize_mixed_workload()
        self.build_summary_comparison()
        return self.artifacts

    def _require_baseline_df(self) -> pd.DataFrame:
        if self.artifacts.baseline_df is None:
            raise RuntimeError("Run the baseline experiment first.")
        return self.artifacts.baseline_df

    def _require_radix_df(self) -> pd.DataFrame:
        if self.artifacts.radix_df is None:
            raise RuntimeError("Run the radix experiment first.")
        return self.artifacts.radix_df

    def _require_multi_df(self) -> pd.DataFrame:
        if self.artifacts.multi_df is None:
            raise RuntimeError("Run the mixed workload experiment first.")
        return self.artifacts.multi_df


def main() -> None:
    lesson = PrefixCachingLesson()
    lesson.run_all(plot=False)


if __name__ == "__main__":
    main()
