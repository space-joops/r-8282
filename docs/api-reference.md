# API 사용 현황 레퍼런스

> 경마픽이 실제로 호출/연동하는 외부 API·CLI를 한 곳에 정리한 문서. 다른 AI 세션이 코드를 다시 뒤지지 않고 "어떤 API를, 어떻게, 어디서, 왜" 쓰는지 바로 파악하도록 작성했다. 마지막 검증: 2026-08-22 (코드 직접 확인 기준).

## 개요

```
data.go.kr KRA Open API 수집(fetch.py)
  → 통계 스코어링(score.py, API 호출 없음)
  → Claude Code CLI 보정(ai.py, claude -p 서브프로세스)
  → data/*.json 커밋·push
  → Vercel Git 연동 자동 배포(정적 SSG, 런타임 API 호출 없음)
```

웹(Next.js) 쪽은 완전 정적이라 런타임에 외부 API를 부르지 않는다. 유일한 예외는 `/admin`(동적 라우트)이 조회 전용으로 Supabase REST API를 호출하는 부분이다. 아래 각 섹션은 실제 호출 지점(파일 경로)까지 짚는다.

---

## 1. KRA Open API (data.go.kr)

- **발급처**: data.go.kr 마이페이지 &gt; 개발계정, 서비스 `B551015`(한국마사회)
- **Base URL**: `https://apis.data.go.kr/B551015`
- **인증**: env `KRA_SERVICE_KEY` (`pipeline/.env`). 요청 파라미터명이 API마다 다름 — 최신 API는 소문자 `serviceKey`, 구세대 API(`racePlan_2`, `jockeyResult_1`, `raceHorseResult_2`)는 대문자 `ServiceKey`. `pipeline/kra_predict/config.py`의 `service_key()`가 data.go.kr의 Encoding 키(`%` 포함)를 넣어도 자동으로 반복 디코딩해 원본 키로 정규화한다(2중 인코딩 실수 방지).
- **레지스트리**: `pipeline/kra_predict/api/endpoints.py` — 경로는 2026-08-15에 더미 키 프로브로 전수 검증됨.

### 엔드포인트 전체 목록

| 상수명 | API ID | 승인 | 용도 | 주요 파라미터 | 코드상 사용 |
|---|---|---|---|---|---|
| `RACE_PLAN` | API72_2 / racePlan_2 | ✅ | 경주 편성 | `meet`, `rc_date` | fetch.py |
| `RACE_RESULT_TOTAL` | API299 / Race_Result_total | ✅ | 경주결과종합(94필드: 성적·기수/조교사 통산·1년스탯·마체중증감) | `meet`, `rc_date` | fetch.py |
| `HORSE_1Y_RECORD` | API145 / rchrLoyRcod | ✅ | 경주마 1년 전적 | `rccrs_cd`, `hr_name` | fetch.py |
| `JOCKEY_CHANGE` | API300 / Jockey_Change_Detail | ✅ | 당일 기수 변경 | `meet`, `rc_date` | fetch.py |
| `SEOUL_ENTRY_REG` | API323 / textDataHoldSeRegInfo | ✅ | 서울 출전등록현황 | `race_dt` | fetch.py (CHULMA_INFO 폴백) |
| `SEOUL_HORSE_WEIGHT` | API317 / textDataHoldSeWegInfo | ✅ | 서울 출전마체중 | `race_dt`, `race_no` | fetch.py |
| `CHULMA_INFO` | API78 / chulmainfo | ✅ | 출전표정보(전 경마장 단일 API, 1순위 소스) | `rccrs_cd`, `race_dt` | fetch.py |
| `BUSAN_ENTRY` | API316 / textDataHoldBuPtinInfo | ✅ | 부산경남 출전마현황 | `race_dt` | fetch.py (CHULMA_INFO 폴백) |
| `JOCKEY_RESULT` | API11_1 / jockeyResult_1 | ✅ | 기수 성적(1년 승률) | `meet` | fetch.py |
| `TRAINER_INFO` | API308 / trainerInfo | ✅ | 조교사 정보(1년 승률) | `meet` | fetch.py |
| `SEOUL_RACE_INFO` | API311 / textDataHoldSeRaceInfo | ✅ | 서울 경주정보(날씨·주로) | `race_dt` | fetch.py |
| `BUSAN_RACE_INFO` | API313 / textDataHoldBuRaceInfo | ✅ | 부산경남 경주정보 | `race_dt` | fetch.py |
| `RACE_DETAIL_RESULT` | API214_1 / RaceDetailResult_1 | ✅ | 경주성적정보(과거 상세+배당) | `meet`, `rc_month` | backtest.py, train.py |
| `DIVIDEND_RATE` | API301 / Dividend_rate_total | ✅ | 확정배당율종합(WIN/PLC/QNL/EXA/QPL/TLA/TRI) | `meet`, `rc_date`/`rc_month`, `pool` | fetch.py(결과), backtest.py(전 풀) |
| `HORSE_DETAIL` | API282 / HorseDetailInfo | ✅ | 마필 상세(혈통) | — | 미사용(등록만) |
| `AI_RACE_RESULT` | API155 / raceResult | ✅ | AI학습용 경주결과 | — | 미사용(등록만) |
| `HORSE_RESULT` | API15_2 / raceHorseResult_2 | ✅ | 경주마 성적 | — | 미사용(등록만) |
| `AI_RACE_PLAN` | API154 / racePlan | ❌ 신청대기 | AI학습용 경주계획 | — | 미사용 |

`meet`: 1=서울, 2=제주, 3=부산경남 (`pipeline/kra_predict/config.py`의 `TRACKS`). `rc_date`/`race_dt`는 `YYYYMMDD`(`config.to_api_date()`).

### 클라이언트 동작 — `pipeline/kra_predict/api/client.py`

- **재시도**: `tenacity`, `httpx.TransportError`·5xx(`RetryableHttpError`)에 대해 최대 4회, exponential backoff(`multiplier=1, max=15`), 최종 실패 시 원본 예외 재발생.
- **캐싱**: 원문 응답을 `pipeline/.cache/<endpoint.name>/<params_key>.json`에 저장. 같은 파라미터 재호출 시 네트워크 요청 없이 캐시 재사용(쿼터 절약) — `--refresh` 플래그로 무시 가능. 오류 응답은 캐시하지 않음.
- **에러 클래스**: `KraApiError`(정상 응답 내 오류 resultCode) / `KraAuthError`(게이트웨이 레벨 — 미등록 키·미승인 API·쿼터 초과, `OpenAPI_ServiceResponse` 래퍼 또는 HTTP 401/403) / `RetryableHttpError`(HTTP 5xx).
- **NODATA 처리**: `resultCode`가 `"03"`/`NODATA_ERROR`면 정상으로 간주하고 빈 목록 반환.
- **JSON/XML 겸용**: `_type=json`을 요청해도 일부 자료실 계열 API는 XML을 반환 — 응답이 `<`로 시작하면 `xmltodict`로 폴백 파싱.
- **보안**: 인증키가 URL 쿼리에 있어 `raise_for_status()`(에러 메시지에 URL 포함 위험) 대신 직접 상태코드 분기 처리, `httpx` 로거는 항상 WARNING으로 억제.
- **흡수 래퍼**(`fetch.py`): `_try_items()`(`KraAuthError`만 흡수, 승인 API는 WARNING/미승인은 INFO 로그), `_try_items_soft()`(`KraApiError`까지 흡수 — 보강용 데이터의 일시 오류 허용).
- **페이징**: `get_items()`가 `totalCount` 기준 자동 전 페이지 순회(기본 `num_of_rows=100`, `max_pages=50`).
- **offline 모드**: `pipeline/fixtures/`만 사용(네트워크 없는 테스트용), 서비스키 불필요.

### 실사용 흐름

- `fetch_meet_bundle()`(`pipeline/kra_predict/fetch.py`, `kra-predict predict`에서 호출) — 순서: `RACE_PLAN` → `CHULMA_INFO`(없으면 `SEOUL_ENTRY_REG`/`BUSAN_ENTRY` 폴백) → `SEOUL_HORSE_WEIGHT` → `JOCKEY_CHANGE` → `HORSE_1Y_RECORD` → `JOCKEY_RESULT`/`TRAINER_INFO`(soft) → `SEOUL_RACE_INFO`/`BUSAN_RACE_INFO` → `RACE_RESULT_TOTAL`(경주 종료 후).
- `fetch_results_bundle()`(`kra-predict results`) — `RACE_PLAN` + `RACE_RESULT_TOTAL` + `DIVIDEND_RATE`(WIN/PLC).
- `backtest.py`의 `fetch_detail_rows()`(`RACE_DETAIL_RESULT`)·`fetch_pool_dividends()`(`DIVIDEND_RATE` 전 풀). **누수 방지 설계**: 마필/기수/조교사 1년 스탯은 API 요약 필드(조회 시점 재계산되어 누수)를 쓰지 않고, 경주일 이전 365일 창을 직접 계산.
- `train.py`가 `backtest.py`의 수집 함수를 재사용해 v2 가중치(`weights_v2.json`)를 학습.

---

## 2. Claude Code CLI (AI 보정)

- **파일**: `pipeline/kra_predict/ai.py`
- **호출 방식**: Anthropic API를 직접 HTTP로 부르지 않고 **로컬 `claude` CLI를 서브프로세스로 실행**.
  ```python
  cmd = ["claude", "-p", "--output-format", "json", "--max-turns", "1"]
  if model:
      cmd += ["--model", model]
  proc = subprocess.run(cmd, input=prompt, capture_output=True, text=True, timeout=TIMEOUT_SEC, check=True)
  envelope = json.loads(proc.stdout)
  ```
  `TIMEOUT_SEC = 180`. 모델은 하드코딩 없이 `--ai-model` CLI 옵션(typer)으로 전달(예: `FLAGS="--ai-model haiku"`), 미지정 시 `claude` CLI 기본 모델 사용.
- **프롬프트 템플릿**: `pipeline/prompts/race_analysis.md` — 경주 정보(날짜/트랙/번호/거리/등급/발주시각) + 출전표·통계 피처 마크다운 표 + 통계 모델 예측 순위 + "JSON만 출력, 코드펜스 금지" 규칙.
- **응답 스키마**: `commentary`(한국어 총평 3~4문장), `confidence`(high/medium/low), `perHorse[].briefComment`(15자 내외), `adjustments[].delta`.
- **설계 원칙**: 통계 예측이 축, AI는 보정만 — `delta`는 **`MAX_DELTA = ±0.08`로 클램핑**되어 통계 score에 가산, 이후 softmax로 winProb·순위·topPicks 재계산.
- **에러 처리**: 파싱/검증 실패 시 `enrich_predictions()`에서 1회 재시도, 그래도 실패하면 **통계 단독 결과로 폴백**(예측 산출은 항상 보장, 파이프라인 중단 없음).
- **비활성화**: `kra-predict predict --no-ai`로 AI 보정 완전 스킵 가능.

---

## 3. Supabase REST API (운영 텔레메트리 — `/admin` 전용)

Supabase는 이 프로젝트에서 **오직 운영 텔레메트리 대시보드(`/admin`)에만** 쓰인다. `data/*.json`을 읽는 웹 본체(`lib/data.ts`)와는 완전히 분리되어 있고, DB에 의존하지 않는다. `@supabase/supabase-js`, `supabase-py` 등 전용 SDK는 **둘 다 설치되어 있지 않음** — 양쪽 다 PostgREST를 순수 HTTP 클라이언트(`httpx`/`fetch`)로 직접 호출한다.

- **테이블**: `public.kyongma_ops_runs` (`supabase/schema.sql`) — `id`, `kind`(`predict`\|`results`), `target_date`, `status`(`success`\|`no_change`\|`no_races`\|`error`), `source`(`timer`\|`manual`), `host`, `started_at`, `finished_at`, `duration_sec`, `metrics`(jsonb), `error`. 인덱스: `started_at desc`.
- **RLS**: 활성화되어 있으나 **정책을 하나도 만들지 않음** → anon/authenticated 완전 차단, `service_role` 키만 RLS를 우회해 접근 가능(Supabase Auth/anon key는 아예 안 씀).
- **기록 측 — `pipeline/kra_predict/telemetry.py`**: `POST {SUPABASE_URL}/rest/v1/kyongma_ops_runs` (헤더 `apikey`/`Authorization: Bearer`/`Prefer: return=minimal`). `track(kind, target_date, enabled=...)` 컨텍스트 매니저가 `predict`/`results` CLI 커맨드를 감싸 종료 시 1행 기록(`fixtures` 모드는 `enabled=False`로 완전 스킵). **fail-soft 계약**: env 없으면 조용히 스킵, 네트워크/HTTP≥300 오류는 경고 로그만 남기고 무시 — `record_run()`은 항상 bool 반환, raise 안 함. 단, 감싼 코드 자체의 예외는 `status="error"`로 기록 후 재전파(텔레메트리가 파이프라인 실패를 삼키지 않음). `source`는 env `OPS_RUN_SOURCE`(기본 `manual`, systemd 타이머는 `timer`)로 결정. 계약은 `pipeline/tests/test_telemetry.py`가 검증.
- **조회 측 — `lib/admin.ts`**: `GET {SUPABASE_URL}/rest/v1/kyongma_ops_runs?select=*&order=started_at.desc&limit=30` (`cache: "no-store"`, `AbortSignal.timeout(8000)`). `app/admin/page.tsx`(서버 컴포넌트, `export const dynamic = "force-dynamic"`)에서만 호출되어 service 키가 브라우저로 노출되지 않음. env 미구성/fetch 실패 시 예외 없이 `null` 반환 → 페이지가 "Supabase가 구성되지 않았거나 조회에 실패했습니다" 안내로 대체.
- **env**: `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`(기본) — Vercel Marketplace Supabase 연동이 자동 주입하는 `SUPABASE_SERVICE_ROLE_KEY`도 동일하게 인식(TS/Python 양쪽 fallback 처리).

---

## 4. 관리자 인증 게이팅 — `proxy.ts`

- Next.js 미들웨어(Next 16 명칭 체계상 `middleware.ts`가 아니라 `proxy.ts`, export 함수명 `proxy`). `config.matcher = "/admin/:path*"`로 `/admin` 하위만 가로챔 — 공개 정적 경로엔 영향 없음.
- `ADMIN_PASSWORD` env가 없으면 503 반환(인증 우회가 아니라 접근 자체 차단 — fail-closed).
- 있으면 `Basic base64("admin:" + ADMIN_PASSWORD)` 기대값과 요청 `authorization` 헤더를 비교. 불일치 시 401 + `WWW-Authenticate: Basic realm="kyongmapick-admin"`. 아이디는 하드코딩된 `admin`, 비밀번호만 env 주입.

---

## 5. Vercel 배포

- `vercel.json`/`vercel.ts`/Vercel Cron 설정 **없음**. `.vercel/project.json`은 `vercel link`가 만든 로컬 전용 파일(gitignore 처리, 커밋 안 됨).
- 배포는 **GitHub 연동 자동 배포** 방식: `scripts/ops.sh`가 파이프라인 실행 후 `data/`를 커밋·`git push origin main` → Vercel이 push를 감지해 자동 프로덕션 배포.
- 실제 "스케줄러"는 Vercel이 아니라 **로컬/홈서버 systemd timer**(`scripts/systemd/kyongma-predict.timer`, `kyongma-results.timer`)가 `scripts/ops.sh predict|results`를 주기 실행 → 파이프라인 → git commit/push까지 담당.
- `next.config.ts`에 Vercel 전용 특수 설정은 없음(`outputFileTracingIncludes`로 `/admin` 서버리스 함수 번들에 `data/**/*` 포함, `typedRoutes: true`).

---

## 6. 환경변수 총정리

| 변수명 | 필수/선택 | 위치 | 용도 |
|---|---|---|---|
| `KRA_SERVICE_KEY` | 필수(파이프라인) | `pipeline/.env` | data.go.kr KRA API 인증 |
| `SUPABASE_URL` | 선택 | `pipeline/.env` + Vercel env | 운영 텔레메트리/관리자 대시보드 |
| `SUPABASE_SERVICE_KEY` (별칭 `SUPABASE_SERVICE_ROLE_KEY`) | 선택 | `pipeline/.env` + Vercel env | 위와 동일(둘 다 없으면 텔레메트리·admin 조회가 fail-soft로 조용히 비활성) |
| `ADMIN_PASSWORD` | 필수(`/admin` 쓰려면) | Vercel env | `/admin` Basic Auth 비밀번호(없으면 `/admin` 자체가 503) |

파이프라인 HTTP 클라이언트는 전부 `httpx`(`pyproject.toml`) — KRA API와 Supabase REST 양쪽에 동일하게 사용. 재시도는 `tenacity`. 웹 쪽은 별도 HTTP 라이브러리 없이 런타임 `fetch` 사용.

---

## 7. 파일 인덱스

| 영역 | 경로 |
|---|---|
| KRA 엔드포인트 레지스트리 | `pipeline/kra_predict/api/endpoints.py` |
| KRA API 클라이언트 | `pipeline/kra_predict/api/client.py` |
| 서비스키·트랙 설정 | `pipeline/kra_predict/config.py` |
| 예측/결과 수집 | `pipeline/kra_predict/fetch.py` |
| 백테스트/학습용 수집 | `pipeline/kra_predict/backtest.py`, `pipeline/kra_predict/train.py` |
| 통계 스코어링(API 호출 없음) | `pipeline/kra_predict/score.py` |
| Claude CLI 보정 | `pipeline/kra_predict/ai.py`, `pipeline/prompts/race_analysis.md` |
| Supabase 기록(파이프라인) | `pipeline/kra_predict/telemetry.py` |
| Supabase 조회(웹) | `lib/admin.ts`, `app/admin/page.tsx` |
| 관리자 인증 게이팅 | `proxy.ts` |
| Supabase 스키마 | `supabase/schema.sql` |
| 정적 데이터 읽기 진입점(외부 호출 없음) | `lib/data.ts` |
