"""raw 번들 → 데이터 계약(RaceFile dict) 조립.

트랙별 소스 차이:
- 서울: 출전등록(API323, 기수·부담중량 없음) + 마체중(API317) 병합
- 부산경남/제주: 출전표(chulmainfo)/출전마현황 — 승인 전이면 빈 출전 목록
공통: 1년전적(API145) → record1y, 기수변경(API300) → jockeyChanged
"""

from __future__ import annotations

import logging
import re

from kra_predict.config import TRACKS

logger = logging.getLogger(__name__)

TRACK_NAMES = {"seoul": "서울", "busan": "부산경남", "jeju": "제주"}
SEX_NORMALIZE = {"수": "수", "암": "암", "거": "거", "수컷": "수", "암컷": "암", "거세": "거"}


def _num(value, cast=float):
    """API의 빈 문자열/None을 null로, 숫자 문자열을 숫자로 정규화."""
    if value in (None, "", "-"):
        return None
    try:
        return cast(value)
    except (TypeError, ValueError):
        return None


def _time_hhmm(value) -> str | None:
    """"1040" | "10:40" → "10:40"."""
    s = str(value or "").strip()
    if re.fullmatch(r"\d{2}:\d{2}", s):
        return s
    if re.fullmatch(r"\d{3,4}", s):
        s = s.zfill(4)
        return f"{s[:2]}:{s[2:]}"
    return None


def _iso_date(value) -> str | None:
    """"20260815" → "2026-08-15"."""
    s = str(value or "").strip()
    if re.fullmatch(r"\d{8}", s):
        return f"{s[:4]}-{s[4:6]}-{s[6:]}"
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        return s
    return None


def _sex(value) -> str:
    return SEX_NORMALIZE.get(str(value or "").strip(), "거")


def _record1y(row: dict | None) -> dict | None:
    if not row:
        return None
    starts = _num(row.get("loyPtinTcnt"), int)
    if starts is None:
        return None
    return {
        "starts": starts,
        "wins": _num(row.get("loyFcmTcnt"), int) or 0,
        "seconds": _num(row.get("loyScmTcnt"), int) or 0,
        "thirds": _num(row.get("loyTcmTcnt"), int) or 0,
    }


def _base_entry() -> dict:
    return {
        "gateNo": 0,
        "horseId": "",
        "horseName": "",
        "age": 1,
        "sex": "거",
        "rating": None,
        "jockey": {"id": "", "name": "미정", "winRate1y": None},
        "trainer": {"id": "", "name": "미정", "winRate1y": None},
        "weightCarriedKg": None,
        "bodyWeightKg": None,
        "bodyWeightDiffKg": None,
        "record1y": None,
        "recentRuns": [],
        "scratched": False,
        "jockeyChanged": False,
    }


def _seoul_entries(bundle: dict, race_no: int) -> list[dict]:
    weights = {
        _num(w.get("pthrNo"), int): w
        for w in bundle["weights"]["seoul"].get(str(race_no), [])
    }
    entries = []
    for row in bundle["entries"].get("seoul", []):
        if _num(row.get("raceNo"), int) != race_no:
            continue
        gate = _num(row.get("rcptNo"), int) or 0
        horse1y = bundle["horse1y"].get("seoul", {}).get(str(row.get("hrnm", "")).strip())
        weight = weights.get(gate, {})
        entry = _base_entry()
        entry.update(
            gateNo=gate,
            horseId=str((horse1y or {}).get("hrno", "")),
            horseName=str(row.get("hrnm", "")).strip(),
            age=_num(row.get("ag"), int) or 1,
            sex=_sex(row.get("gndr")),
            rating=_num(row.get("ratg")),
            bodyWeightKg=_num(weight.get("hrWeg")),
            bodyWeightDiffKg=_num(weight.get("indec")),
            record1y=_record1y(horse1y),
        )
        entry["trainer"] = {
            "id": "",
            "name": str(row.get("trarNm", "")).strip() or "미정",
            "winRate1y": None,
        }
        entries.append(entry)
    return entries


def _chulma_entries(bundle: dict, slug: str, race_no: int) -> list[dict]:
    entries = []
    for row in bundle["entries"].get(slug, []):
        if _num(row.get("raceNo"), int) != race_no:
            continue
        name = str(row.get("hrnm", "")).strip()
        horse1y = bundle["horse1y"].get(slug, {}).get(name)
        entry = _base_entry()
        entry.update(
            gateNo=_num(row.get("gtno") or row.get("pthrNo"), int) or 0,
            horseId=str((horse1y or {}).get("hrno", "")),
            horseName=name,
            age=_num(row.get("hrsAg") or row.get("ag"), int) or 1,
            sex=_sex(row.get("gndrNm") or row.get("gndr")),
            rating=_num(row.get("rating") or row.get("ratg")),
            weightCarriedKg=_num(row.get("burdWgt")),
            record1y=_record1y(horse1y),
        )
        entry["jockey"] = {
            "id": "",
            "name": str(row.get("jckyNm", "")).strip() or "미정",
            "winRate1y": None,
        }
        entry["trainer"] = {
            "id": "",
            "name": str(row.get("trarNm", "")).strip() or "미정",
            "winRate1y": None,
        }
        entries.append(entry)
    return entries


def _apply_jockey_changes(bundle: dict, slug: str, race_no: int, entries: list[dict]) -> None:
    for change in bundle["jockeyChanges"].get(slug, []):
        if _num(change.get("rcNo"), int) != race_no:
            continue
        gate = _num(change.get("chulNo"), int)
        for entry in entries:
            if entry["gateNo"] == gate or entry["horseName"] == str(
                change.get("hrName", "")
            ).strip():
                entry["jockeyChanged"] = True
                after = str(change.get("jkAftName", "")).strip()
                if after:
                    entry["jockey"] = {
                        "id": str(change.get("jkAft", "")),
                        "name": after,
                        "winRate1y": entry["jockey"]["winRate1y"],
                    }


def assemble_races(bundle: dict) -> list[dict]:
    """번들에서 result/prediction이 비어 있는 RaceFile dict 목록을 만든다."""
    races: list[dict] = []
    for slug in TRACKS:
        for plan in bundle["plan"].get(slug, []):
            race_no = _num(plan.get("rcNo"), int)
            if not race_no:
                continue
            if slug == "seoul":
                entries = _seoul_entries(bundle, race_no)
            else:
                entries = _chulma_entries(bundle, slug, race_no)
            _apply_jockey_changes(bundle, slug, race_no, entries)
            entries.sort(key=lambda e: e["gateNo"])

            races.append(
                {
                    "schemaVersion": 1,
                    "date": bundle["date"],
                    "track": slug,
                    "raceNo": race_no,
                    "startTimeKst": _time_hhmm(plan.get("schStTime")) or "00:00",
                    "distanceM": _num(plan.get("rcDist"), int) or 0,
                    "grade": str(plan.get("rank", "")).strip() or "일반",
                    "ageCond": str(plan.get("ageCond", "")).strip() or None,
                    "weather": None,
                    "trackCond": None,
                    "entries": entries,
                    "prediction": None,
                    "result": None,
                }
            )
            if not entries:
                logger.info(
                    "%s %d경주: 출전마 데이터 없음 (해당 트랙 출전 API 미승인일 수 있음)",
                    slug,
                    race_no,
                )
    return races
