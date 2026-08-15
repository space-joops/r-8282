from kra_predict.backtest import (
    AsOfStats,
    _bucket,
    _odds,
    build_backtest_races,
    month_list_with_history,
    simulate,
)


def test_month_list_with_history_covers_12_months_back():
    months = month_list_with_history(["2026-07", "2026-08"])
    assert months[0] == "2025-07"
    assert months[-1] == "2026-08"
    assert len(months) == 14


def test_odds_invalid_marker():
    assert _odds(9999.9) is None
    assert _odds("2.6") == 2.6
    assert _odds(None) is None


def test_asof_window_excludes_race_day_and_older_than_year():
    stats = AsOfStats()
    stats.add("h1", "2025-06-30", 1)  # 1년 밖
    stats.add("h1", "2025-08-01", 2)
    stats.add("h1", "2026-07-04", 1)  # 당일 — 미포함이어야 함 (누수 방지)
    stats.freeze()
    window = stats.window("h1", "2026-07-04")
    assert window == [2]
    assert stats.last_run_before("h1", "2026-07-04") == "2025-08-01"


def _row(date, rc_no, chul, ord_, *, meet="서울", hr=None, win=3.0, plc=1.5):
    return {
        "meet": meet,
        "rcDate": date,
        "rcNo": rc_no,
        "chulNo": chul,
        "ord": ord_,
        "hrNo": hr or f"h{chul}",
        "hrName": f"말{chul}",
        "jkNo": f"j{chul}",
        "trNo": f"t{chul}",
        "age": 3,
        "sex": "수",
        "rating": 40 + chul,
        "wgBudam": 55,
        "wgHr": "480(+2)",
        "winOdds": win,
        "plcOdds": plc,
    }


def test_broken_ord_races_are_excluded():
    # 5두 완주 정상 경주 + 상위 3착만 기록된 비정상 경주
    rows = [_row(20260705, 1, c, c) for c in range(1, 6)]
    rows += [_row(20260705, 2, c, c if c <= 3 else 0) for c in range(1, 9)]
    races = build_backtest_races(rows, ["2026-07"])
    assert len(races) == 1
    assert races[0]["raceNo"] == 1


def test_features_are_as_of_and_thirds_counted():
    # 과거 이력: h1이 6월에 3착 1회
    rows = [_row(20260601, 1, c, c) for c in range(1, 6)]  # h3이 3착
    rows += [_row(20260705, 1, c, 6 - c) for c in range(1, 6)]  # 타깃 경주
    races = build_backtest_races(rows, ["2026-07"])
    assert len(races) == 1
    entry_h3 = next(e for e in races[0]["entries"] if e["horseId"] == "h3")
    assert entry_h3["record1y"] == {"starts": 1, "wins": 0, "seconds": 0, "thirds": 1}
    # 당일 경주 결과는 스탯에 미포함 (6월 1회만)
    entry_h1 = next(e for e in races[0]["entries"] if e["horseId"] == "h1")
    assert entry_h1["record1y"]["starts"] == 1


def test_simulate_and_roi_math():
    rows = [_row(20260601, 1, c, c) for c in range(1, 6)]
    rows += [
        _row(20260705, 1, 1, 1, win=4.0, plc=1.5),
        _row(20260705, 1, 2, 2, win=9999.9, plc=1.2),
        _row(20260705, 1, 3, 3),
        _row(20260705, 1, 4, 4),
        _row(20260705, 1, 5, 5),
    ]
    races = build_backtest_races(rows, ["2026-07"])
    judged = simulate(races)
    assert len(judged) == 1
    j = judged[0]
    assert j["logLoss"] > 0
    bucket = _bucket(judged)
    assert bucket["races"] == 1
    # 픽이 1번(우승)이면 ROI = 4.0 - 1, 아니면 -1 또는 연승 계산 — 수학 일관성만 확인
    if j["winHit"]:
        assert bucket["roiWin"] == 3.0
    elif j["stakeWin"]:
        assert bucket["roiWin"] == -1.0
    else:
        assert bucket["roiWin"] is None
