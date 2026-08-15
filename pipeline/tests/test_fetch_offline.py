"""커밋된 픽스처만으로 개최일 번들 수집이 완주하는지 검증한다."""

import pytest

from kra_predict.api.client import KraClient
from kra_predict.fetch import fetch_meet_bundle

DATE = "2026-08-15"


@pytest.fixture()
def client():
    c = KraClient(offline=True)
    yield c
    c.close()


def test_offline_bundle(client):
    bundle = fetch_meet_bundle(client, DATE)

    assert [r["rcNo"] for r in bundle["plan"]["seoul"]] == [1, 5]
    assert len(bundle["plan"]["jeju"]) == 1
    assert bundle["plan"]["busan"] == []  # NODATA 픽스처

    assert len(bundle["entries"]["seoul"]) == 13  # 7 + 6
    assert len(bundle["entries"]["jeju"]) == 6  # chulmainfo 픽스처
    assert bundle["entries"]["busan"] == []  # 픽스처 없음 → 빈 응답

    assert set(bundle["weights"]["seoul"].keys()) == {"1", "5"}
    assert len(bundle["weights"]["seoul"]["1"]) == 7

    assert len(bundle["horse1y"]["seoul"]) == 13
    assert bundle["horse1y"]["seoul"]["바람의질주"]["loyPtinTcnt"] == 8

    assert len(bundle["jockeyChanges"]["seoul"]) == 1
    assert bundle["jockeyChanges"]["seoul"][0]["hrName"] == "은빛파도"

    assert len(bundle["results"]["seoul"]) == 7
    assert bundle["results"]["seoul"][0]["ord"] == 1

    # 오프라인 모드에선 HTTP 호출이 없어야 한다
    assert client.http_calls == 0
