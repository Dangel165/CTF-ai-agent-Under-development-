from __future__ import annotations

import discord

from bot.config import Settings
from bot.jobs import JobStore


class SolveModal(discord.ui.Modal, title="CTF 문제 입력 (어떤 플랫폼이든)"):
    name = discord.ui.TextInput(
        label="문제 이름",
        placeholder="예: Easy SQL",
        max_length=200,
        required=True,
    )
    category = discord.ui.TextInput(
        label="분야",
        placeholder="web / pwn / crypto / rev / forensics / stego / osint / misc / mobile",
        max_length=50,
        required=True,
    )
    flag_format = discord.ui.TextInput(
        label="플래그 형식",
        placeholder="flag{...}  또는  HTB{...}",
        default="flag{...}",
        max_length=120,
        required=True,
    )
    description = discord.ui.TextInput(
        label="문제 내용",
        style=discord.TextStyle.paragraph,
        placeholder="문제 지문 전체를 붙여넣으세요",
        max_length=4000,
        required=True,
    )
    extra = discord.ui.TextInput(
        label="플랫폼·연결정보 (선택)",
        style=discord.TextStyle.paragraph,
        placeholder="플랫폼: HackTheBox\n연결: nc host 1337",
        max_length=500,
        required=False,
    )

    def __init__(self, settings: Settings, jobs: JobStore, worker):
        super().__init__()
        self.settings = settings
        self.jobs = jobs
        self.worker = worker

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)

        platform = ""
        connection = ""
        if self.extra.value:
            for line in self.extra.value.splitlines():
                line = line.strip()
                if line.lower().startswith("플랫폼:") or line.lower().startswith("platform:"):
                    platform = line.split(":", 1)[-1].strip()
                elif line.lower().startswith("연결:") or line.lower().startswith("connection:"):
                    connection = line.split(":", 1)[-1].strip()
                elif not connection and ("nc " in line or line.startswith("http")):
                    connection = line
                elif not platform:
                    platform = line

        spec = {
            "name": self.name.value.strip(),
            "category": self.category.value.strip(),
            "flag_format": self.flag_format.value.strip(),
            "description": self.description.value,
            "connection_info": connection,
            "platform": platform,
            "hints": [],
            "notes": "",
        }

        job_id = await self.jobs.create_solve_job(
            challenge_name=spec["name"],
            spec=spec,
            requested_by=str(interaction.user.id),
            channel_id=interaction.channel_id,  # type: ignore[arg-type]
        )
        await self.worker.enqueue({"id": job_id, "spec": spec, "channel_id": interaction.channel_id})

        await interaction.followup.send(
            f"**{spec['name']}** ({spec['category']}) 풀이 큐 등록\n"
            f"Job: `{job_id}` · 플래그 형식: `{spec['flag_format']}`"
        )
