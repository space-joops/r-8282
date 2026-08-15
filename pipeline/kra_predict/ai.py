"""AI CLI(claude -p) 분석 결합.

통계 예측이 축이고 AI는 보정만 한다:
- score 보정(delta)은 ±MAX_DELTA로 클램핑 → softmax·순위 재계산
- 호출 실패·파싱 실패 시 1회 재시도 후 통계 단독으로 폴백 (예측 산출은 항상 보장)
"""

from __future__ import annotations

import json
import logging
import math
import re
import subprocess

from kra_predict.config import PIPELINE_DIR
from kra_predict.score import SOFTMAX_TEMP

logger = logging.getLogger(__name__)

PROMPT_PATH = PIPELINE_DIR / "prompts" / "race_analysis.md"
MAX_DELTA = 0.08
TIMEOUT_SEC = 180
TRACK_NAMES = {"seoul": "서울", "busan": "부산경남", "jeju": "제주"}


def run_claude(prompt: str, model: str | None, timeout: float = TIMEOUT_SEC) -> str:
    """claude -p 호출 → 결과 텍스트. 실패 시 예외."""
    cmd = ["claude", "-p", "--output-format", "json", "--max-turns", "1"]
    if model:
        cmd += ["--model", model]
    proc = subprocess.run(
        cmd,
        input=prompt,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=True,
    )
    envelope = json.loads(proc.stdout)
    if envelope.get("is_error"):
        raise RuntimeError(f"claude 오류 응답: {str(envelope.get('result'))[:200]}")
    return str(envelope.get("result", ""))


def _parse_analysis(text: str) -> dict:
    """코드펜스를 벗겨 JSON 계약을 파싱·검증한다."""
    stripped = text.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*\})\s*```", stripped, re.S)
    if fence:
        stripped = fence.group(1)
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start < 0 or end < 0:
        raise ValueError("JSON 객체를 찾지 못함")
    data = json.loads(stripped[start : end + 1])

    if not isinstance(data.get("commentary"), str) or not data["commentary"].strip():
        raise ValueError("commentary 누락")
    if data.get("confidence") not in ("high", "medium", "low"):
        data["confidence"] = None
    for key in ("perHorse", "adjustments"):
        if not isinstance(data.get(key), list):
            data[key] = []
    return data


def _entries_table(race: dict) -> str:
    lines = [
        "| 마번 | 마명 | 성별/연령 | 레이팅 | 부담중량 | 마체중(증감) | 1년 성적(출-1-2-3) | 기수 | 조교사 | 기수변경 |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for e in race["entries"]:
        rec = e["record1y"]
        rec_str = (
            f"{rec['starts']}-{rec['wins']}-{rec['seconds']}-{rec['thirds']}"
            if rec
            else "-"
        )
        body = (
            f"{e['bodyWeightKg']:g}({e['bodyWeightDiffKg']:+g})"
            if e["bodyWeightKg"] is not None and e["bodyWeightDiffKg"] is not None
            else "-"
        )
        lines.append(
            f"| {e['gateNo']} | {e['horseName']} | {e['sex']}{e['age']} "
            f"| {e['rating'] if e['rating'] is not None else '-'} "
            f"| {e['weightCarriedKg'] if e['weightCarriedKg'] is not None else '-'} "
            f"| {body} | {rec_str} | {e['jockey']['name']} | {e['trainer']['name']} "
            f"| {'O' if e['jockeyChanged'] else ''} |"
        )
    return "\n".join(lines)


def _build_prompt(race: dict) -> str:
    template = PROMPT_PATH.read_text("utf-8")
    pred = race["prediction"]
    race_info = (
        f"{race['date']} {TRACK_NAMES.get(race['track'], race['track'])} "
        f"{race['raceNo']}경주 · {race['distanceM']}m · {race['grade']}"
        f" · 발주 {race['startTimeKst']}"
    )
    rankings = "\n".join(
        f"{r['predictedRank']}위 {r['gateNo']}번 (score {r['score']:.2f}, "
        f"winProb {r['winProb']:.0%}) {r['briefComment'] or ''}"
        for r in pred["rankings"]
    )
    return template.format(
        race_info=race_info,
        entries_table=_entries_table(race),
        stat_rankings=rankings,
        stat_version=pred["model"]["statVersion"],
    )


def _apply_analysis(race: dict, analysis: dict, model_label: str) -> None:
    """AI 보정을 클램핑해 반영하고 순위·winProb·topPicks를 재계산한다."""
    pred = race["prediction"]
    deltas: dict[int, float] = {}
    for adj in analysis["adjustments"]:
        gate = adj.get("gateNo")
        try:
            delta = float(adj.get("delta", 0))
        except (TypeError, ValueError):
            continue
        if isinstance(gate, int):
            deltas[gate] = max(-MAX_DELTA, min(MAX_DELTA, delta))

    comments = {
        p["gateNo"]: str(p.get("briefComment", "")).strip()
        for p in analysis["perHorse"]
        if isinstance(p.get("gateNo"), int)
    }

    rankings = [dict(r) for r in pred["rankings"]]
    for row in rankings:
        row["score"] = round(
            max(0.0, min(1.0, row["score"] + deltas.get(row["gateNo"], 0.0))), 4
        )
        ai_comment = comments.get(row["gateNo"])
        if ai_comment:
            row["briefComment"] = ai_comment

    exps = [math.exp(r["score"] / SOFTMAX_TEMP) for r in rankings]
    denom = sum(exps)
    for row, exp in zip(rankings, exps):
        row["winProb"] = round(exp / denom, 4)
    rankings.sort(key=lambda r: r["winProb"], reverse=True)
    for rank, row in enumerate(rankings, start=1):
        row["predictedRank"] = rank

    pred["rankings"] = rankings
    pred["aiCommentary"] = analysis["commentary"].strip()
    if analysis.get("confidence"):
        pred["confidence"] = analysis["confidence"]
    pred["model"]["aiModel"] = model_label
    pred["topPicks"] = {
        "win": rankings[0]["gateNo"],
        "place": [r["gateNo"] for r in rankings[:3]],
        "exacta": [rankings[0]["gateNo"], rankings[1]["gateNo"]]
        if len(rankings) > 1
        else None,
    }


def enrich_predictions(
    races: list[dict],
    *,
    model: str | None = None,
    runner=run_claude,
    retries: int = 1,
) -> tuple[int, int]:
    """예측이 있는 각 경주에 AI 분석을 결합한다. 반환: (성공, 폴백) 경주 수."""
    ok = fallback = 0
    for race in races:
        if not race.get("prediction") or not race.get("entries"):
            continue
        prompt = _build_prompt(race)
        analysis = None
        for attempt in range(retries + 1):
            try:
                analysis = _parse_analysis(runner(prompt, model))
                break
            except Exception as e:  # noqa: BLE001 — 어떤 실패든 통계 단독 폴백
                logger.warning(
                    "%s %d경주 AI 분석 실패(%d/%d): %s",
                    race["track"],
                    race["raceNo"],
                    attempt + 1,
                    retries + 1,
                    e,
                )
        if analysis is None:
            fallback += 1
            continue
        _apply_analysis(race, analysis, model or "claude-cli")
        ok += 1
    return ok, fallback
