#!/usr/bin/env python3
"""
Comfy Cloud REST automation — dayz repo asset generation.

Usage:
  python generate_dayz_assets.py --probe               # list available models/checkpoints
  python generate_dayz_assets.py --asset 1             # generate asset 1 (hero banner)
  python generate_dayz_assets.py --asset 1 --count 4   # generate N variations
  python generate_dayz_assets.py --all                  # all assets in handoff order
  python generate_dayz_assets.py --asset 1 --dry-run   # print workflow JSON, don't submit

Generation order per handoff:
  1 → Hero banner (1280×320, Flux 1.1 Pro)
  6 → Status footer (1280×200, Flux 1.1 Pro)
  2 → Logo/mark (512×512, Flux Dev)
  3 → Architecture diagram (1600×1200, Flux Dev)
  4 → Stream icons ×4 (256×256, Flux Schnell)
  5 → Section dividers ×3 (1536×96, Flux Schnell)
"""

import argparse
import json
import os
import sys
import time
import uuid
from pathlib import Path
import urllib.request
import urllib.error

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

API_KEY = os.environ.get("COMFY_CLOUD_API_KEY", "")
if not API_KEY:
    raise SystemExit(
        "Set COMFY_CLOUD_API_KEY env var. Find your key at platform.comfy.org "
        "or in ~/.claude.json under mcpServers.comfyui-cloud.headers.X-API-Key"
    )
BASE_URL = "https://cloud.comfy.org"
OUTPUT_DIR = Path("~/Downloads/dayz-graphics")

HEADERS = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json",
}

# Model identifiers — update these after running --probe if names differ
MODEL_FLUX_PRO = "flux1-pro"           # Flux 1.1 Pro (Partner Node)
MODEL_FLUX_DEV = "flux1-dev.safetensors"
MODEL_FLUX_SCHNELL = "flux1-schnell.safetensors"
MODEL_SDXL = "sd_xl_base_1.0.safetensors"

# VAE + CLIP for Flux
VAE_FLUX = "ae.safetensors"
CLIP_T5 = "t5xxl_fp16.safetensors"
CLIP_L = "clip_l.safetensors"

# SDXL refiner (optional, set to None to skip)
SDXL_REFINER = None

# ---------------------------------------------------------------------------
# HTTP helpers (stdlib only — no requests dependency required)
# ---------------------------------------------------------------------------

def _req(method: str, path: str, body=None, stream=False):
    url = BASE_URL + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    for k, v in HEADERS.items():
        req.add_header(k, v)
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        raw = resp.read()
        ct = resp.headers.get("Content-Type", "")
        if "application/json" in ct:
            return json.loads(raw)
        return raw
    except urllib.error.HTTPError as e:
        body_text = e.read().decode(errors="replace")
        raise RuntimeError(f"HTTP {e.code} {e.reason} — {body_text[:400]}")


def _download(path: str, dest: Path):
    """Download via redirect (Comfy Cloud /api/view returns 302 to signed URL)."""
    url = BASE_URL + path
    req = urllib.request.Request(url, method="GET")
    for k, v in HEADERS.items():
        req.add_header(k, v)
    # follow redirects manually so we can strip auth headers on redirect
    opener = urllib.request.build_opener(urllib.request.HTTPRedirectHandler())
    with opener.open(req, timeout=60) as resp:
        dest.write_bytes(resp.read())


# ---------------------------------------------------------------------------
# Workflow builders
# ---------------------------------------------------------------------------

def _seed():
    return int(uuid.uuid4()) % (2**32)


def build_flux_dev_workflow(positive: str, negative: str,
                             width: int, height: int,
                             steps: int, cfg: float,
                             unet_name: str = MODEL_FLUX_DEV,
                             batch_size: int = 1) -> dict:
    """Standard ComfyUI Flux Dev/Schnell workflow (UNETLoader path)."""
    seed = _seed()
    return {
        "1": {
            "class_type": "UNETLoader",
            "inputs": {"unet_name": unet_name, "weight_dtype": "default"},
        },
        "2": {
            "class_type": "DualCLIPLoader",
            "inputs": {
                "clip_name1": CLIP_T5,
                "clip_name2": CLIP_L,
                "type": "flux",
            },
        },
        "3": {
            "class_type": "VAELoader",
            "inputs": {"vae_name": VAE_FLUX},
        },
        "4": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": positive, "clip": ["2", 0]},
        },
        "5": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": negative, "clip": ["2", 0]},
        },
        "6": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": width, "height": height, "batch_size": batch_size},
        },
        "7": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["1", 0],
                "positive": ["4", 0],
                "negative": ["5", 0],
                "latent_image": ["6", 0],
                "seed": seed,
                "steps": steps,
                "cfg": cfg,
                "sampler_name": "euler",
                "scheduler": "simple",
                "denoise": 1.0,
            },
        },
        "8": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["7", 0], "vae": ["3", 0]},
        },
        "9": {
            "class_type": "SaveImage",
            "inputs": {"filename_prefix": "dayz", "images": ["8", 0]},
        },
    }


def build_sdxl_workflow(positive: str, negative: str,
                         width: int, height: int,
                         steps: int, cfg: float,
                         batch_size: int = 1) -> dict:
    """Standard SDXL checkpoint workflow."""
    seed = _seed()
    return {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": MODEL_SDXL},
        },
        "2": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": positive, "clip": ["1", 1]},
        },
        "3": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": negative, "clip": ["1", 1]},
        },
        "4": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": width, "height": height, "batch_size": batch_size},
        },
        "5": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["1", 0],
                "positive": ["2", 0],
                "negative": ["3", 0],
                "latent_image": ["4", 0],
                "seed": seed,
                "steps": steps,
                "cfg": cfg,
                "sampler_name": "euler_ancestral",
                "scheduler": "karras",
                "denoise": 1.0,
            },
        },
        "6": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["5", 0], "vae": ["1", 2]},
        },
        "7": {
            "class_type": "SaveImage",
            "inputs": {"filename_prefix": "dayz", "images": ["6", 0]},
        },
    }


def _aspect_ratio_str(width: int, height: int) -> str:
    """Convert pixel dimensions to Flux Pro aspect ratio string.
    Flux Pro accepts ratios between 1:4 and 4:1.
    Clamp to the allowed range if needed.
    """
    from math import gcd
    ratio = width / height
    # Clamp to 4:1 max
    if ratio > 4.0:
        return "4:1"
    if ratio < 0.25:
        return "1:4"
    g = gcd(width, height)
    w, h = width // g, height // g
    return f"{w}:{h}"


def build_flux_pro_workflow(positive: str, negative: str,
                              width: int, height: int,
                              steps: int) -> dict:
    """
    Flux 1.1 Pro via Comfy Cloud Partner Node (FluxProUltraImageNode).
    - Does NOT support negative prompts or explicit steps/CFG.
    - Uses aspect_ratio string, not pixel dimensions.
    - extra_data must include api_key_comfy_org (handled by submit_workflow).
    """
    return {
        "1": {
            "class_type": "FluxProUltraImageNode",
            "inputs": {
                "prompt": positive,
                "prompt_upsampling": False,
                "seed": _seed(),
                "aspect_ratio": _aspect_ratio_str(width, height),
                "raw": False,
            },
        },
        "2": {
            "class_type": "SaveImage",
            "inputs": {
                "filename_prefix": "dayz",
                "images": ["1", 0],
            },
        },
    }


# ---------------------------------------------------------------------------
# Asset definitions
# ---------------------------------------------------------------------------

_HERO_POS = (
    "ultra wide cinematic shot, lone operator's tactical command workbench mid-shift, "
    "olive drab and gunmetal grey palette with warm amber accent lighting, "
    "subtle blueprint blue glow on technical schematics, "
    "multiple displays showing data dashboards and server status with amber and cold blue readouts, "
    "folded tactical map with handwritten coordinates, weathered handheld radio with curled cable, "
    "engineering notebook with handwritten field notes, rolled blueprint paper, "
    "hand-labeled ammo cans and storage cases with stencil markings, "
    "brushed steel and scratched aluminum panels, faded unit patches, dog tags on lanyard, "
    "exposed cable runs along painted concrete wall, slight rust patina on metal edges, "
    "empty operator chair, lived-in but disciplined, lone-operator long-deployment energy, "
    "moody key lighting from upper left, deep ambient shadows, dust particles in light beams, "
    "shallow depth of field, photorealistic, gritty practical aesthetic, "
    "subtle film grain, 35mm anamorphic lens look, no people"
)
_HERO_NEG = (
    "clean polished glossy modern office, bright daylight, sterile, "
    "futuristic sci-fi, cyberpunk neon, anime, illustration, cartoon, "
    "post-apocalyptic ruined decay abandoned dystopian, "
    "low quality, blurry, oversaturated, people, person, character, face, "
    "text overlay, watermark"
)

_LOGO_SIGIL_POS = (
    "military unit patch design, embroidered fabric texture, circular shield shape, "
    "olive drab and gunmetal grey thread with warm amber accent stitching, "
    "subtle blueprint blue accent thread on central technical diagram, "
    "central design featuring stylized network architecture with connected nodes "
    "integrated with subtle hazard skull silhouette, "
    "distressed and weathered, frayed edges, veteran's earned patch aesthetic, "
    "photorealistic embroidery detail, isolated on dark background, "
    "centered composition, flat lighting to emphasize texture"
)
_LOGO_STENCIL_POS = (
    "military stencil spray painted text reading \"DAYZ\" on weathered shipping "
    "container metal surface, cracked olive drab paint, rust streaks, "
    "tactical military aesthetic, single bold stencil typography, "
    "slash mark through text or tactical numbering below, "
    "distressed and weathered, photorealistic close-up, "
    "centered composition, harsh side lighting emphasizing texture"
)
_LOGO_NEG = (
    "clean, polished, modern logo design, vector art, flat design, "
    "corporate, glossy, gradient, multiple subjects, watermark"
)

_ARCH_POS = (
    "hand-drawn technical schematic on aged graph paper, field engineer's notebook page, "
    "five-layer architectural diagram drawn in cross-section, "
    "sepia ink with blueprint blue accent lines and amber highlight marks, "
    "handwritten annotations in military stencil font, "
    "layer 1 drawn as data vault filing cabinet with drawers, "
    "layer 2 drawn as radio antenna array intercepting signals, "
    "layer 3 drawn as wrench crossed with blueprint scroll, "
    "layer 4 drawn as tactical handheld instruments, "
    "layer 5 drawn as small infantry foot patrol icon, "
    "connecting arrows and dotted lines between layers, coffee stain in corner, "
    "eraser smudges, fingerprints, graph paper grid visible underneath, "
    "weathered and aged, photorealistic notebook texture, "
    "slight perspective tilt as if photographed on a desk under amber work lamp"
)
_ARCH_NEG = (
    "clean digital design, vector graphics, modern UI, flat design, "
    "sterile, bright colors, neon, cyberpunk, sci-fi, animated, "
    "clean lines without texture, multiple pages, watermark"
)

_ICON_TEMPLATE = (
    "single bold stencil spray painted icon of {subject}, military tactical aesthetic, "
    "olive drab paint with subtle warm amber edge glow, "
    "weathered painted concrete wall background, "
    "distressed and cracked paint, slight rust streaks, "
    "photorealistic close-up texture, isolated centered subject, "
    "harsh directional key lighting from upper left, deep shadows, "
    "no text, no labels, single color silhouette"
)
_ICON_NEG = (
    "detailed illustration, photorealistic object, color photo, multiple subjects, "
    "text, labels, clean modern design, vector graphic"
)

_DIVIDER_POS = (
    "narrow horizontal tactical HUD readout strip, dark gunmetal grey background, "
    "warm amber and olive drab coordinate ticks and crosshair markings, "
    "subtle blueprint blue accent on data values, range indicator marks, "
    "scan line, military targeting overlay, minimalist, "
    "photorealistic CRT screen aesthetic, slight scanline distortion, "
    "atmospheric, cinematic"
)
_DIVIDER_NEG = (
    "illustration, cartoon, clean modern UI, bright colors, multiple lines, "
    "text, busy composition, watermark"
)

_FOOTER_POS = (
    "ultra wide cinematic shot, long horizontal view of operator's workbench corner, "
    "olive drab and gunmetal grey palette with warm amber accent lighting from work lamp, "
    "subtle blueprint blue glow from technical schematic on the wall, "
    "row of hand-labeled storage cases and ammo cans with stencil markings, "
    "weathered handheld radio, folded tactical map, brushed steel surface, "
    "exposed cable runs along painted concrete wall, faded unit patches pinned up, "
    "lived-in but disciplined, lone-operator end-of-shift mood, "
    "moody key lighting from upper left, deep ambient shadows, dust particles in light beams, "
    "shallow depth of field, photorealistic, gritty practical aesthetic, "
    "subtle film grain, 35mm anamorphic lens look, no people"
)
_FOOTER_NEG = (
    "people visible, character, face, bright daytime, clean modern office, "
    "sci-fi, cyberpunk, post-apocalyptic ruined decay, busy composition, text"
)

# Asset specs: (asset_id, label, workflow_fn_args, output_stem, count)
# workflow_fn_args: (builder_fn, pos, neg, w, h, steps, cfg)
def _asset_specs(logo_variant="sigil"):
    logo_pos = _LOGO_SIGIL_POS if logo_variant == "sigil" else _LOGO_STENCIL_POS
    logo_stem = "logo-sigil" if logo_variant == "sigil" else "logo-stencil"

    return {
        1: {
            "label": "Hero Banner (1280×320, Flux 1.1 Pro)",
            "builder": "flux_pro",
            "pos": _HERO_POS, "neg": _HERO_NEG,
            "w": 1280, "h": 320, "steps": 45, "cfg": 4.5,
            "default_count": 4,
            "stems": ["hero-banner"],
        },
        2: {
            "label": f"Logo / Mark (512×512, Flux Dev) [{logo_variant}]",
            "builder": "flux_dev",
            "pos": logo_pos, "neg": _LOGO_NEG,
            "w": 512, "h": 512, "steps": 50, "cfg": 4.0,
            "default_count": 6,
            "stems": [logo_stem],
        },
        3: {
            "label": "Architecture Diagram (1600×1200, Flux Dev)",
            "builder": "flux_dev",
            "pos": _ARCH_POS, "neg": _ARCH_NEG,
            "w": 1600, "h": 1200, "steps": 50, "cfg": 4.0,
            "default_count": 4,
            "stems": ["architecture-diagram"],
        },
        4: {
            "label": "Stream Icons ×4 (256×256, Flux Schnell)",
            "builder": "flux_schnell",
            "multi": [
                {
                    "pos": _ICON_TEMPLATE.format(subject="multi-tool swiss army knife silhouette"),
                    "neg": _ICON_NEG, "stem": "stream-platform",
                },
                {
                    "pos": _ICON_TEMPLATE.format(subject="geometric beehive hexagon pattern"),
                    "neg": _ICON_NEG, "stem": "stream-hive",
                },
                {
                    "pos": _ICON_TEMPLATE.format(subject="radio antenna tower with signal pulse rings"),
                    "neg": _ICON_NEG, "stem": "stream-bosssignal",
                },
                {
                    "pos": _ICON_TEMPLATE.format(subject="tactical compass with crosshair"),
                    "neg": _ICON_NEG, "stem": "stream-play",
                },
            ],
            "w": 256, "h": 256, "steps": 35, "cfg": 1.0,
            "default_count": 4,
        },
        5: {
            "label": "Section Dividers ×3 (1536×96, Flux Schnell)",
            "builder": "flux_schnell",
            "pos": _DIVIDER_POS, "neg": _DIVIDER_NEG,
            "w": 1536, "h": 96, "steps": 30, "cfg": 1.0,
            "default_count": 6,
            "stems": ["divider-1", "divider-2", "divider-3"],
        },
        6: {
            # 1280×200 = 6.4:1, beyond Flux Pro's 4:1 max → use Flux Dev
            "label": "Status Footer (1280×200, Flux Dev)",
            "builder": "flux_dev",
            "pos": _FOOTER_POS, "neg": _FOOTER_NEG,
            "w": 1280, "h": 200, "steps": 45, "cfg": 4.5,
            "default_count": 4,
            "stems": ["status-footer"],
        },
    }


GENERATION_ORDER = [1, 6, 2, 3, 4, 5]


# ---------------------------------------------------------------------------
# Core: submit / WS-poll / download
# ---------------------------------------------------------------------------

def submit_workflow(workflow: dict, extra_data: dict | None = None) -> str:
    body = {"prompt": workflow}
    if extra_data:
        body["extra_data"] = extra_data
    result = _req("POST", "/api/prompt", body)
    prompt_id = result.get("prompt_id")
    if not prompt_id:
        raise RuntimeError(f"No prompt_id in response: {result}")
    return prompt_id


def ws_poll(prompt_id: str, timeout: int = 600) -> list[dict]:
    """
    Connect to Comfy Cloud WebSocket, track execution of prompt_id,
    and return list of output {filename, subfolder, type} dicts.

    WS URL: wss://cloud.comfy.org/ws?clientId=<uuid>&token=<api_key>
    Relevant messages:
      {"type":"executing",      "data":{"node":null, "prompt_id":X}}  — done
      {"type":"executed",       "data":{"node":N, "prompt_id":X, "output":{"images":[...]}}}
      {"type":"execution_error","data":{"prompt_id":X, "exception_message":...}}
    """
    import websocket as ws_lib

    client_id = str(uuid.uuid4())
    ws_url = f"wss://cloud.comfy.org/ws?clientId={client_id}&token={API_KEY}"

    import threading as _threading
    output_images: list[dict] = []
    done = _threading.Event()
    error = None
    deadline = time.time() + timeout

    print(f"  WS {prompt_id[:8]}… ", end="", flush=True)

    def on_message(ws, msg):
        nonlocal done, error
        if isinstance(msg, bytes):
            return  # binary preview frame, skip
        try:
            data = json.loads(msg)
        except Exception:
            return
        mtype = data.get("type", "")
        mdata = data.get("data", {})

        if mdata.get("prompt_id") not in (None, prompt_id):
            return  # belongs to a different job

        if mtype in ("execution_success",) or (mtype == "executing" and mdata.get("node") is None):
            print("done ", end="", flush=True)
            done.set()
            ws.close()

        elif mtype == "executed":
            imgs = mdata.get("output", {}).get("images", [])
            output_images.extend(imgs)

        elif mtype in ("execution_error", "execution_interrupted"):
            error = mdata.get("exception_message", mtype)
            ws.close()

        elif mtype == "progress":
            step = mdata.get("value", "?")
            total = mdata.get("max", "?")
            print(f"{step}/{total} ", end="", flush=True)

    def on_error(ws, err):
        nonlocal error
        error = str(err)
        done.set()

    wsapp = ws_lib.WebSocketApp(
        ws_url,
        on_message=on_message,
        on_error=on_error,
    )
    import threading as _t2
    t = _t2.Thread(target=wsapp.run_forever, daemon=True)
    t.start()

    done.wait(timeout=timeout)
    wsapp.close()
    t.join(timeout=5)

    if error:
        raise RuntimeError(f"Job {prompt_id} failed: {error}")
    if not done.is_set():
        raise TimeoutError(f"Job {prompt_id} timed out after {timeout}s")

    # Fallback: if WS gave no images, try REST status endpoint
    if not output_images:
        output_images = _get_outputs_rest(prompt_id)

    print(f"OK ({len(output_images)} image(s))")
    return output_images


def _get_outputs_rest(prompt_id: str) -> list[dict]:
    """Best-effort REST fallback for output filenames."""
    try:
        status = _req("GET", f"/api/job/{prompt_id}/status")
        outputs = status.get("outputs", {})
        files = []
        for node_out in outputs.values():
            if isinstance(node_out, dict):
                files.extend(node_out.get("images", []))
        return files
    except Exception:
        return []


def download_output(file_info: dict, dest: Path):
    """Download a generated image to dest path."""
    # file_info may be {filename, subfolder, type} or just {url}
    if "url" in file_info:
        _download_url(file_info["url"], dest)
    else:
        fname = file_info["filename"]
        subfolder = file_info.get("subfolder", "")
        ftype = file_info.get("type", "output")
        path = f"/api/view?filename={fname}&subfolder={subfolder}&type={ftype}"
        _download(path, dest)
    print(f"  Saved -> {dest.name}")


def _download_url(url: str, dest: Path):
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=60) as resp:
        dest.write_bytes(resp.read())


# ---------------------------------------------------------------------------
# Generation runner
# ---------------------------------------------------------------------------

def build_workflow(spec: dict, pos: str, neg: str) -> dict:
    builder = spec["builder"]
    w, h, steps, cfg = spec["w"], spec["h"], spec["steps"], spec["cfg"]
    if builder == "flux_pro":
        return build_flux_pro_workflow(pos, neg, w, h, steps)
    elif builder == "flux_dev":
        return build_flux_dev_workflow(pos, neg, w, h, steps, cfg)
    elif builder == "flux_schnell":
        return build_flux_dev_workflow(pos, neg, w, h, steps, cfg,
                                        unet_name=MODEL_FLUX_SCHNELL)
    elif builder == "sdxl":
        return build_sdxl_workflow(pos, neg, w, h, steps, cfg)
    raise ValueError(f"Unknown builder: {builder}")


def run_generation(asset_id: int, count: int | None = None,
                   logo_variant: str = "sigil", dry_run: bool = False):
    specs = _asset_specs(logo_variant)
    spec = specs[asset_id]
    print(f"\n=== Asset {asset_id}: {spec['label']} ===")

    extra_data = {"api_key_comfy_org": API_KEY} if spec["builder"] == "flux_pro" else None

    # Multi-subject assets (stream icons)
    if "multi" in spec:
        icon_count = count or spec["default_count"]
        for icon in spec["multi"]:
            print(f"\n  -> Icon: {icon['stem']}")
            for i in range(icon_count):
                print(f"    Variation {i+1}/{icon_count}")
                wf = build_workflow(spec, icon["pos"], icon["neg"])
                if dry_run:
                    print(json.dumps(wf, indent=2))
                    continue
                _submit_and_save(wf, extra_data, icon["stem"], icon_count, i)
        return

    # Single-subject assets
    n = count or spec["default_count"]
    pos, neg = spec["pos"], spec["neg"]
    stem = spec["stems"][0]

    for i in range(n):
        print(f"  Variation {i+1}/{n}")
        wf = build_workflow(spec, pos, neg)
        if dry_run:
            print(json.dumps(wf, indent=2))
            continue
        _submit_and_save(wf, extra_data, stem, n, i)


def _submit_and_save(wf: dict, extra_data, stem: str, total: int, idx: int):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    last_err = None
    files = []
    for attempt in range(1, 4):
        try:
            prompt_id = submit_workflow(wf, extra_data)
            files = ws_poll(prompt_id)
            break
        except (RuntimeError, TimeoutError) as e:
            last_err = e
            print(f"\n  [attempt {attempt}/3 failed: {e}] retrying...", flush=True)
            time.sleep(3)
    else:
        print(f"  WARNING: gave up after 3 attempts: {last_err}")
        return
    if not files:
        print(f"  WARNING: no output files found for {prompt_id}")
        return
    for j, f in enumerate(files):
        suffix = f"_{idx+1}" if total > 1 else ""
        part = f"_{j+1}" if len(files) > 1 else ""
        dest = OUTPUT_DIR / f"{stem}{suffix}{part}.png"
        download_output(f, dest)


# ---------------------------------------------------------------------------
# Probe mode
# ---------------------------------------------------------------------------

def probe():
    print("Querying Comfy Cloud for available nodes/models…\n")
    try:
        info = _req("GET", "/api/object_info")
    except RuntimeError as e:
        print(f"Error: {e}")
        sys.exit(1)

    checkpoints = []
    unets = []
    vaes = []
    partner_nodes = []

    for node_name, node_def in info.items():
        if not isinstance(node_def, dict):
            continue
        category = node_def.get("category", "")
        inputs = node_def.get("input", {}).get("required", {})

        # Checkpoint loaders
        if "ckpt_name" in inputs:
            options = inputs["ckpt_name"][0] if isinstance(inputs["ckpt_name"], list) else []
            checkpoints.append((node_name, options))
        # UNET loaders
        if "unet_name" in inputs:
            options = inputs["unet_name"][0] if isinstance(inputs["unet_name"], list) else []
            unets.append((node_name, options))
        # VAE
        if "vae_name" in inputs:
            options = inputs["vae_name"][0] if isinstance(inputs["vae_name"], list) else []
            vaes.append((node_name, options))
        # Heuristic: partner nodes often have "flux" or "pro" in name
        nl = node_name.lower()
        if any(k in nl for k in ("flux", "pro", "partner", "api", "ideogram")):
            partner_nodes.append(node_name)

    print("=== Checkpoint models ===")
    for n, opts in checkpoints:
        print(f"  [{n}]")
        for o in (opts if isinstance(opts, list) else [opts]):
            print(f"    {o}")

    print("\n=== UNET models ===")
    for n, opts in unets:
        print(f"  [{n}]")
        for o in (opts if isinstance(opts, list) else [opts]):
            print(f"    {o}")

    print("\n=== VAE models ===")
    for n, opts in vaes:
        print(f"  [{n}]")
        for o in (opts if isinstance(opts, list) else [opts]):
            print(f"    {o}")

    print("\n=== Possible Partner/API nodes ===")
    for n in partner_nodes:
        print(f"  {n}")

    if not any([checkpoints, unets, partner_nodes]):
        print("(No models found — may need to check auth or update API path)")
        print("\nFull node list:")
        for k in sorted(info.keys()):
            print(f"  {k}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Comfy Cloud dayz asset generator")
    parser.add_argument("--probe", action="store_true",
                        help="List available models and nodes")
    parser.add_argument("--asset", type=int, choices=range(1, 7), metavar="N",
                        help="Generate asset N (1-6)")
    parser.add_argument("--all", action="store_true",
                        help="Generate all assets in handoff order")
    parser.add_argument("--count", type=int,
                        help="Number of variations to generate")
    parser.add_argument("--logo", choices=["sigil", "stencil"], default="sigil",
                        help="Logo variant for asset 2 (default: sigil)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print workflow JSON without submitting")
    args = parser.parse_args()

    if args.probe:
        probe()
        return

    if args.all:
        for aid in GENERATION_ORDER:
            run_generation(aid, count=args.count, logo_variant=args.logo,
                           dry_run=args.dry_run)
        return

    if args.asset:
        run_generation(args.asset, count=args.count, logo_variant=args.logo,
                       dry_run=args.dry_run)
        return

    parser.print_help()


if __name__ == "__main__":
    main()
