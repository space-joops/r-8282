# 로컬 예측 파이프라인 진입점 (pipeline/은 이슈 #2~#4에서 구현)
# 사용 예: make predict DATE=2026-08-22  /  make predict DATE=2026-08-22 FLAGS="--no-ai"
DATE ?=
FLAGS ?=

.PHONY: predict results accuracy validate build

predict:
	cd pipeline && uv run kra-predict predict --date $(DATE) $(FLAGS)

results:
	cd pipeline && uv run kra-predict results --date $(DATE) $(FLAGS)

accuracy:
	cd pipeline && uv run kra-predict accuracy

validate:
	cd pipeline && uv run kra-predict validate

build:
	npm run build
