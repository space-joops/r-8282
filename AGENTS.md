<!-- BEGIN:nextjs-agent-rules -->

# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->

# 경마픽 — 프로젝트 규약

한국경마(서울·부산경남·제주) 예측 PWA. 위 관리 블록은 `next dev`가 소유하므로 수정 금지 — 프로젝트 규약은 이 섹션에만 추가한다.

## 데이터 흐름

로컬 Python 파이프라인(`pipeline/`)이 data.go.kr 한국마사회 API 수집 → 통계 스코어링 + AI CLI(claude -p) 분석 → `data/*.json` 커밋 → push 시 Vercel 자동 배포 → Next.js가 빌드타임에 fs로 읽어 완전 정적(SSG) 서빙. DB·런타임 fetch 없음.

## 명령어

- `make predict DATE=YYYY-MM-DD` — 예측 생성 (`FLAGS="--no-ai"` 통계 단독)
- `make results DATE=YYYY-MM-DD` — 경주 결과 반영 + 적중률 갱신
- `make validate` — data/ 전체 JSON Schema 검증
- `cd pipeline && uv run pytest` — 파이프라인 테스트
- `npm run build` / `npm run lint` — 웹 빌드·린트 (`next lint`는 제거됨)

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

## 운영 절차 (수동, 비용 0원)

1. 개최 전날(보통 금) `make predict DATE=…` → `data/` diff 검토 → 커밋·push (Vercel 자동 배포)
2. 당일 아침 기수 변경 확인 시 재실행 후 재커밋
3. 경마일 저녁 `make results DATE=…` → 커밋·push

## 배포 (Vercel)

- 프로젝트: `kyongmapick` (ppabams-projects, Hobby) — 프로덕션 https://kyongmapick.vercel.app
- GitHub 연동됨: main 머지 → 자동 프로덕션 배포, PR push → 프리뷰 배포
- 수동 배포: `vercel deploy` (프리뷰) / `vercel deploy --prod`
- env: `NEXT_PUBLIC_SITE_URL` 설정됨. 서치콘솔 등록 후 `GOOGLE_SITE_VERIFICATION`·`NAVER_SITE_VERIFICATION` 추가 필요
- Hobby 플랜은 비상업 용도 — 수익화 시 Pro 전환
