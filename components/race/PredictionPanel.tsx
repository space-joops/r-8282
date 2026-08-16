import Link from "next/link";
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
        <h2 className="text-lg font-semibold">AI 경주 브리핑</h2>
        <span
          className="cursor-help rounded-full bg-brand-soft px-2 py-0.5 text-xs font-medium text-brand"
          title="예측 1위와 2위의 승률 격차 기준 — 높음(뚜렷한 우세)/보통/낮음(혼전)"
        >
          {CONFIDENCE_LABEL[prediction.confidence]}
        </span>
      </div>

      {prediction.aiCommentary && (
        <div className="mt-3 border-l-2 border-brand pl-3 text-sm leading-relaxed">
          <p>{renderBold(prediction.aiCommentary)}</p>
        </div>
      )}

      <p className="mt-3 text-xs text-muted">
        모델 상위 후보 — 단승{" "}
        <strong className="text-foreground">
          {prediction.topPicks.win}번 {horseName(prediction.topPicks.win)}
        </strong>{" "}
        · 복승 {prediction.topPicks.place.join("-")}번. 어디까지나 통계적
        후보입니다 — 아래 근거를 보고 직접 판단하세요.
      </p>

      <ol className="mt-4 space-y-2.5">
        {prediction.rankings.map((r) => (
          <li key={r.gateNo} className="text-sm">
            <div className="flex items-baseline justify-between gap-2">
              <span className="font-medium">
                <span className="text-muted">{r.predictedRank}위</span>{" "}
                {r.gateNo}번 {horseName(r.gateNo)}
              </span>
              <span
                className="cursor-help tabular-nums text-muted"
                title="모델이 추정한 1착 확률 — 경주 내 합계 100%"
              >
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
              <p className="mt-0.5 text-sm leading-snug">{r.briefComment}</p>
            )}
          </li>
        ))}
      </ol>

      <p className="mt-4 flex flex-wrap items-center justify-between gap-2 text-xs text-muted">
        <span>
          {prediction.generatedAt.slice(0, 16).replace("T", " ")} 생성 · 통계
          모델 {prediction.model.statVersion}
          {prediction.model.aiModel ? ` + AI(${prediction.model.aiModel})` : ""}
        </span>
        <Link href="/model" className="text-brand hover:underline">
          이 모델의 과거 성적·손익 전부 보기
        </Link>
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
