---
name: ctf-solve
description: Solves CTF challenges on any platform when the user provides problem name, category, flag format, and description. Use for CTF, capture the flag, flag format, web/pwn/crypto/rev/forensics challenges, or when the user pastes a challenge statement.
---

# Universal CTF Solve

Platform-agnostic solver. **No CTFd/Discord required.** The user supplies all challenge metadata.

## Required inputs (ask if missing)

Collect these before solving:

| Field | Example |
|-------|---------|
| **name** | SQL injection 101 |
| **category** | web, pwn, crypto, rev, forensics, stego, osint, misc, mobile |
| **flag_format** | `flag{...}`, `HTB{...}`, `picoCTF{...}`, or `regex:CTF\{[^}]+\}` |
| **description** | Full problem text (statement, story, constraints) |

Optional: `connection_info` (nc/URL), `hints`, `platform` label, files in workspace.

## Workflow

1. **Write metadata** — Create or update `challenge.yaml` in a workspace under `ctf-agent/workspaces/`:

```yaml
name: "Challenge title"
category: web
flag_format: "flag{...}"
description: |
  Full problem content here.
connection_info: "nc host 1337"
platform: "local"
```

Or run CLI: `ctf-agent new -i` (interactive) or flags.

2. **Attach files** — Put binaries/zip/images in `workspaces/<id>/files/`.

3. **Recon** — Read `challenge.yaml`, `PROMPT.md`, and `files/`. Classify techniques for the category.

4. **Solve loop** — Minimal PoC → observe output → iterate. Do not guess flags.

5. **Output** — When verified, respond with exactly:
   ```
   FLAG: <exact_flag_string>
   ```
   Flag must match user's `flag_format`.

## Category quick map

- **web** — HTTP, params, auth, SSTI/SQLi/LFI/SSRF
- **pwn** — checksec, leak, ROP, local then remote
- **crypto** — identify cipher, z3/sage, known attacks
- **rev** — decompile, trace check, patch/keygen
- **forensics** — carve, pcap, volatility, metadata
- **stego** — exiftool, zsteg, steghide, layers
- **osint** — public sources, cross-reference
- **misc** — encodings, esolang, constraints

## CLI (same project)

```bash
cd ctf-agent
uv sync
ctf-agent new -i              # interactive input
ctf-agent solve -i            # create + run Cursor SDK solver
ctf-agent show workspaces/... # verify metadata
```

## Rules

- Do not submit flags to external sites unless user asks.
- Respect rate limits on remote targets.
- If stuck, state blocker + next concrete step — do not hallucinate flags.
