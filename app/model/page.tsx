import type { Metadata } from "next";
import Link from "next/link";
import { getBacktest } from "@/lib/data";
import { formatDateKo, formatPercent } from "@/lib/format";
import { TRACKS, TRACK_ORDER } from "@/lib/tracks";
import type { BacktestMetric, BacktestModel, BettingEntry } from "@/lib/types";

export const metadata: Metadata = {
  title: "모델 성능 (백테스트)",
  description:
    "경마픽 예측 모델의 과거 경주 백테스트 성능 — 단승·연승 적중률, log-loss, 실배당 기반 ROI를 버전별로 투명하게 공개합니다",
  alternates: { canonical: "/model" },
};

const CONFIDENCE_LABEL = {
  high: "신뢰도 높음",
  medium: "신뢰도 보통",
  low: "신뢰도 낮음",
} as const;

function roiText(roi: number | null): string {
  if (roi === null) return "-";
  return `${roi > 0 ? "+" : ""}${(roi * 100).toFixed(1)}%`;
}

export default async function ModelPage() {
  const backtest = await getBacktest();

  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-2xl font-bold">모델 성능 (백테스트)</h1>
        <p className="mt-1 text-sm text-muted">
          과거 경주에 모델을 그대로 적용해 실제 결과와 대조한 시뮬레이션입니다.
        </p>
      </header>

      <section className="rounded-xl border border-border bg-surface p-4 text-sm leading-relaxed">
        <h2 className="font-semibold">읽기 전에</h2>
        <ul className="mt-2 list-disc space-y-1 pl-5 text-muted">
          <li>
            백테스트는 <strong className="text-foreground">사후 시뮬레이션</strong>
            입니다 — 경주 전에 실제로 공개한 예측의 실적은{" "}
            <Link href="/results" className="text-brand hover:underline">
              적중률 추적
            </Link>
            에서 확인하세요.
          </li>
          <li>
            ROI는 매 경주 단승/연승 추천마에 1단위씩 균등 베팅했을 때의
            손익률(실제 확정 배당 기준)입니다. 참고 지표일 뿐 수익을 보장하지
            않습니다.
          </li>
          <li>
            log-loss는 낮을수록 확률 추정이 정확하다는 뜻입니다 (무작위 찍기보다
            낮아야 의미).
          </li>
        </ul>
      </section>

      {!backtest || backtest.models.length === 0 ? (
        <p className="rounded-xl border border-border bg-surface p-4 text-sm text-muted">
          아직 공개된 백테스트가 없습니다.
        </p>
      ) : (
        <>
          {backtest.models.length > 1 && (
            <VersionCompare models={backtest.models} />
          )}
          {[...backtest.models].reverse().map((model, i) => (
            <ModelCard key={model.version} model={model} serving={i === 0} />
          ))}
        </>
      )}
    </div>
  );
}

function VersionCompare({ models }: { models: BacktestModel[] }) {
  return (
    <section>
      <h2 className="mb-3 text-lg font-semibold">버전 비교</h2>
      <div className="overflow-hidden rounded-xl border border-border bg-surface">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-left text-xs text-muted">
              <th className="p-3 font-medium">버전</th>
              <th className="p-3 font-medium">경주</th>
              <th className="p-3 font-medium">단승</th>
              <th className="p-3 font-medium">연승</th>
              <th className="p-3 font-medium">log-loss</th>
              <th className="p-3 font-medium">단승 ROI</th>
            </tr>
          </thead>
          <tbody>
            {models.map((m) => (
              <tr key={m.version} className="border-b border-border last:border-0">
                <td className="p-3 font-semibold">{m.version}</td>
                <td className="p-3 tabular-nums">{m.overall.races}</td>
                <td className="p-3 tabular-nums">
                  {formatPercent(m.overall.winRate)}
                </td>
                <td className="p-3 tabular-nums">
                  {formatPercent(m.overall.placeRate)}
                </td>
                <td className="p-3 tabular-nums">
                  {m.overall.logLoss?.toFixed(3) ?? "-"}
                </td>
                <td className="p-3 tabular-nums">{roiText(m.overall.roiWin)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function ModelCard({
  model,
  serving,
}: {
  model: BacktestModel;
  serving: boolean;
}) {
  return (
    <section className="space-y-4 rounded-xl border border-border bg-surface p-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-lg font-semibold">
          모델 {model.version}
          {serving ? (
            <span className="ml-2 rounded-full bg-brand-soft px-2 py-0.5 text-xs font-medium text-brand">
              현재 서비스 중
            </span>
          ) : (
            <span className="ml-2 rounded-full bg-border px-2 py-0.5 text-xs font-medium text-muted">
              이전 버전
            </span>
          )}
        </h2>
        <p className="text-xs text-muted">
          {formatDateKo(model.periodFrom)} ~ {formatDateKo(model.periodTo)} ·{" "}
          {model.overall.races}경주
        </p>
      </div>

      <dl className="grid grid-cols-2 gap-2 sm:grid-cols-3">
        <StatTile label="단승 적중률" value={formatPercent(model.overall.winRate)} highlight />
        <StatTile label="연승 적중률" value={formatPercent(model.overall.placeRate)} />
        <StatTile
          label="삼복 정순"
          value={`${model.overall.top3ExactHits}회`}
        />
        <StatTile
          label="log-loss"
          value={model.overall.logLoss?.toFixed(3) ?? "-"}
        />
        <StatTile label="단승 ROI" value={roiText(model.overall.roiWin)} />
        <StatTile label="연승 ROI" value={roiText(model.overall.roiPlace)} />
      </dl>

      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <div className="mb-2 flex items-center justify-between">
            <h3 className="text-sm font-semibold">신뢰도별 단승/연승</h3>
            <Legend />
          </div>
          <div className="space-y-2">
            {(["high", "medium", "low"] as const).map((c) => (
              <MetricBars
                key={c}
                label={CONFIDENCE_LABEL[c]}
                metric={model.byConfidence[c]}
              />
            ))}
          </div>
        </div>
        <div>
          <div className="mb-2 flex items-center justify-between">
            <h3 className="text-sm font-semibold">경마장별 단승/연승</h3>
            <Legend />
          </div>
          <div className="space-y-2">
            {TRACK_ORDER.map((slug) => (
              <MetricBars
                key={slug}
                label={TRACKS[slug].name}
                labelClass={TRACKS[slug].colorClass}
                metric={model.byTrack[slug]}
              />
            ))}
          </div>
        </div>
      </div>

      <BettingTable betting={model.betting} />

      {model.monthly.length > 0 && (
        <div>
          <div className="mb-2 flex items-center justify-between">
            <h3 className="text-sm font-semibold">월별 단승/연승</h3>
            <Legend />
          </div>
          <div className="space-y-2">
            {model.monthly.map((m) => (
              <MetricBars
                key={m.month}
                label={`${Number(m.month.slice(5, 7))}월`}
                metric={m}
              />
            ))}
          </div>
        </div>
      )}

      <p className="text-xs leading-relaxed text-muted">{model.note}</p>
    </section>
  );
}

const KRW = new Intl.NumberFormat("ko-KR");

function BettingTable({ betting }: { betting: BettingEntry[] }) {
  if (betting.length === 0) return null;
  return (
    <div>
      <h3 className="mb-1 text-sm font-semibold">
        승식별 베팅 시뮬레이션 (장당 100원)
      </h3>
      <p className="mb-2 text-xs text-muted">
        예측 1·2·3순위를 각 승식에 그대로 1장씩 — 발매된 경주만 베팅, 실제
        확정 배당 기준.{" "}
        <Link href="/guide#betting" className="text-brand hover:underline">
          승식 설명
        </Link>
      </p>
      <div className="overflow-x-auto rounded-lg border border-border">
        <table className="w-full min-w-130 text-sm">
          <thead>
            <tr className="border-b border-border text-left text-xs text-muted">
              <th className="p-2.5 font-medium">승식</th>
              <th className="p-2.5 text-right font-medium">베팅</th>
              <th className="p-2.5 text-right font-medium">적중</th>
              <th className="p-2.5 text-right font-medium">적중률</th>
              <th className="p-2.5 text-right font-medium">베팅액</th>
              <th className="p-2.5 text-right font-medium">회수액</th>
              <th className="p-2.5 text-right font-medium">손익</th>
            </tr>
          </thead>
          <tbody>
            {betting.map((b) => (
              <tr key={b.pool} className="border-b border-border last:border-0">
                <td className="p-2.5 font-medium">{b.label}</td>
                <td className="p-2.5 text-right tabular-nums">{b.bets}</td>
                <td className="p-2.5 text-right tabular-nums">{b.hits}</td>
                <td className="p-2.5 text-right tabular-nums">
                  {formatPercent(b.hitRate)}
                </td>
                <td className="p-2.5 text-right tabular-nums">
                  {KRW.format(b.stakeKrw)}원
                </td>
                <td className="p-2.5 text-right tabular-nums">
                  {KRW.format(b.returnedKrw)}원
                </td>
                <td
                  className={`p-2.5 text-right font-semibold tabular-nums ${
                    b.profitKrw > 0
                      ? "text-brand"
                      : b.profitKrw < 0
                        ? "text-status-error"
                        : "text-muted"
                  }`}
                >
                  {b.profitKrw > 0 ? "+" : ""}
                  {KRW.format(b.profitKrw)}원
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function StatTile({
  label,
  value,
  highlight = false,
}: {
  label: string;
  value: string;
  highlight?: boolean;
}) {
  return (
    <div className="rounded-lg bg-background p-3">
      <dt className="text-xs text-muted">{label}</dt>
      <dd
        className={`mt-0.5 text-lg font-bold tabular-nums ${highlight ? "text-brand" : ""}`}
      >
        {value}
      </dd>
    </div>
  );
}

function Legend() {
  return (
    <div className="flex gap-3 text-xs text-muted">
      <span className="inline-flex items-center gap-1">
        <span className="h-2 w-2 rounded-sm bg-chart-win" /> 단승
      </span>
      <span className="inline-flex items-center gap-1">
        <span className="h-2 w-2 rounded-sm bg-chart-place" /> 연승
      </span>
    </div>
  );
}

function MetricBars({
  label,
  labelClass = "",
  metric,
}: {
  label: string;
  labelClass?: string;
  metric: BacktestMetric;
}) {
  return (
    <div className="flex items-center gap-2 text-sm">
      <span className={`w-20 shrink-0 text-xs ${labelClass}`}>{label}</span>
      <div className="flex-1 space-y-0.5">
        <div className="h-2 overflow-hidden rounded-full bg-border/60">
          <div
            className="h-full rounded-full bg-chart-win"
            style={{ width: `${Math.round(metric.winRate * 100)}%` }}
          />
        </div>
        <div className="h-2 overflow-hidden rounded-full bg-border/60">
          <div
            className="h-full rounded-full bg-chart-place"
            style={{ width: `${Math.round(metric.placeRate * 100)}%` }}
          />
        </div>
      </div>
      <span className="w-28 shrink-0 text-right text-xs tabular-nums text-muted">
        {metric.races
          ? `${formatPercent(metric.winRate)} / ${formatPercent(metric.placeRate)} · ${metric.races}`
          : "0경주"}
      </span>
    </div>
  );
}
