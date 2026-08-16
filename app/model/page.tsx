import type { Metadata } from "next";
import Link from "next/link";
import BettingDashboard, {
  type DashboardModel,
} from "@/components/model/BettingDashboard";
import { getBacktest, getBacktestRaces } from "@/lib/data";
import { formatDateKo, formatPercent } from "@/lib/format";
import { TRACKS, TRACK_ORDER } from "@/lib/tracks";
import type { BacktestMetric, BacktestModel } from "@/lib/types";

export const metadata: Metadata = {
  title: "모델 성적표 (백테스트)",
  description:
    "경마픽 예측 모델의 과거 성적 전부 — 승식별 베팅 시뮬레이션 손익 곡선, 단승·연승 적중률, log-loss를 버전별로 투명하게 공개합니다",
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
  const [backtest, backtestRaces] = await Promise.all([
    getBacktest(),
    getBacktestRaces(),
  ]);

  const dashboardModels: DashboardModel[] = (backtest?.models ?? []).flatMap(
    (m) => {
      const races = backtestRaces?.models.find(
        (r) => r.version === m.version,
      )?.races;
      return races?.length
        ? [{ version: m.version, betting: m.betting, races }]
        : [];
    },
  );
  const serving = backtest?.models.at(-1) ?? null;
  const periodLabel = serving
    ? `${formatDateKo(serving.periodFrom)}~${formatDateKo(serving.periodTo)} ${serving.overall.races}경주`
    : "";

  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-2xl font-bold">모델 성적표</h1>
        <p className="mt-1 text-sm text-muted">
          과거 경주에 모델을 그대로 적용해 실제 결과와 대조했습니다 — 좋은
          것도, 나쁜 것도 전부 공개합니다.
        </p>
      </header>

      <section className="rounded-xl border border-border bg-surface p-4 text-sm leading-relaxed">
        <h2 className="font-semibold">읽기 전에</h2>
        <ul className="mt-2 list-disc space-y-1 pl-5 text-muted">
          <li>
            손익이 마이너스인 것은{" "}
            <strong className="text-foreground">정직한 공개</strong>입니다.
            경마는 파리뮤추얼 방식이라 환급률(약 73~80%)만큼 전체 참가자가
            함께 잃습니다 — 무작위 베팅도 -20%대가 나오며, 모델의 목표는 이
            선을 넘는 것입니다.
          </li>
          <li>
            백테스트는 <strong className="text-foreground">사후 시뮬레이션</strong>
            입니다 — 경주 전에 실제로 공개한 예측의 실적은{" "}
            <Link href="/results" className="text-brand hover:underline">
              적중률 추적
            </Link>
            에서 확인하세요.
          </li>
          <li>
            경마픽은 베팅을 권유하지 않습니다. 이 페이지는 모델을 참고할지
            스스로 판단할 근거를 드리기 위한 것입니다.
          </li>
        </ul>
      </section>

      {!backtest || backtest.models.length === 0 ? (
        <p className="rounded-xl border border-border bg-surface p-4 text-sm text-muted">
          아직 공개된 백테스트가 없습니다.
        </p>
      ) : (
        <>
          {dashboardModels.length > 0 && (
            <BettingDashboard
              models={dashboardModels}
              periodLabel={periodLabel}
            />
          )}

          <section className="space-y-4">
            <h2 className="text-lg font-semibold">상세 지표</h2>
            {backtest.models.length > 1 && (
              <VersionCompare models={backtest.models} />
            )}
            {[...backtest.models].reverse().map((model, i) => (
              <ModelCard key={model.version} model={model} serving={i === 0} />
            ))}
          </section>
        </>
      )}
    </div>
  );
}

function VersionCompare({ models }: { models: BacktestModel[] }) {
  return (
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
        <h3 className="text-lg font-semibold">
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
        </h3>
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
            <h4 className="text-sm font-semibold">신뢰도별 단승/연승</h4>
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
            <h4 className="text-sm font-semibold">경마장별 단승/연승</h4>
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

      {model.monthly.length > 0 && (
        <div>
          <div className="mb-2 flex items-center justify-between">
            <h4 className="text-sm font-semibold">월별 단승/연승</h4>
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
