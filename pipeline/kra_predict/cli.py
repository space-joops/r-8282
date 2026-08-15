"""kra-predict CLI (typer).

이슈 #2 시점에는 fetch만 제공한다. predict/results/accuracy/validate는
이슈 #3·#4·#6에서 추가된다.
"""

from __future__ import annotations

import json
import logging
import re

import typer

from kra_predict import config
from kra_predict.api.client import KraClient
from kra_predict.fetch import fetch_meet_bundle, summarize_bundle

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


if __name__ == "__main__":
    app()
