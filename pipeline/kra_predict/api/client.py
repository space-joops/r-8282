"""data.go.kr KRA API 공통 클라이언트.

- `_type=json` 요청 + XML 응답 폴백 (일부 자료실 API가 json을 무시함)
- totalCount 기반 페이징, 단건 dict → list 정규화
- resultCode "03"(NODATA)은 빈 목록으로 처리
- raw 응답 캐시(pipeline/.cache) — 같은 날 재실행 시 쿼터 소모 0
- offline 모드: pipeline/fixtures만 사용 (네트워크 불가 환경·테스트)
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

import httpx
import xmltodict
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from kra_predict import config
from kra_predict.api.endpoints import Endpoint

logger = logging.getLogger(__name__)

BASE_URL = "https://apis.data.go.kr/B551015"

NODATA_CODES = {"03", "NODATA_ERROR"}


class KraApiError(RuntimeError):
    """API가 정상 응답했지만 resultCode가 오류인 경우."""


class KraAuthError(KraApiError):
    """게이트웨이 오류 (미등록 키, 미승인 API, 쿼터 초과 등)."""


class RetryableHttpError(RuntimeError):
    """5xx 등 재시도 가능한 전송 오류."""


def parse_payload(text: str) -> dict:
    """JSON/XML 응답을 공통 형태로 파싱해 body dict를 돌려준다."""
    stripped = text.strip()
    if stripped.startswith("<"):
        data = xmltodict.parse(stripped)
    else:
        data = json.loads(stripped)

    if "OpenAPI_ServiceResponse" in data:
        header = data["OpenAPI_ServiceResponse"].get("cmmMsgHeader", {})
        raise KraAuthError(
            f"{header.get('errMsg')} (code={header.get('returnReasonCode')})"
        )

    resp = data.get("response", data)
    header = resp.get("header") or {}
    code = str(header.get("resultCode", "")).strip()
    if code in NODATA_CODES:
        return {"items": None, "totalCount": 0}
    if code != "00":
        raise KraApiError(f"resultCode={code} msg={header.get('resultMsg')}")
    body = resp.get("body") or {}
    # XML 파싱 시 body 안에 items가 없고 바로 item이 오는 변형도 방어
    if "items" not in body and "item" in body:
        body = {**body, "items": {"item": body["item"]}}
    return body


def normalize_items(body: dict) -> list[dict]:
    """body.items.item을 항상 list[dict]로 정규화 (단건은 dict로 옴)."""
    items = body.get("items")
    if not items:
        return []
    item = items.get("item") if isinstance(items, dict) else items
    if item is None:
        return []
    return item if isinstance(item, list) else [item]


def _params_key(params: dict) -> str:
    """정렬된 파라미터로 사람이 읽을 수 있는 캐시/픽스처 파일명을 만든다."""
    parts = [f"{k}={v}" for k, v in sorted(params.items()) if v not in (None, "")]
    name = "_".join(parts) or "noparams"
    return re.sub(r"[^\w=.\-가-힣]", "-", name) + ".json"


class KraClient:
    def __init__(
        self,
        service_key: str | None = None,
        *,
        cache_dir: Path = config.CACHE_DIR,
        fixtures_dir: Path = config.FIXTURES_DIR,
        offline: bool = False,
        refresh: bool = False,
        record_fixtures: bool = False,
        timeout: float = 20.0,
    ):
        if not offline and not service_key:
            raise ValueError("온라인 모드에는 service_key가 필요합니다")
        self._key = service_key
        self.cache_dir = cache_dir
        self.fixtures_dir = fixtures_dir
        self.offline = offline
        self.refresh = refresh
        self.record_fixtures = record_fixtures
        self._http = httpx.Client(base_url=BASE_URL, timeout=timeout)
        self.http_calls = 0

    def close(self) -> None:
        self._http.close()

    def get_items(
        self,
        endpoint: Endpoint,
        *,
        num_of_rows: int = 100,
        max_pages: int = 50,
        **params,
    ) -> list[dict]:
        """전 페이지를 순회해 정규화된 item 목록을 돌려준다."""
        collected: list[dict] = []
        for page in range(1, max_pages + 1):
            body = self._get_body(
                endpoint, {**params, "pageNo": page, "numOfRows": num_of_rows}
            )
            page_items = normalize_items(body)
            collected.extend(page_items)
            total = int(body.get("totalCount") or 0)
            if page * num_of_rows >= total or not page_items:
                break
        return collected

    def _get_body(self, endpoint: Endpoint, params: dict) -> dict:
        fname = _params_key(params)
        fixture = self.fixtures_dir / endpoint.name / fname
        cache = self.cache_dir / endpoint.name / fname

        if self.offline:
            if fixture.exists():
                return parse_payload(fixture.read_text("utf-8"))
            logger.warning("픽스처 없음 → 빈 응답 처리: %s/%s", endpoint.name, fname)
            return {"items": None, "totalCount": 0}

        if not self.refresh and cache.exists():
            return parse_payload(cache.read_text("utf-8"))
        if not self.refresh and fixture.exists():
            return parse_payload(fixture.read_text("utf-8"))

        text = self._request(endpoint, params)
        body = parse_payload(text)  # 캐시 저장 전에 파싱해 오류 응답은 캐시하지 않음
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(text, "utf-8")
        if self.record_fixtures:
            fixture.parent.mkdir(parents=True, exist_ok=True)
            fixture.write_text(text, "utf-8")
        return body

    @retry(
        retry=retry_if_exception_type((httpx.TransportError, RetryableHttpError)),
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, max=15),
        reraise=True,
    )
    def _request(self, endpoint: Endpoint, params: dict) -> str:
        query = {k: v for k, v in params.items() if v not in (None, "")}
        query[endpoint.key_param] = self._key
        query.setdefault("_type", "json")
        resp = self._http.get(f"/{endpoint.path}", params=query)
        self.http_calls += 1
        if resp.status_code >= 500:
            raise RetryableHttpError(f"HTTP {resp.status_code}")
        resp.raise_for_status()
        return resp.text
