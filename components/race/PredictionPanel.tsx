import type { Entry, Prediction } from "@/lib/types";
import { formatPercent } from "@/lib/format";

const CONFIDENCE_LABEL = {
  high: "신뢰도 높음",
  medium: "신뢰도 보통",
  low: "신뢰도 낮음",
} as const;

interface Props {
  prediction: Prediction;
  entries: Entry[];
}

export function PredictionPanel({ prediction, entries }: Props) {
  const horseName = (gateNo: number) =>
    entries.find((e) => e.gateNo === gateNo)?.horseName ?? `${gateNo}번`;

  return (
    <section className="rounded-xl border border-border bg-surface p-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">AI·통계 예측</h2>
        <span className="rounded-full bg-brand-soft px-2 py-0.5 text-xs font-medium text-brand">
          {CONFIDENCE_LABEL[prediction.confidence]}
        </span>
      </div>

      <dl className="mt-3 grid grid-cols-2 gap-2 text-sm">
        <div className="rounded-lg bg-background p-3">
          <dt className="text-xs text-muted">단승 추천</dt>
          <dd className="mt-0.5 font-semibold">
            {prediction.topPicks.win}번 {horseName(prediction.topPicks.win)}
          </dd>
        </div>
        <div className="rounded-lg bg-background p-3">
          <dt className="text-xs text-muted">복승 후보</dt>
          <dd className="mt-0.5 font-semibold tabular-nums">
            {prediction.topPicks.place.join(" - ")}번
          </dd>
        </div>
      </dl>

      <ol className="mt-4 space-y-2.5">
        {prediction.rankings.map((r) => (
          <li key={r.gateNo} className="text-sm">
            <div className="flex items-baseline justify-between gap-2">
              <span className="font-medium">
                <span className="text-muted">{r.predictedRank}위</span>{" "}
                {r.gateNo}번 {horseName(r.gateNo)}
              </span>
              <span className="tabular-nums text-muted">
                {formatPercent(r.winProb)}
              </span>
            </div>
            <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-border">
              <div
                className="h-full rounded-full bg-brand"
                style={{ width: `${Math.round(r.winProb * 100)}%` }}
              />
            </div>
            {r.briefComment && (
              <p className="mt-0.5 text-xs text-muted">{r.briefComment}</p>
            )}
          </li>
        ))}
      </ol>

      {prediction.aiCommentary && (
        <div className="mt-4 rounded-lg bg-background p-3 text-sm leading-relaxed">
          <h3 className="mb-1 text-xs font-medium text-muted">AI 총평</h3>
          <p>{renderBold(prediction.aiCommentary)}</p>
        </div>
      )}

      <p className="mt-3 text-xs text-muted">
        {prediction.generatedAt.slice(0, 16).replace("T", " ")} 생성 · 통계 모델{" "}
        {prediction.model.statVersion}
        {prediction.model.aiModel ? ` + AI(${prediction.model.aiModel})` : ""}
      </p>
    </section>
  );
}

/** aiCommentary의 **굵게** 마크다운만 최소 렌더링한다 */
function renderBold(text: string): React.ReactNode[] {
  return text.split(/\*\*(.+?)\*\*/g).map((part, i) =>
    i % 2 === 1 ? <strong key={i}>{part}</strong> : part,
  );
}
