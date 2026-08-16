# TODO — 다음 작업 (AI 재시작 진입점)

> 새 세션에서 AI(Claude Code)에게 "TODO.md 보고 다음 작업 진행해줘"라고 하면 됩니다.
> 규약은 [AGENTS.md](AGENTS.md), 운영 절차는 [README.md](README.md) 참고.
> 작업을 진행하면 이 파일을 갱신할 것 (완료 항목 제거, 상태 스냅샷 날짜 갱신).

## 상태 스냅샷 (2026-08-16 기준)

- 프로덕션 라이브: https://kyongmapick.vercel.app — 8/16(일) 서울 10·부경 7경주 사전 예측 배포됨 (v1 — 타이머 07:33이 v2 머지보다 먼저)
- 파이프라인: 승인 API 전부 통합됨 (출전표정보·기수/조교사 성적·확정배당율·날씨/주로). AI학습용_경주계획(API154)만 미승인
- 적중률: **첫 실전 공개됨** — 8/16 오전 8경주 단승 37.5%·연승 62.5% (수동 반영·배포 완료). 잔여 9경주는 19:30 타이머가 마저 반영
- UX 전환 완료: #39/PR#41(대시보드)·#40/PR#42(관전 가이드 전환) 모두 머지·배포됨

## 🔥 시급 (운영 — 날짜 지정 작업)

1. **8/16(일) 19:30**: 결과 타이머 → 잔여 9경주(서울 9·10, 부경 4·5·7 등) 자동 반영. 수동 폴백: `make results DATE=2026-08-16 FLAGS=--refresh` → 커밋·push
2. **적중률 분석 후속 작업**: [#43](https://github.com/space-joops/r-8282/issues/43) 사용자 활용 가이드(무작위 기준선 병기·신뢰도 툴팁·읽는 법) — 다음 작업으로 적합 (소~중)
3. **사용자 액션**: `vercel env add ADMIN_PASSWORD production` (미설정 — /admin이 503, 사용자명 admin)
4. 첫 실데이터가 쌓였으니 /admin 차트 시각 QA 가능해짐
5. 자동화 로그 확인 습관: `journalctl --user -u kyongma-predict -u kyongma-results -e` (/admin에서도 확인 가능)

## 자동화 상태 (2026-08-15 설치)

- systemd user timer 활성: 예측 금토일 07:30 / 결과 금토일 19:30+월 10:00 (`Persistent=true`, linger 활성)
- 파이프라인 쓰기는 멱등 — 변경 없는 재실행은 커밋 없음
- 해제: `systemctl --user disable --now kyongma-predict.timer kyongma-results.timer`

## 진행 중 · 방향
- **사이트 방향(2026-08-16 확정·반영됨)**: 'AI 브리핑·데이터로 직접 판단을 돕는 관전 가이드'. 모델 손익 공개는 신뢰 요소 (무작위 -20%대 기준선 카피)
- **적중률 분석 완료(2026-08-16)**: 핵심 진단 = ① 단승 ROI(-39%)가 무작위보다 나쁨 → 인기마 편향 ② 신뢰도 배지 비단조(보통 17.2%가 최악) ③ 부경 갭(19.0% vs 서울 27.1%) — 상세는 #43·#44
- **v2는 다음 개최일(8/21 금)부터 자동 적용** (8/16 예측은 v1 — 발주 후 재예측은 정직성 원칙 위반이라 하지 않음)
- 참고: v1 백테스트 재생성은 `kra-predict backtest --months ... --stat v1` (학습 가중치 무시). frontend-design 스킬 설치됨(`.claude/skills/`)

## 백로그 (우선순위순)

| 이슈 | 내용 | 규모 |
|---|---|---|
| [#43](https://github.com/space-joops/r-8282/issues/43) | 적중률 사용자 활용 가이드 — 무작위 기준선 병기·신뢰도 실측 툴팁·실전vs백테스트 비교·guide '읽는 법' | 중 |
| [#44](https://github.com/space-joops/r-8282/issues/44) | 시스템 개선 로드맵 — A.배당 피처(인기마 편향) → B.신뢰도 재설계 → C.캘리브레이션 공개 → D.부경 갭 → E.버전별 실전 추적 | 대 |
| [#24](https://github.com/space-joops/r-8282/issues/24) | 모델 로드맵 잔여 (#44의 F로 흡수 — LightGBM·데이터 확장) | 대 |
| [#19](https://github.com/space-joops/r-8282/issues/19) | 검색엔진 등록 — **사용자 수동 작업** (콘솔 등록 → env 추가) | 소 |

## AI 재시작 체크리스트

새 세션 시작 시 순서대로:
1. `git checkout main && git pull` — 최신 동기화
2. `gh issue list` — 열린 이슈 확인 (위 표와 대조)
3. 운영 작업이면 위 '시급' 절차대로, 코딩 작업이면 **이슈 → 브랜치 → PR** 규약 준수
4. 데이터 커밋(`data/`)은 main 직접 push, 코드 변경은 반드시 PR

### 주의사항 (과거 사고에서 배운 것)
- **스택 PR은 번호 작은 것부터(맨 아래부터) 머지** — 위에서부터 머지하면 main에 안 들어감
- **브랜치 삭제 전 `gh pr view <n> --json mergedAt`으로 머지 확인** — 미머지 브랜치를 지우면 PR이 닫힘
- raw 캐시(`pipeline/.cache/`)는 로컬 전용·재취득 가능. 정제본(`data/`)만 커밋 대상
- `results` 재실행 시 캐시가 미확정 상태를 물고 있으므로 `--refresh` 필수
- 결과 확정 경주의 예측은 불변 (`--force` 사용 금지 — 사후 예측 수정 금지 원칙)
