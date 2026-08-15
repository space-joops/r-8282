import type { Metadata } from "next";
import { RaceCard } from "@/components/race/RaceCard";
import { getDataIndex, getMeet } from "@/lib/data";
import { formatFullDateKo } from "@/lib/format";
import { TRACKS } from "@/lib/tracks";

export const dynamicParams = false;

export async function generateStaticParams() {
  const { meetDates } = await getDataIndex();
  return meetDates.map((date) => ({ date }));
}

export async function generateMetadata({
  params,
}: PageProps<"/races/[date]">): Promise<Metadata> {
  const { date } = await params;
  return {
    title: `${formatFullDateKo(date)} 경마 일정·예측`,
    description: `${formatFullDateKo(date)} 서울·부산경남·제주 경마 경주 일정, 출전표와 AI 예측`,
  };
}

export default async function MeetPage({ params }: PageProps<"/races/[date]">) {
  const { date } = await params;
  const meet = await getMeet(date);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">{formatFullDateKo(date)} 경마</h1>
      {meet.tracks.map((trackMeet) => (
        <section key={trackMeet.track}>
          <h2
            className={`mb-3 text-lg font-semibold ${TRACKS[trackMeet.track].colorClass}`}
          >
            {trackMeet.trackName}
            <span className="ml-2 text-sm font-normal text-muted">
              {trackMeet.races.length}개 경주
            </span>
          </h2>
          <div className="space-y-2">
            {trackMeet.races.map((race) => (
              <RaceCard
                key={race.raceNo}
                date={date}
                track={trackMeet.track}
                race={race}
              />
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
