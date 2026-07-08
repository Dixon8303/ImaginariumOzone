import asyncio
import json
import uuid
import aiofiles
from pathlib import Path
import httpx
import config

BASE = config.COMFYUI_BASE_URL.rstrip("/")

async def test_connection() -> bool:
    async with httpx.AsyncClient(timeout=5) as client:
        try:
            r = await client.get(f"{BASE}/system_stats")
            return r.status_code == 200
        except Exception:
            return False

def _load_workflow(name: str) -> dict:
    path = config.WORKFLOWS_DIR / f"{name}.json"
    return json.loads(path.read_text())

def _inject_video_prompt(workflow: dict, positive_prompt: str,
                          negative_prompt: str, seed: int) -> dict:
    w = json.loads(json.dumps(workflow))  # deep copy
    # Node IDs per wan2_video.json structure
    for node_id, node in w.items():
        cls = node.get("class_type", "")
        if cls == "CLIPTextEncode":
            inputs = node.get("inputs", {})
            # Identify positive vs negative by checking connected node references
            # Convention: node "2" = positive, node "3" = negative
            if node_id == "2":
                inputs["text"] = positive_prompt
            elif node_id == "3":
                inputs["text"] = negative_prompt
        elif cls in ("WanVideoSampler", "KSampler"):
            node["inputs"]["seed"] = seed
    return w

def _inject_image_prompt(workflow: dict, positive_prompt: str,
                          negative_prompt: str, seed: int) -> dict:
    w = json.loads(json.dumps(workflow))
    for node_id, node in w.items():
        cls = node.get("class_type", "")
        if cls == "CLIPTextEncode":
            if node_id == "6":
                node["inputs"]["text"] = positive_prompt
            elif node_id == "7":
                node["inputs"]["text"] = negative_prompt
        elif cls == "KSampler":
            node["inputs"]["seed"] = seed
    return w

async def queue_video(positive_prompt: str, negative_prompt: str, seed: int) -> str:
    workflow = _load_workflow("wan2_video")
    wf = _inject_video_prompt(workflow, positive_prompt, negative_prompt, seed)
    return await _queue(wf)

async def queue_image(positive_prompt: str, negative_prompt: str, seed: int) -> str:
    workflow = _load_workflow("wan2_image")
    wf = _inject_image_prompt(workflow, positive_prompt, negative_prompt, seed)
    return await _queue(wf)

async def _queue(workflow: dict) -> str:
    client_id = str(uuid.uuid4())
    payload = {"prompt": workflow, "client_id": client_id}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(f"{BASE}/prompt", json=payload)
        r.raise_for_status()
        return r.json()["prompt_id"]

async def wait_for_completion(prompt_id: str, timeout_s: int = 1800) -> dict:
    deadline = asyncio.get_event_loop().time() + timeout_s
    async with httpx.AsyncClient(timeout=10) as client:
        while asyncio.get_event_loop().time() < deadline:
            try:
                r = await client.get(f"{BASE}/history/{prompt_id}")
                data = r.json()
                if prompt_id in data:
                    entry = data[prompt_id]
                    if entry.get("outputs"):
                        return entry["outputs"]
                    if entry.get("status", {}).get("status_str") == "error":
                        raise RuntimeError(f"ComfyUI job {prompt_id} errored: {entry.get('status')}")
            except httpx.HTTPError:
                pass
            await asyncio.sleep(5)
    raise TimeoutError(f"ComfyUI job {prompt_id} timed out after {timeout_s}s")

async def download_output(outputs: dict, dest_path: Path) -> Path:
    """Find the first video/image file in outputs and download it."""
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    for node_outputs in outputs.values():
        for key in ("videos", "images", "gifs"):
            files = node_outputs.get(key, [])
            if files:
                file_info = files[0]
                filename = file_info["filename"]
                subfolder = file_info.get("subfolder", "")
                params = {"filename": filename, "type": file_info.get("type", "output")}
                if subfolder:
                    params["subfolder"] = subfolder
                async with httpx.AsyncClient(timeout=120) as client:
                    r = await client.get(f"{BASE}/view", params=params)
                    r.raise_for_status()
                    async with aiofiles.open(dest_path, "wb") as f:
                        await f.write(r.content)
                return dest_path
    raise ValueError(f"No output file found in ComfyUI outputs: {outputs}")

async def generate_asset(asset_type: str, positive_prompt: str, negative_prompt: str,
                          seed: int, dest_path: Path, retries: int = 2) -> Path:
    for attempt in range(retries + 1):
        try:
            effective_seed = seed + attempt * 1000
            if asset_type == "ai_video":
                prompt_id = await queue_video(positive_prompt, negative_prompt, effective_seed)
            else:
                prompt_id = await queue_image(positive_prompt, negative_prompt, effective_seed)
            outputs = await wait_for_completion(prompt_id)
            return await download_output(outputs, dest_path)
        except (TimeoutError, RuntimeError, ValueError) as e:
            if attempt == retries:
                raise RuntimeError(f"ComfyUI generation failed after {retries + 1} attempts: {e}")
            await asyncio.sleep(5)
