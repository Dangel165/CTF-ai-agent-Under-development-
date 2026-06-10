# Cursor 채팅 복붙용 — CTF 문제 입력 템플릿

아래 블록 전체를 복사해서 Cursor 채팅에 붙여넣고, `[ ... ]` 부분만 채우세요.  
(Skill `ctf-solve` 가 있으면 자동으로 인식합니다.)

---

## 기본 템플릿 (추천)

```
CTF 문제 풀어줘. 아래 정보로 진행해.

문제 이름: [예: Easy SQL]
분야: [web / pwn / crypto / rev / forensics / stego / osint / misc / mobile]
플래그 형식: [예: flag{...} / HTB{...} / picoCTF{...}]
플랫폼: [선택 — HackTheBox, picoCTF, 학교CTF, 로컬 등]
연결 정보: [선택 — nc host 1337 / https://...]

문제 내용:
"""
[문제 지문 전체를 여기에 붙여넣기]
"""

첨부 파일: [있으면 경로 — 예: ctf-agent/workspaces/.../files/chall.zip]
추가 힌트: [선택]
```

---

## 짧은 버전 (빠를 때)

```
문제: [이름] | 분야: [web] | 플래그: [flag{...}]

"""
[문제 내용]
"""
```

---

## 워크스페이스 이미 만든 경우

```
workspaces/20250610-xxxx-문제이름/ 폴더에 challenge.yaml 넣어뒀어.
ctf-solve skill 따라서 files/ 확인하고 FLAG: 형식으로 플래그 찾아줘.
```

---

## 분야별 한 줄 힌트 (선택)

| 분야 | 채팅에 덧붙일 수 있는 말 |
|------|-------------------------|
| web | HTTP 파라미터, 소스, 쿠키, SQLi/XSS/SSTI 위주로 |
| pwn | checksec, leak, ROP 순서로 |
| crypto | cipher 종류 먼저 식별해줘 |
| rev | strings/ghidra로 flag 검증 로직 찾아줘 |
| forensics | 파일 타입 식별 후 carving |
| stego | exiftool, zsteg, 레이어 확인 |
| misc | 인코딩 체인 / esolang 의심 |

---

## 플래그 형식 예시

| 입력 | 의미 |
|------|------|
| `flag{...}` | `flag{` + 아무 문자 + `}` |
| `HTB{...}` | HackTheBox 형식 |
| `regex:CTF\{[a-z0-9_]+\}` | 정규식 직접 지정 |

---

## CLI로 YAML 만든 뒤 Cursor에 넘기기

```bash
ctf-agent web          # 브라우저 폼 → 워크스페이스 생성
# 또는
ctf-agent new -i
```

생성된 폴더를 Cursor에서 열고:

```
@PROMPT.md @challenge.yaml 이 문제 풀어줘
```
