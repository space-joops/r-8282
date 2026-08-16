<!-- BEGIN:nextjs-agent-rules -->

# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->

# 경마픽 — 프로젝트 규약

한국경마(서울·부산경남·제주) 예측 PWA. 위 관리 블록은 `next dev`가 소유하므로 수정 금지 — 프로젝트 규약은 이 섹션에만 추가한다.

**세션 시작 시 [TODO.md](TODO.md)를 먼저 읽을 것** — 현재 상태·다음 작업·주의사항이 정리되어 있다. 작업 후 TODO.md 갱신도 잊지 말 것.

## 데이터 흐름

로컬 Python 파이프라인(`pipeline/`)이 data.go.kr 한국마사회 API 수집 → 통계 스코어링 + AI CLI(claude -p) 분석 → `data/*.json` 커밋 → push 시 Vercel 자동 배포 → Next.js가 빌드타임에 fs로 읽어 완전 정적(SSG) 서빙. DB·런타임 fetch 없음.

## 명령어

- `make predict DATE=YYYY-MM-DD` — 예측 생성 (`FLAGS="--no-ai"` 통계 단독)
- `uv run kra-predict train --from YYYY-MM --to YYYY-MM` — v2 가중치 재학습 (`weights_v2.json` 갱신 — **평가/백테스트 기간과 겹치면 안 됨**). 파일 존재 시 predict/backtest가 자동으로 v2 사용, 삭제하면 v1 폴백
- `uv run kra-predict backtest --months YYYY-MM,YYYY-MM` — 활성 모델 백테스트 → `data/stats/backtest.json` (버전별 병기, /model에 공개)
- `make results DATE=YYYY-MM-DD` — 경주 결과 반영 + 적중률 갱신
- `make validate` — data/ 전체 JSON Schema 검증
- `cd pipeline && uv run pytest` — 파이프라인 테스트
- `npm run build` / `npm run lint` — 웹 빌드·린트 (`next lint`는 제거됨)
- **실행 가능한 운영 런북·학습 노트북**: `notes/` — 시작법은 `notes/README.md` (Jupyter Deno+Python, Observable Notebook Kit)

## 데이터 계약 규칙

- 원천: TS측 `lib/types.ts`(zod) ↔ Python측 `pipeline/schemas/*.schema.json` — **항상 양측 동기화**, 변경 시 `schemaVersion` 범프
- camelCase 키, 키 생략 금지(`null` 명시)
- 날짜·시각은 KST 로컬 문자열(`"2026-08-22"`, `"13:05"`), 기계 타임스탬프만 `+09:00` ISO
- `lib/data.ts`가 유일한 읽기 진입점 — 모든 읽기는 zod 검증(스키마 드리프트 시 빌드 실패가 정상)
- `meet.json`·`index.json`은 경주 파일에서 재생성되는 파생물 — 손으로 수정 금지

## Next.js 16 주의사항 (이 리포에서 확정된 것)

- `cacheComponents` OFF 유지 (레거시 모델). 전 동적 라우트 `generateStaticParams` + `export const dynamicParams = false`
- `next/image`의 `priority` 사용 금지 (deprecated) → `preload` 또는 `fetchPriority="high"`
- viewport/themeColor는 `export const viewport`로 분리 (metadata에 넣지 않음)
- `next.config.ts`에 webpack 설정 추가 금지 (Turbopack 빌드 실패함)
- 페이지 렌더링에서 `new Date()`(현재 시각) 금지 — 빌드 타임존이 UTC일 수 있음. 날짜 표시는 `lib/format.ts`(Asia/Seoul 고정) 사용
- 타입 헬퍼 `PageProps<'/...'>`, `LayoutProps<'/'>`는 전역 제공(import 불필요), `typedRoutes` 활성화됨

## 파이썬 개발자를 위한 TS 대응표

| Python | TypeScript |
|---|---|
| `TypedDict` / dataclass | `interface` |
| pydantic `model_validate` | zod `schema.parse` |
| `None` | `null` (이 리포는 `undefined` 대신 `null` 명시) |
| `Literal["a", "b"]` | `"a" \| "b"` (유니온 리터럴) |
| `list[int]` | `number[]` |
| pydantic 모델에서 타입 추출 | `z.infer<typeof schema>` |
| `f"{x}"` | `` `${x}` `` (템플릿 리터럴) |

## 협업 규약

- 소통·이슈·커밋·PR 모두 한국어, 커밋은 Conventional Commits(`feat:`, `chore:`, `fix:`)
- 1 이슈 = 1 브랜치(`feat/…`, `chore/…`) = 1 PR, PR 본문에 `Closes #N`
- 작업 단위별 커밋 유지

## 운영 절차 (비용 0원)

**자동 (기본)**: systemd user timer가 노트북에서 실행 — 설치는 `scripts/install-automation.sh`
- `kyongma-predict.timer`: 금·토·일 07:30 예측 생성 → 변경 시 자동 커밋·push
- `kyongma-results.timer`: 금·토·일 19:30 + 월 10:00 결과 반영(오늘+어제 스윕, `--refresh`)
- 로그: `journalctl --user -u kyongma-predict -u kyongma-results -e`
- 파이프라인 쓰기는 멱등(`write_json_if_changed` — 휘발성 타임스탬프 무시)이라 변경 없는 재실행은 커밋을 만들지 않는다

**수동 (보완)**: 노트북이 꺼져 있었으면 `Persistent=true`로 부팅 후 자동 보충되지만, 직접 돌릴 땐
1. `make predict DATE=…` → `data/` diff 검토 → 커밋·push
2. `make results DATE=… FLAGS=--refresh` → 커밋·push (캐시가 미확정 결과를 물고 있으므로 --refresh)

## 관리자 기능 (/admin) — Supabase는 여기에만 사용

- **사이트 코어는 완전 정적 유지.** `/admin`이 유일한 동적 라우트(`force-dynamic`)이며, `proxy.ts`가 Basic Auth(env `ADMIN_PASSWORD`)로 게이트한다 — matcher가 /admin만 잡아 공개 경로 비용 영향 없음
- 텔레메트리: predict/results 실행이 Supabase `kyongma_ops_runs`에 기록됨(`pipeline/kra_predict/telemetry.py`, fail-soft). 스키마는 `supabase/schema.sql` — RLS 활성·정책 없음 = service 키 전용
- Supabase 조회는 서버에서 service 키로만 — `NEXT_PUBLIC_` 키를 만들지 말 것
- 타이머 일정 상수(`components/admin/schedule.ts`)의 원천은 `scripts/systemd/*.timer` — 타이머 변경 시 함께 갱신
- 필요 env — Vercel: `ADMIN_PASSWORD`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` / 노트북 `pipeline/.env`: `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`
- `new Date()` 렌더링 금지 규칙의 예외: /admin은 동적 렌더이므로 요청 시각 사용 허용

## 배포 (Vercel)

- 프로젝트: `kyongmapick` (ppabams-projects, Hobby) — 프로덕션 https://kyongmapick.vercel.app
- GitHub 연동됨: main 머지 → 자동 프로덕션 배포, PR push → 프리뷰 배포
- 수동 배포: `vercel deploy` (프리뷰) / `vercel deploy --prod`
- env: `NEXT_PUBLIC_SITE_URL` 설정됨. 서치콘솔 등록 후 `GOOGLE_SITE_VERIFICATION`·`NAVER_SITE_VERIFICATION` 추가 필요
- Hobby 플랜은 비상업 용도 — 수익화 시 Pro 전환
