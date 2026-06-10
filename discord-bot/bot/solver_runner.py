from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from bot.config import Settings


@dataclass
class SolveResult:
    ok: bool
    flag: str | None
    exit_code: int
    log_path: str
    summary: str


def _find_uv() -> str:
    uv = shutil.which("uv")
    if uv:
        return uv
    raise RuntimeError("uv is not installed. Install from https://docs.astral.sh/uv/")


def _ctf_solve_cmd(settings: Settings, challenge_dir: Path, *, no_submit: bool) -> list[str]:
    uv = _find_uv()
    cmd = [
        uv,
        "run",
        "ctf-solve",
        "--ctfd-url",
        settings.ctfd_url,
        "--ctfd-token",
        settings.ctfd_token,
        "--image",
        settings.sandbox_image,
        "--challenge",
        str(challenge_dir),
        "--max-challenges",
        str(settings.max_concurrent_jobs),
    ]
    if settings.coordinator:
        cmd.extend(["--coordinator", settings.coordinator])
    if settings.solver_verbose:
        cmd.append("-v")
    if no_submit:
        cmd.append("--no-submit")
    return cmd


async def run_single_challenge(
    settings: Settings,
    challenge_dir: Path,
    *,
    job_id: str,
    no_submit: bool = False,
) -> SolveResult:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    log_path = settings.data_dir / "logs" / f"{job_id}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    if not settings.ctf_agent_path.exists():
        raise RuntimeError(
            f"ctf-agent not found at {settings.ctf_agent_path}. Run scripts/setup.sh first."
        )

    cmd = _ctf_solve_cmd(settings, challenge_dir, no_submit=no_submit)
    env = os.environ.copy()
    env.setdefault("CTFD_URL", settings.ctfd_url)
    env.setdefault("CTFD_TOKEN", settings.ctfd_token)

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=str(settings.ctf_agent_path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        env=env,
    )
    assert proc.stdout is not None
    chunks: list[str] = []
    flag: str | None = None

    while True:
        line = await proc.stdout.readline()
        if not line:
            break
        text = line.decode("utf-8", errors="replace")
        chunks.append(text)
        if "FLAG FOUND:" in text:
            flag = text.split("FLAG FOUND:", 1)[-1].strip()

    exit_code = await proc.wait()
    log_path.write_text("".join(chunks), encoding="utf-8")

    ok = exit_code == 0 and flag is not None
    if ok:
        summary = f"Solved. Flag: {flag}"
    elif flag:
        summary = f"Flag candidate found but process exited {exit_code}: {flag}"
    else:
        tail = "".join(chunks[-30:]).strip()
        summary = f"No flag found (exit {exit_code}).\n{tail[-1500:]}"

    return SolveResult(
        ok=ok,
        flag=flag,
        exit_code=exit_code,
        log_path=str(log_path),
        summary=summary,
    )


async def send_coordinator_hint(settings: Settings, message: str) -> tuple[bool, str]:
    uv = _find_uv()
    cmd = [
        uv,
        "run",
        "ctf-msg",
        message,
        "--host",
        settings.coordinator_msg_host,
        "--port",
        str(settings.coordinator_msg_port),
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=str(settings.ctf_agent_path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    out, _ = await proc.communicate()
    text = out.decode("utf-8", errors="replace")
    return proc.returncode == 0, text.strip()


@dataclass
class CoordinatorProcess:
    popen: subprocess.Popen[str]
    log_path: Path

    def is_running(self) -> bool:
        return self.popen.poll() is None

    def stop(self) -> None:
        if self.is_running():
            self.popen.terminate()
            try:
                self.popen.wait(timeout=15)
            except subprocess.TimeoutExpired:
                self.popen.kill()


class CoordinatorManager:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._proc: CoordinatorProcess | None = None

    @property
    def running(self) -> bool:
        return self._proc is not None and self._proc.is_running()

    def start(self) -> CoordinatorProcess:
        if self.running:
            raise RuntimeError("Coordinator is already running")

        settings = self.settings
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        log_path = settings.data_dir / "logs" / "coordinator.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)

        uv = _find_uv()
        cmd = [
            uv,
            "run",
            "ctf-solve",
            "--ctfd-url",
            settings.ctfd_url,
            "--ctfd-token",
            settings.ctfd_token,
            "--image",
            settings.sandbox_image,
            "--challenges-dir",
            str(settings.challenges_dir),
            "--max-challenges",
            str(settings.max_challenges_coordinator),
            "--coordinator",
            settings.coordinator,
            "--msg-port",
            str(settings.coordinator_msg_port),
        ]
        if settings.solver_verbose:
            cmd.append("-v")

        env = os.environ.copy()
        log_file = log_path.open("w", encoding="utf-8")
        popen = subprocess.Popen(
            cmd,
            cwd=str(settings.ctf_agent_path),
            stdout=log_file,
            stderr=subprocess.STDOUT,
            env=env,
        )
        self._proc = CoordinatorProcess(popen=popen, log_path=log_path)
        meta = settings.data_dir / "coordinator.json"
        meta.write_text(
            json.dumps({"pid": popen.pid, "log_path": str(log_path)}),
            encoding="utf-8",
        )
        return self._proc

    def stop(self) -> bool:
        if not self._proc:
            return False
        self._proc.stop()
        self._proc = None
        return True

    def status_text(self) -> str:
        if not self.running or not self._proc:
            return "Coordinator: **stopped**"
        return (
            f"Coordinator: **running** (pid {self._proc.popen.pid})\n"
            f"Log: `{self._proc.log_path}`\n"
            f"Hint port: `{self.settings.coordinator_msg_host}:{self.settings.coordinator_msg_port}`"
        )
