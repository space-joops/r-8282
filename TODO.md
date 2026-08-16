# TODO — 다음 작업 (AI 재시작 진입점)

> 새 세션에서 AI(Claude Code)에게 "TODO.md 보고 다음 작업 진행해줘"라고 하면 됩니다.
> 규약은 [AGENTS.md](AGENTS.md), 운영 절차는 [README.md](README.md) 참고.
> 작업을 진행하면 이 파일을 갱신할 것 (완료 항목 제거, 상태 스냅샷 날짜 갱신).

## 상태 스냅샷 (2026-08-15 저녁 기준)

- 프로덕션 라이브: https://kyongmapick.vercel.app — **8/16(일) 서울 10·부경 7경주 사전 예측 배포됨**
- 파이프라인: 승인 API 전부 통합됨 (출전표정보·기수/조교사 성적·확정배당율·날씨/주로). AI학습용_경주계획(API154)만 미승인
- 적중률: 아직 0경주 평가 — **8/16 결과 반영이 첫 실적**
- 8/15 결과: 전 17경주 확정 반영 완료 (2026-08-15 저녁)

## 🔥 시급 (운영 — 날짜 지정 작업)

1. **PR [#30](https://github.com/space-joops/r-8282/pull/30) 머지** (운영 텔레메트리 + /admin 대시보드, #28·#29)
   - Supabase 셋업은 완료됨: jd-04 프로젝트에 `kyongma_ops_runs` 생성, Vercel 리소스 연결(env 자동 주입), 노트북 env 구성, 첫 텔레메트리 행 기록 확인
   - **남은 사용자 액션 1개**: `vercel env add ADMIN_PASSWORD production` (원하는 관리자 암호 입력) → 머지 후 `/admin` 접속(사용자명 admin)
2. **8/16(일)**: 타이머가 자동 처리 (07:33 예측 스킵 확인, 19:30 결과+첫 적중률 공개).
   수동 폴백: `make results DATE=2026-08-16 FLAGS=--refresh` → 커밋·push
3. 첫 실데이터가 쌓인 뒤 /admin 차트 시각 QA (현재는 평가 0경주라 빈 상태 문구)
4. 자동화 로그 확인 습관: `journalctl --user -u kyongma-predict -u kyongma-results -e` (머지 후엔 /admin에서도 확인 가능)

## 자동화 상태 (2026-08-15 설치)

- systemd user timer 활성: 예측 금토일 07:30 / 결과 금토일 19:30+월 10:00 (`Persistent=true`, linger 활성)
- 파이프라인 쓰기는 멱등 — 변경 없는 재실행은 커밋 없음
- 해제: `systemctl --user disable --now kyongma-predict.timer kyongma-results.timer`

## 진행 중 — 머지 대기
- **PR [#36](https://github.com/space-joops/r-8282/pull/36)**: notes/ 운영 런북·학습 노트북 (#35)
- 사용자 액션 잔여: `vercel env add ADMIN_PASSWORD production` (미설정 — /admin이 503)
- 8/16(일) 19:30 결과 타이머 → 첫 실전 적중률 자동 공개. **오늘 예측은 v1**(타이머 07:33이 머지 09:36보다 먼저) — 발주 시작 후라 재예측은 정직성 원칙 위반이라 하지 않음. **v2는 다음 개최일(8/21 금)부터 자동 적용**

## 백로그 (우선순위순)

| 이슈 | 내용 | 규모 |
|---|---|---|
| [#24](https://github.com/space-joops/r-8282/issues/24) | 모델 로드맵 잔여: v2 완료(#33) → 다음 후보 = LightGBM 검토·확률 캘리브레이션·단승 ROI 개선(배당 활용 피처) | 대 |
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
