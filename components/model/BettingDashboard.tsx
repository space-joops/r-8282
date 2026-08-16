"use client";

import {
  useId,
  useMemo,
  useRef,
  useState,
  useSyncExternalStore,
} from "react";
import { formatDateKo } from "@/lib/format";
import { TRACKS } from "@/lib/tracks";
import {
  POOL_CODES,
  type BacktestRaceRow,
  type BettingEntry,
  type PoolCode,
} from "@/lib/types";

/**
 * 승식별 베팅 시뮬레이션 대시보드 — 완전 정적 사이트의 유일한 데이터 인터랙션.
 * 서버 컴포넌트(/model)가 빌드 타임 JSON을 props로 넘긴다 (fetch 없음).
 */

export interface DashboardModel {
  version: string;
  betting: BettingEntry[];
  races: BacktestRaceRow[];
}

type PoolSel = "ALL" | PoolCode;

const POOL_LABELS: Record<PoolCode, string> = {
  WIN: "단승",
  PLC: "연승",
  QNL: "복승",
  EXA: "쌍승",
  QPL: "복연승",
  TLA: "삼복승",
  TRI: "삼쌍승",
};

const KRW = new Intl.NumberFormat("ko-KR");

const emptySubscribe = () => () => {};

function readPoolFromUrl(): PoolCode | null {
  const q = new URLSearchParams(window.location.search).get("pool");
  return q !== null && (POOL_CODES as readonly string[]).includes(q)
    ? (q as PoolCode)
    : null;
}

function won(n: number): string {
  return `${n > 0 ? "+" : ""}${KRW.format(n)}원`;
}

function profitClass(n: number): string {
  return n > 0 ? "text-brand" : n < 0 ? "text-status-error" : "text-muted";
}

function raceKey(r: BacktestRaceRow): string {
  return `${r.date}|${r.track}|${String(r.raceNo).padStart(2, "0")}`;
}

/** 한 경주의 손익(원) — ALL이면 7개 승식 합산 */
function raceProfit(r: BacktestRaceRow, pool: PoolSel): number {
  if (pool === "ALL") {
    return POOL_CODES.reduce(
      (sum, p) => sum + r.pools[p][2] - r.pools[p][0] * 100,
      0,
    );
  }
  const [staked, , returned] = r.pools[pool];
  return returned - staked * 100;
}

/** 해당 승식에 실제로 베팅했고(발매) 적중했는가 — ALL은 이익 여부로 판정 */
function raceOutcome(
  r: BacktestRaceRow,
  pool: PoolSel,
): "hit" | "miss" | "skip" {
  if (pool === "ALL") return raceProfit(r, pool) > 0 ? "hit" : "miss";
  const [staked, hit] = r.pools[pool];
  if (staked === 0) return "skip";
  return hit === 1 ? "hit" : "miss";
}

interface Streaks {
  hit: number;
  miss: number;
}

function computeStreaks(races: BacktestRaceRow[], pool: PoolSel): Streaks {
  let hit = 0;
  let miss = 0;
  let curHit = 0;
  let curMiss = 0;
  for (const r of races) {
    const outcome = raceOutcome(r, pool);
    if (outcome === "skip") continue;
    if (outcome === "hit") {
      curHit += 1;
      curMiss = 0;
    } else {
      curMiss += 1;
      curHit = 0;
    }
    hit = Math.max(hit, curHit);
    miss = Math.max(miss, curMiss);
  }
  return { hit, miss };
}

interface BestRace {
  race: BacktestRaceRow;
  profit: number;
  /** 그 경주에서 가장 크게 딴 승식 (ALL 선택 시 표기용) */
  topPool: PoolCode;
  topOdds: number;
}

function findBestRace(
  races: BacktestRaceRow[],
  pool: PoolSel,
): BestRace | null {
  let best: BestRace | null = null;
  for (const r of races) {
    const profit = raceProfit(r, pool);
    if (best !== null && profit <= best.profit) continue;
    let topPool: PoolCode = pool === "ALL" ? "WIN" : pool;
    let topReturn = -1;
    const candidates = pool === "ALL" ? POOL_CODES : [pool];
    for (const p of candidates) {
      if (r.pools[p][2] > topReturn) {
        topReturn = r.pools[p][2];
        topPool = p;
      }
    }
    best = { race: r, profit, topPool, topOdds: topReturn / 100 };
  }
  return best !== null && best.profit > 0 ? best : null;
}

/** 1-2-5 스텝의 보기 좋은 눈금 간격 */
function niceStep(range: number): number {
  const raw = range / 4;
  const mag = 10 ** Math.floor(Math.log10(Math.max(raw, 1)));
  for (const m of [1, 2, 5, 10]) {
    if (raw <= m * mag) return m * mag;
  }
  return 10 * mag;
}

export default function BettingDashboard({
  models,
  periodLabel,
}: {
  /** 버전 오름차순 — 마지막이 현재 서비스 모델 */
  models: DashboardModel[];
  periodLabel: string;
}) {
  // 딥링크: ?pool=TRI 공유 지원 — 정적 HTML은 ALL로 렌더되고 하이드레이션 후 반영
  const urlPool = useSyncExternalStore(
    emptySubscribe,
    readPoolFromUrl,
    () => null,
  );
  const [chosen, setChosen] = useState<PoolSel | null>(null);
  const pool: PoolSel = chosen ?? urlPool ?? "ALL";
  const serving = models[models.length - 1];

  const selectPool = (p: PoolSel) => {
    setChosen(p);
    const url = new URL(window.location.href);
    if (p === "ALL") url.searchParams.delete("pool");
    else url.searchParams.set("pool", p);
    window.history.replaceState(null, "", url);
  };

  const summary = useMemo(() => {
    const pick = (m: DashboardModel) => {
      const rows =
        pool === "ALL" ? m.betting : m.betting.filter((b) => b.pool === pool);
      return {
        bets: rows.reduce((s, b) => s + b.bets, 0),
        hits: rows.reduce((s, b) => s + b.hits, 0),
        stake: rows.reduce((s, b) => s + b.stakeKrw, 0),
        returned: rows.reduce((s, b) => s + b.returnedKrw, 0),
        profit: rows.reduce((s, b) => s + b.profitKrw, 0),
      };
    };
    return models.map(pick);
  }, [models, pool]);
  const servingSummary = summary[summary.length - 1];

  return (
    <section className="space-y-4">
      <div className="rounded-xl border border-border bg-surface p-4">
        <h2 className="text-lg font-semibold">
          만약 전부 베팅했다면 — 승식 시뮬레이터
        </h2>
        <p className="mt-1 text-xs text-muted">
          {periodLabel} 모든 경주에서 예측 1·2·3순위를 각 승식에 장당 100원씩
          샀다고 가정한 사후 시뮬레이션입니다. 실제 확정 배당 기준, 발매된
          경주만 계산합니다.
        </p>

        <div
          className="mt-3 flex gap-1.5 overflow-x-auto pb-1"
          aria-label="승식 선택"
        >
          {(["ALL", ...POOL_CODES] as PoolSel[]).map((p) => (
            <button
              key={p}
              aria-pressed={pool === p}
              onClick={() => selectPool(p)}
              className={`shrink-0 touch-manipulation rounded-full border px-3 py-1 text-xs font-medium transition-colors focus-visible:ring-2 focus-visible:ring-brand focus-visible:outline-none ${
                pool === p
                  ? "border-brand bg-brand-soft text-brand"
                  : "border-border bg-background text-muted hover:border-brand/50 hover:text-foreground"
              }`}
            >
              {p === "ALL" ? "전체 합산" : POOL_LABELS[p]}
            </button>
          ))}
        </div>

        <dl className="mt-3 grid grid-cols-3 gap-2">
          <div className="rounded-lg bg-background p-3">
            <dt className="text-xs text-muted">베팅액</dt>
            <dd className="mt-0.5 text-base font-bold tabular-nums sm:text-lg">
              {KRW.format(servingSummary.stake)}원
            </dd>
          </div>
          <div className="rounded-lg bg-background p-3">
            <dt className="text-xs text-muted">회수액</dt>
            <dd className="mt-0.5 text-base font-bold tabular-nums sm:text-lg">
              {KRW.format(servingSummary.returned)}원
            </dd>
          </div>
          <div className="rounded-lg bg-background p-3">
            <dt className="text-xs text-muted">
              손익 · {serving.version} 기준
            </dt>
            <dd
              className={`mt-0.5 text-base font-bold tabular-nums sm:text-lg ${profitClass(servingSummary.profit)}`}
            >
              {won(servingSummary.profit)}
            </dd>
          </div>
        </dl>
        {models.length > 1 && (
          <p className="mt-2 text-xs text-muted">
            같은 조건의 이전 버전 —{" "}
            {models
              .slice(0, -1)
              .map((m, i) => `${m.version}: ${won(summary[i].profit)}`)
              .join(", ")}
          </p>
        )}

        <ProfitChart models={models} pool={pool} />
        <MonthlyDetails models={models} pool={pool} />
      </div>

      <HighlightCards races={serving.races} pool={pool} version={serving.version} />

      <PoolTable models={models} pool={pool} onSelect={selectPool} />
    </section>
  );
}

/* ---------- 누적 손익 곡선 ---------- */

const W = 640;
const H = 230;
const PAD = { l: 52, r: 64, t: 10, b: 24 };

function ProfitChart({
  models,
  pool,
}: {
  models: DashboardModel[];
  pool: PoolSel;
}) {
  const [hoverIdx, setHoverIdx] = useState<number | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const titleId = useId();

  // x축 = 현재 모델의 경주 순서(시간순). 다른 버전은 키로 매칭.
  const axis = models[models.length - 1].races;
  const series = useMemo(() => {
    return models.map((m) => {
      const byKey = new Map(m.races.map((r) => [raceKey(r), r]));
      let acc = 0;
      return axis.map((ar) => {
        const r = byKey.get(raceKey(ar));
        acc += r ? raceProfit(r, pool) : 0;
        return acc;
      });
    });
  }, [models, axis, pool]);

  const n = axis.length;
  if (n < 2) return null;

  const all = series.flat();
  const rawMin = Math.min(0, ...all);
  const rawMax = Math.max(0, ...all);
  const span = Math.max(rawMax - rawMin, 100);
  const yMin = rawMin - span * 0.06;
  const yMax = rawMax + span * 0.06;
  const x = (i: number) => PAD.l + ((W - PAD.l - PAD.r) * i) / (n - 1);
  const y = (v: number) =>
    PAD.t + (H - PAD.t - PAD.b) * (1 - (v - yMin) / (yMax - yMin));

  const step = niceStep(yMax - yMin);
  const ticks: number[] = [];
  for (let t = Math.ceil(yMin / step) * step; t <= yMax; t += step) {
    ticks.push(t);
  }

  const monthStarts = axis
    .map((r, i) => ({ month: r.date.slice(5, 7), i }))
    .filter((m, i, arr) => i === 0 || m.month !== arr[i - 1].month);

  // v1=파랑(chart-place), 최신=초록(chart-win) — 검증된 시리즈 토큰 고정 배정
  const colorOf = (idx: number) =>
    idx === models.length - 1
      ? "var(--color-chart-win)"
      : "var(--color-chart-place)";

  const onMove = (e: React.PointerEvent<SVGSVGElement>) => {
    const rect = svgRef.current?.getBoundingClientRect();
    if (!rect) return;
    const fx = ((e.clientX - rect.left) / rect.width) * W;
    const idx = Math.round(((fx - PAD.l) / (W - PAD.l - PAD.r)) * (n - 1));
    setHoverIdx(Math.min(n - 1, Math.max(0, idx)));
  };

  const hover = hoverIdx === null ? null : axis[hoverIdx];

  return (
    <figure className="mt-4">
      <div className="mb-1 flex items-center justify-between">
        <figcaption className="text-sm font-semibold">
          누적 손익 곡선
        </figcaption>
        <div className="flex gap-3 text-xs text-muted">
          {models.map((m, i) => (
            <span key={m.version} className="inline-flex items-center gap-1">
              <span
                className="h-2 w-2 rounded-sm"
                style={{ background: colorOf(i) }}
              />
              {m.version}
              {i === models.length - 1 && " (현재)"}
            </span>
          ))}
        </div>
      </div>
      <div className="relative">
        <svg
          ref={svgRef}
          viewBox={`0 0 ${W} ${H}`}
          className="h-auto w-full select-none [touch-action:pan-y]"
          role="img"
          aria-labelledby={titleId}
          onPointerMove={onMove}
          onPointerLeave={() => setHoverIdx(null)}
        >
          <title id={titleId}>
            경주 순서에 따른 누적 손익(원) — 아래 월별 손익 표에서 수치로 확인할
            수 있습니다
          </title>
          {ticks.map((t) => (
            <g key={t}>
              <line
                x1={PAD.l}
                x2={W - PAD.r}
                y1={y(t)}
                y2={y(t)}
                stroke="var(--color-border)"
                strokeWidth={t === 0 ? 1.5 : 0.5}
              />
              <text
                x={PAD.l - 6}
                y={y(t) + 3}
                textAnchor="end"
                fontSize={10}
                fill="var(--color-muted)"
              >
                {t === 0 ? "0" : `${KRW.format(t / 1000)}천`}
              </text>
            </g>
          ))}
          {monthStarts.map(({ month, i }) => (
            <text
              key={month}
              x={x(i)}
              y={H - 6}
              fontSize={10}
              fill="var(--color-muted)"
            >
              {Number(month)}월
            </text>
          ))}
          {series.map((s, mi) => (
            <polyline
              key={models[mi].version}
              fill="none"
              stroke={colorOf(mi)}
              strokeWidth={2}
              strokeLinejoin="round"
              points={s.map((v, i) => `${x(i)},${y(v)}`).join(" ")}
            />
          ))}
          {series.map((s, mi) => (
            <text
              key={models[mi].version}
              x={W - PAD.r + 5}
              y={y(s[n - 1]) + 3}
              fontSize={10}
              fontWeight={600}
              fill={colorOf(mi)}
            >
              {models[mi].version} {KRW.format(Math.round(s[n - 1] / 1000))}천
            </text>
          ))}
          {hoverIdx !== null && (
            <g>
              <line
                x1={x(hoverIdx)}
                x2={x(hoverIdx)}
                y1={PAD.t}
                y2={H - PAD.b}
                stroke="var(--color-muted)"
                strokeWidth={1}
                strokeDasharray="3 3"
              />
              {series.map((s, mi) => (
                <circle
                  key={models[mi].version}
                  cx={x(hoverIdx)}
                  cy={y(s[hoverIdx])}
                  r={4}
                  fill={colorOf(mi)}
                  stroke="var(--color-surface)"
                  strokeWidth={2}
                />
              ))}
            </g>
          )}
        </svg>
        {hover !== null && hoverIdx !== null && (
          <div
            className="pointer-events-none absolute top-1 z-10 w-44 -translate-x-1/2 rounded-lg border border-border bg-surface p-2 text-xs shadow-lg"
            style={{
              left: `${Math.min(84, Math.max(16, (x(hoverIdx) / W) * 100))}%`,
            }}
          >
            <p className="font-semibold">
              {formatDateKo(hover.date)} {TRACKS[hover.track].name}{" "}
              {hover.raceNo}경주
            </p>
            <p className="mt-0.5 text-muted">
              픽 {hover.picks.join("·")} → 결과 {hover.actual.join("·")}
            </p>
            {models.map((m, mi) => {
              const r = m.races.find((rr) => raceKey(rr) === raceKey(hover));
              const delta = r ? raceProfit(r, pool) : 0;
              return (
                <p key={m.version} className="mt-0.5 tabular-nums">
                  <span className="text-muted">{m.version}</span>{" "}
                  <span className={profitClass(delta)}>{won(delta)}</span>{" "}
                  <span className="text-muted">
                    (누적 {won(series[mi][hoverIdx])})
                  </span>
                </p>
              );
            })}
          </div>
        )}
      </div>
    </figure>
  );
}

/* ---------- 월별 손익 표 (차트 대체 텍스트 겸용) ---------- */

function MonthlyDetails({
  models,
  pool,
}: {
  models: DashboardModel[];
  pool: PoolSel;
}) {
  const months = useMemo(() => {
    const set = new Set<string>();
    for (const m of models) for (const r of m.races) set.add(r.date.slice(0, 7));
    return [...set].sort();
  }, [models]);

  const profitOf = (m: DashboardModel, month: string) =>
    m.races
      .filter((r) => r.date.startsWith(month))
      .reduce((s, r) => s + raceProfit(r, pool), 0);

  return (
    <details className="mt-2">
      <summary className="cursor-pointer text-xs text-muted hover:text-foreground">
        월별 손익 표로 보기
      </summary>
      <table className="mt-2 w-full text-xs">
        <thead>
          <tr className="border-b border-border text-left text-muted">
            <th className="p-1.5 font-medium">월</th>
            {models.map((m) => (
              <th key={m.version} className="p-1.5 text-right font-medium">
                {m.version} 손익
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {months.map((month) => (
            <tr key={month} className="border-b border-border last:border-0">
              <td className="p-1.5">{`${Number(month.slice(5, 7))}월`}</td>
              {models.map((m) => {
                const p = profitOf(m, month);
                return (
                  <td
                    key={m.version}
                    className={`p-1.5 text-right tabular-nums ${profitClass(p)}`}
                  >
                    {won(p)}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </details>
  );
}

/* ---------- 흥미 카드 ---------- */

function HighlightCards({
  races,
  pool,
  version,
}: {
  races: BacktestRaceRow[];
  pool: PoolSel;
  version: string;
}) {
  const best = useMemo(() => findBestRace(races, pool), [races, pool]);
  const streaks = useMemo(() => computeStreaks(races, pool), [races, pool]);
  const poolName = pool === "ALL" ? "전체 합산" : POOL_LABELS[pool];

  return (
    <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
      <div className="rounded-xl border border-border bg-surface p-3">
        <p className="text-xs text-muted">
          최고의 한 방 · {poolName} ({version})
        </p>
        {best ? (
          <>
            <p
              className={`mt-1 text-lg font-bold tabular-nums ${profitClass(best.profit)}`}
            >
              {won(best.profit)}
            </p>
            <p className="mt-0.5 text-xs text-muted">
              {formatDateKo(best.race.date)} {TRACKS[best.race.track].name}{" "}
              {best.race.raceNo}경주 — {POOL_LABELS[best.topPool]}{" "}
              {KRW.format(best.topOdds)}배 적중
            </p>
          </>
        ) : (
          <p className="mt-1 text-sm text-muted">
            이 승식은 흑자 경주가 없었습니다.
          </p>
        )}
      </div>
      <div className="rounded-xl border border-border bg-surface p-3">
        <p className="text-xs text-muted">최장 연속 적중</p>
        <p className="mt-1 text-lg font-bold tabular-nums text-brand">
          {streaks.hit}경주
        </p>
        <p className="mt-0.5 text-xs text-muted">
          {pool === "ALL" ? "합산 이익 기준" : `${poolName} 적중 기준`}
        </p>
      </div>
      <div className="rounded-xl border border-border bg-surface p-3">
        <p className="text-xs text-muted">최장 연속 미적중</p>
        <p className="mt-1 text-lg font-bold tabular-nums text-status-error">
          {streaks.miss}경주
        </p>
        <p className="mt-0.5 text-xs text-muted">
          이 골짜기를 버틸 수 있는지가 실전과 시뮬의 차이입니다.
        </p>
      </div>
    </div>
  );
}

/* ---------- 승식별 비교 표 ---------- */

function PoolTable({
  models,
  pool,
  onSelect,
}: {
  models: DashboardModel[];
  pool: PoolSel;
  onSelect: (p: PoolSel) => void;
}) {
  const serving = models[models.length - 1];
  const others = models.slice(0, -1);

  return (
    <div>
      <h3 className="mb-1 text-sm font-semibold">
        승식별 성적 (장당 100원, 행을 누르면 곡선이 바뀝니다)
      </h3>
      <div className="overflow-x-auto rounded-xl border border-border bg-surface">
        <table className="w-full min-w-120 text-sm">
          <thead>
            <tr className="border-b border-border text-left text-xs text-muted">
              <th className="p-2.5 font-medium">승식</th>
              <th className="p-2.5 text-right font-medium">베팅</th>
              <th className="p-2.5 text-right font-medium">
                적중률 ({serving.version})
              </th>
              <th className="p-2.5 text-right font-medium">
                손익 ({serving.version})
              </th>
              {others.map((m) => (
                <th key={m.version} className="p-2.5 text-right font-medium">
                  손익 ({m.version})
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {serving.betting.map((b) => (
              <tr
                key={b.pool}
                onClick={() => onSelect(b.pool)}
                className={`cursor-pointer border-b border-border last:border-0 ${
                  pool === b.pool ? "bg-brand-soft/40" : "hover:bg-background"
                }`}
              >
                <td className="p-0 font-medium">
                  <button
                    aria-pressed={pool === b.pool}
                    onClick={() => onSelect(b.pool)}
                    className="w-full touch-manipulation p-2.5 text-left font-medium focus-visible:ring-2 focus-visible:ring-brand focus-visible:outline-none"
                  >
                    {b.label}
                  </button>
                </td>
                <td className="p-2.5 text-right tabular-nums">{b.bets}</td>
                <td className="p-2.5 text-right tabular-nums">
                  {b.hits}회 ({(b.hitRate * 100).toFixed(1)}%)
                </td>
                <td
                  className={`p-2.5 text-right font-semibold tabular-nums ${profitClass(b.profitKrw)}`}
                >
                  {won(b.profitKrw)}
                </td>
                {others.map((m) => {
                  const ob = m.betting.find((x) => x.pool === b.pool);
                  return (
                    <td
                      key={m.version}
                      className={`p-2.5 text-right tabular-nums ${profitClass(ob?.profitKrw ?? 0)}`}
                    >
                      {ob ? won(ob.profitKrw) : "-"}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
