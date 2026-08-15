import type { Entry } from "@/lib/types";
import { formatPercent } from "@/lib/format";

export function EntryTable({ entries }: { entries: Entry[] }) {
  return (
    <section className="rounded-xl border border-border bg-surface p-4">
      <h2 className="text-lg font-semibold">출전표</h2>
      <div className="mt-3 overflow-x-auto">
        <table className="w-full min-w-130 text-sm">
          <thead>
            <tr className="border-b border-border text-left text-xs text-muted">
              <th className="py-2 pr-2 font-medium">번</th>
              <th className="py-2 pr-2 font-medium">마명</th>
              <th className="py-2 pr-2 font-medium">성/연령</th>
              <th className="py-2 pr-2 font-medium">레이팅</th>
              <th className="py-2 pr-2 font-medium">부담</th>
              <th className="py-2 pr-2 font-medium">마체중</th>
              <th className="py-2 pr-2 font-medium">1년 성적</th>
              <th className="py-2 pr-2 font-medium">기수</th>
              <th className="py-2 font-medium">조교사</th>
            </tr>
          </thead>
          <tbody>
            {entries.map((e) => (
              <tr
                key={e.gateNo}
                className={`border-b border-border last:border-0 ${e.scratched ? "opacity-40" : ""}`}
              >
                <td className="py-2 pr-2 font-bold tabular-nums">{e.gateNo}</td>
                <td className="py-2 pr-2 font-medium">
                  {e.horseName}
                  {e.scratched && (
                    <span className="ml-1 text-xs text-muted">(출주취소)</span>
                  )}
                </td>
                <td className="py-2 pr-2 text-muted">
                  {e.sex}
                  {e.age}
                </td>
                <td className="py-2 pr-2 tabular-nums">{e.rating ?? "-"}</td>
                <td className="py-2 pr-2 tabular-nums">
                  {e.weightCarriedKg !== null ? `${e.weightCarriedKg}kg` : "미발표"}
                </td>
                <td className="py-2 pr-2 tabular-nums">
                  {e.bodyWeightKg !== null ? (
                    <>
                      {e.bodyWeightKg}
                      {e.bodyWeightDiffKg !== null && (
                        <span className="text-xs text-muted">
                          ({e.bodyWeightDiffKg > 0 ? "+" : ""}
                          {e.bodyWeightDiffKg})
                        </span>
                      )}
                    </>
                  ) : (
                    "미발표"
                  )}
                </td>
                <td className="py-2 pr-2 tabular-nums">
                  {e.record1y
                    ? `${e.record1y.starts}전 ${e.record1y.wins}승 (${formatPercent(
                        e.record1y.starts
                          ? e.record1y.wins / e.record1y.starts
                          : 0,
                      )})`
                    : "-"}
                </td>
                <td className="py-2 pr-2">
                  {e.jockey.name}
                  {e.jockeyChanged && (
                    <span className="ml-1 rounded bg-track-busan/10 px-1 text-xs text-track-busan">
                      변경
                    </span>
                  )}
                </td>
                <td className="py-2">{e.trainer.name}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
