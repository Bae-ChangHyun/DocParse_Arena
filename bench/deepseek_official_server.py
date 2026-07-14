"""OpenAI-compatible server wrapping DeepSeek-OCR's OFFICIAL DeepSeek-OCR-vllm
pipeline, so the docparse_arena app (custom provider) runs DeepSeek the official
way in Battle / Playground / Benchmark.

It reuses the repo's own code (config, deepseek_ocr, process.*) + vllm-0.8.5
(V0 engine): each request's image is preprocessed with the official
DeepseekOCRProcessor.tokenize_with_images and generated with the official ngram
+ SamplingParams. Concurrent app requests are dynamically batched into one
llm.generate. The response carries the RAW grounding text; the app's
``deepseek_clean`` postprocessor applies the official grounding→markdown cleanup.

Run in the deepseek_env venv:
  bench/deepseek_env/bin/python bench/deepseek_official_server.py --port 8001
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import io
import os
import sys
import time
import uuid

os.environ["VLLM_USE_V1"] = "0"
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "0")

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VLLM_DIR = os.path.join(REPO, "bench", "vendor", "DeepSeek-OCR",
                        "DeepSeek-OCR-master", "DeepSeek-OCR-vllm")
os.chdir(VLLM_DIR)
sys.path.insert(0, VLLM_DIR)

import torch  # noqa: E402

if torch.version.cuda == "11.8":
    os.environ["TRITON_PTXAS_PATH"] = "/usr/local/cuda-11.8/bin/ptxas"

from PIL import Image  # noqa: E402
from fastapi import FastAPI, Request  # noqa: E402
import uvicorn  # noqa: E402

from config import MODEL_PATH, PROMPT, CROP_MODE, MAX_CONCURRENCY  # noqa: E402
from deepseek_ocr import DeepseekOCRForCausalLM  # noqa: E402
from vllm import LLM, SamplingParams  # noqa: E402
from vllm.model_executor.models.registry import ModelRegistry  # noqa: E402
from process.ngram_norepeat import NoRepeatNGramLogitsProcessor  # noqa: E402
from process.image_process import DeepseekOCRProcessor  # noqa: E402

ModelRegistry.register_model("DeepseekOCRForCausalLM", DeepseekOCRForCausalLM)

_GPU_UTIL = float(os.environ.get("DS_GPU_UTIL", "0.75"))
_MAX_BATCH = int(os.environ.get("DS_MAX_BATCH", "64"))
# vLLM throughput scales with batch size, so briefly accumulate arriving requests
# before firing a generate. Image preprocessing (crop tiling) is CPU-heavy, so run
# it on a dedicated pool instead of competing with generate on the default one.
_BATCH_WAIT = float(os.environ.get("DS_BATCH_WAIT", "0.15"))
from concurrent.futures import ThreadPoolExecutor  # noqa: E402
_PRE_POOL = ThreadPoolExecutor(max_workers=int(os.environ.get("DS_PRE_WORKERS", "32")))
_GEN_POOL = ThreadPoolExecutor(max_workers=1)

_llm = LLM(
    model=MODEL_PATH,
    hf_overrides={"architectures": ["DeepseekOCRForCausalLM"]},
    block_size=256,
    enforce_eager=True,          # CUDA-graph memory saving; output-identical
    trust_remote_code=True,
    max_model_len=8192,
    swap_space=0,
    max_num_seqs=MAX_CONCURRENCY,
    tensor_parallel_size=1,
    gpu_memory_utilization=_GPU_UTIL,
    disable_mm_preprocessor_cache=True,
)
# OmniDocBench recipe (ngram 40/90) — the primary document→markdown setting.
_SAMPLING = SamplingParams(
    temperature=0.0, max_tokens=8192,
    logits_processors=[NoRepeatNGramLogitsProcessor(ngram_size=40, window_size=90,
                                                    whitelist_token_ids={128821, 128822})],
    skip_special_tokens=False,
)
_PROC = DeepseekOCRProcessor()

app = FastAPI()
_queue: asyncio.Queue = asyncio.Queue()

# Official grounding→markdown post-processing (run_dpsk_ocr_eval_batch.py): the
# server returns CLEAN markdown so the app stays a thin client (just POSTs to the
# base_url and uses the response as-is).
import re  # noqa: E402
_REF_DET = re.compile(r"<\|ref\|>.*?<\|/ref\|><\|det\|>.*?<\|/det\|>", re.DOTALL)
_FORMULA = re.compile(r"\\\[(.*?)\\\]")
_QUAD = re.compile(r"\\quad\s*\([^)]*\)")


def _postprocess(text: str) -> str:
    text = text.replace("<｜end▁of▁sentence｜>", "").replace("<|end▁of▁sentence|>", "")
    text = _FORMULA.sub(lambda m: r"\[" + _QUAD.sub("", m.group(1)).strip() + r"\]", text)
    for blk in _REF_DET.findall(text):
        text = text.replace(blk, "")
    text = text.replace("<center>", "").replace("</center>", "")
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")
    return text.strip()


def _preprocess(pil: Image.Image) -> dict:
    return {"prompt": PROMPT,
            "multi_modal_data": {"image": _PROC.tokenize_with_images(
                images=[pil], bos=True, eos=True, cropping=CROP_MODE)}}


def _extract_image(messages: list) -> Image.Image:
    for m in messages:
        content = m.get("content")
        if isinstance(content, list):
            for part in content:
                if part.get("type") == "image_url":
                    url = part["image_url"]["url"]
                    b64 = url.split(",", 1)[1] if "," in url else url
                    return Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB")
    raise ValueError("no image_url in request")


async def _batcher():
    loop = asyncio.get_event_loop()
    while True:
        first = await _queue.get()
        batch = [first]
        # briefly accumulate so vLLM gets a big, efficient batch
        if _BATCH_WAIT > 0:
            await asyncio.sleep(_BATCH_WAIT)
        while len(batch) < _MAX_BATCH:
            try:
                batch.append(_queue.get_nowait())
            except asyncio.QueueEmpty:
                break
        inputs = [b[0] for b in batch]
        try:
            outs = await loop.run_in_executor(_GEN_POOL, lambda: _llm.generate(inputs, _SAMPLING))
            for (_, fut), out in zip(batch, outs):
                if not fut.done():
                    fut.set_result(out.outputs[0].text)
        except Exception as e:  # noqa: BLE001
            for _, fut in batch:
                if not fut.done():
                    fut.set_exception(e)


@app.on_event("startup")
async def _startup():
    asyncio.create_task(_batcher())


@app.get("/v1/models")
async def models():
    return {"object": "list", "data": [{"id": MODEL_PATH, "object": "model", "owned_by": "deepseek"}]}


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()
    loop = asyncio.get_event_loop()
    pil = _extract_image(body["messages"])
    inp = await loop.run_in_executor(_PRE_POOL, _preprocess, pil)
    fut: asyncio.Future = loop.create_future()
    await _queue.put((inp, fut))
    text = _postprocess(await fut)
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:24]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": body.get("model", MODEL_PATH),
        "choices": [{"index": 0, "finish_reason": "stop",
                     "message": {"role": "assistant", "content": text}}],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8001)
    ap.add_argument("--host", default="0.0.0.0")
    a = ap.parse_args()
    uvicorn.run(app, host=a.host, port=a.port, log_level="info")


if __name__ == "__main__":
    main()
