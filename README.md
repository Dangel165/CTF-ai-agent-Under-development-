# CTF AI Agent 

**어떤 CTF 플랫폼이든** 쓸 수 있는 AI 풀이 도구 모음입니다.

## 폴더 구조

```
F:\ofntkd\ctf-ai-agent\
├── universal\          ← CLI · 웹 폼 · Cursor Skill
├── discord-bot\        ← Discord /풀이 (같은 AI, 같은 workspaces)
└── README.md
```

| 도구 | 용도 |
|------|------|
| **universal** | `ctf-agent web` 웹 폼, `ctf-agent solve -i` CLI |
| **discord-bot** | Discord `/풀이` 폼 → 팀 채널에 결과 |
| `ctf_auto_solver_bot` | (기존) 로컬 패턴 분석, LLM 없음 |

## 공통 입력 (4가지 + 선택)

1. **문제 이름**
2. **분야** — web, pwn, crypto, rev, forensics, stego, osint, misc, mobile
3. **플래그 형식** — `flag{...}`, `HTB{...}` 등
4. **문제 내용** — 지문 전체  
5. (선택) 연결 정보, 플랫폼 이름

## 빠른 시작

### 웹 (한국어)

```powershell
cd F:\ofntkd\ctf-ai-agent\universal
uv sync
copy .env.example .env
uv run ctf-agent web
```

### Discord (어떤 CTF든)

```powershell
cd F:\ofntkd\ctf-ai-agent\discord-bot
uv sync
copy .env.example .env
# DISCORD_TOKEN + CURSOR_API_KEY
uv run ctf-discord-bot
```

Discord에서 `/풀이` → 폼 작성

### Cursor 채팅

복붙: `universal\templates\CURSOR-CHAT-KO.md`  
Skill: `F:\ofntkd\.cursor\skills\ctf-solve`

## 자세한 사용법

- CLI·웹·YAML: [`universal/README.md`](universal/README.md)
- Discord 명령: [`discord-bot/README.md`](discord-bot/README.md)

## CTFd (선택)

Discord 봇 `.env`에 `CTFD_URL` + `CTFD_TOKEN` 넣으면 `/ctfd` 명령이 추가됩니다.  
**없어도** `/풀이`로 모든 CTF 풀이 가능합니다.
