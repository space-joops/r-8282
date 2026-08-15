import type { Prediction, RaceResult } from "@/lib/types";

interface Props {
  result: RaceResult;
  prediction: Prediction | null;
}

export function ResultTable({ result, prediction }: Props) {
  const predictedRank = new Map(
    (prediction?.rankings ?? []).map((r) => [r.gateNo, r.predictedRank]),
  );
  const winHit =
    prediction !== null &&
    result.order.find((o) => o.finishPos === 1)?.gateNo ===
      prediction.topPicks.win;

  return (
    <section className="rounded-xl border border-border bg-surface p-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">경주 결과</h2>
        {prediction && (
          <span
            className={`rounded-full px-2 py-0.5 text-xs font-medium ${
              winHit ? "bg-brand-soft text-brand" : "bg-border text-muted"
            }`}
          >
            단승 {winHit ? "적중" : "미적중"}
          </span>
        )}
      </div>
      <div className="mt-3 overflow-x-auto">
        <table className="w-full min-w-100 text-sm">
          <thead>
            <tr className="border-b border-border text-left text-xs text-muted">
              <th className="py-2 pr-2 font-medium">순위</th>
              <th className="py-2 pr-2 font-medium">번</th>
              <th className="py-2 pr-2 font-medium">마명</th>
              <th className="py-2 pr-2 font-medium">기록</th>
              <th className="py-2 pr-2 font-medium">착차</th>
              <th className="py-2 font-medium">예측</th>
            </tr>
          </thead>
          <tbody>
            {result.order.map((o) => {
              const predicted = predictedRank.get(o.gateNo);
              const hit = predicted !== undefined && predicted <= 3 && o.finishPos <= 3;
              return (
                <tr key={o.gateNo} className="border-b border-border last:border-0">
                  <td className="py-2 pr-2 font-bold tabular-nums">{o.finishPos}</td>
                  <td className="py-2 pr-2 tabular-nums">{o.gateNo}</td>
                  <td className="py-2 pr-2 font-medium">{o.horseName}</td>
                  <td className="py-2 pr-2 tabular-nums">
                    {o.timeSec !== null ? `${o.timeSec.toFixed(1)}초` : "-"}
                  </td>
                  <td className="py-2 pr-2 tabular-nums">{o.margin ?? "-"}</td>
                  <td className="py-2 tabular-nums">
                    {predicted !== undefined ? (
                      <span className={hit ? "font-medium text-brand" : "text-muted"}>
                        {predicted}위 예측
                      </span>
                    ) : (
                      "-"
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {result.payouts?.win != null && (
        <p className="mt-2 text-xs text-muted">
          단승 배당 {result.payouts.win.toFixed(1)}배
          {result.payouts.place
            ? ` · 연승 ${result.payouts.place.map((p) => p.toFixed(1)).join(" / ")}배`
            : ""}
        </p>
      )}
    </section>
  );
}
