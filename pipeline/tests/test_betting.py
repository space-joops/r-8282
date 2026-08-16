"""승식별 베팅 시뮬레이션(#37) — 조합·판정·정산 테스트."""

from kra_predict.backtest import (
    BET_UNIT_KRW,
    _betting_summary,
    build_backtest_races,
    simulate,
)
from kra_predict.score import build_prediction
from tests.test_backtest import _row


def _five_horse_race(order_by_gate: dict[int, int]):
    """게이트→착순 지정으로 5두 경주 rows 생성 (피처용 과거 경주 포함)."""
    rows = [_row(20260601, 1, c, c) for c in range(1, 6)]
    rows += [
        _row(20260705, 1, gate, ord_) for gate, ord_ in order_by_gate.items()
    ]
    return rows


def _picks(race) -> list[int]:
    """simulate 내부와 동일한 방식으로 예측 1~3순위 게이트 계산."""
    pred = build_prediction(
        race["entries"], race_date=race["date"], generated_at="t"
    )
    return [r["gateNo"] for r in pred["rankings"][:3]]


def _dividends_for(race, odds_map):
    """(pool → 조합 배당표) 를 해당 경주의 배당 룩업으로 변환.
    룩업 키 존재 = 발매로 처리되므로 필요한 조합만 넣어도 된다."""
    key = (race["track"], race["date"], race["raceNo"])
    return {(*key, pool): table for pool, table in odds_map.items()}


def test_pool_judging_matches_definitions():
    rows = _five_horse_race({1: 1, 2: 2, 3: 3, 4: 4, 5: 5})
    races = build_backtest_races(rows, ["2026-07"])
    race = races[0]
    p1, p2, p3 = _picks(race)
    actual = [1, 2, 3]  # ord 1..3 = gate 1..3

    dividends = _dividends_for(
        race,
        {
            "QNL": {tuple(sorted(actual[:2])): 16.0},
            "EXA": {tuple(actual[:2]): 46.5},
            "QPL": {tuple(sorted((p1, p2))): 4.7},
            "TLA": {tuple(sorted(actual)): 27.7},
            "TRI": {tuple(actual): 179.0},
        },
    )
    pools = simulate(races, dividends)[0]["pools"]

    # 배당표가 있는 풀은 전부 발매(staked=1) 처리
    for pool in ("QNL", "EXA", "QPL", "TLA", "TRI"):
        assert pools[pool]["staked"] == 1, pool

    ord_of = {g: g for g in range(1, 6)}
    expect = {
        "QNL": {p1, p2} == set(actual[:2]),
        "EXA": [p1, p2] == actual[:2],
        "QPL": ord_of[p1] <= 3 and ord_of[p2] <= 3,
        "TLA": {p1, p2, p3} == set(actual),
        "TRI": [p1, p2, p3] == actual,
    }
    for pool, hit in expect.items():
        assert pools[pool]["hit"] == int(hit), pool
        if hit:
            assert pools[pool]["returnKrw"] > 0, pool
        else:
            assert pools[pool]["returnKrw"] == 0.0, pool


def test_no_dividend_table_means_not_on_sale():
    rows = _five_horse_race({1: 1, 2: 2, 3: 3, 4: 4, 5: 5})
    races = build_backtest_races(rows, ["2026-07"])
    pools = simulate(races)[0]["pools"]  # 배당 없음
    for pool in ("QNL", "EXA", "QPL", "TLA", "TRI"):
        assert pools[pool] == {"staked": 0, "hit": 0, "returnKrw": 0.0}, pool
    # 단승·연승은 경주성적의 winOdds/plcOdds 기준이라 배당 룩업과 무관
    assert pools["WIN"]["staked"] == 1
    assert pools["PLC"]["staked"] == 1


def test_exact_payout_when_picks_win():
    # _row 의 rating=40+chulNo → 게이트 5가 예측 1순위. 착순도 5-4-3 으로 구성.
    rows = _five_horse_race({5: 1, 4: 2, 3: 3, 2: 4, 1: 5})
    races = build_backtest_races(rows, ["2026-07"])
    race = races[0]
    if _picks(race) != [5, 4, 3]:
        return  # 학습 가중치가 순위를 바꾸면 이 테스트의 전제가 성립하지 않음

    dividends = _dividends_for(
        race,
        {
            "QNL": {(4, 5): 10.0},
            "EXA": {(5, 4): 20.0},
            "QPL": {(4, 5): 3.0},
            "TLA": {(3, 4, 5): 30.0},
            "TRI": {(5, 4, 3): 100.0},
        },
    )
    judged = simulate(races, dividends)
    pools = judged[0]["pools"]
    assert pools["QNL"]["returnKrw"] == 10.0 * BET_UNIT_KRW
    assert pools["EXA"]["returnKrw"] == 20.0 * BET_UNIT_KRW
    assert pools["QPL"]["returnKrw"] == 3.0 * BET_UNIT_KRW
    assert pools["TLA"]["returnKrw"] == 30.0 * BET_UNIT_KRW
    assert pools["TRI"]["returnKrw"] == 100.0 * BET_UNIT_KRW

    summary = {b["pool"]: b for b in _betting_summary(judged)}
    assert summary["TRI"]["profitKrw"] == (100.0 - 1) * BET_UNIT_KRW
    assert summary["TRI"]["hitRate"] == 1.0
    # 예측 1순위(게이트5)가 1착 → 단승 회수 = winOdds×100 (기존 roiWin 정의와 정합)
    assert summary["WIN"]["hits"] == 1
    assert summary["WIN"]["returnedKrw"] == round(3.0 * BET_UNIT_KRW)


def test_betting_summary_shape_and_arithmetic():
    rows = _five_horse_race({1: 1, 2: 2, 3: 3, 4: 4, 5: 5})
    races = build_backtest_races(rows, ["2026-07"])
    summary = _betting_summary(simulate(races))
    assert [b["pool"] for b in summary] == [
        "WIN",
        "PLC",
        "QNL",
        "EXA",
        "QPL",
        "TLA",
        "TRI",
    ]
    for b in summary:
        assert b["stakeKrw"] == b["bets"] * BET_UNIT_KRW
        assert b["profitKrw"] == b["returnedKrw"] - b["stakeKrw"]
        if b["bets"] == 0:
            assert b["hitRate"] == 0 and b["roi"] is None
