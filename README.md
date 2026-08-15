# 경마픽 — 한국경마 예측 PWA

서울·부산경남·제주 경마의 출전표와 **통계 + AI(claude CLI) 결합 예측**, 경주 결과와
누적 적중률을 제공하는 모바일 우선 PWA.

- 프로덕션: https://kyongmapick.vercel.app
- 스택: Next.js 16 (완전 정적 SSG) · Tailwind v4 · zod / Python 3.11+ (uv) · data.go.kr 한국마사회 오픈API

## 아키텍처 — 운영비 0원

```
[로컬 Python 파이프라인]                       [Vercel]
data.go.kr KRA API ─→ 수집(fetch) ─→ 통계 스코어링 ─→ AI 보정(claude -p)
                                        │
                                        ▼
                              data/*.json 커밋 → git push → 자동 빌드/배포
                                                              │
                                              완전 정적 페이지(SSG) — 서버리스 0회
```

- 예측·결과는 모두 **경기 전/후 로컬에서 생성**해 리포에 커밋 — DB·런타임 API 없음
- 모든 데이터는 zod(웹)·JSON Schema(파이프라인) 이중 검증 — 스키마가 어긋나면 빌드 실패

## 운영 절차

```bash
# 1) 개최 전날: 예측 생성 (pipeline/.env에 KRA_SERVICE_KEY 필요)
make predict DATE=2026-08-22          # FLAGS="--no-ai" 통계 단독, FLAGS="--ai-model haiku"
git diff data/ && git add data/ && git commit -m "data: 8/22 예측" && git push

# 2) 경마일 저녁: 결과 반영 + 적중률 갱신
make results DATE=2026-08-22
git add data/ && git commit -m "data: 8/22 결과" && git push

# 검증
make validate                          # data/ 전체 스키마 검증
cd pipeline && uv run pytest           # 파이프라인 테스트
npm run build                          # 웹 빌드(=데이터 스모크 테스트)
```

자세한 규약은 [AGENTS.md](AGENTS.md) 참고.

## 고지

본 서비스는 한국마사회가 공공데이터포털(data.go.kr)에 제공한 데이터를 이용합니다.
예측은 통계·AI 기반 참고 정보이며 적중을 보장하지 않습니다. 마권 구매와 그 결과에
대한 책임은 이용자 본인에게 있으며, 미성년자는 마권을 구매할 수 없습니다.
