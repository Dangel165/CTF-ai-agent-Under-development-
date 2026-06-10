from __future__ import annotations

import asyncio
import logging
import sys

import discord
from discord import app_commands

from bot.config import load_settings
from bot.jobs import JobStore
from bot.modals import SolveModal
from bot.worker import SolveWorker

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("ctf-discord-bot")


class CTFBot(discord.Client):
    def __init__(self, settings, jobs: JobStore):
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.settings = settings
        self.jobs = jobs
        self.tree = app_commands.CommandTree(self)
        self.worker = SolveWorker(settings, jobs, self)
        self._ctfd = None

    async def setup_hook(self) -> None:
        self.worker.start(self.settings.max_concurrent_jobs)
        if self.settings.discord_guild_id:
            guild = discord.Object(id=self.settings.discord_guild_id)
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
            logger.info("Synced %d commands to guild %s", len(synced), guild.id)
        else:
            synced = await self.tree.sync()
            logger.info("Synced %d global commands", len(synced))

    def allowed(self, user_id: int) -> bool:
        allowed = self.settings.allowed_user_ids
        return not allowed or user_id in allowed


async def _require_access(bot: CTFBot, interaction: discord.Interaction) -> bool:
    if bot.allowed(interaction.user.id):
        return True
    await interaction.response.send_message("이 봇을 사용할 권한이 없습니다.", ephemeral=True)
    return False


def _register_universal_commands(bot: CTFBot) -> None:
    @bot.tree.command(name="풀이", description="어떤 CTF든 — 문제 이름·분야·플래그형식·내용 입력 후 AI 풀이")
    async def solve_modal(interaction: discord.Interaction):
        if not await _require_access(bot, interaction):
            return
        await interaction.response.send_modal(
            SolveModal(bot.settings, bot.jobs, bot.worker)
        )

    @bot.tree.command(name="solve", description="Same as /풀이 — open challenge input form")
    async def solve_en(interaction: discord.Interaction):
        if not await _require_access(bot, interaction):
            return
        await interaction.response.send_modal(
            SolveModal(bot.settings, bot.jobs, bot.worker)
        )

    @bot.tree.command(name="상태", description="풀이 작업 상태 확인")
    @app_commands.describe(job_id="Job ID (비우면 최근 목록)")
    async def status_ko(interaction: discord.Interaction, job_id: str | None = None):
        await _status(bot, interaction, job_id)

    @bot.tree.command(name="status", description="Check solve job status")
    @app_commands.describe(job_id="Job ID (recent list if empty)")
    async def status_en(interaction: discord.Interaction, job_id: str | None = None):
        await _status(bot, interaction, job_id)

    @bot.tree.command(name="목록", description="최근 풀이 작업 목록")
    async def list_ko(interaction: discord.Interaction):
        await _list_jobs(bot, interaction)

    @bot.tree.command(name="help", description="사용법 안내")
    async def help_cmd(interaction: discord.Interaction):
        if not await _require_access(bot, interaction):
            return
        text = (
            "**범용 CTF AI 봇** — CTFd/HackTheBox/picoCTF 등 플랫폼 무관\n\n"
            "`/풀이` — 문제 입력 폼 (이름, 분야, 플래그 형식, 내용)\n"
            "`/상태 [job_id]` — 진행/결과 확인\n"
            "`/목록` — 최근 작업\n\n"
            "**분야:** web, pwn, crypto, rev, forensics, stego, osint, misc, mobile\n"
            "**플래그 형식 예:** `flag{...}`, `HTB{...}`\n"
        )
        if bot.settings.ctfd_enabled:
            text += "\n*CTFd 연동:* `/ctfd 목록`, `/ctfd 풀이 <id>`"
        await interaction.response.send_message(text, ephemeral=True)


async def _status(bot: CTFBot, interaction: discord.Interaction, job_id: str | None) -> None:
    if not await _require_access(bot, interaction):
        return
    await interaction.response.defer(ephemeral=True)
    if job_id:
        job = await bot.jobs.get(job_id)
        if not job:
            await interaction.followup.send(f"Job `{job_id}` 없음")
            return
        result = job.get("result") or {}
        spec = job.get("spec") or {}
        text = (
            f"**Job `{job['id']}`** — `{job['status']}`\n"
            f"문제: **{job.get('challenge_name')}**\n"
            f"분야: `{spec.get('category', '?')}` · 플래그형식: `{spec.get('flag_format', '?')}`\n"
        )
        if job.get("challenge_dir"):
            text += f"폴더: `{job['challenge_dir']}`\n"
        if result.get("flag"):
            text += f"**Flag:** `{result['flag']}`\n"
        if result.get("error"):
            text += f"오류: {result['error'][:500]}\n"
        await interaction.followup.send(text[:1900])
        return

    recent = await bot.jobs.list_recent(8)
    if not recent:
        await interaction.followup.send("아직 작업 없음. `/풀이` 로 시작하세요.")
        return
    lines = ["**최근 작업**"]
    for job in recent:
        flag = (job.get("result") or {}).get("flag")
        extra = f" → `{flag}`" if flag else ""
        lines.append(f"- `{job['id']}` **{job.get('challenge_name')}** — `{job['status']}`{extra}")
    await interaction.followup.send("\n".join(lines)[:1900])


async def _list_jobs(bot: CTFBot, interaction: discord.Interaction) -> None:
    if not await _require_access(bot, interaction):
        return
    await interaction.response.defer(ephemeral=True)
    await _status(bot, interaction, None)


def _register_ctfd_commands(bot: CTFBot) -> None:
    from bot.challenge_pull import pull_challenge_by_id
    from bot.ctfd_client import CTFdClient
    from ctf_agent.challenge import ChallengeSpec

    ctfd = CTFdClient(bot.settings.ctfd_url, bot.settings.ctfd_token)
    bot._ctfd = ctfd

    group = app_commands.Group(name="ctfd", description="CTFd 연동 (선택 — CTFD_URL/TOKEN 설정 시)")

    @group.command(name="목록", description="CTFd 미해결 챌린지 목록")
    async def ctfd_list(interaction: discord.Interaction):
        if not await _require_access(bot, interaction):
            return
        await interaction.response.defer(thinking=True)
        try:
            challenges = await ctfd.list_challenges(include_solved=False)
            if not challenges:
                await interaction.followup.send("챌린지 없음")
                return
            lines = [
                f"`{c.id}` **{c.name}** — {c.category} ({c.value}pt)"
                for c in challenges[:25]
            ]
            await interaction.followup.send("\n".join(lines))
        except Exception as exc:
            await interaction.followup.send(f"CTFd 오류: {exc}")

    @group.command(name="풀이", description="CTFd 챌린지 ID로 풀이 큐 등록")
    @app_commands.describe(challenge_id="CTFd 챌린지 ID")
    async def ctfd_solve(interaction: discord.Interaction, challenge_id: int):
        if not await _require_access(bot, interaction):
            return
        await interaction.response.defer(ephemeral=True)
        try:
            await ctfd.get_challenge(challenge_id)
            ch_dir = await pull_challenge_by_id(
                base_url=bot.settings.ctfd_url,
                token=bot.settings.ctfd_token,
                challenge_id=challenge_id,
                output_dir=bot.settings.workspaces_dir,
            )
            spec = ChallengeSpec.load_yaml(ch_dir / "challenge.yaml").to_dict()
            if spec.get("flag_format") in ("", "flag{...}"):
                spec["flag_format"] = "flag{...}"
            job_id = await bot.jobs.create_solve_job(
                challenge_name=spec["name"],
                spec=spec,
                requested_by=str(interaction.user.id),
                channel_id=interaction.channel_id,  # type: ignore[arg-type]
                challenge_id=challenge_id,
            )
            await bot.worker.enqueue(
                {
                    "id": job_id,
                    "spec": spec,
                    "channel_id": interaction.channel_id,
                    "workspace_dir": str(ch_dir),
                }
            )
            await interaction.followup.send(
                f"CTFd `{challenge_id}` → Job `{job_id}` (**{spec['name']}**)"
            )
        except Exception as exc:
            await interaction.followup.send(f"실패: {exc}")

    bot.tree.add_command(group)


def build_bot() -> CTFBot:
    settings = load_settings()
    jobs = JobStore(str(settings.data_dir / "jobs.db"))
    bot = CTFBot(settings, jobs)
    _register_universal_commands(bot)
    if settings.ctfd_enabled:
        _register_ctfd_commands(bot)
    return bot


async def _async_main() -> None:
    settings = load_settings()
    jobs = JobStore(str(settings.data_dir / "jobs.db"))
    await jobs.init()
    bot = build_bot()
    try:
        await bot.start(settings.discord_token)
    finally:
        if bot._ctfd:
            await bot._ctfd.close()


def main() -> None:
    try:
        asyncio.run(_async_main())
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
