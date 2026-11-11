from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _int_set(raw: str) -> frozenset[int]:
    out = set()
    for part in raw.replace(";", ",").split(","):
        part = part.strip()
        if part.lstrip("-").isdigit():
            out.add(int(part))
    return frozenset(out)


@dataclass(frozen=True)
class Config:
    token: str
    admin_ids: frozenset[int] = frozenset()
    data_dir: Path = Path("data")
    port: int = 10000
    gemini_api_key: str = ""
    gemini_model: str = "gemini-flash-latest"
    libre_url: str = ""
    libre_api_key: str = ""
    mymemory_email: str = ""
    engine_order: tuple[str, ...] = ("gemini", "google", "libre", "mymemory")
    max_chars: int = 4000
    rate_limit_count: int = 6
    rate_limit_window: int = 20
    cache_size: int = 2000
    cache_ttl: int = 24 * 3600
    log_level: str = "INFO"
    api_base: str = ""   # optional: self-hosted Bot API server, e.g. http://localhost:8081

    @property
    def db_path(self) -> Path:
        return self.data_dir / "botam.db"

    @staticmethod
    def _load_dotenv(path: str = ".env") -> None:
        """Tiny .env loader for local development (never overrides real env vars)."""
        f = Path(path)
        if not f.is_file():
            return
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip("\"'"))

    @classmethod
    def from_env(cls) -> "Config":
        cls._load_dotenv()
        env = os.environ
        token = env.get("BOT_TOKEN", "").strip()
        if not token:
            raise SystemExit(
                "BOT_TOKEN is not set. Put it in the environment variables "
                "(Render → Environment) or in a local .env file."
            )
        order = tuple(
            x.strip().lower()
            for x in env.get("ENGINE_ORDER", "gemini,google,libre,mymemory").split(",")
            if x.strip()
        )
        return cls(
            token=token,
            admin_ids=_int_set(env.get("ADMIN_ID", "")),
            data_dir=Path(env.get("DATA_DIR", "data")),
            port=int(env.get("PORT", "10000") or 10000),
            gemini_api_key=env.get("GEMINI_API_KEY", "").strip(),
            gemini_model=env.get("GEMINI_MODEL", "gemini-flash-latest").strip(),
            libre_url=env.get("LIBRETRANSLATE_URL", "").strip().rstrip("/"),
            libre_api_key=env.get("LIBRETRANSLATE_API_KEY", "").strip(),
            mymemory_email=env.get("MYMEMORY_EMAIL", "").strip(),
            engine_order=order,
            max_chars=int(env.get("MAX_CHARS", "4000")),
            rate_limit_count=int(env.get("RATE_LIMIT_COUNT", "6")),
            rate_limit_window=int(env.get("RATE_LIMIT_WINDOW", "20")),
            log_level=env.get("LOG_LEVEL", "INFO").upper(),
            api_base=env.get("TELEGRAM_API_BASE", "").strip().rstrip("/"),
        )
