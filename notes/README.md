# notes/ — 운영 가이드·학습 실습 노트북

실행 가능한 문서입니다. 읽고 → 셀을 돌려보고 → 상황이 오면 그대로 씁니다.

## 시작하기

### Jupyter (Deno + Python 혼합)

```bash
# 리포 루트에서 — Python 커널이 파이프라인(uv) 환경을 보도록 pipeline에서 띄운다
cd pipeline && uv run --with jupyterlab jupyter lab --notebook-dir=..
```

- **Deno 커널**(TypeScript)은 이 머신에 이미 설치돼 있습니다. 없으면: `deno jupyter --install`
- 노트북 상단에 필요한 커널이 표시돼 있습니다 — JupyterLab 우상단에서 커널 확인/변경

### Observable Notebook Kit (로컬 노트북)

```bash
npm install          # @observablehq/notebook-kit 포함
npm run notes:preview
# → 안내된 주소에서 /notes/observable/backtest-explorer.html 열기
```

리액티브 JS 노트북 — 셀을 고치면 즉시 다시 계산됩니다. 데이터는 리포의 `/data/**`를 직접 fetch합니다.

## 노트북 목록

| 파일 | 커널 | 내용 | 난이도 |
|---|---|---|---|
| `10-operations-guide.ipynb` | Deno | **상황별 운영 런북** — 수동 예측 재실행, 결과 반영, 타이머 점검, 재학습, 트러블슈팅 | ★ |
| `20-data-contract.ipynb` | Deno | 데이터 계약 실습 — 웹의 zod 스키마를 그대로 import해 검증 체험 | ★ |
| `30-pipeline-lab.ipynb` | Python | 파이프라인 실습 — 픽스처로 수집→조립→스코어링, 멱등성 실험 | ★★ |
| `40-model-v2-lab.ipynb` | Python | v2 모델 — 조건부 로짓 수식·β 해석·v1 비교·미니 학습 | ★★★ |
| `observable/backtest-explorer.html` | Observable | 백테스트(v1·v2) 시각 탐색 — 리액티브 셀 실습 | ★★ |
| `observable/accuracy-live.html` | Observable | 실전 적중률 추적 시각화 | ★ |

## 실행 규약 (중요)

- ✅ **상태 확인 셀** — 읽기 전용, 언제든 안전
- ⚠️ **실행 셀** — 실제로 데이터를 만들고 **커밋·push(=프로덕션 배포)** 까지 합니다. 기본 주석 처리돼 있으며, 주석을 풀기 전에 위쪽 설명을 읽으세요
- 절대 규칙: 결과 확정 경주 예측 불변(`--force` 금지) · `validate` 실패 시 커밋 금지 · 학습/평가 기간 분리
