"""L2: LLM inference fundamentals as a Python class.

This module converts the `L2.ipynb` notebook into a reusable class-based
workflow while preserving the notebook's behavior and terminology.
"""

from __future__ import annotations

import time
import warnings
from dataclasses import dataclass
from typing import Any

import torch
import torch.nn.functional as F
from torch import Tensor

try:
    from .helper import (
        TinyLLM,
        auto_regressive_decode,
        auto_regressive_decode_with_kv_cache,
        demo_tokenization,
    )
except ImportError:
    from helper import (  # type: ignore
        TinyLLM,
        auto_regressive_decode,
        auto_regressive_decode_with_kv_cache,
        demo_tokenization,
    )


warnings.filterwarnings("ignore")


@dataclass
class TimingResult:
    text: str
    elapsed_seconds: float


class LLMInferenceFundamentalsLesson:
    """Class wrapper for the Lesson 2 notebook workflow."""

    def __init__(
        self,
        model_path: str = "../models/deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B",
        input_text: str = "SGLang is a fast inference engine for",
        max_new_tokens: int = 16,
    ) -> None:
        self.model_path = model_path
        self.input_text = input_text
        self.max_new_tokens = max_new_tokens

        self.tiny_llm = TinyLLM(model_path)
        self.output_text_std: str | None = None
        self.token_ids: list[int] = []
        self.initial_tokens = 0

    @staticmethod
    def _attention_impl(
        q: Tensor,
        k: Tensor,
        v: Tensor,
        scale: float,
        mask: Tensor,
    ) -> Tensor:
        """Core: softmax(Q @ K^T / sqrt(d_k)) @ V."""
        scores = torch.matmul(q, k.transpose(-2, -1)) * scale
        scores = scores.masked_fill(~mask, float("-inf"))
        probs = torch.softmax(scores, dim=-1)
        return torch.matmul(probs, v)

    @classmethod
    def simple_causal_attention(
        cls,
        query: Tensor,
        key: Tensor,
        value: Tensor,
        **_: Any,
    ) -> Tensor:
        """Educational drop-in replacement for scaled dot-product attention."""
        dh = query.shape[-1]
        scale = 1.0 / (dh**0.5)

        gqa_group_size = query.shape[1] // key.shape[1]
        key = key.repeat_interleave(gqa_group_size, dim=1)
        value = value.repeat_interleave(gqa_group_size, dim=1)

        qf, kf, vf = query.float(), key.float(), value.float()
        tq, tk = qf.shape[-2], kf.shape[-2]
        mask = torch.ones((tq, tk), device=qf.device, dtype=torch.bool).tril()
        mask = mask[None, None, :, :]

        out = cls._attention_impl(qf, kf, vf, scale, mask)
        return out.to(dtype=query.dtype)

    def run_baseline_generation(self, temperature: float = 0.0) -> str:
        """Run HuggingFace generation as the lesson baseline."""
        self.output_text_std = self.tiny_llm.generate_std(
            self.input_text,
            self.max_new_tokens,
            temperature=temperature,
        )

        print(f'Input:  "{self.input_text}"')
        print(f'Output: "{self.output_text_std}"')
        print(
            "\nThis is our ground truth"
            " — every implementation must match this exactly."
        )
        return self.output_text_std

    def run_tokenization_demo(self) -> list[int]:
        """Show tokenization and store the prompt token count."""
        self.token_ids = demo_tokenization(self.tiny_llm, self.input_text)
        self.initial_tokens = len(self.token_ids)
        print(f"\n{self.initial_tokens} input tokens — remember this number for later.")
        return self.token_ids

    def run_custom_attention_demo(self, temperature: float = 0.0) -> TimingResult:
        """Monkey-patch PyTorch attention and validate output parity."""
        if self.output_text_std is None:
            self.run_baseline_generation(temperature=temperature)

        original_sdp = F.scaled_dot_product_attention
        F.scaled_dot_product_attention = self.simple_causal_attention

        try:
            tic = time.time()
            text_monkey_patch = auto_regressive_decode(
                self.tiny_llm,
                self.input_text,
                self.max_new_tokens,
                temperature=temperature,
            )
            toc = time.time()
        finally:
            F.scaled_dot_product_attention = original_sdp

        elapsed = toc - tic
        print(f'Output: "{text_monkey_patch}"')
        print(f"Time:   {elapsed:.2f}s ({self.max_new_tokens / elapsed:.1f} tok/s)")
        match = text_monkey_patch == self.output_text_std
        print(f"Match:  {'Yes' if match else 'MISMATCH!'}")
        return TimingResult(text=text_monkey_patch, elapsed_seconds=elapsed)

    def compare_kv_cache(self, temperature: float = 0.0) -> dict[str, float | int | str]:
        """Compare naive autoregressive decoding with KV-cache decoding."""
        if self.output_text_std is None:
            self.run_baseline_generation(temperature=temperature)
        if not self.token_ids:
            self.run_tokenization_demo()

        tic = time.time()
        text_no_cache = auto_regressive_decode(
            self.tiny_llm,
            self.input_text,
            self.max_new_tokens,
            temperature=temperature,
        )
        toc = time.time()
        time_no_cache = toc - tic

        assert text_no_cache == self.output_text_std

        total_ops = sum(self.initial_tokens + i for i in range(self.max_new_tokens))

        print(f'Output: "{text_no_cache}"')
        print(
            f"Time:   {time_no_cache:.2f}s "
            f"({self.max_new_tokens / time_no_cache:.1f} tok/s)"
        )
        print(f"Total token computations: {total_ops}")

        tic = time.time()
        text_kv_cache = auto_regressive_decode_with_kv_cache(
            self.tiny_llm,
            self.input_text,
            self.max_new_tokens,
            temperature=temperature,
        )
        toc = time.time()
        time_with_cache = toc - tic

        assert text_kv_cache == self.output_text_std

        total_ops_kv = self.initial_tokens + (self.max_new_tokens - 1)
        speedup = time_no_cache / time_with_cache

        print(f'Output: "{text_kv_cache}"')
        print(
            f"Time:   {time_with_cache:.2f}s "
            f"({self.max_new_tokens / time_with_cache:.1f} tok/s)"
        )
        print(f"Total token computations: {total_ops_kv}")
        print("\n--- Comparison ---")
        print(
            f"Operations: {total_ops} -> {total_ops_kv}"
            f" ({total_ops // total_ops_kv}x fewer)"
        )
        print(f"Speedup:    {speedup:.1f}x")

        return {
            "text_no_cache": text_no_cache,
            "text_kv_cache": text_kv_cache,
            "time_no_cache": time_no_cache,
            "time_with_cache": time_with_cache,
            "total_ops": total_ops,
            "total_ops_kv": total_ops_kv,
            "speedup": speedup,
        }

    def plot_kv_cache_comparison(self) -> None:
        """Recreate the notebook visualization."""
        if not self.token_ids:
            self.run_tokenization_demo()

        import matplotlib.pyplot as plt
        import numpy as np

        steps = np.arange(1, self.max_new_tokens + 1)
        ops_no_cache = [self.initial_tokens + i for i in range(self.max_new_tokens)]
        ops_kv_cache = [self.initial_tokens] + [1] * (self.max_new_tokens - 1)
        total_ops = sum(ops_no_cache)
        total_ops_kv = sum(ops_kv_cache)

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))

        ax1.bar(
            steps - 0.2,
            ops_no_cache,
            0.4,
            label="Without KV Cache",
            color="#e74c3c",
        )
        ax1.bar(
            steps + 0.2,
            ops_kv_cache,
            0.4,
            label="With KV Cache",
            color="#2ecc71",
        )
        ax1.set(
            xlabel="Decode Step",
            ylabel="Tokens Processed",
            title="Per-Step Token Computations",
        )
        ax1.legend()

        ax2.fill_between(
            steps,
            torch.tensor(ops_no_cache).cumsum(0).numpy(),
            alpha=0.3,
            color="#e74c3c",
        )
        ax2.fill_between(
            steps,
            torch.tensor(ops_kv_cache).cumsum(0).numpy(),
            alpha=0.3,
            color="#2ecc71",
        )
        ax2.plot(
            steps,
            torch.tensor(ops_no_cache).cumsum(0).numpy(),
            "o-",
            color="#e74c3c",
            label=f"Without KV Cache ({total_ops} total)",
        )
        ax2.plot(
            steps,
            torch.tensor(ops_kv_cache).cumsum(0).numpy(),
            "o-",
            color="#2ecc71",
            label=f"With KV Cache ({total_ops_kv} total)",
        )
        ax2.set(
            xlabel="Decode Step",
            ylabel="Cumulative Tokens Processed",
            title="Cumulative Computations",
        )
        ax2.legend()
        plt.tight_layout()
        plt.show()

    def run_all(self, temperature: float = 0.0, plot: bool = False) -> dict[str, Any]:
        """Run the full lesson sequence."""
        baseline = self.run_baseline_generation(temperature=temperature)
        token_ids = self.run_tokenization_demo()
        custom_attention = self.run_custom_attention_demo(temperature=temperature)
        comparison = self.compare_kv_cache(temperature=temperature)

        if plot:
            self.plot_kv_cache_comparison()

        return {
            "baseline": baseline,
            "token_ids": token_ids,
            "custom_attention": custom_attention,
            "comparison": comparison,
        }


def main() -> None:
    lesson = LLMInferenceFundamentalsLesson()
    lesson.run_all(plot=False)


if __name__ == "__main__":
    main()
