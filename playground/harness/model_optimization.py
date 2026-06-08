import warnings
warnings.filterwarnings("ignore")

import os, gc, math, pathlib
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

if not hasattr(torch.fx.Graph, "find_nodes"):
    def _find_nodes(self, op=None, target=None):
        return [
            node for node in self.nodes
            if (op is None or node.op == op) and (target is None or node.target == target)
        ]

    torch.fx.Graph.find_nodes = _find_nodes

os.environ['TOKENIZERS_PARALLELISM'] = 'false'

MODEL_DIR = "Qwen/Qwen3-0.6B"
OUTPUT_DIR = "Qwen/Qwen3-0.6B-W4A16"
SKIP_QUANTIZATION = os.environ.get("SKIP_QUANTIZATION", "").lower() in {"1", "true", "yes"}

print(f"Base model:      {MODEL_DIR}")
print(f"Quantized model: {OUTPUT_DIR}")

def has_model_files(path):
    p = pathlib.Path(path)
    return p.is_dir() and (p / "config.json").is_file()

if SKIP_QUANTIZATION or has_model_files(OUTPUT_DIR):
    if not has_model_files(OUTPUT_DIR):
        raise FileNotFoundError(
            f"SKIP_QUANTIZATION is set, but no model config was found in {OUTPUT_DIR}"
        )
    print(f"Found existing quantized model. Skipping quantization: {OUTPUT_DIR}")
else:
    from llmcompressor.modifiers.quantization import GPTQModifier
    from llmcompressor import oneshot

    recipe = GPTQModifier(
        scheme="W4A16",
        targets="Linear",
        ignore=["lm_head"],
    )

    print(f"Recipe: {recipe}")

    oneshot(
        model="Qwen/Qwen3-0.6B",
        dataset="wikitext",
        dataset_config_name="wikitext-2-raw-v1",
        recipe=recipe,
        output_dir=OUTPUT_DIR,
        max_seq_length=4096,
        num_calibration_samples=256,
    )
    print(f"Quantization complete. Model saved to: {OUTPUT_DIR}")

def folder_size(path):
    p = pathlib.Path(path)
    if not p.exists():
        return 0
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file())

def format_size(nbytes):
    if nbytes < 1024**2:
        return f"{nbytes/1024:.1f} KB"
    if nbytes < 1024**3:
        return f"{nbytes/1024**2:.1f} MB"
    return f"{nbytes/1024**3:.2f} GB"

size_orig = folder_size(MODEL_DIR)
size_q = folder_size(OUTPUT_DIR)
reduction = (1 - size_q / size_orig) * 100 if size_orig > 0 else 0

print("Model Size Comparison")
print("=" * 45)
print(f"Original (BF16):    {format_size(size_orig)}")
print(f"Quantized (W4A16):  {format_size(size_q)}")
print(f"Reduction:          {reduction:.0f}%")


prompt = "Machine learning is a branch of"

tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
base_model = AutoModelForCausalLM.from_pretrained(
    MODEL_DIR, device_map="cpu", dtype=torch.bfloat16,
)

inputs = tokenizer(prompt, return_tensors="pt")
outputs = base_model.generate(
    **inputs, 
    max_new_tokens=60, 
    do_sample=False,
    pad_token_id=tokenizer.eos_token_id,
)
generated = outputs[0][inputs["input_ids"].shape[-1]:]

print(f"Base Model ({MODEL_DIR})")
print(f"Prompt: {prompt}")
print(f"Response: {tokenizer.decode(generated, skip_special_tokens=True)}")


import logging
logging.getLogger("llmcompressor").setLevel(logging.WARNING)

quant_model = AutoModelForCausalLM.from_pretrained(
    OUTPUT_DIR, device_map="cpu", dtype=torch.bfloat16,
)

inputs = tokenizer(prompt, return_tensors="pt")
outputs = quant_model.generate(
    **inputs, 
    max_new_tokens=60, 
    do_sample=False,
    pad_token_id=tokenizer.eos_token_id,
)
generated = outputs[0][inputs["input_ids"].shape[-1]:]

print(f"Quantized Model ({OUTPUT_DIR})")
print(f"Prompt: {prompt}")
print(f"Response: {tokenizer.decode(generated, skip_special_tokens=True)}")

from datasets import load_dataset

def calculate_perplexity(model, tokenizer, dataset, max_tokens=5000, stride=512):
    encodings = tokenizer(
        "\n\n".join(dataset["text"]),
        return_tensors="pt", truncation=True, max_length=max_tokens,
    )
    input_ids = encodings.input_ids
    nlls, prev_end = [], 0

    for begin_loc in range(0, input_ids.size(1), stride):
        end_loc = min(begin_loc + stride, input_ids.size(1))
        trg_len = end_loc - prev_end
        input_slice = input_ids[:, begin_loc:end_loc]
        target_slice = input_slice.clone()
        target_slice[:, :-trg_len] = -100
        with torch.no_grad():
            loss = model(input_slice, labels=target_slice).loss
            nlls.append(loss * trg_len)
        prev_end = end_loc

    return math.exp(torch.stack(nlls).sum() / prev_end)

test_data = load_dataset("wikitext", "wikitext-2-raw-v1", split="test")
print(f"Loaded {len(test_data)} test samples")

quant_ppl = calculate_perplexity(quant_model, tokenizer, test_data)
print(f"Quantized perplexity: {quant_ppl:.2f}")

base_model = AutoModelForCausalLM.from_pretrained(
    MODEL_DIR, device_map="cpu", dtype=torch.bfloat16,
)
base_ppl = calculate_perplexity(base_model, tokenizer, test_data)
print(f"Base perplexity: {base_ppl:.2f}")

print("Perplexity Comparison")
print("=" * 40)
print(f"Base (BF16):      {base_ppl:.2f}")
print(f"Quantized (W4A16): {quant_ppl:.2f}")
print(f"Difference:       {quant_ppl - base_ppl:+.2f} ({(quant_ppl/base_ppl - 1)*100:+.1f}%)")
print(f"\nA small increase in perplexity is expected — the quantized layers use 4-bit weights.")


# inference optimization 
