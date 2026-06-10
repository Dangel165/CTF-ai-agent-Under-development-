from __future__ import annotations

from ctf_agent.challenge import Category, ChallengeSpec

CATEGORY_PLAYBOOK: dict[Category, str] = {
    Category.WEB: """
- Map endpoints, parameters, cookies, headers.
- Check source/comments, robots.txt, backup files.
- Try: SQLi, SSTI, LFI/RFI, SSRF, auth bypass, JWT, deserialization.
- Use curl/scripts before heavy brute force.
""",
    Category.PWN: """
- Run: file, checksec, strings on binaries in files/.
- Identify: overflow, format string, heap, sandbox, seccomp.
- Leak → overwrite → get shell/flag locally first.
""",
    Category.CRYPTO: """
- Identify cipher/hash/encoding chain.
- Small brute, known attacks (RSA, AES modes, XOR, LCG).
- Use z3/sage for constraints when needed.
""",
    Category.REV: """
- strings, file, binwalk; decompile (ghidra/r2).
- Trace flag check logic; patch or reverse computation.
""",
    Category.FORENSICS: """
- Identify artifact type (pcap, disk, memory, logs).
- Carve/extract; timeline and metadata analysis.
""",
    Category.STEGO: """
- exiftool, binwalk, zsteg, steghide, spectrograms.
- Look for hidden data in images/audio/text.
""",
    Category.OSINT: """
- Gather public info; cross-reference usernames, domains, geo.
- Document sources for each finding.
""",
    Category.MISC: """
- Encoding chains, esoteric languages, QR/barcode, jail escapes.
- Read challenge text carefully for non-standard flag location.
""",
    Category.MOBILE: """
- APK/IPA static analysis; strings, manifest, decompile.
- Frida/dynamic if remote service involved.
""",
}


def build_solver_prompt(spec: ChallengeSpec, workspace_hint: str) -> str:
    playbook = CATEGORY_PLAYBOOK.get(spec.category, CATEGORY_PLAYBOOK[Category.MISC])
    hints = ""
    if spec.hints:
        hints = "Hints from user:\n" + "\n".join(f"- {h}" for h in spec.hints) + "\n\n"

    conn = ""
    if spec.connection_info.strip():
        conn = f"Connection info:\n{spec.connection_info.strip()}\n\n"

    platform_line = f"Platform/context: {spec.platform}\n" if spec.platform else ""

    return f"""You are a universal CTF solving agent. Work ONLY inside the workspace directory.

Workspace: {workspace_hint}

Challenge name: {spec.name}
Category: {spec.category.value}
Expected flag format: {spec.flag_format}
{platform_line}
Problem description:
{spec.description.strip()}

{conn}{hints}Category playbook:
{playbook.strip()}

Rules:
1. Run recon before guessing.
2. Write short PoC scripts; read their output.
3. Do not brute-force remote services without bounds.
4. Do not fabricate flags — derive from evidence.
5. When verified, output exactly one line: FLAG: <the_flag>
"""
