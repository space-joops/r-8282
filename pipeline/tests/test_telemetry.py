import httpx
import pytest
import typer

from kra_predict import telemetry


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for key in ("SUPABASE_URL", "SUPABASE_SERVICE_KEY", "SUPABASE_SERVICE_ROLE_KEY", "OPS_RUN_SOURCE"):
        monkeypatch.delenv(key, raising=False)


def _set_env(monkeypatch, key_name="SUPABASE_SERVICE_KEY"):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv(key_name, "sb_secret_test")


def test_record_run_skips_without_env(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("env 없이 HTTP 호출 금지")

    monkeypatch.setattr(httpx, "post", boom)
    assert telemetry.record_run({"kind": "predict"}) is False


def test_record_run_posts_payload(monkeypatch):
    _set_env(monkeypatch)
    captured = {}

    def fake_post(url, *, json, headers, timeout):
        captured.update(url=url, json=json, headers=headers)
        return httpx.Response(201, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "post", fake_post)
    assert telemetry.record_run({"kind": "results", "status": "success"}) is True
    assert captured["url"] == "https://example.supabase.co/rest/v1/kyongma_ops_runs"
    assert captured["headers"]["apikey"] == "sb_secret_test"
    assert captured["headers"]["Authorization"] == "Bearer sb_secret_test"
    assert captured["json"]["kind"] == "results"


def test_record_run_accepts_vercel_env_name(monkeypatch):
    _set_env(monkeypatch, key_name="SUPABASE_SERVICE_ROLE_KEY")
    monkeypatch.setattr(
        httpx,
        "post",
        lambda url, **k: httpx.Response(201, request=httpx.Request("POST", url)),
    )
    assert telemetry.record_run({"kind": "predict"}) is True


def test_record_run_fail_soft(monkeypatch, caplog):
    _set_env(monkeypatch)

    def fail(*a, **k):
        raise httpx.ConnectError("no network")

    monkeypatch.setattr(httpx, "post", fail)
    assert telemetry.record_run({"kind": "predict"}) is False  # 예외 없이 False


def test_record_run_http_error_is_soft(monkeypatch):
    _set_env(monkeypatch)
    monkeypatch.setattr(
        httpx,
        "post",
        lambda url, **k: httpx.Response(
            401, text="denied", request=httpx.Request("POST", url)
        ),
    )
    assert telemetry.record_run({"kind": "predict"}) is False


def _capture_runs(monkeypatch):
    rows = []
    monkeypatch.setattr(telemetry, "record_run", lambda p: rows.append(p) or True)
    return rows


def test_track_success_and_metrics(monkeypatch):
    rows = _capture_runs(monkeypatch)
    with telemetry.track("predict", "2026-08-16") as run:
        run.status = "no_change"
        run.metrics = {"changed": 0}
    assert len(rows) == 1
    row = rows[0]
    assert row["kind"] == "predict"
    assert row["target_date"] == "2026-08-16"
    assert row["status"] == "no_change"
    assert row["metrics"] == {"changed": 0}
    assert row["source"] == "manual"
    assert row["duration_sec"] >= 0


def test_track_records_error_and_reraises(monkeypatch):
    rows = _capture_runs(monkeypatch)
    with pytest.raises(ValueError):
        with telemetry.track("results", "2026-08-16"):
            raise ValueError("boom")
    assert rows[0]["status"] == "error"
    assert "boom" in rows[0]["error"]


def test_track_keeps_explicit_status_on_typer_exit(monkeypatch):
    rows = _capture_runs(monkeypatch)
    with pytest.raises(typer.Exit):
        with telemetry.track("predict", "2026-08-21") as run:
            run.status = "no_races"
            raise typer.Exit(1)
    assert rows[0]["status"] == "no_races"
    assert rows[0]["error"] is None


def test_track_disabled_records_nothing(monkeypatch):
    rows = _capture_runs(monkeypatch)
    with telemetry.track("predict", "2026-08-16", enabled=False):
        pass
    assert rows == []


def test_track_source_from_env(monkeypatch):
    rows = _capture_runs(monkeypatch)
    monkeypatch.setenv("OPS_RUN_SOURCE", "timer")
    with telemetry.track("results", "2026-08-16"):
        pass
    assert rows[0]["source"] == "timer"
