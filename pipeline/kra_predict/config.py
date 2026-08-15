"""경로 상수·환경 변수·트랙 매핑."""

import os
from pathlib import Path
from urllib.parse import unquote

from dotenv import load_dotenv

PIPELINE_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = PIPELINE_DIR.parent
DATA_DIR = REPO_ROOT / "data"
CACHE_DIR = PIPELINE_DIR / ".cache"
FIXTURES_DIR = PIPELINE_DIR / "fixtures"
SCHEMAS_DIR = PIPELINE_DIR / "schemas"

load_dotenv(PIPELINE_DIR / ".env")


def service_key() -> str:
    key = os.environ.get("KRA_SERVICE_KEY", "")
    if not key:
        raise RuntimeError(
            "KRA_SERVICE_KEY가 설정되지 않았습니다. "
            "pipeline/.env.example을 .env로 복사해 인증키를 넣으세요."
        )
    # data.go.kr 'Encoding' 키(%2B…)를 넣어도 동작하도록 디코딩.
    # httpx가 전송 시 다시 인코딩하므로 원본(Decoding) 키가 필요하다.
    while "%" in key:
        decoded = unquote(key)
        if decoded == key:
            break
        key = decoded
    return key


# KRA API의 시행경마장 코드: 1=서울, 2=제주, 3=부산경남 (4=영천, 미사용)
TRACKS: dict[str, dict] = {
    "seoul": {"meet": 1, "name": "서울"},
    "busan": {"meet": 3, "name": "부산경남"},
    "jeju": {"meet": 2, "name": "제주"},
}
MEET_TO_SLUG = {v["meet"]: slug for slug, v in TRACKS.items()}


def to_api_date(date: str) -> str:
    """"2026-08-15" → "20260815" (KRA API 날짜 형식)."""
    return date.replace("-", "")
