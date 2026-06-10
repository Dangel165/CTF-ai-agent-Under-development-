from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from cursor_sdk import Agent, CursorAgentError, LocalAgentOptions

from ctf_agent.challenge import ChallengeSpec
from ctf_agent.prompts import build_solver_prompt


@dataclass
class SolveResult:
    ok: bool
    flag: str | None
    raw_text: str
    error: str | None = None


def _parse_flag_line(text: str, spec: ChallengeSpec) -> str | None:
    for line in (text or "").splitlines():
        line = line.strip()
        if line.upper().startswith("FLAG:"):
            candidate = line.split(":", 1)[1].strip()
            if candidate:
                return candidate
    return spec.extract_flag(text)


async def solve_workspace_async(
    workspace: Path,
    spec: ChallengeSpec,
    *,
    model: str | None = None,
    api_key: str | None = None,
    max_followups: int = 1,
) -> SolveResult:
    workspace = workspace.resolve()
    model = model or os.getenv("CURSOR_MODEL", "composer-2.5")
    api_key = api_key or os.environ.get("CURSOR_API_KEY", "")
    if not api_key:
        raise RuntimeError("CURSOR_API_KEY is required")

    prompt = build_solver_prompt(spec, str(workspace))

    try:
        with Agent.create(
            model=model,
            api_key=api_key,
            local=LocalAgentOptions(cwd=str(workspace), setting_sources=[]),
        ) as agent:
            run = agent.send(prompt)
            result = run.wait()
            if result.status == "error":
                return SolveResult(False, None, result.result or "", f"run failed: {result.id}")

            raw = result.result or ""
            flag = _parse_flag_line(raw, spec)

            followups = 0
            while not flag and followups < max_followups:
                followups += 1
                run2 = agent.send(
                    "Continue solving. When the flag is verified, reply with exactly one line: FLAG: <flag>"
                )
                result2 = run2.wait()
                if result2.status == "error":
                    break
                raw = (result2.result or "") + "\n" + raw
                flag = _parse_flag_line(raw, spec)

            return SolveResult(ok=bool(flag), flag=flag, raw_text=raw)
    except CursorAgentError as exc:
        return SolveResult(False, None, "", str(exc))


def solve_workspace(
    workspace: Path,
    spec: ChallengeSpec,
    **kwargs,
) -> SolveResult:
    import asyncio

    return asyncio.run(solve_workspace_async(workspace, spec, **kwargs))
