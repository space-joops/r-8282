"""재실행 멱등성 — 내용이 같으면(휘발성 타임스탬프 제외) 파일을 다시 쓰지 않는다.

cron 자동 운영(#23)의 전제: 변경 없는 재실행이 자동 커밋을 만들지 않아야 한다.
"""

import json

from kra_predict.emit import write_json_if_changed


def test_skips_write_when_only_volatile_keys_differ(tmp_path):
    path = tmp_path / "x.json"
    write_json_if_changed(
        path, {"updatedAt": "T1", "value": 1, "nested": {"fetchedAt": "T1", "a": 2}}
    )
    before = path.read_text("utf-8")

    changed = write_json_if_changed(
        path, {"updatedAt": "T2", "value": 1, "nested": {"fetchedAt": "T2", "a": 2}}
    )
    assert changed is False
    assert path.read_text("utf-8") == before  # 타임스탬프까지 기존 값 유지


def test_writes_when_content_differs(tmp_path):
    path = tmp_path / "x.json"
    write_json_if_changed(path, {"updatedAt": "T1", "value": 1})
    changed = write_json_if_changed(path, {"updatedAt": "T2", "value": 2})
    assert changed is True
    assert json.loads(path.read_text("utf-8"))["value"] == 2


def test_volatile_stripped_recursively_in_lists(tmp_path):
    path = tmp_path / "x.json"
    write_json_if_changed(path, {"rows": [{"generatedAt": "T1", "gate": 1}]})
    changed = write_json_if_changed(path, {"rows": [{"generatedAt": "T2", "gate": 1}]})
    assert changed is False
