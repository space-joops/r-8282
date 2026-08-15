"""운영 텔레메트리 — 실행 요약을 Supabase ops_runs에 기록한다.

계약: 절대 파이프라인을 방해하지 않는다.
- env(SUPABASE_URL·SUPABASE_SERVICE_KEY) 없으면 조용히 스킵
- 네트워크/서버 오류는 경고 로그 후 무시
- track()은 감싼 코드의 예외를 그대로 전파한다 (status=error로 기록만 남김)
"""

from __future__ import annotations

import logging
import os
import platform
import time
from contextlib import contextmanager
from dataclasses import dataclass, field

import httpx

from kra_predict import config  # noqa: F401 — .env 로드 부수효과
from kra_predict.emit import now_kst_iso

logger = logging.getLogger(__name__)

TIMEOUT_SEC = 10.0


def _supabase_env() -> tuple[str, str] | None:
    url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get(
        "SUPABASE_SERVICE_ROLE_KEY", ""
    )
    if not url or not key:
        return None
    return url, key


def record_run(payload: dict) -> bool:
    """ops_runs에 1행 기록. 성공 시 True — 어떤 경우에도 예외를 던지지 않는다."""
    env = _supabase_env()
    if env is None:
        logger.debug("Supabase env 없음 — 텔레메트리 스킵")
        return False
    url, key = env
    try:
        resp = httpx.post(
            f"{url}/rest/v1/ops_runs",
            json=payload,
            headers={
                "apikey": key,
                "Authorization": f"Bearer {key}",
                "Prefer": "return=minimal",
            },
            timeout=TIMEOUT_SEC,
        )
        if resp.status_code >= 300:
            logger.warning(
                "텔레메트리 기록 실패(무시): HTTP %s %s",
                resp.status_code,
                resp.text[:200],
            )
            return False
        return True
    except Exception as e:  # noqa: BLE001 — fail-soft 계약
        logger.warning("텔레메트리 기록 실패(무시): %s", e)
        return False


@dataclass
class Run:
    status: str = "success"
    metrics: dict = field(default_factory=dict)
    error: str | None = None


@contextmanager
def track(kind: str, target_date: str, *, enabled: bool = True):
    """predict/results 실행을 감싸 시작/종료·상태를 기록한다.

    사용처에서 run.status("success"|"no_change"|"no_races")와 run.metrics를
    채운다. 예외 발생 시 status="error"로 기록하고 예외를 재전파한다.
    """
    run = Run()
    started_at = now_kst_iso()
    t0 = time.monotonic()
    try:
        yield run
    except BaseException as e:
        # typer.Exit 등 의도된 종료는 사용처가 status를 미리 설정한다
        if run.status == "success":
            run.status = "error"
            run.error = repr(e)[:500]
        raise
    finally:
        if enabled:
            record_run(
                {
                    "kind": kind,
                    "target_date": target_date,
                    "status": run.status,
                    "source": os.environ.get("OPS_RUN_SOURCE", "manual"),
                    "host": platform.node(),
                    "started_at": started_at,
                    "finished_at": now_kst_iso(),
                    "duration_sec": round(time.monotonic() - t0, 1),
                    "metrics": run.metrics,
                    "error": run.error,
                }
            )
