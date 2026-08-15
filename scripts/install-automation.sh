#!/usr/bin/env bash
# systemd user timer 설치 — 노트북(우분투)용 운영 자동화.
# 실행: scripts/install-automation.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UNIT_DIR="$HOME/.config/systemd/user"

mkdir -p "$UNIT_DIR"
cp "$SCRIPT_DIR"/systemd/kyongma-*.service "$SCRIPT_DIR"/systemd/kyongma-*.timer "$UNIT_DIR/"

systemctl --user daemon-reload
systemctl --user enable --now kyongma-predict.timer kyongma-results.timer

# 로그인 세션이 없어도(화면 잠금·재부팅 직후) 타이머가 돌도록
loginctl enable-linger "$USER"

echo
echo "✓ 설치 완료. 예정된 실행:"
systemctl --user list-timers kyongma-\* --no-pager
echo
echo "로그 보기:  journalctl --user -u kyongma-predict -u kyongma-results -e"
echo "수동 실행:  systemctl --user start kyongma-results.service"
echo "해제:       systemctl --user disable --now kyongma-predict.timer kyongma-results.timer"
