# Universal CTF AI Agent

> 위치: `F:\ofntkd\ctf-ai-agent\universal`  
> 전체 구조: [`../README.md`](../README.md)

**어떤 CTF 플랫폼이든** 사용 가능합니다 (CTFd, HackTheBox, picoCTF, 로컬 대회 등).  
플랫폼 API 없이 **직접 입력**하는 방식입니다.

## 입력 항목

| 항목 | 설명 | 예시 |
|------|------|------|
| **문제 이름** | `name` | `Easy SQL` |
| **분야** | `category` | `web`, `pwn`, `crypto`, `rev`, `forensics`, `stego`, `osint`, `misc`, `mobile` |
| **플래그 형식** | `flag_format` | `flag{...}`, `HTB{...}`, `regex:CTF\{[^}]+\}` |
| **문제 내용** | `description` | 문제 지문 전체 |
| (선택) 연결 정보 | `connection_info` | `nc 10.0.0.1 1337` |
| (선택) 플랫폼 이름 | `platform` | `HackTheBox`, `학교CTF` |

## 설치

```bash
cd ctf-agent
uv sync
cp .env.example .env   # CURSOR_API_KEY 설정
```

## 사용법

### 1) 대화형 입력 (가장 쉬움)

```bash
ctf-agent new -i
# → 문제 이름, 분야, 플래그 형식, 내용 순서로 입력

ctf-agent solve workspaces/20250610-xxxx-easy-sql
```

한 번에 생성+풀이:

```bash
ctf-agent solve -i
```

### 2) CLI 옵션으로 한 번에

```bash
ctf-agent new \
  --name "Buffer overflow 1" \
  --category pwn \
  --flag-format "flag{...}" \
  --description "Overwrite the return address..." \
  --connection "nc host 9999" \
  --file ./challenge.bin
```

### 3) YAML 파일로 작성

```bash
cp templates/challenge.example.yaml my-challenge.yaml
# 편집 후

ctf-agent new --from-yaml my-challenge.yaml --file ./attachments/
```

`challenge.yaml` 예:

```yaml
name: "XSS warm-up"
category: web
flag_format: "flag{...}"
description: |
  Find the flag in the admin cookie.
connection_info: "https://challenge.example.com"
platform: "any"
```

### 4) Cursor IDE에서

**복붙 템플릿:** [`templates/CURSOR-CHAT-KO.md`](templates/CURSOR-CHAT-KO.md)

**웹 폼:**

```bash
ctf-agent web
# → http://127.0.0.1:8765 브라우저에서 입력
# → 워크스페이스 생성 / YAML 다운로드 / Cursor 채팅 템플릿 복사
```

1. 이 폴더를 Cursor로 열기
2. Skill **`ctf-solve`** 사용 (`.cursor/skills/ctf-solve/`)
3. 웹 폼 또는 템플릿으로 입력 후 채팅에 붙여넣기

전역 Skill로 쓰려면:

```bash
cp -r .cursor/skills/ctf-solve ~/.cursor/skills/
```

## 워크스페이스 구조

```
workspaces/20250610-120000-easy-sql/
├── challenge.yaml    ← 메타데이터 (직접 수정 가능)
├── PROMPT.md         ← 에이전트용 요약
└── files/            ← 첨부 파일
```

메타데이터 수정:

```bash
ctf-agent edit workspaces/... --description "updated text"
ctf-agent show workspaces/...
```

## Cursor 채팅 복붙 (한국어)

`templates/CURSOR-CHAT-KO.md` 를 열거나, 아래를 그대로 복사:

```
CTF 문제 풀어줘. 아래 정보로 진행해.

문제 이름: [이름]
분야: [web / pwn / crypto / rev / forensics / stego / osint / misc / mobile]
플래그 형식: [flag{...}]
플랫폼: [선택]
연결 정보: [선택]

문제 내용:
"""
[지문 붙여넣기]
"""
```

## 웹 폼

```bash
ctf-agent web
```

| 기능 | 설명 |
|------|------|
| 문제 입력 | 이름, 분야, 플래그 형식, 내용 (한국어 UI) |
| 미리보기 | challenge.yaml / Cursor 채팅 텍스트 |
| 워크스페이스 생성 | `workspaces/` 에 자동 저장 + 파일 업로드 |
| 복사 / 다운로드 | YAML 또는 Cursor 템플릿 |


| 방식 | 용도 |
|------|------|
| **Cursor + ctf-solve skill** | IDE에서 대화하며 풀기 (추천) |
| **`ctf-agent solve`** | Cursor SDK로 자동 1회 실행 |

## 플래그 형식 문법

- `flag{...}` — `flag{` 로 시작, `}` 로 끝, 가운데 임의 문자
- `HTB{...}`, `picoCTF{...}` — 동일 패턴
- `regex:flag\{[a-z0-9_]+\}` — 직접 정규식 지정

## 참고

- 이전 `ctf-discord-bot/` 은 CTFd/Discord 전용이었습니다. **범용 풀이는 이 `ctf-agent/` 를 사용하세요.**
- 대회 규정상 자동 풀이가 금지된 경우 사용하지 마세요.
