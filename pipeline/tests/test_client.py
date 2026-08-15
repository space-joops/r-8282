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


def test_params_key_sorted_and_safe():
    key = _params_key({"rc_date": "20260815", "meet": 1, "pageNo": 1, "numOfRows": 100})
    assert key == "meet=1_numOfRows=100_pageNo=1_rc_date=20260815.json"
    assert _params_key({"hr_name": "바람의질주", "rccrs_cd": 1}) == (
        "hr_name=바람의질주_rccrs_cd=1.json"
    )
