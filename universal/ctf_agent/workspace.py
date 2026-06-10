from __future__ import annotations

import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

from ctf_agent.challenge import ChallengeSpec


def _slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r'[<>:"/\\|?*.\x00-\x1f]', "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug or "challenge"


def create_workspace(
    spec: ChallengeSpec,
    *,
    root: Path,
    files: list[Path] | None = None,
) -> Path:
    """Create an isolated workspace with challenge.yaml and optional files/."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    ws = root / f"{stamp}-{_slugify(spec.name)}"
    ws.mkdir(parents=True, exist_ok=False)

    spec.save_yaml(ws / "challenge.yaml")

    (ws / "files").mkdir(exist_ok=True)
    if files:
        for src in files:
            src = src.resolve()
            if src.is_dir():
                dest = ws / "files" / src.name
                shutil.copytree(src, dest, dirs_exist_ok=True)
            elif src.is_file():
                shutil.copy2(src, ws / "files" / src.name)

    prompt = build_prompt_markdown(spec, ws)
    (ws / "PROMPT.md").write_text(prompt, encoding="utf-8")

    return ws


def load_workspace(path: Path) -> tuple[Path, ChallengeSpec]:
    path = path.resolve()
    yaml_path = path / "challenge.yaml"
    if not yaml_path.exists():
        raise FileNotFoundError(f"No challenge.yaml in {path}")
    return path, ChallengeSpec.load_yaml(yaml_path)


def build_prompt_markdown(spec: ChallengeSpec, workspace: Path) -> str:
    hints_block = ""
    if spec.hints:
        lines = "\n".join(f"- {h}" for h in spec.hints)
        hints_block = f"\n## Hints\n{lines}\n"

    conn = spec.connection_info.strip()
    conn_block = f"\n## Connection\n```\n{conn}\n```\n" if conn else ""

    platform = spec.platform.strip()
    platform_block = f"\n**Platform:** {platform}\n" if platform else ""

    notes = spec.notes.strip()
    notes_block = f"\n## Notes\n{notes}\n" if notes else ""

    files_dir = workspace / "files"
    file_list = ""
    if files_dir.exists():
        names = sorted(p.name for p in files_dir.iterdir() if p.is_file() or p.is_dir())
        if names:
            file_list = "\n## Files\n" + "\n".join(f"- `files/{n}`" for n in names) + "\n"

    return f"""# CTF Challenge

**Name:** {spec.name}
**Category:** {spec.category.value}
**Expected flag format:** `{spec.flag_format}`
{platform_block}
## Description

{spec.description.strip()}
{conn_block}{hints_block}{notes_block}{file_list}
## Your goal

1. Classify techniques for **{spec.category.value}** challenges.
2. Inspect everything under this workspace (especially `files/`).
3. Build a minimal PoC, verify locally, then recover the flag.
4. The flag MUST match format `{spec.flag_format}`.
5. Do NOT submit flags to external platforms unless the user explicitly asks.
6. Final answer: state the exact flag string on its own line prefixed with `FLAG:`.
"""
