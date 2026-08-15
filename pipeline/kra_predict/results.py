"""경주 후 결과 반영 — 경주결과종합(API299) 행 → RaceResult.

규칙: prediction은 절대 건드리지 않는다. 경주 파일이 없거나 출전표가 비어
있으면(부경·제주 사전 API 미승인 시) 결과 행으로 출전표를 역구성한다.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from kra_predict.config import DATA_DIR, MEET_TO_SLUG
from kra_predict.emit import (
    atomic_write_json,
    now_kst_iso,
    race_path,
    validation_errors,
)
from kra_predict.features import _num, _sex, _time_hhmm

logger = logging.getLogger(__name__)

CANCEL_FLAGS = {"1", "2"}  # 1:경주취소, 2:경주불성립


def parse_race_time(value) -> float | None:
    """"73.7" | "1:13.7" → 초 단위 float."""
    s = str(value or "").strip()
    if not s:
        return None
    if ":" in s:
        try:
            minutes, seconds = s.split(":", 1)
            return round(int(minutes) * 60 + float(seconds), 1)
        except ValueError:
            return None
    return _num(s)


def parse_body_weight(value) -> tuple[float | None, float | None]:
    """"478(+4)" → (478.0, 4.0). 형식이 다르면 (숫자, None)."""
    s = str(value or "").strip()
    match = re.fullmatch(r"([\d.]+)\s*\(\s*([+-]?[\d.]+)\s*\)", s)
    if match:
        return _num(match.group(1)), _num(match.group(2))
    return _num(s), None


def _group_result_rows(bundle: dict) -> dict[tuple[str, int], list[dict]]:
    grouped: dict[tuple[str, int], list[dict]] = {}
    for slug, rows in bundle.get("results", {}).items():
        for row in rows:
            race_no = _num(row.get("rcNo"), int)
            if race_no:
                grouped.setdefault((slug, race_no), []).append(row)
    return grouped


def _build_result(rows: list[dict], dividends: dict[str, dict[int, float]]) -> dict | None:
    finishers = [r for r in rows if _num(r.get("ord"), int)]
    if not finishers:
        return None
    finishers.sort(key=lambda r: _num(r.get("ord"), int) or 99)
    order = [
        {
            "finishPos": _num(r.get("ord"), int) or 0,
            "gateNo": _num(r.get("chulNo"), int) or 0,
            "horseName": str(r.get("hrName", "")).strip(),
            "timeSec": parse_race_time(r.get("rcTime")),
            "margin": str(r.get("diffUnit", "")).strip() or None,
        }
        for r in finishers
    ]
    # 확정배당율(API301) 우선, 없으면 결과종합 행의 배당 필드 폴백
    win_odds = dividends.get("WIN", {}).get(order[0]["gateNo"])
    if win_odds is None:
        win_odds = _num(finishers[0].get("winOdds"))
    place_odds = [
        odds
        for o in order[:3]
        if (odds := dividends.get("PLC", {}).get(o["gateNo"])) is not None
    ]
    if not place_odds:
        place_odds = [
            v for r in finishers[:3] if (v := _num(r.get("plcOdds"))) is not None
        ]
    payouts = None
    if win_odds is not None or place_odds:
        payouts = {"win": win_odds, "place": place_odds or None}
    return {"fetchedAt": now_kst_iso(), "order": order, "payouts": payouts}


def _entries_from_result_rows(rows: list[dict]) -> list[dict]:
    """사전 출전 데이터가 없던 경주의 출전표를 결과 행으로 역구성한다."""
    entries = []
    for row in rows:
        body, diff = parse_body_weight(row.get("wgHr"))
        # rcCntY/ord1CntY/ord2CntY는 출전마의 최근 1년 성적 (3착 수는 미제공 → 0)
        hr_starts_1y = _num(row.get("rcCntY"), int)
        record1y = (
            {
                "starts": hr_starts_1y,
                "wins": _num(row.get("ord1CntY"), int) or 0,
                "seconds": _num(row.get("ord2CntY"), int) or 0,
                "thirds": 0,
            }
            if hr_starts_1y is not None
            else None
        )
        jk_starts_1y = _num(row.get("jkRcCntY"), int)
        jk_wins_1y = _num(row.get("jkOrd1CntY"), int)
        tr_starts_1y = _num(row.get("trRcCntY"), int)
        tr_wins_1y = _num(row.get("trOrd1CntY"), int)
        entries.append(
            {
                "gateNo": _num(row.get("chulNo"), int) or 0,
                "horseId": str(row.get("hrNo", "")),
                "horseName": str(row.get("hrName", "")).strip(),
                "age": _num(row.get("age"), int) or 1,
                "sex": _sex(row.get("sex")),
                "rating": _num(row.get("rating")),
                "jockey": {
                    "id": str(row.get("jkNo", "")),
                    "name": str(row.get("jkName", "")).strip() or "미정",
                    "winRate1y": round(jk_wins_1y / jk_starts_1y, 3)
                    if jk_starts_1y and jk_wins_1y is not None
                    else None,
                },
                "trainer": {
                    "id": str(row.get("trNo", "")),
                    "name": str(row.get("trName", "")).strip() or "미정",
                    "winRate1y": round(tr_wins_1y / tr_starts_1y, 3)
                    if tr_starts_1y and tr_wins_1y is not None
                    else None,
                },
                "weightCarriedKg": _num(row.get("wgBudam")),
                "bodyWeightKg": body,
                "bodyWeightDiffKg": diff,
                "record1y": record1y,
                "recentRuns": [],
                "scratched": False,
                "jockeyChanged": False,
            }
        )
    entries.sort(key=lambda e: e["gateNo"])
    return entries


def _skeleton_race(
    date: str, slug: str, race_no: int, rows: list[dict], plan: dict | None
) -> dict:
    """결과 행 + 계획표 행으로 경주 파일 골격을 만든다 (거리는 계획표에만 있음)."""
    first = rows[0]
    plan = plan or {}
    return {
        "schemaVersion": 1,
        "date": date,
        "track": slug,
        "raceNo": race_no,
        "startTimeKst": _time_hhmm(plan.get("schStTime"))
        or _time_hhmm(first.get("schStTime"))
        or "00:00",
        "distanceM": _num(plan.get("rcDist"), int) or 1,
        "grade": str(first.get("rank") or plan.get("rank") or "").strip() or "일반",
        "canceled": False,
        "ageCond": str(plan.get("ageCond", "")).strip() or None,
        "weather": None,
        # 결과종합의 track 필드가 주로 상태("건조 (3%)")를 담는다
        "trackCond": str(first.get("track", "")).strip() or None,
        "entries": [],
        "prediction": None,
        "result": None,
    }


def apply_results(bundle: dict, *, data_dir: Path = DATA_DIR) -> tuple[int, int]:
    """번들의 결과 행을 data/ 경주 파일에 반영한다. 반환: (반영, 취소) 경주 수."""
    date = bundle["date"]
    applied = canceled_count = 0
    plans = {
        (slug, _num(p.get("rcNo"), int)): p
        for slug, rows in bundle.get("plan", {}).items()
        for p in rows
    }
    # 확정배당율: (트랙, 경주) → {pool: {마번: 배당}}
    dividends: dict[tuple[str, int], dict[str, dict[int, float]]] = {}
    for slug, rows in bundle.get("dividends", {}).items():
        for row in rows:
            rc_no = _num(row.get("rcNo"), int)
            gate = _num(row.get("chulNo"), int)
            odds = _num(row.get("odds"))
            pool = str(row.get("pool", "")).strip()
            if rc_no and gate and odds is not None and pool:
                dividends.setdefault((slug, rc_no), {}).setdefault(pool, {})[gate] = odds

    for (slug, race_no), rows in _group_result_rows(bundle).items():
        path = race_path(data_dir, date, slug, race_no)
        if path.exists():
            race = json.loads(path.read_text("utf-8"))
        else:
            race = _skeleton_race(
                date, slug, race_no, rows, plans.get((slug, race_no))
            )

        is_canceled = any(
            str(r.get("noraceFlag", "")).strip() in CANCEL_FLAGS for r in rows
        )
        race["canceled"] = is_canceled
        if is_canceled:
            race["result"] = None
        else:
            result = _build_result(rows, dividends.get((slug, race_no), {}))
            if result is None:
                logger.warning("%s %d경주: 순위 미확정 → 건너뜀", slug, race_no)
                continue
            race["result"] = result

        if race.get("trackCond") is None:
            race["trackCond"] = str(rows[0].get("track", "")).strip() or None
        if not race["entries"]:
            race["entries"] = _entries_from_result_rows(rows)

        errors = validation_errors("race", race)
        if errors:
            logger.error("%s %d경주 스키마 오류: %s", slug, race_no, errors[:3])
            continue
        atomic_write_json(path, race)
        if is_canceled:
            canceled_count += 1
        else:
            applied += 1

    return applied, canceled_count
