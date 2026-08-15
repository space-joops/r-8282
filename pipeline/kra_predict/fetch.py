"""개최일 단위 raw 데이터 수집 오케스트레이션.

수집 결과는 API 응답을 그대로 담은 "번들" dict — 피처 가공은 features.py(#3) 몫.
미승인 API(KraAuthError)는 경고 후 빈 목록으로 진행해, 승인 범위가 늘면
자동으로 데이터가 채워진다.
"""

from __future__ import annotations

import logging

from kra_predict.api import endpoints as ep
from kra_predict.api.client import KraAuthError, KraClient
from kra_predict.config import TRACKS, to_api_date

logger = logging.getLogger(__name__)


def _try_items(client: KraClient, endpoint: ep.Endpoint, **params) -> list[dict]:
    """미승인/권한 오류를 빈 목록으로 흡수한다 (경로·키 문제는 경고 로그)."""
    try:
        return client.get_items(endpoint, **params)
    except KraAuthError as e:
        level = logging.INFO if not endpoint.approved else logging.WARNING
        logger.log(level, "%s 호출 불가 (%s) → 빈 목록", endpoint.name, e)
        return []


def fetch_meet_bundle(client: KraClient, date: str) -> dict:
    """한 개최일의 예측·결과에 필요한 raw 데이터를 모두 수집한다."""
    api_date = to_api_date(date)
    bundle: dict = {
        "date": date,
        "plan": {},
        "entries": {},
        "weights": {"seoul": {}},
        "horse1y": {},
        "jockeyChanges": {},
        "results": {},
    }

    # 1) 경주 편성 (트랙별)
    for slug, track in TRACKS.items():
        bundle["plan"][slug] = _try_items(
            client, ep.RACE_PLAN, meet=track["meet"], rc_date=api_date
        )

    # 2) 출전마
    #    서울: 출전등록현황(API323, 승인) — 전 경주 일괄
    bundle["entries"]["seoul"] = _try_items(
        client, ep.SEOUL_ENTRY_REG, race_dt=api_date
    )
    #    부산경남: 출전마현황(API316, 신청 대기)
    bundle["entries"]["busan"] = _try_items(
        client, ep.BUSAN_ENTRY, race_dt=api_date
    )
    #    제주: 출전표정보(API78, 신청 대기)가 유일한 사전 출전마 소스
    bundle["entries"]["jeju"] = _try_items(
        client, ep.CHULMA_INFO, rccrs_cd=TRACKS["jeju"]["meet"], race_dt=api_date
    )

    # 3) 서울 마체중 (경주별 필수 파라미터)
    for race in bundle["plan"]["seoul"]:
        rc_no = int(race.get("rcNo") or 0)
        if rc_no:
            bundle["weights"]["seoul"][str(rc_no)] = _try_items(
                client, ep.SEOUL_HORSE_WEIGHT, race_dt=api_date, race_no=rc_no
            )

    # 4) 당일 기수 변경 (트랙별)
    for slug, track in TRACKS.items():
        bundle["jockeyChanges"][slug] = _try_items(
            client, ep.JOCKEY_CHANGE, meet=track["meet"], rc_date=api_date
        )

    # 5) 출전마별 1년간 전적 (마명 기준, 트랙별 중복 제거)
    for slug, track in TRACKS.items():
        names = _entry_horse_names(bundle["entries"].get(slug, []))
        records: dict[str, dict] = {}
        for name in names:
            rows = _try_items(
                client,
                ep.HORSE_1Y_RECORD,
                rccrs_cd=track["meet"],
                hr_name=name,
            )
            if rows:
                records[name] = rows[0]
        bundle["horse1y"][slug] = records

    # 6) 경주 결과 (경주 종료 후 실행 시 채워짐 — 결과종합 API)
    for slug, track in TRACKS.items():
        bundle["results"][slug] = _try_items(
            client, ep.RACE_RESULT_TOTAL, meet=track["meet"], rc_date=api_date
        )

    return bundle


def fetch_results_bundle(client: KraClient, date: str) -> dict:
    """결과 반영에 필요한 데이터만 수집한다 (결과종합 + 경주 메타용 계획표)."""
    api_date = to_api_date(date)
    return {
        "date": date,
        "plan": {
            slug: _try_items(
                client, ep.RACE_PLAN, meet=track["meet"], rc_date=api_date
            )
            for slug, track in TRACKS.items()
        },
        "results": {
            slug: _try_items(
                client, ep.RACE_RESULT_TOTAL, meet=track["meet"], rc_date=api_date
            )
            for slug, track in TRACKS.items()
        },
    }


def _entry_horse_names(rows: list[dict]) -> list[str]:
    names = []
    for row in rows:
        name = str(row.get("hrnm") or "").strip()
        if name and name not in names:
            names.append(name)
    return names


def summarize_bundle(bundle: dict) -> str:
    lines = [f"개최일 {bundle['date']}"]
    for slug in TRACKS:
        plan = len(bundle["plan"].get(slug, []))
        entries = len(bundle["entries"].get(slug, []))
        results = len(bundle["results"].get(slug, []))
        horse1y = len(bundle["horse1y"].get(slug, {}))
        lines.append(
            f"  {slug:5s} 경주 {plan:2d} · 출전마 {entries:3d} · "
            f"1년전적 {horse1y:3d} · 결과행 {results:3d}"
        )
    return "\n".join(lines)
