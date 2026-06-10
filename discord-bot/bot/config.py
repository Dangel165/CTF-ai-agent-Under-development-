from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Sibling universal package: F:\ofntkd\ctf-ai-agent\universal
UNIVERSAL_ROOT = Path(__file__).resolve().parent.parent.parent / "universal"
if UNIVERSAL_ROOT.is_dir() and str(UNIVERSAL_ROOT) not in sys.path:
    sys.path.insert(0, str(UNIVERSAL_ROOT))


@dataclass(frozen=True)
class Settings:
    discord_token: str
    discord_guild_id: int | None
    allowed_user_ids: frozenset[int]

    universal_root: Path
    workspaces_dir: Path
    data_dir: Path

    cursor_api_key: str
    cursor_model: str
    max_concurrent_jobs: int

    ctfd_url: str
    ctfd_token: str

    @property
    def ctfd_enabled(self) -> bool:
        return bool(self.ctfd_url and self.ctfd_token)


def _parse_ids(raw: str) -> frozenset[int]:
    ids: set[int] = set()
    for part in (raw or "").split(","):
        part = part.strip()
        if part:
            ids.add(int(part))
    return frozenset(ids)


def load_settings() -> Settings:
    root = Path(__file__).resolve().parent.parent
    guild_raw = os.getenv("DISCORD_GUILD_ID", "").strip()
    guild_id = int(guild_raw) if guild_raw else None

    universal = Path(os.getenv("UNIVERSAL_ROOT", str(UNIVERSAL_ROOT)))
    if not universal.is_absolute():
        universal = (root / universal).resolve()

    workspaces = Path(os.getenv("WORKSPACES_DIR", str(universal / "workspaces")))
    if not workspaces.is_absolute():
        workspaces = (root / workspaces).resolve()
    workspaces.mkdir(parents=True, exist_ok=True)

    data_dir = root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    token = os.getenv("DISCORD_TOKEN", "").strip()
    if not token:
        raise RuntimeError("DISCORD_TOKEN 환경 변수가 필요합니다.")

    cursor_key = os.getenv("CURSOR_API_KEY", "").strip()
    if not cursor_key:
        raise RuntimeError("CURSOR_API_KEY 환경 변수가 필요합니다. (AI 솔버)")

    return Settings(
        discord_token=token,
        discord_guild_id=guild_id,
        allowed_user_ids=_parse_ids(os.getenv("ALLOWED_DISCORD_USER_IDS", "")),
        universal_root=universal,
        workspaces_dir=workspaces,
        data_dir=data_dir,
        cursor_api_key=cursor_key,
        cursor_model=os.getenv("CURSOR_MODEL", "composer-2.5"),
        max_concurrent_jobs=max(1, int(os.getenv("MAX_CONCURRENT_JOBS", "1"))),
        ctfd_url=os.getenv("CTFD_URL", "").strip().rstrip("/"),
        ctfd_token=os.getenv("CTFD_TOKEN", "").strip(),
    )
