import type { Metadata } from "next";
import Link from "next/link";
import { EntryTable } from "@/components/race/EntryTable";
import { PredictionPanel } from "@/components/race/PredictionPanel";
import { ResultTable } from "@/components/race/ResultTable";
import { getRace, listAllRaces } from "@/lib/data";
import { formatDateKo, formatRaceLabel } from "@/lib/format";
import { TRACKS } from "@/lib/tracks";
import { trackSlugSchema } from "@/lib/types";

export const dynamicParams = false;

export async function generateStaticParams() {
  const races = await listAllRaces();
  return races.map(({ date, track, raceNo }) => ({
    date,
    track,
    raceNo: String(raceNo),
  }));
}

type Props = PageProps<"/races/[date]/[track]/[raceNo]">;

async function loadRace(params: Props["params"]) {
  const { date, track: rawTrack, raceNo } = await params;
  const track = trackSlugSchema.parse(rawTrack);
  return getRace(date, track, Number(raceNo));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const race = await loadRace(params);
  const label = formatRaceLabel(race.track, race.raceNo);
  return {
    title: `${formatDateKo(race.date)} ${label} 예측·출전표`,
    description: `${formatDateKo(race.date)} ${label}(${race.distanceM}m, ${race.grade}) 출전표와 AI·통계 예측${race.result ? ", 경주 결과" : ""}`,
  };
}

export default async function RacePage({ params }: Props) {
  const race = await loadRace(params);

  return (
    <div className="space-y-4">
      <header>
        <p className="text-sm text-muted">
          <Link href={`/races/${race.date}`} className="hover:text-brand">
            {formatDateKo(race.date)}
          </Link>
        </p>
        <h1 className="mt-1 text-2xl font-bold">
          <span className={TRACKS[race.track].colorClass}>
            {TRACKS[race.track].name}
          </span>{" "}
          {race.raceNo}경주
        </h1>
        <p className="mt-1 text-sm text-muted">
          {race.startTimeKst} 발주 · {race.distanceM}m · {race.grade}
          {race.ageCond ? ` · ${race.ageCond}` : ""}
          {race.weather ? ` · ${race.weather}` : ""}
          {race.trackCond ? ` · ${race.trackCond}` : ""}
        </p>
      </header>

      {race.result && (
        <ResultTable result={race.result} prediction={race.prediction} />
      )}

      {race.prediction ? (
        <PredictionPanel prediction={race.prediction} entries={race.entries} />
      ) : (
        <p className="rounded-xl border border-border bg-surface p-4 text-sm text-muted">
          이 경주의 예측은 아직 준비되지 않았습니다.
        </p>
      )}

      {race.entries.length > 0 ? (
        <EntryTable entries={race.entries} />
      ) : (
        <p className="rounded-xl border border-border bg-surface p-4 text-sm text-muted">
          출전표가 아직 발표되지 않았습니다.
        </p>
      )}

      <p className="text-xs text-muted">
        예측은 통계·AI 기반 참고 정보이며 적중을 보장하지 않습니다.
      </p>
    </div>
  );
}
