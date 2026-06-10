from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass
class ChallengeStub:
    id: int
    name: str
    category: str
    value: int
    solved_by_me: bool = False


class CTFdClient:
    USER_AGENT = "ctf-discord-bot/0.1"

    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=f"{self.base_url}/api/v1",
            headers={
                "Authorization": f"Token {token}",
                "Content-Type": "application/json",
                "User-Agent": self.USER_AGENT,
            },
            timeout=60.0,
            verify=False,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def _get(self, path: str) -> dict[str, Any]:
        resp = await self._client.get(path)
        resp.raise_for_status()
        body = resp.json()
        if not body.get("success", True):
            raise RuntimeError(f"CTFd API error on GET {path}")
        return body

    async def me(self) -> dict[str, Any]:
        return (await self._get("/users/me"))["data"]

    async def solved_challenge_ids(self) -> set[int]:
        me = await self.me()
        team_id = me.get("team_id")
        if team_id:
            solves = (await self._get(f"/teams/{team_id}/solves"))["data"]
        else:
            user_id = me["id"]
            solves = (await self._get(f"/users/{user_id}/solves"))["data"]

        ids: set[int] = set()
        for row in solves:
            ch = row.get("challenge") or {}
            cid = ch.get("id")
            if cid is not None:
                ids.add(int(cid))
        return ids

    async def list_challenges(self, include_solved: bool = False) -> list[ChallengeStub]:
        solved = await self.solved_challenge_ids()
        data = (await self._get("/challenges?per_page=500"))["data"]
        out: list[ChallengeStub] = []
        for row in data:
            if row.get("type") == "hidden":
                continue
            cid = int(row["id"])
            is_solved = cid in solved
            if is_solved and not include_solved:
                continue
            out.append(
                ChallengeStub(
                    id=cid,
                    name=row.get("name", "?"),
                    category=row.get("category", "?"),
                    value=int(row.get("value") or 0),
                    solved_by_me=is_solved,
                )
            )
        out.sort(key=lambda c: (c.value, c.id))
        return out

    async def get_challenge(self, challenge_id: int) -> dict[str, Any]:
        return (await self._get(f"/challenges/{challenge_id}"))["data"]

    async def submit_flag(self, challenge_id: int, submission: str) -> dict[str, Any]:
        resp = await self._client.post(
            "/challenges/attempt",
            json={"challenge_id": challenge_id, "submission": submission},
        )
        resp.raise_for_status()
        return resp.json()["data"]

    @staticmethod
    def slugify(name: str) -> str:
        slug = name.lower().strip()
        slug = re.sub(r'[<>:"/\\|?*.\x00-\x1f]', "", slug)
        slug = re.sub(r"[\s_]+", "-", slug)
        slug = re.sub(r"-+", "-", slug).strip("-")
        return slug or "challenge"
