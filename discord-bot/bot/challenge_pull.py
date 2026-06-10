from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
import yaml
from markdownify import markdownify as html2md

from bot.ctfd_client import CTFdClient


def _html_to_markdown(html: str | None) -> str:
    if not html:
        return ""
    md = html2md(html, heading_style="atx", escape_asterisks=False, escape_underscores=False)
    md = re.sub(r"[^\S\r\n]*!\[[^\]]*\]\([^)]*\)\s*", "", md)
    md = re.sub(r"\n{3,}", "\n\n", md)
    return md.strip()


def _filename_from_url(url: str) -> str:
    path = urlparse(url).path
    name = path.rstrip("/").rsplit("/", 1)[-1]
    return name or "file"


def _make_absolute(url: str, base_url: str) -> str:
    if url.startswith("http"):
        return url
    return f"{base_url.rstrip('/')}/{url.lstrip('/')}"


def _build_metadata(challenge: dict[str, Any], hints: list[dict[str, Any]]) -> dict[str, Any]:
    tags = [t["value"] if isinstance(t, dict) else str(t) for t in (challenge.get("tags") or [])]
    meta: dict[str, Any] = {
        "version": "beta1",
        "name": challenge.get("name", "Unknown"),
        "category": challenge.get("category", ""),
        "description": _html_to_markdown(challenge.get("description") or ""),
        "value": challenge.get("value", 0),
        "ctfd_id": challenge.get("id"),
    }
    if challenge.get("solves") is not None:
        meta["solves"] = challenge["solves"]
    if tags:
        meta["tags"] = tags
    if challenge.get("connection_info"):
        meta["connection_info"] = challenge["connection_info"]
    if hints:
        meta["hints"] = []
        for hint in hints:
            entry: dict[str, Any] = {"cost": hint.get("cost", 0)}
            if hint.get("name"):
                entry["title"] = hint["name"]
            if hint.get("content"):
                entry["content"] = _html_to_markdown(hint["content"])
            meta["hints"].append(entry)
    return meta


async def _fetch_hints(
    client: httpx.AsyncClient,
    base_url: str,
    hints: list[dict[str, Any]],
    headers: dict[str, str],
) -> list[dict[str, Any]]:
    if not hints:
        return []

    result: list[dict[str, Any]] = []
    for i, hint in enumerate(hints, 1):
        hint_id = hint.get("id")
        cost = hint.get("cost", 1)
        content = hint.get("content")

        if cost <= 0 and content is None and hint_id is not None:
            await client.post(
                f"{base_url}/api/v1/unlocks",
                json={"target": hint_id, "type": "hints"},
                headers=headers,
            )
            resp = await client.get(f"{base_url}/api/v1/hints/{hint_id}", headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("success"):
                    hint = {**hint, **data["data"]}
                    content = hint.get("content")

        result.append(
            {
                "id": hint_id,
                "cost": cost,
                "content": content,
                "index": i,
                "name": hint.get("title") or hint.get("name"),
            }
        )
    return result


async def pull_challenge_by_id(
    *,
    base_url: str,
    token: str,
    challenge_id: int,
    output_dir: Path,
) -> Path:
    """Download one CTFd challenge into ctf-agent layout (metadata.yml + distfiles/)."""
    headers = {
        "Authorization": f"Token {token}",
        "Content-Type": "application/json",
        "User-Agent": CTFdClient.USER_AGENT,
    }
    base_url = base_url.rstrip("/")
    output_dir.mkdir(parents=True, exist_ok=True)

    async with httpx.AsyncClient(timeout=120.0, verify=False) as client:
        detail_resp = await client.get(
            f"{base_url}/api/v1/challenges/{challenge_id}",
            headers=headers,
        )
        detail_resp.raise_for_status()
        detail_body = detail_resp.json()
        if not detail_body.get("success"):
            raise RuntimeError(f"Challenge {challenge_id} not found or not accessible")
        challenge = detail_body["data"]

        slug = CTFdClient.slugify(challenge.get("name", f"challenge-{challenge_id}"))
        ch_dir = output_dir / slug
        ch_dir.mkdir(parents=True, exist_ok=True)
        distfiles_dir = ch_dir / "distfiles"

        for raw_url in challenge.get("files") or []:
            distfiles_dir.mkdir(exist_ok=True)
            url = _make_absolute(raw_url, base_url)
            fname = _filename_from_url(raw_url)
            dest = distfiles_dir / fname
            file_resp = await client.get(url, headers=headers, follow_redirects=True)
            file_resp.raise_for_status()
            dest.write_bytes(file_resp.content)

        raw_hints = challenge.get("hints") or []
        hints = await _fetch_hints(client, base_url, raw_hints, headers)
        meta = _build_metadata(challenge, hints)
        (ch_dir / "metadata.yml").write_text(
            yaml.dump(meta, allow_unicode=True, default_flow_style=False, sort_keys=False),
            encoding="utf-8",
        )

        return ch_dir


async def pull_all_challenges(
    *,
    base_url: str,
    token: str,
    output_dir: Path,
) -> list[Path]:
    headers = {
        "Authorization": f"Token {token}",
        "Content-Type": "application/json",
        "User-Agent": CTFdClient.USER_AGENT,
    }
    base_url = base_url.rstrip("/")
    pulled: list[Path] = []

    async with httpx.AsyncClient(timeout=120.0, verify=False) as client:
        list_resp = await client.get(f"{base_url}/api/v1/challenges", headers=headers)
        list_resp.raise_for_status()
        stubs = list_resp.json().get("data") or []

        for stub in stubs:
            if stub.get("type") == "hidden":
                continue
            path = await pull_challenge_by_id(
                base_url=base_url,
                token=token,
                challenge_id=int(stub["id"]),
                output_dir=output_dir,
            )
            pulled.append(path)

    return pulled
