"""백테스트 — 과거 경주에 통계 모델 v1을 '경주 전 정보'만으로 적용해 성능을 잰다.

누수 방지 설계:
- 소스는 경주성적정보(API214_1)만 사용. 행에 저장된 값(레이팅·부담중량·마체중·
  배당·결과)은 경주 당시 기록임을 확인함(다회 출전마의 레이팅이 경주별 상이).
- 마필/기수/조교사 1년 스탯은 API의 요약 필드(조회 시점 재계산 — 누수 확인됨)를
  쓰지 않고, 타깃 이전 12개월 데이터를 함께 수집해 **경주일 이전 365일 창**으로
  직접 계산한다. 휴양일도 직전 출주일에서 자체 계산.
- 배당 9999.9는 무효 마커 → ROI에서 해당 경주 제외.
"""

from __future__ import annotations

import logging
import math
from bisect import bisect_left
from collections import defaultdict
from datetime import date as date_cls
from datetime import timedelta
from pathlib import Path

import json

from kra_predict.api import endpoints as ep
from kra_predict.api.client import KraClient
from kra_predict.config import DATA_DIR
from kra_predict.emit import (
    now_kst_iso,
    validation_errors,
    write_json_if_changed,
)
from kra_predict.features import _base_entry, _iso_date, _num, _rating, _sex
from kra_predict.results import parse_body_weight
from kra_predict.score import build_prediction, load_learned_model

logger = logging.getLogger(__name__)

MODEL_VERSION = "v1"
MODEL_NOTE = (
    "통계 가중 모델 v1 단독 백테스트 (실서비스의 AI 보정 미포함). "
    "마필·기수·조교사 1년 성적은 경주일 이전 365일 데이터로 직접 계산해 "
    "사후 정보 누수를 차단함. ROI는 실제 확정 배당 기준 1단위 균등 베팅 시뮬레이션."
)

HISTORY_MONTHS = 12
MEET_NAME_TO_SLUG = {"서울": "seoul", "부산경남": "busan", "제주": "jeju", "부경": "busan"}
CONFIDENCES = ("high", "medium", "low")
TRACKS = ("seoul", "busan", "jeju")
INVALID_ODDS = 9999.0  # 이 값 이상은 발매 무효 마커

# 승식별 베팅 시뮬레이션 — 예측 1·2·3순위를 그대로 1장(100원)씩
BET_UNIT_KRW = 100
POOL_DEFS = [
    ("WIN", "단승"),
    ("PLC", "연승"),
    ("QNL", "복승"),
    ("EXA", "쌍승"),
    ("QPL", "복연승"),
    ("TLA", "삼복승"),
    ("TRI", "삼쌍승"),
]
EXOTIC_POOLS = ("QNL", "EXA", "QPL", "TLA", "TRI")
ORDERED_POOLS = {"EXA", "TRI"}  # 착순 순서까지 맞혀야 하는 풀


def month_list_with_history(target_months: list[str]) -> list[str]:
    """타깃 월 + 이전 12개월을 오름차순으로 돌려준다."""
    first = min(target_months)
    year, month = int(first[:4]), int(first[5:7])
    months: list[str] = []
    for _ in range(HISTORY_MONTHS):
        month -= 1
        if month == 0:
            year, month = year - 1, 12
        months.append(f"{year:04d}-{month:02d}")
    return sorted(set(months) | set(target_months))


def fetch_detail_rows(client: KraClient, months: list[str]) -> list[dict]:
    rows: list[dict] = []
    for month in months:
        ym = month.replace("-", "")
        for meet in (1, 2, 3):
            rows += client.get_items(ep.RACE_DETAIL_RESULT, meet=meet, rc_month=ym)
    return rows


def _odds(value) -> float | None:
    odds = _num(value)
    if odds is None or odds >= INVALID_ODDS:
        return None
    return odds


DividendLookup = dict[tuple, dict[tuple, float]]


def fetch_pool_dividends(client: KraClient, months: list[str]) -> DividendLookup:
    """확정배당율종합(API301)에서 복승·쌍승·복연승·삼복승·삼쌍승 배당을 수집.

    반환: {(slug, date, rcNo, pool): {조합: 배당}} — 전 조합 배당이 제공되므로
    (경주, 풀) 키의 존재 여부가 곧 '해당 승식 발매 여부'다.
    순서 무관 풀(QNL·QPL·TLA)의 조합은 정렬 튜플로 정규화한다.
    """
    lookup: DividendLookup = {}
    for month in months:
        ym = month.replace("-", "")
        for meet in (1, 2, 3):
            for pool in EXOTIC_POOLS:
                rows = client.get_items(
                    ep.DIVIDEND_RATE,
                    meet=meet,
                    rc_month=ym,
                    pool=pool,
                    num_of_rows=999,
                    max_pages=200,
                )
                for row in rows:
                    slug = MEET_NAME_TO_SLUG.get(str(row.get("meet", "")).strip())
                    date = _iso_date(row.get("rcDate"))
                    rc_no = _num(row.get("rcNo"), int)
                    odds = _odds(row.get("odds"))
                    combo = tuple(
                        c
                        for c in (
                            _num(row.get("chulNo"), int),
                            _num(row.get("chulNo2"), int),
                            _num(row.get("chulNo3"), int),
                        )
                        if c
                    )
                    if not slug or not date or not rc_no or odds is None or not combo:
                        continue
                    if pool not in ORDERED_POOLS:
                        combo = tuple(sorted(combo))
                    lookup.setdefault((slug, date, rc_no, pool), {})[combo] = odds
    return lookup


class AsOfStats:
    """개체(마필/기수/조교사)별 출주 이력 → 경주일 이전 365일 창 집계."""

    def __init__(self) -> None:
        self._runs: dict[str, list[tuple[str, int]]] = defaultdict(list)

    def add(self, key: str, date_iso: str, ord_: int) -> None:
        if key:
            self._runs[key].append((date_iso, ord_))

    def freeze(self) -> None:
        for runs in self._runs.values():
            runs.sort()

    def window(self, key: str, date_iso: str) -> list[int]:
        """경주일 이전 365일 내 착순 목록 (당일 미포함)."""
        runs = self._runs.get(key, [])
        start = (date_cls.fromisoformat(date_iso) - timedelta(days=365)).isoformat()
        lo = bisect_left(runs, (start, 0))
        hi = bisect_left(runs, (date_iso, 0))
        return [ord_ for _, ord_ in runs[lo:hi]]

    def last_run_before(self, key: str, date_iso: str) -> str | None:
        runs = self._runs.get(key, [])
        hi = bisect_left(runs, (date_iso, 0))
        return runs[hi - 1][0] if hi > 0 else None

    @staticmethod
    def win_rate(orders: list[int]) -> float | None:
        if not orders:
            return None
        return round(sum(1 for o in orders if o == 1) / len(orders), 3)


def build_backtest_races(rows: list[dict], target_months: list[str]) -> list[dict]:
    horses, jockeys, trainers = AsOfStats(), AsOfStats(), AsOfStats()
    grouped: dict[tuple, list[dict]] = {}

    row_totals: dict[tuple, int] = defaultdict(int)
    for row in rows:
        slug = MEET_NAME_TO_SLUG.get(str(row.get("meet", "")).strip())
        date = _iso_date(row.get("rcDate"))
        rc_no = _num(row.get("rcNo"), int)
        if not slug or not date or not rc_no:
            continue
        if date[:7] in target_months:
            row_totals[(slug, date, rc_no)] += 1
        ord_ = _num(row.get("ord"), int)
        if not ord_:
            continue  # 출주취소·실격(ord 없음)은 이력·필드에서 제외
        horses.add(str(row.get("hrNo", "")), date, ord_)
        jockeys.add(str(row.get("jkNo", "")), date, ord_)
        trainers.add(str(row.get("trNo", "")), date, ord_)
        if date[:7] in target_months:
            grouped.setdefault((slug, date, rc_no), []).append(row)

    for stats in (horses, jockeys, trainers):
        stats.freeze()

    races: list[dict] = []
    skipped_broken = 0
    for (slug, date, rc_no), race_rows in sorted(grouped.items()):
        # 데이터 무결성: 완주 순위가 1..k로 온전히 기록된 경주만 평가.
        # (일부 특이 개최일은 상위 3착만 ord가 기록돼 필드가 왜곡됨)
        ords = sorted(_num(r.get("ord"), int) or 0 for r in race_rows)
        k = len(ords)
        if k < 5 or ords != list(range(1, k + 1)):
            skipped_broken += 1
            continue
        entries = []
        results = {}
        for row in race_rows:
            gate = _num(row.get("chulNo"), int) or 0
            hr_no = str(row.get("hrNo", ""))
            body, diff = parse_body_weight(row.get("wgHr"))
            hr_window = horses.window(hr_no, date)
            entry = _base_entry()
            entry.update(
                gateNo=gate,
                horseId=hr_no,
                horseName=str(row.get("hrName", "")).strip(),
                age=_num(row.get("age"), int) or 1,
                sex=_sex(row.get("sex")),
                rating=_rating(row.get("rating")),
                weightCarriedKg=_num(row.get("wgBudam")),
                bodyWeightKg=body,
                bodyWeightDiffKg=diff,
                record1y=None
                if not hr_window
                else {
                    "starts": len(hr_window),
                    "wins": sum(1 for o in hr_window if o == 1),
                    "seconds": sum(1 for o in hr_window if o == 2),
                    "thirds": sum(1 for o in hr_window if o == 3),
                },
            )
            entry["jockey"]["winRate1y"] = AsOfStats.win_rate(
                jockeys.window(str(row.get("jkNo", "")), date)
            )
            entry["trainer"]["winRate1y"] = AsOfStats.win_rate(
                trainers.window(str(row.get("trNo", "")), date)
            )
            last = horses.last_run_before(hr_no, date)
            if last:
                entry["recentRuns"] = [
                    {
                        "date": last,
                        "track": slug,
                        "finishPos": 1,
                        "entryCount": 2,
                        "distanceM": 1,
                        "timeSec": None,
                    }
                ]
            entries.append(entry)
            results[gate] = {
                "ord": _num(row.get("ord"), int) or 0,
                "winOdds": _odds(row.get("winOdds")),
                "plcOdds": _odds(row.get("plcOdds")),
            }
        entries.sort(key=lambda e: e["gateNo"])
        races.append(
            {
                "track": slug,
                "date": date,
                "raceNo": rc_no,
                "entries": entries,
                "results": results,
            }
        )
    if skipped_broken:
        logger.warning(
            "순위 기록이 불완전한 경주 %d건 제외 (평가 %d건)",
            skipped_broken,
            len(races),
        )
    return races


def _judge_pools(
    race: dict,
    picks: list[int],
    results: dict,
    win_hit: bool,
    place_hit: bool,
    dividends: DividendLookup | None,
) -> dict[str, dict]:
    """풀별 (베팅 여부, 적중, 회수액 KRW). 발매 여부 = 배당 룩업 키 존재."""
    ord_of = {gate: res["ord"] for gate, res in results.items()}
    by_pos = sorted(results.items(), key=lambda kv: kv[1]["ord"])
    actual = [g for g, _ in by_pos[:3]]
    p1 = picks[0]
    p2 = picks[1] if len(picks) > 1 else None
    p3 = picks[2] if len(picks) > 2 else None

    pools: dict[str, dict] = {}
    # 단승·연승은 경주성적정보의 배당 필드 기준 (기존 ROI 정의와 동일)
    win_odds = results.get(p1, {}).get("winOdds")
    plc_odds = results.get(p1, {}).get("plcOdds")
    pools["WIN"] = {
        "staked": 1 if win_odds is not None else 0,
        "hit": 1 if (win_hit and win_odds is not None) else 0,
        "returnKrw": win_odds * BET_UNIT_KRW if (win_hit and win_odds) else 0.0,
    }
    pools["PLC"] = {
        "staked": 1 if plc_odds is not None else 0,
        "hit": 1 if (place_hit and plc_odds is not None) else 0,
        "returnKrw": plc_odds * BET_UNIT_KRW if (place_hit and plc_odds) else 0.0,
    }

    combos: dict[str, tuple | None] = {
        "QNL": tuple(sorted((p1, p2))) if p2 else None,
        "EXA": (p1, p2) if p2 else None,
        "QPL": tuple(sorted((p1, p2))) if p2 else None,
        "TLA": tuple(sorted((p1, p2, p3))) if p3 else None,
        "TRI": (p1, p2, p3) if p3 else None,
    }
    hits = {
        "QNL": p2 is not None and set(actual[:2]) == {p1, p2},
        "EXA": p2 is not None and actual[:2] == [p1, p2],
        "QPL": p2 is not None
        and (ord_of.get(p1) or 99) <= 3
        and (ord_of.get(p2) or 99) <= 3,
        "TLA": p3 is not None and set(actual) == {p1, p2, p3},
        "TRI": p3 is not None and actual == [p1, p2, p3],
    }
    key_base = (race["track"], race["date"], race["raceNo"])
    for pool in EXOTIC_POOLS:
        combo = combos[pool]
        table = (dividends or {}).get((*key_base, pool))
        if combo is None or table is None:
            pools[pool] = {"staked": 0, "hit": 0, "returnKrw": 0.0}
            continue
        hit = hits[pool]
        payout = 0.0
        if hit:
            odds = table.get(combo)
            if odds is None:
                logger.warning(
                    "%s %s %d경주 %s: 적중 조합 %s의 배당 행 없음 → 회수 0 처리",
                    race["track"], race["date"], race["raceNo"], pool, combo,
                )
            else:
                payout = odds * BET_UNIT_KRW
        pools[pool] = {"staked": 1, "hit": 1 if hit else 0, "returnKrw": payout}
    return pools


def simulate(
    races: list[dict], dividends: DividendLookup | None = None
) -> list[dict]:
    """경주별 활성 모델 예측 → 실제 결과 대조 (+승식별 베팅 시뮬)."""
    judged = []
    for race in races:
        pred = build_prediction(
            race["entries"], race_date=race["date"], generated_at="backtest"
        )
        if pred is None:
            continue
        results = race["results"]
        by_pos = sorted(results.items(), key=lambda kv: kv[1]["ord"])
        winner_gate = by_pos[0][0]
        top3_actual = [g for g, _ in by_pos[:3]]
        pick = pred["topPicks"]["win"]
        pick_result = results.get(pick, {})
        top3_pred = [r["gateNo"] for r in pred["rankings"][:3]]
        winner_prob = next(
            (r["winProb"] for r in pred["rankings"] if r["gateNo"] == winner_gate),
            None,
        )
        win_hit = pick == winner_gate
        place_hit = (pick_result.get("ord") or 99) <= 3

        win_odds = pick_result.get("winOdds")
        plc_odds = pick_result.get("plcOdds")
        judged.append(
            {
                "track": race["track"],
                "date": race["date"],
                "raceNo": race["raceNo"],
                "month": race["date"][:7],
                "confidence": pred["confidence"],
                "picks": top3_pred,
                "actual": top3_actual,
                "winHit": win_hit,
                "placeHit": place_hit,
                "top3Exact": top3_pred == top3_actual and len(top3_actual) == 3,
                "logLoss": -math.log(max(winner_prob or 1e-6, 1e-6)),
                # 배당이 유효한 경주만 ROI 분모에 포함
                "stakeWin": 1 if win_odds is not None else 0,
                "returnWin": win_odds if (win_hit and win_odds is not None) else 0.0,
                "stakePlace": 1 if plc_odds is not None else 0,
                "returnPlace": plc_odds
                if (place_hit and plc_odds is not None)
                else 0.0,
                "pools": _judge_pools(
                    race, top3_pred, results, win_hit, place_hit, dividends
                ),
            }
        )
    return judged


def _roi(rows: list[dict], stake_key: str, return_key: str) -> float | None:
    stake = sum(r[stake_key] for r in rows)
    if not stake:
        return None
    return round((sum(r[return_key] for r in rows) - stake) / stake, 4)


def _bucket(rows: list[dict]) -> dict:
    races = len(rows)
    win_hits = sum(1 for r in rows if r["winHit"])
    place_hits = sum(1 for r in rows if r["placeHit"])
    return {
        "races": races,
        "winHits": win_hits,
        "winRate": round(win_hits / races, 4) if races else 0,
        "placeHits": place_hits,
        "placeRate": round(place_hits / races, 4) if races else 0,
        "top3ExactHits": sum(1 for r in rows if r["top3Exact"]),
        "logLoss": round(sum(r["logLoss"] for r in rows) / races, 4) if races else None,
        "roiWin": _roi(rows, "stakeWin", "returnWin"),
        "roiPlace": _roi(rows, "stakePlace", "returnPlace"),
    }


def _model_meta() -> tuple[str, str]:
    """활성 모델(v1/v2)에 맞는 버전·설명."""
    model = load_learned_model()
    if model:
        note = (
            f"조건부 로짓 {model['version']} — {model['trainFrom']}~{model['trainTo']} "
            f"{model['trainRaces']}경주로 학습한 가중치 (평가 기간과 분리된 "
            "아웃오브샘플 백테스트, AI 보정 미포함). 마필·기수·조교사 1년 성적은 "
            "경주일 이전 365일 데이터로 직접 계산해 사후 정보 누수를 차단함. "
            "ROI는 실제 확정 배당 기준 1단위 균등 베팅 시뮬레이션."
        )
        return model["version"], note
    return MODEL_VERSION, MODEL_NOTE


def _betting_summary(judged: list[dict]) -> list[dict]:
    """승식별 최소단위(100원) 균등 베팅 결과 집계."""
    out = []
    for pool, label in POOL_DEFS:
        rows = [r["pools"][pool] for r in judged if "pools" in r]
        bets = sum(r["staked"] for r in rows)
        hits = sum(r["hit"] for r in rows)
        returned = sum(r["returnKrw"] for r in rows)
        stake = bets * BET_UNIT_KRW
        out.append(
            {
                "pool": pool,
                "label": label,
                "bets": bets,
                "hits": hits,
                "hitRate": round(hits / bets, 4) if bets else 0,
                "stakeKrw": stake,
                "returnedKrw": round(returned),
                "profitKrw": round(returned - stake),
                "roi": round((returned - stake) / stake, 4) if stake else None,
            }
        )
    return out


def aggregate(judged: list[dict], months: list[str]) -> dict:
    dates = sorted({r["date"] for r in judged})
    version, note = _model_meta()
    return {
        "version": version,
        "generatedAt": now_kst_iso(),
        "periodFrom": dates[0] if dates else f"{months[0]}-01",
        "periodTo": dates[-1] if dates else f"{months[-1]}-01",
        "note": note,
        "overall": _bucket(judged),
        "byTrack": {
            slug: _bucket([r for r in judged if r["track"] == slug])
            for slug in TRACKS
        },
        "byConfidence": {
            c: _bucket([r for r in judged if r["confidence"] == c])
            for c in CONFIDENCES
        },
        "monthly": [
            {"month": m, **_bucket([r for r in judged if r["month"] == m])}
            for m in sorted({r["month"] for r in judged})
        ],
        "betting": _betting_summary(judged),
    }


def write_backtest_races(
    version: str, judged: list[dict], *, data_dir: Path = DATA_DIR
) -> None:
    """경주별 베팅 결과를 /model 대시보드용으로 공개한다 (버전별 교체 삽입).

    pools 값은 [staked, hit, returnKrw] 압축 배열 — POOL_DEFS 순서의 7개 키.
    """
    races = []
    for r in sorted(judged, key=lambda x: (x["date"], x["track"], x["raceNo"])):
        pools = {
            pool: [
                r["pools"][pool]["staked"],
                r["pools"][pool]["hit"],
                round(r["pools"][pool]["returnKrw"]),
            ]
            for pool, _ in POOL_DEFS
        }
        races.append(
            {
                "date": r["date"],
                "track": r["track"],
                "raceNo": r["raceNo"],
                "confidence": r["confidence"],
                "picks": r["picks"],
                "actual": r["actual"],
                "pools": pools,
            }
        )
    path = data_dir / "stats" / "backtest_races.json"
    doc = {"schemaVersion": 1, "models": []}
    if path.exists():
        doc = json.loads(path.read_text("utf-8"))
    doc["models"] = [m for m in doc.get("models", []) if m["version"] != version]
    doc["models"].append({"version": version, "races": races})
    doc["models"].sort(key=lambda m: m["version"])
    errors = validation_errors("backtest_races", doc)
    if errors:
        raise ValueError(f"backtest_races 스키마 오류: {errors[:3]}")
    write_json_if_changed(path, doc)


def write_backtest(entry: dict, *, data_dir: Path = DATA_DIR) -> None:
    """models 배열에 같은 version 항목을 교체 삽입한다 (v2 추가 대비)."""
    path = data_dir / "stats" / "backtest.json"
    doc = {"schemaVersion": 1, "models": []}
    if path.exists():
        doc = json.loads(path.read_text("utf-8"))
    doc["models"] = [
        m for m in doc.get("models", []) if m["version"] != entry["version"]
    ]
    doc["models"].append(entry)
    doc["models"].sort(key=lambda m: m["version"])
    errors = validation_errors("backtest", doc)
    if errors:
        raise ValueError(f"backtest 스키마 오류: {errors[:3]}")
    write_json_if_changed(path, doc)
