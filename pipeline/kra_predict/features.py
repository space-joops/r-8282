"""raw 번들 → 데이터 계약(RaceFile dict) 조립.

출전마 소스 우선순위 (fetch.py에서 결정):
1. 출전표정보(chulmainfo, API78) — 전 트랙, 기수·부담중량·레이팅 포함
2. 폴백: 서울 출전등록(API323)+마체중(API317), 부경 출전마현황(API316)
공통: 1년전적(API145) → record1y, 기수변경(API300) → jockeyChanged,
기수/조교사 성적(API11_1/API308) → winRate1y, 경주정보(API311/313) → 날씨·주로
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


def _int_loose(value) -> int | None:
    """"제1경주" | "1" | 1 → 1 (숫자만 추출)."""
    digits = re.sub(r"[^0-9]", "", str(value or ""))
    return int(digits) if digits else None


def _time_hhmm(value) -> str | None:
    """1040 | "10:40" | "2026-08-15T12:55:00+09:00" → "HH:MM"."""
    s = str(value or "").strip()
    iso = re.match(r"\d{4}-\d{2}-\d{2}T(\d{2}:\d{2})", s)
    if iso:
        return iso.group(1)
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


def _rating(value) -> float | None:
    """레이팅 정규화 — "(45)" 형식 허용, 0·빈 값은 미부여로 null."""
    cleaned = re.sub(r"[^0-9.]", "", str(value or ""))
    rating = _num(cleaned)
    return rating if rating else None


def _dash_none(value) -> str | None:
    s = str(value or "").strip()
    return None if s in ("", "-") else s


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


def _race_no_of(row: dict) -> int | None:
    value = row.get("raceNo") if row.get("raceNo") is not None else row.get("rcNo")
    return _int_loose(value)


def _entry_from_chulma(row: dict) -> dict:
    """출전표정보(API78) 행 → 엔트리. wgtIndec은 마체중 증감(당일 체중은 별도)."""
    entry = _base_entry()
    entry.update(
        gateNo=_num(row.get("gtno"), int) or 0,
        horseName=str(row.get("hrnm", "")).strip(),
        age=_num(row.get("hrsAg"), int) or 1,
        sex=_sex(row.get("gndrNm")),
        rating=_rating(row.get("rating")),
        weightCarriedKg=_num(row.get("burdWgt")),
        bodyWeightDiffKg=_num(row.get("wgtIndec")),
    )
    entry["jockey"]["name"] = str(row.get("jckyNm", "")).strip() or "미정"
    entry["trainer"]["name"] = str(row.get("trarNm", "")).strip() or "미정"
    return entry


def _entry_from_seoul_reg(row: dict) -> dict:
    """서울 출전등록(API323) 행 → 엔트리 (기수·부담중량 없음)."""
    entry = _base_entry()
    entry.update(
        gateNo=_num(row.get("rcptNo"), int) or 0,
        horseName=str(row.get("hrnm", "")).strip(),
        age=_num(row.get("ag"), int) or 1,
        sex=_sex(row.get("gndr")),
        rating=_rating(row.get("ratg")),
    )
    entry["trainer"]["name"] = str(row.get("trarNm", "")).strip() or "미정"
    return entry


def _entry_from_busan(row: dict) -> dict:
    """부경 출전마현황(API316) 행 → 엔트리."""
    entry = _base_entry()
    entry.update(
        gateNo=_num(row.get("pthrNo"), int) or 0,
        horseName=str(row.get("hrnm", "")).strip(),
        age=_num(row.get("ag"), int) or 1,
        sex=_sex(row.get("gndr")),
        rating=_rating(row.get("ratg")),
        weightCarriedKg=_num(row.get("burdWgt")),
    )
    entry["jockey"]["name"] = str(row.get("jckyNm", "")).strip() or "미정"
    entry["trainer"]["name"] = str(row.get("trarNm", "")).strip() or "미정"
    return entry


def _build_entries(bundle: dict, slug: str, race_no: int) -> list[dict]:
    entries = []
    for row in bundle["entries"].get(slug, []):
        if _race_no_of(row) != race_no:
            continue
        if "gtno" in row:
            entries.append(_entry_from_chulma(row))
        elif "rcptNo" in row:
            entries.append(_entry_from_seoul_reg(row))
        else:
            entries.append(_entry_from_busan(row))
    return entries


def _enrich_entries(bundle: dict, slug: str, race_no: int, entries: list[dict]) -> None:
    """마체중(서울)·1년전적·기수/조교사 성적을 이름/번호로 병합한다."""
    weights = {
        _num(w.get("pthrNo"), int): w
        for w in bundle.get("weights", {}).get("seoul", {}).get(str(race_no), [])
    }
    horse1y = bundle.get("horse1y", {}).get(slug, {})
    jockey_stats = bundle.get("jockeyStats", {}).get(slug, {})
    trainer_stats = bundle.get("trainerStats", {}).get(slug, {})

    for entry in entries:
        if slug == "seoul":
            weight = weights.get(entry["gateNo"], {})
            if entry["bodyWeightKg"] is None:
                entry["bodyWeightKg"] = _num(weight.get("hrWeg"))
            if entry["bodyWeightDiffKg"] is None:
                entry["bodyWeightDiffKg"] = _num(weight.get("indec"))

        record = horse1y.get(entry["horseName"])
        if record:
            entry["horseId"] = entry["horseId"] or str(record.get("hrno", ""))
            if entry["record1y"] is None:
                entry["record1y"] = _record1y(record)

        jockey = jockey_stats.get(entry["jockey"]["name"])
        if jockey:
            entry["jockey"]["id"] = entry["jockey"]["id"] or jockey["id"]
            entry["jockey"]["winRate1y"] = jockey["winRate1y"]
        trainer = trainer_stats.get(entry["trainer"]["name"])
        if trainer:
            entry["trainer"]["id"] = entry["trainer"]["id"] or trainer["id"]
            entry["trainer"]["winRate1y"] = trainer["winRate1y"]


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
                        "winRate1y": None,
                    }


def _race_info_of(bundle: dict, slug: str, race_no: int) -> dict:
    for row in bundle.get("raceInfo", {}).get(slug, []):
        if _num(row.get("raceNo"), int) == race_no:
            return row
    return {}


def assemble_races(bundle: dict) -> list[dict]:
    """번들에서 result/prediction이 비어 있는 RaceFile dict 목록을 만든다."""
    races: list[dict] = []
    for slug in TRACKS:
        for plan in bundle["plan"].get(slug, []):
            race_no = _num(plan.get("rcNo"), int)
            if not race_no:
                continue
            entries = _build_entries(bundle, slug, race_no)
            _enrich_entries(bundle, slug, race_no, entries)
            _apply_jockey_changes(bundle, slug, race_no, entries)
            entries.sort(key=lambda e: e["gateNo"])

            info = _race_info_of(bundle, slug, race_no)
            races.append(
                {
                    "schemaVersion": 1,
                    "date": bundle["date"],
                    "track": slug,
                    "raceNo": race_no,
                    "startTimeKst": _time_hhmm(plan.get("schStTime")) or "00:00",
                    "distanceM": _num(plan.get("rcDist"), int) or 0,
                    "grade": str(plan.get("rank", "")).strip() or "일반",
                    "canceled": False,
                    "ageCond": str(plan.get("ageCond", "")).strip() or None,
                    "weather": _dash_none(info.get("wetr")),
                    "trackCond": _dash_none(info.get("going")),
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
