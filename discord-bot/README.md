# CTF Discord Bot — 범용 (어떤 CTF든)

Discord에서 **문제 이름 · 분야 · 플래그 형식 · 문제 내용**을 입력하면 AI가 풉니다.  
CTFd/HackTheBox/picoCTF 등 **플랫폼 API 불필요**.

> 위치: `F:\ofntkd\ctf-ai-agent\discord-bot`  
> 솔버 엔진: [`../universal`](../universal) (Cursor SDK)

## Discord 명령

| 명령 | 설명 |
|------|------|
| `/풀이` 또는 `/solve` | 입력 폼 (이름, 분야, 플래그형식, 내용) |
| `/상태` / `/status` | Job 진행·플래그 결과 |
| `/목록` | 최근 작업 |
| `/help` | 사용법 |

**CTFd만 쓸 때 (선택):** `.env`에 `CTFD_URL`, `CTFD_TOKEN` 설정 → `/ctfd 목록`, `/ctfd 풀이 <id>`

## 설치

```powershell
cd F:\ofntkd\ctf-ai-agent\discord-bot
uv sync
copy .env.example .env
# DISCORD_TOKEN, CURSOR_API_KEY 필수
uv run ctf-discord-bot
```

## 입력 예 (폼)

- **문제 이름:** SQL Injection 101  
- **분야:** web  
- **플래그 형식:** flag{...}  
- **문제 내용:** (지문 전체)  
- **플랫폼·연결 (선택):**  
  ```
  플랫폼: HackTheBox
  연결: nc 10.10.10.1 1337
  ```

## CLI·웹과 같은 데이터

Discord로 만든 워크스페이스는 `../universal/workspaces/` 에 저장됩니다.  
웹 폼·CLI와 동일한 `challenge.yaml` 형식입니다.

자세한 사용법: [`../universal/README.md`](../universal/README.md)
