"""L4 CPU: Diffusion inference fundamentals as a Python module."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
from diffusers import DiffusionPipeline, ZImagePipeline
from diffusers.image_processor import VaeImageProcessor
from diffusers.pipelines.z_image.pipeline_z_image import (
    calculate_shift,
    retrieve_timesteps,
)
from diffusers.utils.torch_utils import randn_tensor
from tqdm import tqdm


PROMPT = (
    "A cute anime girl wearing a white hoodie with an orange rust-colored "
    "(#D55816) 'SGLang' logo text on the chest, digital illustration, soft lighting"
)
IMG_WIDTH = 256
IMG_HEIGHT = 256
MODEL_PATH = "../models/Tongyi-MAI/Z-Image-Turbo"
DEVICE = "cpu"
NUM_INFERENCE_STEPS = 4


class Stage:
    """Base class for all pipeline stages."""

    def __init__(self, pipeline: DiffusionPipeline, device: str = DEVICE) -> None:
        self.diffusers_pipeline = pipeline
        self.device = device

    def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError


class EncodingStage(Stage):
    """Convert a text prompt into embeddings for the denoising model."""

    def __init__(self, pipeline: DiffusionPipeline, device: str = DEVICE) -> None:
        super().__init__(pipeline, device)
        self.tokenizer = pipeline.tokenizer
        self.text_encoder = pipeline.text_encoder

    def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        self.text_encoder = self.text_encoder.to(self.device)
        prompt = params["prompt"]

        messages = [{"role": "user", "content": prompt}]
        prompt_item = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=True,
        )

        text_inputs = self.tokenizer(
            [prompt_item],
            padding="max_length",
            max_length=512,
            truncation=True,
            return_tensors="pt",
        )

        text_input_ids = text_inputs.input_ids.to(self.device)
        prompt_masks = text_inputs.attention_mask.to(self.device).bool()

        prompt_embeds = self.text_encoder(
            input_ids=text_input_ids,
            attention_mask=prompt_masks,
            output_hidden_states=True,
        ).hidden_states[-2]

        embeddings_list = [
            prompt_embeds[i][prompt_masks[i]] for i in range(len(prompt_embeds))
        ]

        del text_input_ids, prompt_masks, text_inputs, prompt_item
        self.text_encoder = self.text_encoder.to("cpu")

        params["prompt_embeds"] = embeddings_list
        return params


class LatentPreparationStage(Stage):
    """Generate the initial random noise tensor in latent space."""

    def __init__(self, pipeline: DiffusionPipeline, device: str = DEVICE) -> None:
        super().__init__(pipeline, device)
        self.vae_scale_factor = 8

    def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        height, width = params["height"], params["width"]
        height = 2 * (int(height) // (self.vae_scale_factor * 2))
        width = 2 * (int(width) // (self.vae_scale_factor * 2))

        shape = (1, 16, height, width)
        generator = torch.Generator("cpu").manual_seed(42)
        latents = randn_tensor(
            shape,
            generator=generator,
            device=self.device,
            dtype=torch.float32,
        )

        params["latents"] = latents
        return params


class TimestepPreparationStage(Stage):
    """Compute the denoising schedule."""

    def __init__(self, pipeline: DiffusionPipeline, device: str = DEVICE) -> None:
        super().__init__(pipeline, device)
        self.scheduler = self.diffusers_pipeline.scheduler

    def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        latents = params["latents"]
        image_seq_len = (latents.shape[2] // 2) * (latents.shape[3] // 2)
        mu = calculate_shift(image_seq_len, 256, 4096, 0.5, 1.15)

        self.scheduler.sigma_min = 0.0
        timesteps, num_inference_steps = retrieve_timesteps(
            self.scheduler,
            NUM_INFERENCE_STEPS,
            self.device,
            sigmas=None,
            mu=mu,
        )

        params["timesteps"] = timesteps
        params["num_inference_steps"] = num_inference_steps
        return params


class DenoisingStage(Stage):
    """Iteratively denoise latents using the transformer model."""

    def __init__(self, pipeline: DiffusionPipeline, device: str = DEVICE) -> None:
        super().__init__(pipeline, device)
        self.transformer = pipeline.transformer.float()
        self.scheduler = pipeline.scheduler
        self.guidance_scale = 5.0

    def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        timesteps = params["timesteps"]
        latents = params["latents"]
        prompt_embeds = params["prompt_embeds"]

        for t in tqdm(timesteps):
            timestep = t.expand(latents.shape[0])
            timestep = (1000 - timestep) / 1000

            latent_model_input = latents.to(self.transformer.dtype).unsqueeze(2)
            latent_model_input_list = list(latent_model_input.unbind(dim=0))

            model_out_list = self.transformer(
                latent_model_input_list,
                timestep,
                prompt_embeds,
                return_dict=False,
            )[0]

            noise_pred = torch.stack([out.float() for out in model_out_list], dim=0)
            noise_pred = noise_pred.squeeze(2)
            noise_pred = -noise_pred

            latents = self.scheduler.step(
                noise_pred.to(torch.float32),
                t,
                latents,
                return_dict=False,
            )[0]

        params["latents"] = latents
        return params


class DecodingStage(Stage):
    """Decode denoised latents into a PIL image via the VAE."""

    def __init__(self, pipeline: DiffusionPipeline, device: str = DEVICE) -> None:
        super().__init__(pipeline, device)
        self.vae = pipeline.vae
        self.vae_scale_factor = 8
        self.image_processor = VaeImageProcessor(
            vae_scale_factor=self.vae_scale_factor * 2
        )

    def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        latents = params["latents"].to(self.vae.dtype)
        latents = (
            latents / self.vae.config.scaling_factor
        ) + self.vae.config.shift_factor

        image = self.vae.decode(latents, return_dict=False)[0]
        image = self.image_processor.postprocess(image, output_type="pil")
        params["image"] = image
        return params


class Pipeline:
    """Chain all five diffusion stages."""

    def __init__(self, diffusers_pipeline: DiffusionPipeline, device: str = DEVICE) -> None:
        self.diffusers_pipeline = diffusers_pipeline
        self.stages = [
            EncodingStage(diffusers_pipeline, device),
            LatentPreparationStage(diffusers_pipeline, device),
            TimestepPreparationStage(diffusers_pipeline, device),
            DenoisingStage(diffusers_pipeline, device),
            DecodingStage(diffusers_pipeline, device),
        ]


class Engine:
    """Run the diffusion stages in order."""

    def __init__(self, diffusers_pipeline: DiffusionPipeline, device: str = DEVICE) -> None:
        self.pipeline = Pipeline(diffusers_pipeline, device)
        self.device = device

    def generate(self, params: dict[str, Any]) -> dict[str, Any]:
        with torch.inference_mode():
            for stage in self.pipeline.stages:
                params = stage.execute(params)
                torch.cuda.empty_cache()
        return params


class CacheStrategy:
    def should_skip(self, noise: torch.Tensor) -> bool:
        raise NotImplementedError

    def reset(self) -> None:
        raise NotImplementedError


class SimpleCacheStrategy(CacheStrategy):
    def __init__(self, threshold: float = 0.05) -> None:
        self.threshold = threshold
        self.last_noise: torch.Tensor | None = None
        self.skipped_steps = 0
        self.diff_history: list[float] = []

    def should_skip(self, noise: torch.Tensor) -> bool:
        if self.last_noise is None:
            self.last_noise = noise
            self.diff_history.append(0.0)
            return False

        diff = torch.norm(noise - self.last_noise) / torch.norm(noise)
        self.diff_history.append(diff.item())
        self.last_noise = noise
        return bool(diff < self.threshold)

    def reset(self) -> None:
        self.last_noise = None
        self.skipped_steps = 0
        self.diff_history = []


class DenoisingStageWithCache(DenoisingStage):
    def __init__(
        self,
        pipeline: DiffusionPipeline,
        cache_strategy: CacheStrategy,
        device: str = DEVICE,
    ) -> None:
        super().__init__(pipeline, device)
        self.cache_strategy = cache_strategy

    def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        timesteps = params["timesteps"]
        latents = params["latents"]
        prompt_embeds = params["prompt_embeds"]

        self.cache_strategy.reset()
        skip_next = False
        last_noise: torch.Tensor | None = None
        executed_steps = 0

        for t in tqdm(timesteps):
            timestep = t.expand(latents.shape[0])
            timestep = (1000 - timestep) / 1000

            latent_model_input = latents.to(self.transformer.dtype).unsqueeze(2)
            latent_model_input_list = list(latent_model_input.unbind(dim=0))

            if skip_next:
                noise_pred = last_noise
                self.cache_strategy.skipped_steps += 1
                skip_next = False
            else:
                model_out_list = self.transformer(
                    latent_model_input_list,
                    timestep,
                    prompt_embeds,
                    return_dict=False,
                )[0]
                noise_pred = torch.stack([out.float() for out in model_out_list], dim=0)
                noise_pred = noise_pred.squeeze(2)
                noise_pred = -noise_pred

                executed_steps += 1
                skip_next = self.cache_strategy.should_skip(noise_pred)
                last_noise = noise_pred

            latents = self.scheduler.step(
                noise_pred.to(torch.float32),
                t,
                latents,
                return_dict=False,
            )[0]

        params["latents"] = latents
        params["executed_steps"] = executed_steps
        params["diff_history"] = self.cache_strategy.diff_history
        return params


@dataclass
class BenchmarkResult:
    name: str
    time_seconds: float
    steps_executed: int
    steps_skipped: int
    image: Any
    diff_history: list[float]


class DiffusionInferenceCpuLesson:
    """Class wrapper for the CPU version of the Lesson 4 notebook."""

    def __init__(
        self,
        model_path: str = MODEL_PATH,
        prompt: str = PROMPT,
        width: int = IMG_WIDTH,
        height: int = IMG_HEIGHT,
        device: str = DEVICE,
    ) -> None:
        self.model_path = model_path
        self.prompt = prompt
        self.width = width
        self.height = height
        self.device = device

        self.pipe = ZImagePipeline.from_pretrained(
            model_path,
            low_cpu_mem_usage=True,
        )
        self.pipe.to(self.device)
        self.engine = Engine(self.pipe, self.device)

    def base_params(self) -> dict[str, Any]:
        return dict(width=self.width, height=self.height, prompt=self.prompt)

    def print_model_info(self) -> None:
        print(f"Model loaded: {self.model_path}")
        print(f"Device: {self.device}")
        print(f"Components: {list(self.pipe.components.keys())}")

    def run_encoding_demo(self) -> dict[str, Any]:
        encoding_stage = EncodingStage(self.pipe, self.device)
        params = self.base_params()

        with torch.inference_mode():
            params = encoding_stage.execute(params)
            torch.cuda.empty_cache()

        embeds = params["prompt_embeds"][0]
        arr = embeds[:64].cpu().float().numpy()
        vlo, vhi = np.percentile(arr, [2, 98])
        print(
            f"Embedding value range (2nd-98th percentile): [{vlo:.4f}, {vhi:.4f}]"
        )

        fig, ax = plt.subplots(1, 1, figsize=(8, 3))
        ax.imshow(arr, aspect="auto", cmap="RdBu_r", vmin=vlo, vmax=vhi)
        ax.set_xlabel("Embedding dimension")
        ax.set_ylabel("Token position")
        ax.set_title(
            "Stage 1 output: prompt embeddings "
            f"({embeds.shape[0]} tokens x {embeds.shape[1]} dims)"
        )
        plt.tight_layout()
        plt.show()
        return params

    def run_latent_and_timestep_demo(
        self,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        params = params or self.base_params()
        latent_stage = LatentPreparationStage(self.pipe, self.device)
        timestep_stage = TimestepPreparationStage(self.pipe, self.device)

        with torch.inference_mode():
            params = latent_stage.execute(params)
            params = timestep_stage.execute(params)

        latents = params["latents"]
        timesteps = params["timesteps"]

        fig, axes = plt.subplots(1, 3, figsize=(16, 5))

        noise_rgb = latents[0, :3].cpu().permute(1, 2, 0).numpy()
        noise_rgb = (noise_rgb - noise_rgb.min()) / (noise_rgb.max() - noise_rgb.min())
        axes[0].imshow(noise_rgb)
        axes[0].set_title(
            "Stage 2: Initial Noise (RGB preview)",
            fontsize=11,
            fontweight="bold",
        )
        axes[0].axis("off")
        h, w = latents.shape[2], latents.shape[3]
        axes[0].text(
            0.5,
            -0.12,
            f"Shape: [1, 16, {h}, {w}]  |  16 channels in latent space\n"
            f"{self.height}x{self.width} image compressed to {h}x{w} "
            "(8x reduction per side)",
            transform=axes[0].transAxes,
            ha="center",
            fontsize=9,
            color="#555",
            bbox=dict(
                boxstyle="round,pad=0.3",
                facecolor="#f0f0f0",
                edgecolor="#ccc",
            ),
        )

        axes[1].imshow(latents[0, 0].cpu().numpy(), cmap="coolwarm")
        axes[1].set_title(
            "Stage 2: Single Channel (ch 0)",
            fontsize=11,
            fontweight="bold",
        )
        axes[1].axis("off")
        axes[1].text(
            0.5,
            -0.12,
            "Each of the 16 channels encodes different features.\n"
            "Values are Gaussian noise ~ N(0, 1) - pure randomness, no image yet.",
            transform=axes[1].transAxes,
            ha="center",
            fontsize=9,
            color="#555",
            bbox=dict(
                boxstyle="round,pad=0.3",
                facecolor="#f0f0f0",
                edgecolor="#ccc",
            ),
        )

        ts = timesteps.cpu().numpy()
        axes[2].bar(
            range(len(ts)),
            ts,
            color="#4CAF50",
            alpha=0.85,
            edgecolor="#388E3C",
        )
        axes[2].set_xlabel("Denoising Step", fontsize=10)
        axes[2].set_ylabel("Timestep Value (noise level)", fontsize=10)
        axes[2].set_title(
            f"Stage 3: Denoising Schedule ({len(ts)} steps)",
            fontsize=11,
            fontweight="bold",
        )
        axes[2].annotate(
            "High noise\n(big changes)",
            xy=(0, ts[0]),
            xytext=(1.5, ts[0] * 0.95),
            fontsize=8,
            color="#D32F2F",
            fontweight="bold",
            arrowprops=dict(arrowstyle="->", color="#D32F2F", lw=1.5),
        )
        axes[2].annotate(
            "Low noise\n(fine details)",
            xy=(len(ts) - 1, ts[-1]),
            xytext=(len(ts) - 3, ts[-1] + ts[0] * 0.15),
            fontsize=8,
            color="#1565C0",
            fontweight="bold",
            arrowprops=dict(arrowstyle="->", color="#1565C0", lw=1.5),
        )
        axes[2].text(
            0.5,
            -0.25,
            "Schedule front-loads big changes. Early steps set structure,\n"
            "later steps refine details - this is why caching works for later steps.",
            transform=axes[2].transAxes,
            ha="center",
            fontsize=9,
            color="#555",
            bbox=dict(
                boxstyle="round,pad=0.3",
                facecolor="#f0f0f0",
                edgecolor="#ccc",
            ),
        )

        plt.suptitle(
            "Stages 2-3: Starting point - pure noise + the plan to clean it up",
            fontsize=13,
            fontweight="bold",
            y=1.02,
        )
        plt.tight_layout()
        plt.subplots_adjust(bottom=0.24)
        plt.show()
        return params

    def run_denoising_timelapse(
        self,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        denoising_stage = DenoisingStage(self.pipe, self.device)
        vae = self.pipe.vae
        image_processor = VaeImageProcessor(vae_scale_factor=16)
        snapshots: list[tuple[str, Any]] = []

        with torch.inference_mode():
            timesteps = params["timesteps"]
            latents = params["latents"].float()
            prompt_embeds = params["prompt_embeds"]

            latents_scaled = (
                latents / vae.config.scaling_factor
            ) + vae.config.shift_factor
            image = vae.decode(latents_scaled.to(vae.dtype), return_dict=False)[0]
            snapshots.append(
                ("Start\n(noise)", image_processor.postprocess(image.float(), output_type="pil")[0])
            )

            for i, timestep_value in enumerate(tqdm(timesteps, desc="Decode per step")):
                timestep = timestep_value.expand(latents.shape[0])
                timestep = (1000 - timestep) / 1000
                latent_model_input = latents.float().unsqueeze(2)
                latent_model_input_list = list(latent_model_input.unbind(dim=0))

                model_out = denoising_stage.transformer(
                    latent_model_input_list,
                    timestep,
                    prompt_embeds,
                    return_dict=False,
                )[0]
                noise_pred = torch.stack([out.float() for out in model_out], dim=0)
                noise_pred = noise_pred.squeeze(2)
                noise_pred = -noise_pred

                latents = denoising_stage.scheduler.step(
                    noise_pred,
                    timestep_value,
                    latents,
                    return_dict=False,
                )[0]

                latents_scaled = (
                    latents / vae.config.scaling_factor
                ) + vae.config.shift_factor
                image = vae.decode(latents_scaled.to(vae.dtype), return_dict=False)[0]
                snapshots.append(
                    (
                        f"Step {i + 1}/{len(timesteps)}",
                        image_processor.postprocess(image.float(), output_type="pil")[0],
                    )
                )

        params["latents"] = latents
        params["image"] = [snapshots[-1][1]]

        n = len(snapshots)
        fig, axes = plt.subplots(1, n, figsize=(2.4 * n, 3.8))

        for idx, (ax, (label, image)) in enumerate(zip(axes, snapshots)):
            ax.imshow(image)
            ax.set_title(label, fontsize=9)
            ax.axis("off")

            if idx == 0:
                color = "#999"
            elif idx <= max(1, len(timesteps) // 2):
                color = "#D32F2F"
            else:
                color = "#1565C0"
            if idx == n - 1:
                color = "#2E7D32"

            for spine in ax.spines.values():
                spine.set_visible(True)
                spine.set_color(color)
                spine.set_linewidth(2.5)

        plt.suptitle(
            "Stages 4-5: Denoising + Decoding - noise to pixels",
            fontsize=13,
            fontweight="bold",
            y=1.02,
        )
        plt.tight_layout()
        plt.show()
        return params

    def generate_full_pipeline(self) -> dict[str, Any]:
        print("Pipeline stages:")
        for i, stage in enumerate(self.engine.pipeline.stages, 1):
            print(f"  {i}. {stage.__class__.__name__}")
        return self.engine.generate(self.base_params())

    def run_benchmark(
        self,
        cache_strategy: CacheStrategy | None = None,
        name: str = "Run",
    ) -> BenchmarkResult:
        params = self.base_params()

        torch.cuda.empty_cache()
        start_time = time.time()
        output = self.engine.generate(params)
        torch.cuda.empty_cache()
        duration = time.time() - start_time

        if cache_strategy:
            steps = params.get("executed_steps", NUM_INFERENCE_STEPS)
            skipped = cache_strategy.skipped_steps
            diff_history = params.get("diff_history", [])
        else:
            steps = params.get("num_inference_steps", NUM_INFERENCE_STEPS)
            skipped = 0
            diff_history = []

        return BenchmarkResult(
            name=name,
            time_seconds=duration,
            steps_executed=steps,
            steps_skipped=skipped,
            image=output["image"][0],
            diff_history=diff_history,
        )

    def compare_cache_vs_no_cache(
        self,
        threshold: float = 0.30,
    ) -> tuple[BenchmarkResult, BenchmarkResult]:
        pipeline = self.engine.pipeline
        diffusers_pipeline = pipeline.diffusers_pipeline
        denoise_idx = next(
            i for i, stage in enumerate(pipeline.stages)
            if isinstance(stage, DenoisingStage)
        )

        print("Running: No Cache...")
        pipeline.stages[denoise_idx] = DenoisingStage(diffusers_pipeline, self.device)
        res_no_cache = self.run_benchmark(name="No Cache")

        print("\nRunning: With Cache...")
        cache_strategy = SimpleCacheStrategy(threshold=threshold)
        pipeline.stages[denoise_idx] = DenoisingStageWithCache(
            diffusers_pipeline,
            cache_strategy,
            self.device,
        )
        res_cache = self.run_benchmark(cache_strategy, name="With Cache")

        df = pd.DataFrame(
            [
                {
                    "Name": res_no_cache.name,
                    "Time (s)": f"{res_no_cache.time_seconds:.2f}",
                    "Steps Executed": res_no_cache.steps_executed,
                    "Steps Skipped": res_no_cache.steps_skipped,
                    "Speedup": "1.00x",
                },
                {
                    "Name": res_cache.name,
                    "Time (s)": f"{res_cache.time_seconds:.2f}",
                    "Steps Executed": res_cache.steps_executed,
                    "Steps Skipped": res_cache.steps_skipped,
                    "Speedup": f"{res_no_cache.time_seconds / res_cache.time_seconds:.2f}x",
                },
            ]
        )
        print("Results:")
        print(df.to_markdown(index=False))

        fig, axes = plt.subplots(1, 2, figsize=(10, 5.5))
        axes[0].imshow(res_no_cache.image.resize((512, 512)))
        axes[0].set_title("No Cache (baseline)", fontsize=12, fontweight="bold", color="#333")
        axes[0].axis("off")
        axes[0].text(
            0.5,
            -0.10,
            f"{NUM_INFERENCE_STEPS}/{NUM_INFERENCE_STEPS} transformer calls  |  "
            f"{res_no_cache.time_seconds:.2f}s",
            transform=axes[0].transAxes,
            ha="center",
            fontsize=10,
            color="#D32F2F",
            bbox=dict(
                boxstyle="round,pad=0.3",
                facecolor="#FFEBEE",
                edgecolor="#D32F2F",
            ),
        )

        axes[1].imshow(res_cache.image.resize((512, 512)))
        axes[1].set_title("With Cache", fontsize=12, fontweight="bold", color="#333")
        axes[1].axis("off")
        axes[1].text(
            0.5,
            -0.10,
            f"{res_cache.steps_executed}/{NUM_INFERENCE_STEPS} calls "
            f"({res_cache.steps_skipped} skipped)  |  "
            f"{res_cache.time_seconds:.2f}s  |  "
            f"{res_no_cache.time_seconds / res_cache.time_seconds:.2f}x faster",
            transform=axes[1].transAxes,
            ha="center",
            fontsize=10,
            color="#1565C0",
            bbox=dict(
                boxstyle="round,pad=0.3",
                facecolor="#E3F2FD",
                edgecolor="#1565C0",
            ),
        )

        plt.suptitle(
            "Cache vs No Cache - same prompt, same seed, same quality",
            fontsize=14,
            fontweight="bold",
            y=1.0,
        )
        plt.tight_layout()
        plt.subplots_adjust(bottom=0.13)
        plt.show()

        if res_cache.diff_history:
            self.plot_temporal_locality(res_cache.diff_history, threshold)

        return res_no_cache, res_cache

    def plot_temporal_locality(
        self,
        diffs: list[float],
        threshold: float,
    ) -> None:
        fig, ax = plt.subplots(figsize=(10, 5))

        for i, diff in enumerate(diffs):
            if diff < threshold and i > 0:
                color, marker, label = (
                    "#1565C0",
                    "s",
                    "Below threshold (next step skipped)",
                )
            else:
                color, marker, label = (
                    "#D32F2F",
                    "o",
                    "Above threshold (computed)",
                )
            ax.plot(
                i,
                diff,
                marker=marker,
                color=color,
                markersize=10,
                zorder=3,
                label=label if i <= 1 else "",
            )

        ax.plot(range(len(diffs)), diffs, color="#888", linewidth=1.5, zorder=2, linestyle="--")
        ax.axhline(
            y=threshold,
            color="#FF9800",
            linewidth=2,
            linestyle="--",
            label=f"Threshold = {threshold}",
        )
        ax.axhspan(0, threshold, alpha=0.08, color="#1565C0")
        ax.axhspan(threshold, max(diffs) * 1.1, alpha=0.08, color="#D32F2F")

        ax.text(
            len(diffs) - 1,
            threshold * 0.5,
            "SKIP zone\n(reuse cached prediction)",
            ha="right",
            fontsize=9,
            color="#1565C0",
            fontweight="bold",
        )
        ax.text(
            len(diffs) - 1,
            threshold + (max(diffs) - threshold) * 0.4,
            "COMPUTE zone\n(run transformer)",
            ha="right",
            fontsize=9,
            color="#D32F2F",
            fontweight="bold",
        )

        ax.set_xlabel("Denoising Step", fontsize=11)
        ax.set_ylabel(
            "Relative Noise Difference\n||current - previous|| / ||current||",
            fontsize=10,
        )
        ax.set_title(
            "Temporal Locality: Why caching works for diffusion",
            fontsize=13,
            fontweight="bold",
        )
        ax.legend(loc="upper right", fontsize=9)
        ax.grid(True, alpha=0.3)
        ax.set_xlim(-0.5, len(diffs) - 0.5)
        ax.set_ylim(0, max(diffs) * 1.15)
        plt.tight_layout()
        plt.show()

    def run_all(self, include_plots: bool = True) -> None:
        self.print_model_info()
        params = self.run_encoding_demo() if include_plots else self.base_params()
        params = self.run_latent_and_timestep_demo(params) if include_plots else params
        if include_plots:
            self.run_denoising_timelapse(params)
        self.generate_full_pipeline()
        self.compare_cache_vs_no_cache()


def main() -> None:
    lesson = DiffusionInferenceCpuLesson()
    lesson.run_all(include_plots=False)


if __name__ == "__main__":
    main()
