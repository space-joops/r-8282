"""kra-predict CLI (typer).

fetch / predict / validate 제공. results/accuracy는 이슈 #6에서 추가된다.
"""

from __future__ import annotations

import json
import logging
import re

import typer

from kra_predict import config, telemetry
from kra_predict.api.client import KraClient
from kra_predict.accuracy import recompute_accuracy
from kra_predict.emit import (
    emit_races,
    now_kst_iso,
    rebuild_meet_and_index,
    validate_tree,
)
from kra_predict.features import assemble_races
from kra_predict.fetch import (
    fetch_meet_bundle,
    fetch_results_bundle,
    summarize_bundle,
)
from kra_predict.results import apply_results
from kra_predict.score import build_prediction

app = typer.Typer(help="한국경마 예측 데이터 파이프라인")

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _validate_date(date: str) -> str:
    if not DATE_RE.match(date):
        raise typer.BadParameter("날짜는 YYYY-MM-DD 형식이어야 합니다")
    return date


def make_client(
    fixtures: bool, refresh: bool = False, record_fixtures: bool = False
) -> KraClient:
    return KraClient(
        None if fixtures else config.service_key(),
        offline=fixtures,
        refresh=refresh,
        record_fixtures=record_fixtures,
    )


@app.callback()
def main(verbose: bool = typer.Option(False, "--verbose", "-v")) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )
    # httpx INFO 로그는 요청 URL(인증키 포함)을 노출하므로 항상 억제한다
    logging.getLogger("httpx").setLevel(logging.WARNING)


@app.command()
def fetch(
    date: str = typer.Option(..., "--date", callback=_validate_date, help="개최일 (YYYY-MM-DD)"),
    fixtures: bool = typer.Option(
        False, "--fixtures", help="네트워크 없이 pipeline/fixtures만 사용"
    ),
    refresh: bool = typer.Option(False, "--refresh", help="raw 캐시를 무시하고 재요청"),
    record_fixtures: bool = typer.Option(
        False, "--record-fixtures", help="실응답을 픽스처로도 저장"
    ),
) -> None:
    """개최일 raw 데이터를 수집해 .cache/bundle_<date>.json으로 저장한다."""
    client = make_client(fixtures, refresh, record_fixtures)
    try:
        bundle = fetch_meet_bundle(client, date)
    finally:
        client.close()

    out = config.CACHE_DIR / f"bundle_{date}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(bundle, ensure_ascii=False, indent=1), "utf-8")

    typer.echo(summarize_bundle(bundle))
    typer.echo(f"HTTP 호출 {client.http_calls}회 → {out}")


@app.command()
def predict(
    date: str = typer.Option(..., "--date", callback=_validate_date, help="개최일 (YYYY-MM-DD)"),
    fixtures: bool = typer.Option(False, "--fixtures", help="네트워크 없이 픽스처만 사용"),
    refresh: bool = typer.Option(False, "--refresh", help="raw 캐시 무시"),
    no_ai: bool = typer.Option(False, "--no-ai", help="AI 분석 없이 통계 단독"),
    ai_model: str = typer.Option(
        "", "--ai-model", help="claude CLI에 넘길 모델 (예: haiku, sonnet)"
    ),
    force: bool = typer.Option(
        False, "--force", help="결과가 확정된 경주의 예측도 덮어쓴다"
    ),
) -> None:
    """개최일 데이터를 수집·스코어링해 data/에 예측을 기록한다."""
    # --fixtures(오프라인 테스트)는 운영 이력에 남기지 않는다
    with telemetry.track("predict", date, enabled=not fixtures) as run:
        client = make_client(fixtures, refresh)
        try:
            bundle = fetch_meet_bundle(client, date)
        finally:
            client.close()

        races = assemble_races(bundle)
        if not races:
            run.status = "no_races"
            typer.echo("경주 편성이 없습니다 — 개최일이 맞는지 확인하세요.")
            raise typer.Exit(1)

        generated_at = now_kst_iso()
        for race in races:
            if race["entries"]:
                race["prediction"] = build_prediction(
                    race["entries"], race_date=race["date"], generated_at=generated_at
                )

        ok = fallback = 0
        if not no_ai:
            from kra_predict.ai import enrich_predictions

            ok, fallback = enrich_predictions(races, model=ai_model or None)
            typer.echo(f"AI 분석: 성공 {ok}경주 · 통계 단독 폴백 {fallback}경주")

        written, skipped, changed = emit_races(races, force=force)
        rebuild_meet_and_index()

        with_pred = sum(1 for r in races if r["prediction"] is not None)
        run.status = "success" if changed else "no_change"
        run.metrics = {
            "racesTotal": len(races),
            "withPrediction": with_pred,
            "aiOk": ok,
            "aiFallback": fallback,
            "written": len(written),
            "skippedFinal": len(skipped),
            "changed": changed,
            "httpCalls": client.http_calls,
        }
        typer.echo(
            f"예측 생성 {with_pred}/{len(races)}경주 · 기록 {len(written)}건 "
            f"(변경 {changed}건)"
        )
        if skipped:
            typer.echo(f"건너뜀(결과 확정): {', '.join(skipped)}")
        typer.echo("git diff로 data/ 변경을 검토한 뒤 커밋·push 하세요.")


@app.command()
def results(
    date: str = typer.Option(..., "--date", callback=_validate_date, help="개최일 (YYYY-MM-DD)"),
    fixtures: bool = typer.Option(False, "--fixtures", help="네트워크 없이 픽스처만 사용"),
    refresh: bool = typer.Option(False, "--refresh", help="raw 캐시 무시"),
) -> None:
    """경주 결과를 data/에 반영하고 적중률을 재계산한다 (prediction 불변)."""
    with telemetry.track("results", date, enabled=not fixtures) as run:
        client = make_client(fixtures, refresh)
        try:
            bundle = fetch_results_bundle(client, date)
        finally:
            client.close()

        applied, canceled, changed = apply_results(bundle)
        rebuild_meet_and_index()
        stats = recompute_accuracy()

        run.status = "success" if changed else "no_change"
        run.metrics = {
            "applied": applied,
            "canceled": canceled,
            "changed": changed,
            "httpCalls": client.http_calls,
            "accuracy": {
                "races": stats["overall"]["races"],
                "winRate": stats["overall"]["winRate"],
                "placeRate": stats["overall"]["placeRate"],
            },
        }
        typer.echo(f"결과 반영 {applied}경주 · 취소 {canceled}경주 (변경 {changed}건)")
        typer.echo(
            f"누적 적중률: 단승 {stats['overall']['winRate']:.1%} · "
            f"연승 {stats['overall']['placeRate']:.1%} ({stats['overall']['races']}경주)"
        )
        typer.echo("git diff로 data/ 변경을 검토한 뒤 커밋·push 하세요.")


@app.command()
def backtest(
    months: str = typer.Option(
        "2026-07,2026-08", "--months", help="쉼표 구분 YYYY-MM 목록"
    ),
    fixtures: bool = typer.Option(False, "--fixtures", help="네트워크 없이 픽스처만 사용"),
    refresh: bool = typer.Option(False, "--refresh", help="raw 캐시 무시"),
) -> None:
    """과거 경주에 통계 모델 v1을 적용해 성능을 측정하고 data/stats/backtest.json에 기록한다."""
    from kra_predict.backtest import (
        aggregate,
        build_backtest_races,
        fetch_detail_rows,
        month_list_with_history,
        simulate,
        write_backtest,
    )

    month_list = [m.strip() for m in months.split(",") if m.strip()]
    if not month_list or any(not re.match(r"^\d{4}-\d{2}$", m) for m in month_list):
        raise typer.BadParameter("months는 YYYY-MM 형식이어야 합니다")

    all_months = month_list_with_history(month_list)
    typer.echo(f"수집: {all_months[0]} ~ {all_months[-1]} (피처용 과거 12개월 포함)")
    client = make_client(fixtures, refresh)
    try:
        detail_rows = fetch_detail_rows(client, all_months)
    finally:
        client.close()

    races = build_backtest_races(detail_rows, month_list)
    judged = simulate(races)
    if not judged:
        typer.echo("평가할 경주가 없습니다 — 기간을 확인하세요.")
        raise typer.Exit(1)

    entry = aggregate(judged, month_list)
    write_backtest(entry)

    overall = entry["overall"]
    typer.echo(
        f"백테스트 {entry['version']} · {entry['periodFrom']}~{entry['periodTo']} · "
        f"{overall['races']}경주"
    )
    typer.echo(
        f"단승 {overall['winRate']:.1%} · 연승 {overall['placeRate']:.1%} · "
        f"log-loss {overall['logLoss']:.3f}"
    )
    typer.echo(
        f"ROI(1단위 베팅): 단승 {overall['roiWin']:+.1%} · 연승 {overall['roiPlace']:+.1%}"
    )
    typer.echo("data/stats/backtest.json 기록 완료 — diff 검토 후 커밋·push 하세요.")


@app.command()
def accuracy() -> None:
    """data/ 전체에서 적중률 통계를 재계산한다."""
    stats = recompute_accuracy()
    overall = stats["overall"]
    typer.echo(
        f"단승 {overall['winRate']:.1%} · 연승 {overall['placeRate']:.1%} · "
        f"삼복 정순 {overall['top3ExactHits']}회 ({overall['races']}경주)"
    )


@app.command()
def validate() -> None:
    """data/ 전체를 스키마·정합성 검증한다."""
    errors = validate_tree()
    if errors:
        for e in errors:
            typer.echo(f"✗ {e}")
        raise typer.Exit(1)
    typer.echo("✓ data/ 검증 통과")


if __name__ == "__main__":
    app()
