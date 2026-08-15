"""개최일 단위 raw 데이터 수집 오케스트레이션.

수집 결과는 API 응답을 그대로 담은 "번들" dict — 피처 가공은 features.py(#3) 몫.
미승인 API(KraAuthError)는 경고 후 빈 목록으로 진행해, 승인 범위가 늘면
자동으로 데이터가 채워진다.
"""

from __future__ import annotations

import logging

from kra_predict.api import endpoints as ep
from kra_predict.api.client import KraApiError, KraAuthError, KraClient
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


def _try_items_soft(client: KraClient, endpoint: ep.Endpoint, **params) -> list[dict]:
    """보강용 데이터: 서버측 일시 오류(세션 고갈 등)까지 흡수한다."""
    try:
        return client.get_items(endpoint, **params)
    except (KraAuthError, KraApiError) as e:
        logger.warning("%s 호출 실패 (%s) → 보강 생략", endpoint.name, e)
        return []


def _stats_map(rows: list[dict], name_key: str, id_key: str) -> dict[str, dict]:
    """기수/조교사 성적 행 → {이름: {id, winRate1y}} (최근 1년 승률)."""
    stats: dict[str, dict] = {}
    for row in rows:
        name = str(row.get(name_key, "")).strip()
        starts = row.get("rcCntY")
        wins = row.get("ord1CntY")
        try:
            rate = round(int(wins) / int(starts), 3) if int(starts) else None
        except (TypeError, ValueError):
            rate = None
        if name:
            stats[name] = {"id": str(row.get(id_key, "")), "winRate1y": rate}
    return stats


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

    # 2) 출전마: 출전표정보(API78, 전 트랙·기수·부담중량 포함) 우선,
    #    비어 있으면 트랙별 레거시 소스로 폴백
    for slug, track in TRACKS.items():
        rows = _try_items(
            client, ep.CHULMA_INFO, rccrs_cd=track["meet"], race_dt=api_date
        )
        if not rows and slug == "seoul":
            rows = _try_items(client, ep.SEOUL_ENTRY_REG, race_dt=api_date)
        elif not rows and slug == "busan":
            rows = _try_items(client, ep.BUSAN_ENTRY, race_dt=api_date)
        bundle["entries"][slug] = rows

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

    # 6) 기수/조교사 최근 1년 성적 (트랙별 전체 목록 → 이름 매핑)
    bundle["jockeyStats"] = {}
    bundle["trainerStats"] = {}
    for slug, track in TRACKS.items():
        if not bundle["entries"].get(slug):
            bundle["jockeyStats"][slug] = {}
            bundle["trainerStats"][slug] = {}
            continue
        bundle["jockeyStats"][slug] = _stats_map(
            _try_items_soft(client, ep.JOCKEY_RESULT, meet=track["meet"]),
            "jkName",
            "jkNo",
        )
        bundle["trainerStats"][slug] = _stats_map(
            _try_items_soft(client, ep.TRAINER_INFO, meet=track["meet"]),
            "trName",
            "trNo",
        )

    # 7) 경주 조건 상세 (날씨·주로 — 서울/부경만 제공)
    bundle["raceInfo"] = {
        "seoul": _try_items(client, ep.SEOUL_RACE_INFO, race_dt=api_date),
        "busan": _try_items(client, ep.BUSAN_RACE_INFO, race_dt=api_date),
        "jeju": [],
    }

    # 8) 경주 결과 (경주 종료 후 실행 시 채워짐 — 결과종합 API)
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
        # 확정배당율 (단승 WIN·연승 PLC)
        "dividends": {
            slug: [
                row
                for pool in ("WIN", "PLC")
                for row in _try_items(
                    client,
                    ep.DIVIDEND_RATE,
                    meet=track["meet"],
                    rc_date=api_date,
                    pool=pool,
                )
            ]
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
