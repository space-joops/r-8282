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


def _build_result(rows: list[dict]) -> dict | None:
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
    win_odds = _num(finishers[0].get("winOdds"))
    place_odds = [
        v
        for r in finishers[:3]
        if (v := _num(r.get("plcOdds"))) is not None
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
                "record1y": None,  # 결과 행에는 1년 성적이 없음 (통산만 제공)
                "recentRuns": [],
                "scratched": False,
                "jockeyChanged": False,
            }
        )
    entries.sort(key=lambda e: e["gateNo"])
    return entries


def _skeleton_race(date: str, slug: str, race_no: int, rows: list[dict]) -> dict:
    first = rows[0]
    return {
        "schemaVersion": 1,
        "date": date,
        "track": slug,
        "raceNo": race_no,
        "startTimeKst": _time_hhmm(first.get("schStTime")) or "00:00",
        "distanceM": _num(first.get("rcDist"), int) or 0,
        "grade": str(first.get("rank", "")).strip() or "일반",
        "canceled": False,
        "ageCond": None,
        "weather": None,
        "trackCond": None,
        "entries": [],
        "prediction": None,
        "result": None,
    }


def apply_results(bundle: dict, *, data_dir: Path = DATA_DIR) -> tuple[int, int]:
    """번들의 결과 행을 data/ 경주 파일에 반영한다. 반환: (반영, 취소) 경주 수."""
    date = bundle["date"]
    applied = canceled_count = 0

    for (slug, race_no), rows in _group_result_rows(bundle).items():
        path = race_path(data_dir, date, slug, race_no)
        if path.exists():
            race = json.loads(path.read_text("utf-8"))
        else:
            race = _skeleton_race(date, slug, race_no, rows)

        is_canceled = any(
            str(r.get("noraceFlag", "")).strip() in CANCEL_FLAGS for r in rows
        )
        race["canceled"] = is_canceled
        if is_canceled:
            race["result"] = None
            canceled_count += 1
        else:
            result = _build_result(rows)
            if result is None:
                logger.warning("%s %d경주: 순위 데이터 없음 → 건너뜀", slug, race_no)
                continue
            race["result"] = result
            applied += 1

        if not race["entries"]:
            race["entries"] = _entries_from_result_rows(rows)

        errors = validation_errors("race", race)
        if errors:
            logger.error("%s %d경주 스키마 오류: %s", slug, race_no, errors[:3])
            continue
        atomic_write_json(path, race)

    return applied, canceled_count
