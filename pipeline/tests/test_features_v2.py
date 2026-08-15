"""신규 승인 API 통합(#22) 매핑 헬퍼 테스트."""

from kra_predict.features import (
    _dash_none,
    _entry_from_chulma,
    _int_loose,
    _race_no_of,
    _rating,
)
from kra_predict.fetch import _stats_map


def test_int_loose():
    assert _int_loose("제1경주") == 1
    assert _int_loose("제10경주") == 10
    assert _int_loose(3) == 3
    assert _int_loose("") is None


def test_race_no_of_prefers_race_no():
    assert _race_no_of({"raceNo": "제2경주"}) == 2
    assert _race_no_of({"rcNo": 5}) == 5


def test_rating_paren_and_zero():
    assert _rating("()") is None
    assert _rating("(45)") == 45
    assert _rating(0) is None
    assert _rating(52.5) == 52.5


def test_dash_none():
    assert _dash_none("-") is None
    assert _dash_none(" ") is None
    assert _dash_none("맑음") == "맑음"


def test_entry_from_chulma():
    row = {
        "gtno": 3,
        "hrnm": "봉봉티아라",
        "hrsAg": 2,
        "gndrNm": "암",
        "rating": "()",
        "burdWgt": 52.5,
        "wgtIndec": -1,
        "jckyNm": "이혁",
        "trarNm": "토니",
        "raceNo": "제1경주",
    }
    entry = _entry_from_chulma(row)
    assert entry["gateNo"] == 3
    assert entry["horseName"] == "봉봉티아라"
    assert entry["sex"] == "암"
    assert entry["rating"] is None
    assert entry["weightCarriedKg"] == 52.5
    assert entry["bodyWeightDiffKg"] == -1
    assert entry["jockey"]["name"] == "이혁"
    assert entry["trainer"]["name"] == "토니"


def test_stats_map():
    rows = [
        {"jkName": "이혁", "jkNo": "080001", "rcCntY": 372, "ord1CntY": 48},
        {"jkName": "무출전", "jkNo": "080002", "rcCntY": 0, "ord1CntY": 0},
    ]
    stats = _stats_map(rows, "jkName", "jkNo")
    assert stats["이혁"] == {"id": "080001", "winRate1y": 0.129}
    assert stats["무출전"]["winRate1y"] is None
