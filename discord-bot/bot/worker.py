from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING

import discord

from ctf_agent.challenge import ChallengeSpec
from ctf_agent.solver import solve_workspace_async
from ctf_agent.workspace import create_workspace

from bot.jobs import JobStore

if TYPE_CHECKING:
    from bot.config import Settings

logger = logging.getLogger(__name__)


class SolveWorker:
    def __init__(self, settings: Settings, jobs: JobStore, bot: discord.Client):
        self.settings = settings
        self.jobs = jobs
        self.bot = bot
        self.queue: asyncio.Queue[dict] = asyncio.Queue()
        self._workers: list[asyncio.Task] = []

    def start(self, worker_count: int) -> None:
        for _ in range(worker_count):
            self._workers.append(asyncio.create_task(self._loop()))

    async def enqueue(self, job: dict) -> None:
        await self.queue.put(job)

    async def _loop(self) -> None:
        while True:
            job = await self.queue.get()
            job_id = job["id"]
            channel_id = int(job["channel_id"])
            spec_data = job["spec"]
            preset_ws = job.get("workspace_dir")

            channel = self.bot.get_channel(channel_id)
            try:
                await self.jobs.mark(job_id, status="running")
                if isinstance(channel, discord.abc.Messageable):
                    await channel.send(
                        f"Job `{job_id}` 시작 — **{spec_data['name']}** ({spec_data['category']})"
                    )

                if preset_ws:
                    ws = Path(preset_ws)
                    spec = ChallengeSpec.load_yaml(ws / "challenge.yaml")
                else:
                    spec = ChallengeSpec.from_dict(spec_data)
                    ws = create_workspace(spec, root=self.settings.workspaces_dir)
                await self.jobs.mark(job_id, status="running", challenge_dir=str(ws))

                result = await solve_workspace_async(
                    ws,
                    spec,
                    model=self.settings.cursor_model,
                    api_key=self.settings.cursor_api_key,
                )

                payload = {
                    "ok": result.ok,
                    "flag": result.flag,
                    "error": result.error,
                    "summary": (result.raw_text or "")[-1500:],
                }
                status = "done" if result.ok else "failed"
                await self.jobs.mark(job_id, status=status, result=payload)

                msg = (
                    f"**{spec.name}** — {'✅ 완료' if result.ok else '❌ 실패'}\n"
                    f"Job: `{job_id}`\n"
                    f"워크스페이스: `{ws}`"
                )
                if result.flag:
                    msg += f"\n**Flag:** `{result.flag}`"
                if result.error:
                    msg += f"\n오류: {result.error[:400]}"
                if isinstance(channel, discord.abc.Messageable):
                    await channel.send(msg[:1900])

            except Exception as exc:
                logger.exception("Job %s failed", job_id)
                await self.jobs.mark(job_id, status="failed", result={"error": str(exc)})
                if isinstance(channel, discord.abc.Messageable):
                    await channel.send(f"Job `{job_id}` 오류: {exc}")
            finally:
                self.queue.task_done()
