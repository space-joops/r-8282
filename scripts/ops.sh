#!/usr/bin/env bash
# 경마픽 자동 운영 스크립트 — systemd timer가 호출한다.
#   ops.sh predict : 오늘 개최 경주 예측 생성 → data/ 커밋·push
#   ops.sh results : 오늘+어제 결과 반영·적중률 갱신 → data/ 커밋·push
# 멱등 설계: 파이프라인이 내용 동일 시 파일을 쓰지 않으므로(휘발성 타임스탬프
# 무시) 변경 없는 실행은 커밋 없이 조용히 끝난다. 개최 없는 날도 정상 종료.
set -uo pipefail

CMD="${1:?사용법: ops.sh predict|results}"
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"

# systemd 환경엔 PATH가 최소만 있다 (uv·claude는 ~/.local/bin)
export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

TODAY="$(TZ=Asia/Seoul date +%F)"
YESTERDAY="$(TZ=Asia/Seoul date -d yesterday +%F)"

# 중복 실행 방지
exec 9>"/tmp/kyongmapick-ops.lock"
if ! flock -n 9; then
    echo "다른 ops 작업이 실행 중 — 종료"
    exit 0
fi

echo "== 경마픽 ops: $CMD ($TODAY, $(date '+%H:%M %Z'))"

# OPS_NO_GIT=1 이면 git 조작 없이 파이프라인만 실행 (테스트용)
if [ "${OPS_NO_GIT:-0}" != "1" ]; then
    if [ -n "$(git status --porcelain)" ]; then
        echo "작업 트리에 커밋되지 않은 변경이 있어 중단합니다 (수동 확인 필요)"
        exit 1
    fi
    git checkout -q main
    git pull --rebase -q origin main || echo "git pull 실패 — 로컬 상태로 진행"
fi

case "$CMD" in
predict)
    # 개최 없는 날은 predict가 rc=1로 끝난다 — 실패로 취급하지 않음
    make predict DATE="$TODAY" FLAGS="--ai-model haiku" \
        || echo "predict 종료 rc=$? (개최 없음이거나 오류 — 로그 확인)"
    ;;
results)
    # raw 캐시가 미확정 결과를 물고 있을 수 있어 --refresh 필수.
    # 어제 것도 재실행해 늦게 확정되는 경주를 쓸어담는다.
    for D in "$TODAY" "$YESTERDAY"; do
        make results DATE="$D" FLAGS="--refresh" \
            || echo "results $D 종료 rc=$? (개최 없음이거나 오류)"
    done
    ;;
*)
    echo "알 수 없는 명령: $CMD"
    exit 2
    ;;
esac

(cd pipeline && uv run kra-predict validate) || {
    echo "data/ 검증 실패 — 커밋하지 않고 중단"
    exit 1
}

if [ "${OPS_NO_GIT:-0}" = "1" ]; then
    echo "[테스트 모드] git 커밋 생략 — data/ 변경:"
    git status --short data/ || true
    exit 0
fi

git add data/
if git diff --cached --quiet; then
    echo "데이터 변경 없음 — 커밋 생략"
    exit 0
fi

git commit -q -m "data: 자동 $CMD $TODAY" -m "scripts/ops.sh (systemd timer)"
if git push -q origin main; then
    echo "push 완료 — Vercel 자동 배포 트리거됨"
else
    echo "push 실패 — 커밋은 로컬에 남아 있음 (다음 실행에서 재시도됨)"
    exit 1
fi
