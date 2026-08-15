import Link from "next/link";
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
              <th
                className="cursor-help py-2 pr-2 font-medium underline decoration-dotted underline-offset-2"
                title="한국마사회가 매기는 능력 점수 — 높을수록 강함, 미부여는 '-'"
              >
                레이팅
              </th>
              <th
                className="cursor-help py-2 pr-2 font-medium underline decoration-dotted underline-offset-2"
                title="부담중량 — 말이 짊어지는 총 무게(기수+장구). 무거울수록 불리"
              >
                부담
              </th>
              <th
                className="cursor-help py-2 pr-2 font-medium underline decoration-dotted underline-offset-2"
                title="당일 아침 몸무게. 괄호는 직전 경주 대비 증감 — 급변(±8kg↑)은 컨디션 신호"
              >
                마체중
              </th>
              <th
                className="cursor-help py-2 pr-2 font-medium underline decoration-dotted underline-offset-2"
                title="최근 1년 출전·1착 횟수와 승률"
              >
                1년 성적
              </th>
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
      <p className="mt-3 text-xs text-muted">
        용어가 낯설다면{" "}
        <Link href="/guide" className="text-brand hover:underline">
          경마 용어 가이드
        </Link>
        를 참고하세요.
      </p>
    </section>
  );
}
