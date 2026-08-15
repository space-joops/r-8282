import type { Metadata } from "next";
import Link from "next/link";
import {
  getOpsRuns,
  listJudgedRaces,
  type JudgedRace,
  type OpsRun,
} from "@/lib/admin";
import { getAccuracy, getDataIndex, getMeet } from "@/lib/data";
import { formatDateKo, formatPercent } from "@/lib/format";
import { TRACKS } from "@/lib/tracks";
import type { Meet } from "@/lib/types";
import {
  PREDICT_SLOTS,
  RESULTS_SLOTS,
  formatAgo,
  lastDueSlot,
} from "@/components/admin/schedule";

// 이 사이트 유일의 동적 라우트 — 방문 시마다 최신 운영 데이터를 읽는다.
// (proxy.ts의 Basic Auth 뒤에 있으며, 동적 렌더이므로 요청 시각 사용 허용)
export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "운영 대시보드",
  robots: { index: false, follow: false },
};

const STATUS_META: Record<
  OpsRun["status"],
  { label: string; chip: string; badge: string }
> = {
  success: {
    label: "성공",
    chip: "bg-chart-win",
    badge: "bg-brand-soft text-brand",
  },
  no_change: {
    label: "변경 없음",
    chip: "bg-muted/50",
    badge: "bg-border text-muted",
  },
  no_races: {
    label: "개최 없음",
    chip: "bg-border",
    badge: "bg-border text-muted",
  },
  error: {
    label: "✕ 오류",
    chip: "bg-status-error",
    badge: "bg-status-error/10 text-status-error",
  },
};

const KIND_LABEL = { predict: "예측", results: "결과" } as const;

export default async function AdminPage() {
  // force-dynamic 라우트의 요청 시각 스냅숏 — 신선도 계산 기준점 (의도된 비순수)
  // eslint-disable-next-line react-hooks/purity
  const now = Date.now();
  const [runs, index, accuracy, judged] = await Promise.all([
    getOpsRuns(30),
    getDataIndex(),
    getAccuracy(),
    listJudgedRaces(),
  ]);
  const meets = await Promise.all(index.meetDates.map((d) => getMeet(d)));

  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-2xl font-bold">운영 대시보드</h1>
        <p className="mt-1 text-sm text-muted">
          파이프라인 실행 이력·데이터 커버리지·적중률 심화 — 관리자 전용
        </p>
      </header>

      <FreshnessSection runs={runs} now={now} />
      <OpsRunsSection runs={runs} now={now} />
      <CoverageSection meets={meets} />
      <ConfidenceSection judged={judged} />
      <TrendSection history={accuracy.history} />
    </div>
  );
}

/* ── 타이머 생존 ─────────────────────────────────────────── */

function FreshnessSection({
  runs,
  now,
}: {
  runs: OpsRun[] | null;
  now: number;
}) {
  const kinds = [
    { kind: "predict" as const, slots: PREDICT_SLOTS },
    { kind: "results" as const, slots: RESULTS_SLOTS },
  ];
  return (
    <section className="grid gap-2 sm:grid-cols-2">
      {kinds.map(({ kind, slots }) => {
        const newest = runs?.find((r) => r.kind === kind) ?? null;
        const due = lastDueSlot(slots, now);
        const missed =
          due !== null && (!newest || Date.parse(newest.started_at) < due);
        return (
          <div
            key={kind}
            className={`rounded-xl border bg-surface p-4 ${
              missed ? "border-status-error" : "border-border"
            }`}
          >
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold">
                {KIND_LABEL[kind]} 타이머
              </h2>
              {newest && (
                <span
                  className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_META[newest.status].badge}`}
                >
                  {STATUS_META[newest.status].label}
                </span>
              )}
            </div>
            <p className="mt-2 text-lg font-bold">
              {newest
                ? formatAgo(Date.parse(newest.started_at), now)
                : "기록 없음"}
            </p>
            <p className="text-xs text-muted">
              {newest
                ? `${newest.target_date} 대상 · ${newest.source === "timer" ? "자동" : "수동"} 실행`
                : "아직 텔레메트리 기록이 없습니다"}
            </p>
            {missed && (
              <p className="mt-2 text-xs font-medium text-status-error">
                ⚠ 예정된 실행이 기록되지 않았습니다 — 노트북 전원/타이머 확인
                (오프라인이면 부팅 후 자동 보충됨)
              </p>
            )}
          </div>
        );
      })}
    </section>
  );
}

/* ── 실행 이력 ───────────────────────────────────────────── */

function metricsSummary(run: OpsRun): string {
  const m = run.metrics ?? {};
  const num = (key: string) => {
    const v = m[key];
    return typeof v === "number" ? v : null;
  };
  const parts: string[] = [];
  if (run.kind === "predict") {
    const ok = num("aiOk");
    const fb = num("aiFallback");
    if (ok !== null && fb !== null) parts.push(`AI ${ok}/${ok + fb}`);
    if (num("withPrediction") !== null)
      parts.push(`예측 ${num("withPrediction")}건`);
  } else {
    if (num("applied") !== null) parts.push(`반영 ${num("applied")}건`);
    if (num("canceled")) parts.push(`취소 ${num("canceled")}건`);
  }
  if (num("changed") !== null) parts.push(`변경 ${num("changed")}`);
  if (num("httpCalls") !== null) parts.push(`API ${num("httpCalls")}회`);
  return parts.join(" · ") || "-";
}

function OpsRunsSection({ runs, now }: { runs: OpsRun[] | null; now: number }) {
  return (
    <section>
      <h2 className="mb-3 text-lg font-semibold">실행 이력</h2>
      {runs === null ? (
        <p className="rounded-xl border border-border bg-surface p-4 text-sm text-muted">
          Supabase가 구성되지 않았거나 조회에 실패했습니다 — env(SUPABASE_URL,
          SUPABASE_SERVICE_KEY)와 <code>supabase/schema.sql</code> 적용 여부를
          확인하세요.
        </p>
      ) : runs.length === 0 ? (
        <p className="rounded-xl border border-border bg-surface p-4 text-sm text-muted">
          아직 기록된 실행이 없습니다 — 다음 파이프라인 실행부터 쌓입니다.
        </p>
      ) : (
        <div className="rounded-xl border border-border bg-surface p-4">
          {/* 최근 30회 상태 스트립 (오른쪽이 최신) — 상세는 아래 표에 텍스트로 */}
          <div className="flex flex-wrap gap-0.5" aria-hidden>
            {[...runs].reverse().map((run) => (
              <span
                key={run.id}
                title={`${run.target_date} ${KIND_LABEL[run.kind]} — ${STATUS_META[run.status].label}`}
                className={`h-3 w-3 rounded-sm ${STATUS_META[run.status].chip}`}
              />
            ))}
          </div>
          <div className="mt-3 overflow-x-auto">
            <table className="w-full min-w-140 text-sm">
              <thead>
                <tr className="border-b border-border text-left text-xs text-muted">
                  <th className="py-2 pr-2 font-medium">실행</th>
                  <th className="py-2 pr-2 font-medium">종류</th>
                  <th className="py-2 pr-2 font-medium">대상일</th>
                  <th className="py-2 pr-2 font-medium">상태</th>
                  <th className="py-2 pr-2 font-medium">소요</th>
                  <th className="py-2 pr-2 font-medium">요약</th>
                  <th className="py-2 font-medium">주체</th>
                </tr>
              </thead>
              <tbody>
                {runs.map((run) => (
                  <tr key={run.id} className="border-b border-border last:border-0">
                    <td className="py-2 pr-2 tabular-nums text-muted">
                      {formatAgo(Date.parse(run.started_at), now)}
                    </td>
                    <td className="py-2 pr-2">{KIND_LABEL[run.kind]}</td>
                    <td className="py-2 pr-2 tabular-nums">{run.target_date}</td>
                    <td className="py-2 pr-2">
                      <span
                        className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_META[run.status].badge}`}
                        title={run.error ?? undefined}
                      >
                        {STATUS_META[run.status].label}
                      </span>
                    </td>
                    <td className="py-2 pr-2 tabular-nums">
                      {run.duration_sec !== null
                        ? `${Math.round(run.duration_sec)}초`
                        : "-"}
                    </td>
                    <td className="py-2 pr-2 text-muted">
                      {metricsSummary(run)}
                    </td>
                    <td className="py-2 text-muted">
                      {run.source === "timer" ? "자동" : "수동"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </section>
  );
}

/* ── 데이터 커버리지 ─────────────────────────────────────── */

function CoverageSection({ meets }: { meets: Meet[] }) {
  const pending = meets.flatMap((meet) =>
    meet.tracks.flatMap((t) =>
      t.races
        .filter((r) => r.hasPrediction && !r.hasResult && !r.canceled)
        .map((r) => ({ date: meet.date, track: t.track, raceNo: r.raceNo })),
    ),
  );

  return (
    <section>
      <h2 className="mb-3 text-lg font-semibold">데이터 커버리지</h2>
      <div className="overflow-hidden rounded-xl border border-border bg-surface">
        <div className="overflow-x-auto">
          <table className="w-full min-w-120 text-sm">
            <thead>
              <tr className="border-b border-border text-left text-xs text-muted">
                <th className="p-3 font-medium">개최일</th>
                <th className="p-3 font-medium">경마장</th>
                <th className="p-3 font-medium">경주</th>
                <th className="p-3 font-medium">예측</th>
                <th className="p-3 font-medium">결과</th>
                <th className="p-3 font-medium">상태</th>
              </tr>
            </thead>
            <tbody>
              {meets.flatMap((meet) =>
                meet.tracks.map((t, ti) => {
                  const total = t.races.length;
                  const pred = t.races.filter((r) => r.hasPrediction).length;
                  const res = t.races.filter((r) => r.hasResult).length;
                  const cancel = t.races.filter((r) => r.canceled).length;
                  const open = t.races.filter(
                    (r) => r.hasPrediction && !r.hasResult && !r.canceled,
                  ).length;
                  const complete = res + cancel >= total;
                  return (
                    <tr
                      key={`${meet.date}-${t.track}`}
                      className="border-b border-border last:border-0"
                    >
                      <td className="p-3">
                        {ti === 0 ? (
                          <Link
                            href={`/races/${meet.date}`}
                            className="font-medium hover:text-brand"
                          >
                            {formatDateKo(meet.date)}
                          </Link>
                        ) : null}
                      </td>
                      <td className={`p-3 ${TRACKS[t.track].colorClass}`}>
                        {t.trackName}
                      </td>
                      <td className="p-3 tabular-nums">{total}</td>
                      <td className="p-3 tabular-nums">
                        {pred}/{total}
                      </td>
                      <td className="p-3 tabular-nums">
                        {res}/{total}
                        {cancel > 0 && (
                          <span className="text-xs text-muted"> (취소 {cancel})</span>
                        )}
                      </td>
                      <td className="p-3">
                        {open > 0 ? (
                          <span className="rounded-full bg-status-error/10 px-2 py-0.5 text-xs font-medium text-status-error">
                            미확정 {open}
                          </span>
                        ) : complete ? (
                          <span className="rounded-full bg-brand-soft px-2 py-0.5 text-xs font-medium text-brand">
                            완결
                          </span>
                        ) : (
                          <span className="rounded-full bg-border px-2 py-0.5 text-xs font-medium text-muted">
                            진행 중
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                }),
              )}
            </tbody>
          </table>
        </div>
        {pending.length > 0 && (
          <p className="border-t border-border p-3 text-xs text-muted">
            미확정:{" "}
            {pending.map((p, i) => (
              <span key={`${p.date}-${p.track}-${p.raceNo}`}>
                {i > 0 && " · "}
                <Link
                  href={`/races/${p.date}/${p.track}/${p.raceNo}`}
                  className="text-brand hover:underline"
                >
                  {formatDateKo(p.date)} {TRACKS[p.track].name} {p.raceNo}경주
                </Link>
              </span>
            ))}
          </p>
        )}
      </div>
    </section>
  );
}

/* ── 적중률 심화 ─────────────────────────────────────────── */

function RateBars({ win, place }: { win: number; place: number }) {
  return (
    <div className="flex-1 space-y-1">
      <div className="h-2 overflow-hidden rounded-full bg-border/60">
        <div
          className="h-full rounded-full bg-chart-win"
          style={{ width: `${Math.round(win * 100)}%` }}
        />
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-border/60">
        <div
          className="h-full rounded-full bg-chart-place"
          style={{ width: `${Math.round(place * 100)}%` }}
        />
      </div>
    </div>
  );
}

function SeriesLegend() {
  return (
    <div className="flex gap-4 text-xs text-muted">
      <span className="inline-flex items-center gap-1.5">
        <span className="h-2.5 w-2.5 rounded-sm bg-chart-win" /> 단승 적중률
      </span>
      <span className="inline-flex items-center gap-1.5">
        <span className="h-2.5 w-2.5 rounded-sm bg-chart-place" /> 연승 적중률
      </span>
    </div>
  );
}

const CONFIDENCE_LABEL = {
  high: "신뢰도 높음",
  medium: "신뢰도 보통",
  low: "신뢰도 낮음",
} as const;

function ConfidenceSection({ judged }: { judged: JudgedRace[] }) {
  const buckets = (["high", "medium", "low"] as const).map((confidence) => {
    const rows = judged.filter((j) => j.confidence === confidence);
    const races = rows.length;
    const winHits = rows.filter((j) => j.winHit).length;
    const placeHits = rows.filter((j) => j.placeHit).length;
    return {
      confidence,
      races,
      winRate: races ? winHits / races : 0,
      placeRate: races ? placeHits / races : 0,
    };
  });

  return (
    <section>
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-lg font-semibold">신뢰도별 적중률</h2>
        <SeriesLegend />
      </div>
      <div className="space-y-3 rounded-xl border border-border bg-surface p-4">
        {judged.length === 0 && (
          <p className="text-sm text-muted">아직 평가된 경주가 없습니다.</p>
        )}
        {buckets.map((b) => (
          <div key={b.confidence} className="flex items-center gap-3 text-sm">
            <span className="w-24 shrink-0">
              {CONFIDENCE_LABEL[b.confidence]}
            </span>
            <RateBars win={b.winRate} place={b.placeRate} />
            <span className="w-36 shrink-0 text-right text-xs tabular-nums text-muted">
              {b.races
                ? `${formatPercent(b.winRate)} / ${formatPercent(b.placeRate)} · ${b.races}경주`
                : "0경주"}
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}

function TrendSection({
  history,
}: {
  history: { date: string; races: number; winHits: number; placeHits: number }[];
}) {
  if (history.length === 0) return null;
  return (
    <section>
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-lg font-semibold">개최일별 트렌드</h2>
        <SeriesLegend />
      </div>
      <div className="space-y-3 rounded-xl border border-border bg-surface p-4">
        {[...history].reverse().map((h) => (
          <div key={h.date} className="flex items-center gap-3 text-sm">
            <span className="w-24 shrink-0">{formatDateKo(h.date)}</span>
            <RateBars
              win={h.races ? h.winHits / h.races : 0}
              place={h.races ? h.placeHits / h.races : 0}
            />
            <span className="w-36 shrink-0 text-right text-xs tabular-nums text-muted">
              {formatPercent(h.races ? h.winHits / h.races : 0)} /{" "}
              {formatPercent(h.races ? h.placeHits / h.races : 0)} · {h.races}
              경주
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}
