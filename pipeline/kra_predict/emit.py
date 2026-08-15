"""데이터 계약 이행 계층: 검증 → 원자적 쓰기 → 파생물(meet/index) 재생성.

규칙 (AGENTS.md 데이터 계약 참조):
- 모든 쓰기는 pipeline/schemas/*.schema.json 검증을 통과해야 한다
- result가 있는 경주의 prediction은 --force 없이 덮어쓰지 않는다
- meet.json·index.json은 경주 파일에서 재생성되는 파생물이다
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from datetime import date as date_cls
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

from jsonschema import Draft202012Validator

from kra_predict.config import DATA_DIR, SCHEMAS_DIR, TRACKS

logger = logging.getLogger(__name__)

KST = ZoneInfo("Asia/Seoul")
TRACK_ORDER = ["seoul", "busan", "jeju"]


def now_kst_iso() -> str:
    return datetime.now(KST).isoformat(timespec="seconds")


@lru_cache(maxsize=None)
def _validator(name: str) -> Draft202012Validator:
    schema = json.loads((SCHEMAS_DIR / f"{name}.schema.json").read_text("utf-8"))
    return Draft202012Validator(schema)


def validation_errors(schema_name: str, obj: dict) -> list[str]:
    return [
        f"{'/'.join(str(p) for p in e.absolute_path) or '(root)'}: {e.message}"
        for e in _validator(schema_name).iter_errors(obj)
    ]


def _assert_valid(schema_name: str, obj: dict, label: str) -> None:
    errors = validation_errors(schema_name, obj)
    if errors:
        details = "\n  ".join(errors[:10])
        raise ValueError(f"{label} 스키마 검증 실패:\n  {details}")


def atomic_write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=1)
            f.write("\n")
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


# 재실행 때마다 갱신되는 타임스탬프 — 이것만 다르면 '변경 없음'으로 본다
VOLATILE_KEYS = {"updatedAt", "fetchedAt", "generatedAt"}


def _strip_volatile(obj):
    if isinstance(obj, dict):
        return {
            k: _strip_volatile(v) for k, v in obj.items() if k not in VOLATILE_KEYS
        }
    if isinstance(obj, list):
        return [_strip_volatile(v) for v in obj]
    return obj


def write_json_if_changed(path: Path, obj: dict) -> bool:
    """휘발성 타임스탬프 외 내용이 같으면 쓰지 않는다 (cron 재실행 멱등성 —
    변경 없는 날 자동 커밋이 생기지 않도록). 썼으면 True."""
    if path.exists():
        try:
            existing = json.loads(path.read_text("utf-8"))
        except (OSError, json.JSONDecodeError):
            existing = None
        if existing is not None and _strip_volatile(existing) == _strip_volatile(obj):
            return False
    atomic_write_json(path, obj)
    return True


def race_path(data_dir: Path, date: str, track: str, race_no: int) -> Path:
    return data_dir / "meets" / date / track / f"r{race_no:02d}.json"


def emit_races(
    races: list[dict], *, data_dir: Path = DATA_DIR, force: bool = False
) -> tuple[list[str], list[str], int]:
    """경주 파일을 쓴다. 반환: (기록한 라벨, 건너뛴 라벨, 실제 변경된 파일 수)."""
    written: list[str] = []
    skipped: list[str] = []
    changed = 0
    for race in races:
        label = f"{race['track']} {race['raceNo']}경주"
        path = race_path(data_dir, race["date"], race["track"], race["raceNo"])
        if path.exists():
            existing = json.loads(path.read_text("utf-8"))
            if existing.get("result") is not None and not force:
                logger.warning("%s: 결과가 확정된 경주 → 건너뜀 (--force로 강제)", label)
                skipped.append(label)
                continue
            # 새 조립본에 결과가 없으면 기존 결과를 보존한다
            if race.get("result") is None and existing.get("result") is not None:
                race = {**race, "result": existing["result"]}
        _assert_valid("race", race, label)
        if write_json_if_changed(path, race):
            changed += 1
        written.append(label)
    return written, skipped, changed


def _load_races(meet_dir: Path) -> dict[str, list[dict]]:
    by_track: dict[str, list[dict]] = {}
    for slug in TRACK_ORDER:
        track_dir = meet_dir / slug
        if not track_dir.is_dir():
            continue
        races = [
            json.loads(f.read_text("utf-8"))
            for f in sorted(track_dir.glob("r[0-9][0-9].json"))
        ]
        if races:
            by_track[slug] = races
    return by_track


def rebuild_meet_and_index(*, data_dir: Path = DATA_DIR) -> None:
    """data/meets/**의 경주 파일에서 meet.json과 index.json을 재생성한다."""
    meets_dir = data_dir / "meets"
    meets_dir.mkdir(parents=True, exist_ok=True)
    meet_dates = sorted(
        (d.name for d in meets_dir.iterdir() if d.is_dir()), reverse=True
    )
    if not meet_dates:
        logger.warning("개최일 데이터가 없어 index/meet 재생성을 건너뜁니다")
        return

    for date in meet_dates:
        meet_dir = meets_dir / date
        tracks = []
        for slug, races in _load_races(meet_dir).items():
            tracks.append(
                {
                    "track": slug,
                    "trackName": TRACKS[slug]["name"],
                    "meetCode": TRACKS[slug]["meet"],
                    "races": [
                        {
                            "raceNo": r["raceNo"],
                            "startTimeKst": r["startTimeKst"],
                            "distanceM": r["distanceM"],
                            "grade": r["grade"],
                            "raceName": None,
                            "entryCount": len(r["entries"]),
                            "hasPrediction": r["prediction"] is not None,
                            "hasResult": r["result"] is not None,
                            "canceled": r.get("canceled", False),
                        }
                        for r in races
                    ],
                }
            )
        meet = {"schemaVersion": 1, "date": date, "tracks": tracks}
        _assert_valid("meet", meet, f"meet {date}")
        write_json_if_changed(meet_dir / "meet.json", meet)

    today = datetime.now(KST).date()
    past = [d for d in meet_dates if date_cls.fromisoformat(d) <= today]
    future = [d for d in meet_dates if date_cls.fromisoformat(d) > today]
    index = {
        "schemaVersion": 1,
        "updatedAt": now_kst_iso(),
        "latestMeetDate": (past or meet_dates)[0],
        "nextMeetDate": future[-1] if future else None,
        "meetDates": meet_dates,
    }
    _assert_valid("index", index, "index")
    write_json_if_changed(data_dir / "index.json", index)


def validate_tree(*, data_dir: Path = DATA_DIR) -> list[str]:
    """data/ 전체를 스키마·정합성 검증하고 오류 목록을 돌려준다."""
    errors: list[str] = []

    index_path = data_dir / "index.json"
    if not index_path.exists():
        return ["index.json 없음"]
    index = json.loads(index_path.read_text("utf-8"))
    errors += [f"index.json {e}" for e in validation_errors("index", index)]

    meets_dir = data_dir / "meets"
    dir_dates = sorted(
        (d.name for d in meets_dir.iterdir() if d.is_dir()), reverse=True
    )
    if index.get("meetDates") != dir_dates:
        errors.append(
            f"index.meetDates({index.get('meetDates')}) ≠ 디렉터리({dir_dates})"
        )

    for date in dir_dates:
        meet_dir = meets_dir / date
        meet_path = meet_dir / "meet.json"
        if not meet_path.exists():
            errors.append(f"{date}: meet.json 없음")
            continue
        meet = json.loads(meet_path.read_text("utf-8"))
        errors += [f"{date}/meet.json {e}" for e in validation_errors("meet", meet)]

        summary_counts = {
            (t["track"], r["raceNo"]): r
            for t in meet.get("tracks", [])
            for r in t.get("races", [])
        }
        for slug, races in _load_races(meet_dir).items():
            for race in races:
                label = f"{date}/{slug}/r{race.get('raceNo', 0):02d}"
                errors += [
                    f"{label} {e}" for e in validation_errors("race", race)
                ]
                summary = summary_counts.get((slug, race.get("raceNo")))
                if summary is None:
                    errors.append(f"{label}: meet.json에 요약 없음")
                elif summary["entryCount"] != len(race.get("entries", [])):
                    errors.append(
                        f"{label}: entryCount {summary['entryCount']} ≠ "
                        f"{len(race.get('entries', []))}"
                    )

    stats_path = data_dir / "stats" / "accuracy.json"
    if stats_path.exists():
        stats = json.loads(stats_path.read_text("utf-8"))
        errors += [
            f"stats/accuracy.json {e}"
            for e in validation_errors("accuracy", stats)
        ]
    return errors
