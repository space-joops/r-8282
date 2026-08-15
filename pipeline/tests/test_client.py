import json

import pytest

from kra_predict.api.client import (
    KraApiError,
    KraAuthError,
    _params_key,
    normalize_items,
    parse_payload,
)


def test_parse_payload_json_ok():
    text = json.dumps(
        {
            "response": {
                "header": {"resultCode": "00", "resultMsg": "NORMAL SERVICE."},
                "body": {"items": {"item": [{"a": 1}]}, "totalCount": 1},
            }
        }
    )
    body = parse_payload(text)
    assert normalize_items(body) == [{"a": 1}]


def test_parse_payload_single_item_dict():
    text = json.dumps(
        {
            "response": {
                "header": {"resultCode": "00"},
                "body": {"items": {"item": {"a": 1}}, "totalCount": 1},
            }
        }
    )
    assert normalize_items(parse_payload(text)) == [{"a": 1}]


def test_parse_payload_nodata():
    text = json.dumps(
        {
            "response": {
                "header": {"resultCode": "03", "resultMsg": "NODATA_ERROR"},
                "body": {"items": "", "totalCount": 0},
            }
        }
    )
    assert normalize_items(parse_payload(text)) == []


def test_parse_payload_xml_fallback():
    text = (
        "<response><header><resultCode>00</resultCode></header>"
        "<body><items><item><hrnm>바람</hrnm></item></items>"
        "<totalCount>1</totalCount></body></response>"
    )
    assert normalize_items(parse_payload(text)) == [{"hrnm": "바람"}]


def test_parse_payload_gateway_error():
    text = json.dumps(
        {
            "OpenAPI_ServiceResponse": {
                "cmmMsgHeader": {
                    "errMsg": "SERVICE_KEY_IS_NOT_REGISTERED_ERROR",
                    "returnReasonCode": "30",
                }
            }
        }
    )
    with pytest.raises(KraAuthError):
        parse_payload(text)


def test_parse_payload_result_error():
    text = json.dumps(
        {"response": {"header": {"resultCode": "99", "resultMsg": "oops"}, "body": {}}}
    )
    with pytest.raises(KraApiError):
        parse_payload(text)


def test_service_key_accepts_encoding_key(monkeypatch):
    from kra_predict.config import service_key

    raw = "abc+def/ghi=="
    monkeypatch.setenv("KRA_SERVICE_KEY", raw)
    assert service_key() == raw
    # data.go.kr 'Encoding' 키 (1회 인코딩)
    monkeypatch.setenv("KRA_SERVICE_KEY", "abc%2Bdef%2Fghi%3D%3D")
    assert service_key() == raw
    # 실수로 이중 인코딩된 키
    monkeypatch.setenv("KRA_SERVICE_KEY", "abc%252Bdef%252Fghi%253D%253D")
    assert service_key() == raw


def test_online_mode_ignores_fixtures(tmp_path, monkeypatch):
    """픽스처는 오프라인 전용 — 온라인 모드에선 실 요청을 시도해야 한다."""
    from kra_predict.api.client import KraClient
    from kra_predict.api.endpoints import RACE_PLAN

    fixture = tmp_path / "fixtures" / RACE_PLAN.name / "meet=1_numOfRows=100_pageNo=1_rc_date=20990101.json"
    fixture.parent.mkdir(parents=True)
    fixture.write_text('{"response":{"header":{"resultCode":"00"},"body":{"items":{"item":[{"rcNo":1}]},"totalCount":1}}}', "utf-8")

    client = KraClient(
        "dummy", cache_dir=tmp_path / "cache", fixtures_dir=tmp_path / "fixtures"
    )
    called = {}

    def fake_request(endpoint, params):
        called["yes"] = True
        return '{"response":{"header":{"resultCode":"03"},"body":{}}}'

    monkeypatch.setattr(client, "_request", fake_request)
    assert client.get_items(RACE_PLAN, meet=1, rc_date="20990101") == []
    assert called.get("yes"), "온라인 모드가 픽스처를 읽고 실 요청을 생략했다"
    client.close()


def test_params_key_sorted_and_safe():
    key = _params_key({"rc_date": "20260815", "meet": 1, "pageNo": 1, "numOfRows": 100})
    assert key == "meet=1_numOfRows=100_pageNo=1_rc_date=20260815.json"
    assert _params_key({"hr_name": "바람의질주", "rccrs_cd": 1}) == (
        "hr_name=바람의질주_rccrs_cd=1.json"
    )
