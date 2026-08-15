import Link from "next/link";
import type { RaceSummary, TrackSlug } from "@/lib/types";

interface Props {
  date: string;
  track: TrackSlug;
  race: RaceSummary;
}

export function RaceCard({ date, track, race }: Props) {
  return (
    <Link
      href={`/races/${date}/${track}/${race.raceNo}`}
      className="flex items-center justify-between rounded-xl border border-border bg-surface p-4 transition-colors hover:border-brand"
    >
      <div className="flex items-center gap-3">
        <span className="text-lg font-bold tabular-nums">
          {race.raceNo}
          <span className="text-sm font-normal text-muted">경주</span>
        </span>
        <div className="text-sm text-muted">
          <p>
            {race.startTimeKst} 발주 · {race.distanceM}m · {race.grade}
          </p>
          <p>{race.entryCount}두 출전</p>
        </div>
      </div>
      <div className="flex gap-1.5">
        {race.canceled ? (
          <Badge tone="muted">취소</Badge>
        ) : (
          <>
            {race.hasPrediction && <Badge tone="brand">예측</Badge>}
            {race.hasResult && <Badge tone="muted">결과</Badge>}
          </>
        )}
      </div>
    </Link>
  );
}

function Badge({
  tone,
  children,
}: {
  tone: "brand" | "muted";
  children: React.ReactNode;
}) {
  const styles =
    tone === "brand"
      ? "bg-brand-soft text-brand"
      : "bg-border text-muted";
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${styles}`}>
      {children}
    </span>
  );
}
