"""v2 학습 — 조건부 로짓(경주 내 softmax) MLE.

v1과 동일한 피처·경주 내 min-max 정규화를 유지하고, 선형 계수 β만
데이터로 학습한다 (β에 softmax 온도가 흡수됨). 결측 피처는 0.5(중립) 대치.
학습 데이터는 백테스트 하네스(as-of 누수 차단)를 그대로 재사용한다.
"""

from __future__ import annotations

import logging

import numpy as np
from scipy.optimize import minimize

from kra_predict.emit import now_kst_iso
from kra_predict.score import (
    WEIGHTS,
    _minmax_normalize,
    extract_features,
)

logger = logging.getLogger(__name__)

FEATURES = list(WEIGHTS.keys())
IMPUTE = 0.5


def build_training_blocks(races: list[dict]) -> list[tuple[np.ndarray, int]]:
    """백테스트 하네스의 race dict → (X[n×K], 우승마 인덱스) 목록."""
    blocks: list[tuple[np.ndarray, int]] = []
    for race in races:
        entries = race["entries"]
        results = race["results"]
        winner_gate = next(
            (g for g, res in results.items() if res["ord"] == 1), None
        )
        if winner_gate is None:
            continue
        winner_idx = next(
            (i for i, e in enumerate(entries) if e["gateNo"] == winner_gate), None
        )
        if winner_idx is None:
            continue

        features = [extract_features(e, race["date"]) for e in entries]
        matrix = np.empty((len(entries), len(FEATURES)))
        for j, key in enumerate(FEATURES):
            column = _minmax_normalize([f[key] for f in features])
            matrix[:, j] = [IMPUTE if v is None else v for v in column]
        blocks.append((matrix, winner_idx))
    return blocks


def _nll_and_grad(
    beta: np.ndarray, blocks: list[tuple[np.ndarray, int]], l2: float
) -> tuple[float, np.ndarray]:
    nll = 0.0
    grad = np.zeros_like(beta)
    for X, winner in blocks:
        u = X @ beta
        u -= u.max()
        p = np.exp(u)
        p /= p.sum()
        nll -= float(np.log(max(p[winner], 1e-12)))
        grad += X.T @ p - X[winner]
    n = len(blocks)
    nll = nll / n + l2 * float(beta @ beta)
    grad = grad / n + 2.0 * l2 * beta
    return nll, grad


def fit_conditional_logit(
    blocks: list[tuple[np.ndarray, int]], l2: float = 0.01
) -> np.ndarray:
    result = minimize(
        _nll_and_grad,
        x0=np.zeros(len(FEATURES)),
        args=(blocks, l2),
        jac=True,
        method="L-BFGS-B",
    )
    if not result.success:
        logger.warning("최적화 미수렴: %s", result.message)
    return result.x


def evaluate(blocks: list[tuple[np.ndarray, int]], beta: np.ndarray) -> dict:
    """log-loss와 1순위(top-pick) 적중률."""
    nll = 0.0
    hits = 0
    for X, winner in blocks:
        u = X @ beta
        u -= u.max()
        p = np.exp(u)
        p /= p.sum()
        nll -= float(np.log(max(p[winner], 1e-12)))
        if int(np.argmax(u)) == winner:
            hits += 1
    n = len(blocks)
    return {
        "races": n,
        "logLoss": round(nll / n, 4),
        "winRate": round(hits / n, 4),
    }


def select_l2(
    train_blocks: list[tuple[np.ndarray, int]],
    val_blocks: list[tuple[np.ndarray, int]],
    grid: tuple[float, ...] = (0.001, 0.01, 0.1, 1.0),
) -> tuple[float, dict[float, float]]:
    """검증 log-loss가 최소인 L2 강도를 고른다."""
    scores: dict[float, float] = {}
    for l2 in grid:
        beta = fit_conditional_logit(train_blocks, l2)
        scores[l2] = evaluate(val_blocks, beta)["logLoss"]
    best = min(scores, key=lambda k: scores[k])
    return best, scores


def make_weights_doc(
    beta: np.ndarray,
    *,
    train_from: str,
    train_to: str,
    train_races: int,
    l2: float,
    in_sample: dict,
) -> dict:
    return {
        "version": "v2",
        "method": "conditional-logit",
        "trainedAt": now_kst_iso(),
        "trainFrom": train_from,
        "trainTo": train_to,
        "trainRaces": train_races,
        "l2": l2,
        "impute": IMPUTE,
        "features": FEATURES,
        "beta": {k: round(float(b), 6) for k, b in zip(FEATURES, beta)},
        "inSample": in_sample,
    }
