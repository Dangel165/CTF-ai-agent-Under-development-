from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import yaml


class Category(str, Enum):
    WEB = "web"
    PWN = "pwn"
    CRYPTO = "crypto"
    REV = "rev"
    FORENSICS = "forensics"
    STEGO = "stego"
    OSINT = "osint"
    MISC = "misc"
    MOBILE = "mobile"

    @classmethod
    def choices(cls) -> list[str]:
        return [c.value for c in cls]

    @classmethod
    def normalize(cls, raw: str) -> Category:
        key = raw.strip().lower().replace(" ", "_").replace("-", "_")
        aliases = {
            "reverse": cls.REV,
            "reversing": cls.REV,
            "reverse_engineering": cls.REV,
            "binary": cls.PWN,
            "binary_exploitation": cls.PWN,
            "cryptography": cls.CRYPTO,
            "forensic": cls.FORENSICS,
            "dfir": cls.FORENSICS,
            "steganography": cls.STEGO,
            "miscellaneous": cls.MISC,
        }
        if key in aliases:
            return aliases[key]
        try:
            return cls(key)
        except ValueError as exc:
            valid = ", ".join(cls.choices())
            raise ValueError(f"알 수 없는 분야 '{raw}'. 다음 중 하나를 사용하세요: {valid}") from exc


@dataclass
class ChallengeSpec:
    """Platform-agnostic challenge definition."""

    name: str
    category: Category
    flag_format: str
    description: str
    connection_info: str = ""
    hints: list[str] = field(default_factory=list)
    platform: str = ""
    notes: str = ""

    def __post_init__(self) -> None:
        self.name = self.name.strip()
        if not self.name:
            raise ValueError("문제 이름을 입력하세요.")
        if isinstance(self.category, str):
            self.category = Category.normalize(self.category)
        if not self.description.strip():
            raise ValueError("문제 내용을 입력하세요.")
        self.flag_format = self.flag_format.strip()
        if not self.flag_format:
            raise ValueError("플래그 형식을 입력하세요. (예: flag{...} 또는 regex:...)")

    def flag_regex(self) -> re.Pattern[str]:
        """Turn user flag format into a regex pattern."""
        fmt = self.flag_format
        if fmt.startswith("regex:"):
            return re.compile(fmt[6:], re.IGNORECASE)
        if "{" in fmt and "}" in fmt:
            # flag{...} style — escape braces, allow inner content
            prefix, _, rest = fmt.partition("{")
            suffix = "}" if rest.endswith("}") else ""
            inner = rest[:-1] if suffix else rest
            if inner in ("...", "*", ".*"):
                inner = r"[^\s}]+"
            elif inner == "":
                inner = r"[^\s}]+"
            escaped_prefix = re.escape(prefix)
            escaped_suffix = re.escape(suffix) if suffix else r"\}"
            return re.compile(rf"{escaped_prefix}{inner}{escaped_suffix}", re.IGNORECASE)
        return re.compile(re.escape(fmt), re.IGNORECASE)

    def extract_flag(self, text: str) -> str | None:
        m = self.flag_regex().search(text or "")
        return m.group(0) if m else None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category.value,
            "flag_format": self.flag_format,
            "description": self.description,
            "connection_info": self.connection_info,
            "hints": self.hints,
            "platform": self.platform,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ChallengeSpec:
        return cls(
            name=str(data["name"]),
            category=data["category"],
            flag_format=str(data["flag_format"]),
            description=str(data.get("description", "")),
            connection_info=str(data.get("connection_info") or ""),
            hints=list(data.get("hints") or []),
            platform=str(data.get("platform") or ""),
            notes=str(data.get("notes") or ""),
        )

    @classmethod
    def load_yaml(cls, path: Path) -> ChallengeSpec:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError(f"올바르지 않은 challenge 파일입니다: {path}")
        return cls.from_dict(data)

    def save_yaml(self, path: Path) -> None:
        path.write_text(
            yaml.dump(self.to_dict(), allow_unicode=True, sort_keys=False, default_flow_style=False),
            encoding="utf-8",
        )
