import type { Metadata } from "next";
import Link from "next/link";
import { RaceCard } from "@/components/race/RaceCard";
import { getAccuracy, getDataIndex, getMeet, getRace } from "@/lib/data";
import { formatFullDateKo, formatPercent, formatRaceLabel } from "@/lib/format";
import { JsonLd, webSiteJsonLd } from "@/lib/seo";
import { TRACKS } from "@/lib/tracks";
import type { Meet } from "@/lib/types";

export const metadata: Metadata = {
  alternates: { canonical: "/" },
};

export default async function Home() {
  const index = await getDataIndex();
  // 다음 개최일이 준비되어 있으면(예측 배포됨) 그것을 우선 보여준다
  const meet = await getMeet(index.nextMeetDate ?? index.latestMeetDate);
  const accuracy = await getAccuracy();
  const picks = await featuredPicks(meet);

  return (
    <div className="space-y-8">
      <JsonLd data={webSiteJsonLd()} />
      <section>
        <h1 className="text-2xl font-bold">
          {formatFullDateKo(meet.date)} 경마
        </h1>
        <p className="mt-1 text-sm text-muted">
          서울·부산경남·제주 출전표와 AI·통계 예측을 무료로 제공합니다.
        </p>
        {accuracy.overall.races > 0 && (
          <p className="mt-3 inline-flex items-center gap-1.5 rounded-full bg-brand-soft px-3 py-1 text-sm text-brand">
            누적 단승 적중률 {formatPercent(accuracy.overall.winRate)}
            <span className="text-xs">({accuracy.overall.races}경주)</span>
          </p>
        )}
      </section>

      {picks.length > 0 && (
        <section>
          <h2 className="mb-3 text-lg font-semibold">오늘의 대표 픽</h2>
          <div className="grid gap-2 sm:grid-cols-3">
            {picks.map((pick) => (
              <Link
                key={`${pick.track}-${pick.raceNo}`}
                href={`/races/${meet.date}/${pick.track}/${pick.raceNo}`}
                className="rounded-xl border border-border bg-surface p-4 transition-colors hover:border-brand"
              >
                <p className={`text-xs font-medium ${TRACKS[pick.track].colorClass}`}>
                  {formatRaceLabel(pick.track, pick.raceNo)}
                </p>
                <p className="mt-1 font-semibold">
                  {pick.gateNo}번 {pick.horseName}
                </p>
                <p className="mt-0.5 text-sm text-muted">
                  승률 {formatPercent(pick.winProb)}
                </p>
              </Link>
            ))}
          </div>
        </section>
      )}

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
                date={meet.date}
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

interface FeaturedPick {
  track: Meet["tracks"][number]["track"];
  raceNo: number;
  gateNo: number;
  horseName: string;
  winProb: number;
}

/** 트랙별 첫 예측 경주의 단승 픽을 모은다 (최대 3건) */
async function featuredPicks(meet: Meet): Promise<FeaturedPick[]> {
  const picks: FeaturedPick[] = [];
  for (const trackMeet of meet.tracks) {
    const summary = trackMeet.races.find((r) => r.hasPrediction && !r.canceled);
    if (!summary) continue;
    const race = await getRace(meet.date, trackMeet.track, summary.raceNo);
    const prediction = race.prediction;
    if (!prediction) continue;
    const top = prediction.rankings[0];
    picks.push({
      track: trackMeet.track,
      raceNo: summary.raceNo,
      gateNo: top.gateNo,
      horseName:
        race.entries.find((e) => e.gateNo === top.gateNo)?.horseName ??
        `${top.gateNo}번`,
      winProb: top.winProb,
    });
  }
  return picks.slice(0, 3);
}
