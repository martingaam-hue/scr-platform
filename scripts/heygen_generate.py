#!/usr/bin/env python3
"""
SCR Platform — HeyGen Video Generation Script
==============================================
Automates creation of the 22-scene product demo video via HeyGen API.

Usage:
    python heygen_generate.py --clips-dir ./clips [OPTIONS]

Required environment variable (or --api-key flag):
    HEYGEN_API_KEY=your_key_here

Quick start:
    1. Record the 26 screen clips (see docs/HEYGEN_SCENES.md Section B)
    2. Run the ffmpeg combiner:   bash scripts/heygen_combine_clips.sh ./clips
    3. Set your API key:          export HEYGEN_API_KEY=your_key
    4. Discover avatar/voice IDs: python heygen_generate.py --list-avatars
                                  python heygen_generate.py --list-voices
    5. Generate the video:        python heygen_generate.py --clips-dir ./clips
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import httpx

# ── API constants ─────────────────────────────────────────────────────────────
BASE_URL   = "https://api.heygen.com"
HEADERS    = {}   # populated after arg parsing

# ── Scene data ────────────────────────────────────────────────────────────────
# Each entry defines one HeyGen scene (= one video_inputs element).
#
# Keys:
#   id           int   scene number (1-22)
#   name         str   human label
#   bg_type      str   "color" | "video"
#   bg_color     str   hex string for color scenes
#   clip         str | None  filename in clips_dir (None for color slides)
#   avatar       bool  show avatar (False on pure title/logo slides)
#   script       str | None  TTS text (None for silence-duration slides)
#   silence_sec  int | None  seconds of silence (for non-speaking slides)
#   overlay      str | None  primary text overlay content
#   title_lines  list[str]   centred title text lines (for slides 01-04, 22)
#   voice_speed  float       override default 0.92 speed

SCENES = [
    {
        "id": 1,
        "name": "Pain Point 1",
        "bg_type": "color",
        "bg_color": "#0A0A0A",
        "clip": None,
        "avatar": False,
        "script": None,
        "silence_sec": 4,
        "overlay": None,
        "title_lines": [
            '"Every week, a fund manager loses a deal',
            'because their due diligence took too long."',
        ],
    },
    {
        "id": 2,
        "name": "Pain Point 2",
        "bg_type": "color",
        "bg_color": "#0A0A0A",
        "clip": None,
        "avatar": False,
        "script": None,
        "silence_sec": 4,
        "overlay": None,
        "title_lines": [
            '"Every quarter, an LP receives a report',
            'that took their analyst two weeks to assemble."',
        ],
    },
    {
        "id": 3,
        "name": "Pain Point 3",
        "bg_type": "color",
        "bg_color": "#0A0A0A",
        "clip": None,
        "avatar": False,
        "script": None,
        "silence_sec": 4,
        "overlay": None,
        "title_lines": [
            '"Every day, a covenant breach builds — undetected —',
            'in a spreadsheet no one is watching."',
        ],
    },
    {
        "id": 4,
        "name": "Logo Reveal",
        "bg_type": "color",
        "bg_color": "#0A0A0A",
        "clip": None,
        "avatar": False,
        "script": None,
        "silence_sec": 8,
        "overlay": None,
        "title_lines": [
            "SCR Platform",
            "The AI-Native Operating System for Sustainable Infrastructure Investment",
        ],
    },
    {
        "id": 5,
        "name": "Dashboard Overview",
        "bg_type": "video",
        "clip": "scene05_bg.mp4",
        "avatar": True,
        "script": (
            "This is the SCR Platform. A single operating system for every stage "
            "of the investment lifecycle. From the first deal screen to LP reporting, "
            "every workflow lives here."
        ),
        "overlay": "Live Portfolio Data",
    },
    {
        "id": 6,
        "name": "Navigation Depth",
        "bg_type": "video",
        "clip": "scene06_bg.mp4",
        "avatar": True,
        "script": (
            "The platform covers eighty-one distinct modules. Deal origination, "
            "due diligence, portfolio monitoring, covenant tracking, and automated "
            "LP reporting. We'll walk through the ones that matter most."
        ),
        "overlay": "81 Modules · Single Platform",
    },
    {
        "id": 7,
        "name": "Signal Score Introduction",
        "bg_type": "video",
        "clip": "scene07_bg.mp4",
        "avatar": True,
        "script": (
            "Every project on SCR receives a Signal Score. "
            "An AI-calculated viability rating that tells an investor, in a single number, "
            "how investment-ready this project is. "
            "Seventy-four out of one hundred. "
            "But the number alone tells you nothing. "
            "The value is in what's underneath it."
        ),
        "overlay": "Signal Score™  74 / 100",
    },
    {
        "id": 8,
        "name": "Signal Score Dimensions",
        "bg_type": "video",
        "clip": "scene08_bg.mp4",
        "avatar": True,
        "script": (
            "Six dimensions. Forty-eight specific criteria. "
            "The platform has read every document in this project's data room, "
            "financial models, technical studies, legal agreements, ESG reports, "
            "and assessed each one against its standard. "
            "Hover into any dimension and you see the criterion-level breakdown. "
            "This project scores well on its revenue model and PPA structure. "
            "But the debt service coverage analysis hasn't been uploaded yet. "
            "That's what's holding the financial planning score down."
        ),
        "overlay": "6 Dimensions · 48 Criteria",
    },
    {
        "id": 9,
        "name": "Gap Analysis",
        "bg_type": "video",
        "clip": "scene09_bg.mp4",
        "avatar": True,
        "script": (
            "The Gap Analysis turns the score into an action plan. "
            "Uploading the DSCR analysis would add nine points to financial planning. "
            "That's the single highest-impact action this developer can take today."
        ),
        "overlay": "+9 pts if DSCR uploaded",
    },
    {
        "id": 10,
        "name": "What Changed Timeline",
        "bg_type": "video",
        "clip": "scene10_bg.mp4",
        "avatar": True,
        "script": (
            "Every score change is explained. "
            "Three weeks ago, the team uploaded the grid connection study. "
            "That added eleven points to project viability. "
            "The developer can see exactly what moved the needle, and why."
        ),
        "overlay": "Explainable AI — Every change traced to its source",
    },
    {
        "id": 11,
        "name": "Smart Screener Query",
        "bg_type": "video",
        "clip": "scene11_bg.mp4",
        "avatar": True,
        "script": (
            "Finding deals shouldn't require a filter panel. "
            "The Smart Screener accepts plain English. "
            "Watch."
        ),
        "overlay": "Smart Screener — Natural Language Search",
    },
    {
        "id": 12,
        "name": "Screener Results",
        "bg_type": "video",
        "clip": "scene12_bg.mp4",
        "avatar": True,
        "script": (
            "The AI reads that query, extracts the intent, "
            "and returns ranked results in under a second. "
            "Drawing on the full text of every project document in the platform. "
            "Not just headline metadata. "
            "Save the search, and the platform will notify you the moment "
            "a new project matching these criteria is added."
        ),
        "overlay": "Never miss a deal that fits your mandate",
    },
    {
        "id": 13,
        "name": "Ralph Introduction",
        "bg_type": "video",
        "clip": "scene13_bg.mp4",
        "avatar": True,
        "script": (
            "Ralph is SCR's AI research assistant. "
            "He can answer complex investment questions by reasoning across "
            "every document in the platform. "
            "Not a generic chatbot. "
            "An analyst who has read everything you've uploaded. "
            "Watch what happens when we ask about legal risk."
        ),
        "overlay": "Ralph — AI Research Assistant",
    },
    {
        "id": 14,
        "name": "Ralph Citations",
        "bg_type": "video",
        "clip": "scene14_bg.mp4",   # CLIP-10 + CLIP-11 pre-combined
        "avatar": True,
        "script": (
            "Notice the citations. "
            "Every claim Ralph makes is sourced from a specific document. "
            "This isn't a hallucination. It's a traceable analysis. "
            "Click citation one, and the platform takes you directly to the source. "
            "The exact paragraph in the original document that Ralph drew from. "
            "Every AI output on this platform works this way. "
            "You can verify every conclusion."
        ),
        "overlay": "Click any citation → jumps to exact source paragraph",
    },
    {
        "id": 15,
        "name": "Ralph Portfolio Comparison",
        "bg_type": "video",
        "clip": "scene15_bg.mp4",   # CLIP-12
        "avatar": True,
        "script": (
            "Ralph has access to nineteen specialised tools that give him "
            "direct access to platform data. "
            "Signal scores, portfolio metrics, valuations, "
            "carbon credit calculations, legal document analysis. "
            "He's not just summarising text. "
            "He's computing answers from live data."
        ),
        "overlay": "19 Tools · Live Platform Data",
    },
    {
        "id": 16,
        "name": "Data Room & Document Intelligence",
        "bg_type": "video",
        "clip": "scene16_bg.mp4",   # CLIP-13
        "avatar": True,
        "script": (
            "The data room is where deals live. "
            "But unlike a traditional VDR, every document here is actively processed "
            "by the platform's AI the moment it's uploaded. "
            "When this financial model was uploaded, the platform automatically "
            "classified it, extracted forty-three key metrics, "
            "IRR, NPV, DSCR, revenue by year, "
            "and made them available for scoring, benchmarking, and Ralph's analysis. "
            "No manual tagging. No copy-paste."
        ),
        "overlay": "43 metrics extracted automatically",
    },
    {
        "id": 17,
        "name": "Version History & Redaction",
        "bg_type": "video",
        "clip": "scene17_bg.mp4",   # CLIP-14 + CLIP-15 pre-combined
        "avatar": True,
        "script": (
            "Full version control on every document. "
            "SHA-256 checksums for integrity verification. "
            "The Access Log shows exactly which investor viewed which version, and when. "
            "That's the engagement data that tells you whether an LP has actually "
            "read the materials before a call. "
            "And before sharing externally, the redaction tool runs an AI scan "
            "for sensitive entities. "
            "The AI flags every candidate for human review. "
            "Approved redactions are applied, a clean PDF is generated, "
            "and the entire decision is in the audit trail."
        ),
        "overlay": "AI-assisted redaction · Human review required",
    },
    {
        "id": 18,
        "name": "Covenant Monitoring",
        "bg_type": "video",
        "clip": "scene18_bg.mp4",   # CLIP-16 + CLIP-17 + CLIP-18 pre-combined
        "avatar": True,
        "script": (
            "Portfolio management is only as good as its ability to catch problems early. "
            "SCR checks every investment covenant every night. "
            "This project's Debt Service Coverage Ratio dropped below the warning "
            "threshold three nights ago. "
            "The portfolio manager received an alert the morning it happened. "
            "Not in the next quarterly report. "
            "The trend chart shows six months of deterioration. "
            "Without this, that conversation happens at the board meeting, "
            "not three weeks before it. "
            "And every metric is benchmarked. "
            "This project's IRR sits at the sixty-eighth percentile versus "
            "comparable solar assets from the same vintage year."
        ),
        "overlay": "Compliant → Warning → Breach · Daily automated checks",
    },
    {
        "id": 19,
        "name": "LP Reporting",
        "bg_type": "video",
        "clip": "scene19_bg.mp4",   # CLIP-19 + CLIP-20 + CLIP-21 pre-combined
        "avatar": True,
        "script": (
            "Quarterly LP reporting is the most time-consuming recurring task "
            "in fund management. SCR eliminates most of it. "
            "Select the template, select the fund, choose the output format. "
            "The platform draws from live data, portfolio performance, "
            "benchmark positions, covenant status, pacing analysis, ESG scores, "
            "and generates the report. In under ten seconds. "
            "A publication-quality quarterly report, compiled automatically. "
            "The same report that previously took a two-person analyst team "
            "two weeks now takes seconds. "
            "Set a schedule once, and the platform generates and distributes "
            "the report automatically every quarter."
        ),
        "overlay": "PDF · Excel · PowerPoint — All formats, all automated",
    },
    {
        "id": 20,
        "name": "Enterprise & Admin",
        "bg_type": "video",
        "clip": "scene20_bg.mp4",   # CLIP-22+23+24+25 pre-combined
        "avatar": True,
        "script": (
            "For platform administrators, everything is visible and controllable. "
            "The AI cost dashboard shows real-time spend by provider and task type "
            "across every organisation on the platform. "
            "Every AI behaviour is managed through the Prompt Registry. "
            "When an analyst needs the investment memo template to emphasise "
            "climate risk differently, an admin changes the prompt here. "
            "No code. No redeployment. Live in minutes. "
            "Features can be toggled globally or per organisation. "
            "And for enterprise clients, the platform deploys under "
            "their own brand and domain."
        ),
        "overlay": "Edit AI behaviour without code",
    },
    {
        "id": 21,
        "name": "Closing Monologue",
        "bg_type": "video",
        "clip": "scene21_bg.mp4",   # CLIP-26
        "avatar": True,
        "script": (
            "SCR Platform is not a suite of tools bolted together. "
            "It's a single operating system where every component shares "
            "the same data foundation, and reinforces every other. "
            "When a document is uploaded, the score updates. "
            "When the score changes, the portfolio manager is notified. "
            "When the covenant breaches, the LP report already reflects it. "
            "When the analyst asks Ralph a question, the answer cites the document "
            "that was uploaded this morning. "
            "Eighty-one application modules. "
            "One hundred and seventy-six data models. "
            "Five AI providers. "
            "Twenty-five automated workflows running every day. "
            "This is what AI-native infrastructure investment looks like."
        ),
        "overlay": "81 Modules · 176 Data Models · 5 AI Providers · 25 Automations",
    },
    {
        "id": 22,
        "name": "End Card",
        "bg_type": "color",
        "bg_color": "#0A0A0A",
        "clip": None,
        "avatar": False,
        "script": None,
        "silence_sec": 10,
        "overlay": None,
        "title_lines": [
            "SCR Platform",
            "Request a live demo",
            "scr-platform.com",
        ],
    },
]

# ── Clip → scene mapping (for validation) ────────────────────────────────────
# Maps each scene's expected clip filename to the original shot list clips.
# Users run heygen_combine_clips.sh to produce the combined files.
CLIP_SOURCES = {
    "scene05_bg.mp4":  ["clip01.mp4"],
    "scene06_bg.mp4":  ["clip02.mp4"],
    "scene07_bg.mp4":  ["clip03.mp4"],
    "scene08_bg.mp4":  ["clip04.mp4"],
    "scene09_bg.mp4":  ["clip05.mp4"],
    "scene10_bg.mp4":  ["clip06.mp4"],
    "scene11_bg.mp4":  ["clip07.mp4"],
    "scene12_bg.mp4":  ["clip08.mp4"],
    "scene13_bg.mp4":  ["clip09.mp4"],
    "scene14_bg.mp4":  ["clip10.mp4", "clip11.mp4"],       # combined
    "scene15_bg.mp4":  ["clip12.mp4"],
    "scene16_bg.mp4":  ["clip13.mp4"],
    "scene17_bg.mp4":  ["clip14.mp4", "clip15.mp4"],       # combined
    "scene18_bg.mp4":  ["clip16.mp4", "clip17.mp4", "clip18.mp4"],  # combined
    "scene19_bg.mp4":  ["clip19.mp4", "clip20.mp4", "clip21.mp4"],  # combined
    "scene20_bg.mp4":  ["clip22.mp4", "clip23.mp4", "clip24.mp4", "clip25.mp4"],
    "scene21_bg.mp4":  ["clip26.mp4"],
}


# ── API helpers ───────────────────────────────────────────────────────────────

def api_get(path: str, params: dict | None = None) -> dict:
    url = f"{BASE_URL}{path}"
    r = httpx.get(url, headers=HEADERS, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def api_post(path: str, json_body: dict) -> dict:
    url = f"{BASE_URL}{path}"
    r = httpx.post(url, headers=HEADERS, json=json_body, timeout=60)
    r.raise_for_status()
    return r.json()


def upload_video_asset(filepath: Path) -> str:
    """Upload a video file to HeyGen and return the asset_id."""
    print(f"  Uploading {filepath.name} ({filepath.stat().st_size // 1024:,} KB)...")
    url = f"{BASE_URL}/v1/asset/upload"
    with open(filepath, "rb") as fh:
        r = httpx.post(
            url,
            headers={**HEADERS, "Content-Type": "video/mp4"},
            content=fh.read(),
            params={"name": filepath.name},
            timeout=300,
        )
    r.raise_for_status()
    data = r.json()
    asset_id = (
        data.get("data", {}).get("asset_id")
        or data.get("data", {}).get("id")
        or data.get("asset_id")
    )
    if not asset_id:
        raise ValueError(f"Unexpected upload response: {data}")
    print(f"    → asset_id: {asset_id}")
    return asset_id


# ── Scene builder ─────────────────────────────────────────────────────────────

def build_scene(scene: dict, asset_map: dict, avatar_id: str, voice_id: str) -> dict:
    """Convert a SCENES entry into a HeyGen video_inputs object."""
    obj: dict = {}

    # Background
    if scene["bg_type"] == "color":
        obj["background"] = {"type": "color", "value": scene["bg_color"]}
    else:
        asset_id = asset_map[scene["clip"]]
        obj["background"] = {
            "type": "video",
            "video_asset_id": asset_id,
            "play_style": "fit_to_scene",
            "fit": "cover",
        }

    # Character (avatar)
    if scene.get("avatar"):
        obj["character"] = {
            "type": "avatar",
            "avatar_id": avatar_id,
            "avatar_style": "circle",
            "scale": 0.28,
            "offset": {"x": 0.36, "y": 0.36},   # bottom-right quadrant
        }

    # Voice
    if scene.get("script"):
        obj["voice"] = {
            "type": "text",
            "voice_id": voice_id,
            "input_text": scene["script"],
            "speed": scene.get("voice_speed", 0.92),
        }
    else:
        # Silence for title/logo slides
        obj["voice"] = {
            "type": "silence",
            "duration": str(scene.get("silence_sec", 4)),
        }

    # Primary text overlay
    if scene.get("overlay"):
        obj["text"] = {
            "text": scene["overlay"],
            "font_family": "Inter",
            "font_size": 18,
            "font_weight": "bold",
            "color": "#FFFFFF",
            "background_color": "#1F3864",
            "background_border_radius": 12,
            "position": {"x": -0.30, "y": 0.38},   # lower-left
        }
    elif scene.get("title_lines"):
        # Centred title text for full-screen slides
        obj["text"] = {
            "text": "\n".join(scene["title_lines"]),
            "font_family": "Inter",
            "font_size": 28 if scene["id"] == 4 else 24,
            "font_weight": "bold",
            "color": "#FFFFFF",
            "position": {"x": 0.0, "y": 0.0},   # centre
            "alignment": "center",
        }

    return obj


# ── Progress persistence ──────────────────────────────────────────────────────

def load_progress(progress_file: Path) -> dict:
    if progress_file.exists():
        return json.loads(progress_file.read_text())
    return {"uploaded": {}, "video_id": None}


def save_progress(progress_file: Path, progress: dict) -> None:
    progress_file.write_text(json.dumps(progress, indent=2))


# ── Main steps ────────────────────────────────────────────────────────────────

def step_list_avatars() -> None:
    print("\nAvailable avatars:")
    data = api_get("/v2/avatars")
    avatars = data.get("data", {}).get("avatars", [])
    if not avatars:
        print("  (none returned — check your API key)")
        return
    for a in avatars:
        print(f"  ID: {a.get('avatar_id'):<30}  Name: {a.get('avatar_name', '')}")


def step_list_voices() -> None:
    print("\nAvailable voices:")
    data = api_get("/v2/voices")
    voices = data.get("data", {}).get("voices", [])
    if not voices:
        print("  (none returned — check your API key)")
        return
    for v in voices[:50]:  # cap at 50 for readability
        print(
            f"  ID: {v.get('voice_id'):<36}  "
            f"Name: {v.get('name', ''):<25}  "
            f"Gender: {v.get('gender', ''):<8}  "
            f"Locale: {v.get('locale', '')}"
        )
    if len(voices) > 50:
        print(f"  ... and {len(voices) - 50} more. Filter in HeyGen Studio.")


def step_validate_clips(clips_dir: Path) -> list[Path]:
    """Check all required scene clip files exist. Return sorted list."""
    missing = []
    found = []
    for scene in SCENES:
        if scene["bg_type"] != "video":
            continue
        clip_path = clips_dir / scene["clip"]
        if not clip_path.exists():
            missing.append(scene["clip"])
        else:
            found.append(clip_path)

    if missing:
        print("\nMissing clip files:")
        for m in missing:
            sources = CLIP_SOURCES.get(m, [])
            src_str = " + ".join(sources) if sources else "—"
            print(f"  {m}  (from: {src_str})")
        print("\nRun 'bash scripts/heygen_combine_clips.sh <clips_dir>' to create combined files.")
        print("Or manually place the pre-recorded files with the names above.")
        sys.exit(1)

    print(f"\nAll {len(found)} clip files found.")
    return found


def step_upload_clips(
    clips_dir: Path,
    progress: dict,
    progress_file: Path,
    dry_run: bool,
) -> dict:
    """Upload all clip files that haven't been uploaded yet. Returns asset_map."""
    asset_map: dict = dict(progress.get("uploaded", {}))
    clips_needed = [s["clip"] for s in SCENES if s["bg_type"] == "video"]

    to_upload = [c for c in clips_needed if c not in asset_map]
    if not to_upload:
        print(f"\nAll {len(clips_needed)} clips already uploaded (from progress file).")
        return asset_map

    print(f"\nUploading {len(to_upload)} clip(s) to HeyGen...")
    for clip_name in to_upload:
        clip_path = clips_dir / clip_name
        if dry_run:
            asset_map[clip_name] = f"DRY_RUN_ASSET_{clip_name}"
            print(f"  [dry-run] Would upload {clip_name}")
        else:
            asset_id = upload_video_asset(clip_path)
            asset_map[clip_name] = asset_id
            progress["uploaded"] = asset_map
            save_progress(progress_file, progress)

    return asset_map


def step_build_payload(
    asset_map: dict,
    avatar_id: str,
    voice_id: str,
    callback_url: str | None,
) -> dict:
    """Build the full HeyGen /v2/video/generate payload."""
    video_inputs = []
    for scene in SCENES:
        vi = build_scene(scene, asset_map, avatar_id, voice_id)
        video_inputs.append(vi)

    payload: dict = {
        "title": "SCR Platform — Product Demo v1",
        "video_inputs": video_inputs,
        "dimension": {"width": 1920, "height": 1080},
        "caption": False,
    }
    if callback_url:
        payload["callback_url"] = callback_url

    return payload


def step_submit(payload: dict, dry_run: bool) -> str | None:
    """Submit video generation request. Returns video_id."""
    if dry_run:
        print("\n[dry-run] Payload preview (first 2 scenes):")
        preview = {**payload, "video_inputs": payload["video_inputs"][:2]}
        print(json.dumps(preview, indent=2))
        print(f"\n[dry-run] Total scenes: {len(payload['video_inputs'])}")
        return None

    print("\nSubmitting video generation request to HeyGen...")
    resp = api_post("/v2/video/generate", payload)
    video_id = resp.get("data", {}).get("video_id")
    if not video_id:
        print(f"ERROR: Unexpected response: {resp}")
        sys.exit(1)
    print(f"  → video_id: {video_id}")
    return video_id


def step_poll(video_id: str, progress: dict, progress_file: Path) -> str:
    """Poll until rendering is complete. Returns download URL."""
    print("\nPolling render status (this typically takes 15–30 minutes)...")
    wait = 30  # initial wait seconds
    max_wait = 120

    while True:
        time.sleep(wait)
        resp = api_get("/v1/video_status.get", params={"video_id": video_id})
        status = resp.get("data", {}).get("status", "unknown")
        pct    = resp.get("data", {}).get("progress", "?")
        print(f"  Status: {status}  ({pct}%)  [waiting {wait}s before next check]")

        if status == "completed":
            url = (
                resp.get("data", {}).get("video_url")
                or resp.get("data", {}).get("url")
                or resp.get("data", {}).get("download_url")
            )
            if not url:
                print(f"ERROR: completed but no download URL in response: {resp}")
                sys.exit(1)
            progress["video_url"] = url
            save_progress(progress_file, progress)
            return url

        if status == "failed":
            error = resp.get("data", {}).get("error", "unknown error")
            print(f"ERROR: Video generation failed: {error}")
            sys.exit(1)

        wait = min(wait + 15, max_wait)


def step_download(url: str, output_path: Path) -> None:
    """Download the finished MP4."""
    print(f"\nDownloading video to {output_path}...")
    with httpx.stream("GET", url, timeout=600, follow_redirects=True) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        downloaded = 0
        with open(output_path, "wb") as fh:
            for chunk in r.iter_bytes(chunk_size=65536):
                fh.write(chunk)
                downloaded += len(chunk)
                if total:
                    pct = downloaded / total * 100
                    print(f"\r  {pct:.1f}%  ({downloaded // 1024 // 1024} MB)", end="", flush=True)
    print(f"\n  Done. Saved to: {output_path}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Generate SCR Platform demo video via HeyGen API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--clips-dir",    type=Path, default=Path("./clips"),
                   help="Directory containing scene clip files (default: ./clips)")
    p.add_argument("--api-key",      type=str,
                   help="HeyGen API key (default: $HEYGEN_API_KEY)")
    p.add_argument("--avatar-id",    type=str,
                   help="HeyGen avatar ID (default: $HEYGEN_AVATAR_ID)")
    p.add_argument("--voice-id",     type=str,
                   help="HeyGen voice ID (default: $HEYGEN_VOICE_ID)")
    p.add_argument("--output",       type=Path, default=Path("SCR_PLATFORM_DEMO.mp4"),
                   help="Output MP4 path (default: SCR_PLATFORM_DEMO.mp4)")
    p.add_argument("--callback-url", type=str,
                   help="Webhook URL to call when HeyGen finishes rendering")
    p.add_argument("--list-avatars", action="store_true",
                   help="Print available avatars and exit")
    p.add_argument("--list-voices",  action="store_true",
                   help="Print available voices and exit")
    p.add_argument("--dry-run",      action="store_true",
                   help="Build payload and print it without submitting")
    p.add_argument("--resume",       type=Path,
                   help="Path to a previous run's progress JSON to resume from")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    # Resolve API key
    api_key = args.api_key or os.environ.get("HEYGEN_API_KEY", "")
    if not api_key:
        print("ERROR: No API key. Set HEYGEN_API_KEY or pass --api-key")
        sys.exit(1)

    global HEADERS
    HEADERS = {
        "X-Api-Key": api_key,
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    # Discovery flags
    if args.list_avatars:
        step_list_avatars()
        return
    if args.list_voices:
        step_list_voices()
        return

    # Resolve avatar + voice
    avatar_id = args.avatar_id or os.environ.get("HEYGEN_AVATAR_ID", "")
    voice_id  = args.voice_id  or os.environ.get("HEYGEN_VOICE_ID",  "")
    if not avatar_id and not args.dry_run:
        print("ERROR: No avatar ID. Run --list-avatars to find one, then set --avatar-id or $HEYGEN_AVATAR_ID")
        sys.exit(1)
    if not voice_id and not args.dry_run:
        print("ERROR: No voice ID. Run --list-voices to find one, then set --voice-id or $HEYGEN_VOICE_ID")
        sys.exit(1)

    # Progress file
    progress_file = args.resume or Path(".heygen_progress.json")
    progress = load_progress(progress_file)

    print("=" * 60)
    print("SCR Platform — HeyGen Video Generator")
    print("=" * 60)
    print(f"  Clips dir : {args.clips_dir}")
    print(f"  Avatar    : {avatar_id or '(dry-run)'}")
    print(f"  Voice     : {voice_id  or '(dry-run)'}")
    print(f"  Output    : {args.output}")
    print(f"  Dry run   : {args.dry_run}")
    print(f"  Progress  : {progress_file}")
    print()

    # Step 1 — Validate clips exist
    if not args.dry_run:
        step_validate_clips(args.clips_dir)

    # Step 2 — Upload clips
    asset_map = step_upload_clips(args.clips_dir, progress, progress_file, args.dry_run)

    # Step 3 — Build payload
    payload = step_build_payload(asset_map, avatar_id or "DRY_RUN", voice_id or "DRY_RUN", args.callback_url)

    # Step 4 — Submit (or resume)
    video_id = progress.get("video_id")
    if video_id:
        print(f"\nResuming with existing video_id: {video_id}")
    else:
        video_id = step_submit(payload, args.dry_run)
        if video_id:
            progress["video_id"] = video_id
            save_progress(progress_file, progress)

    if args.dry_run or not video_id:
        print("\n[dry-run] Complete. No video submitted.")
        return

    # Step 5 — Poll for completion
    download_url = progress.get("video_url")
    if not download_url:
        download_url = step_poll(video_id, progress, progress_file)

    # Step 6 — Download
    step_download(download_url, args.output)

    # Also copy to desktop
    desktop = Path.home() / "Desktop" / args.output.name
    import shutil
    shutil.copy2(args.output, desktop)
    print(f"  Also copied to: {desktop}")

    print("\nDone! Your video is ready.")
    print(f"  Project file: {args.output}")
    print(f"  Desktop copy: {desktop}")
    print(f"\nNote: The HeyGen download URL expires in 7 days.")


if __name__ == "__main__":
    main()
