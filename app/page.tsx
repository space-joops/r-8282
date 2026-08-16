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
          출전표·AI 브리핑·투명한 성적표로 경마를 더 재미있게 — 판단은 직접,
          근거는 여기서.
        </p>
        <p className="mt-3 flex flex-wrap items-center gap-2">
          {accuracy.overall.races > 0 && (
            <span className="inline-flex items-center gap-1.5 rounded-full bg-brand-soft px-3 py-1 text-sm text-brand">
              누적 단승 적중률 {formatPercent(accuracy.overall.winRate)}
              <span className="text-xs">({accuracy.overall.races}경주)</span>
            </span>
          )}
          <Link
            href="/model"
            className="text-xs text-muted underline decoration-dotted underline-offset-2 hover:text-brand"
          >
            모델 성적표 — 손익까지 전부 공개
          </Link>
        </p>
      </section>

      {picks.length > 0 && (
        <section>
          <h2 className="mb-3 text-lg font-semibold">오늘의 관전 포인트</h2>
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
                {pick.comment && (
                  <p className="mt-1 text-sm leading-snug">{pick.comment}</p>
                )}
                <p className="mt-1.5 text-xs text-muted">
                  모델 1순위 {pick.gateNo}번 {pick.horseName} · 승률{" "}
                  {formatPercent(pick.winProb)}
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
  /** AI 총평 첫 문장 (없으면 1순위 한줄평) — 카드의 주인공 */
  comment: string | null;
}

/** AI 총평의 첫 문장을 카드용 한 줄로 추출한다 (** 마크다운 제거) */
function commentLead(commentary: string | null): string | null {
  if (!commentary) return null;
  const plain = commentary.replace(/\*\*/g, "").trim();
  const first = plain.match(/^.+?다\./)?.[0] ?? plain;
  return first.length <= 90 ? first : null;
}

/** 트랙별 첫 예측 경주의 브리핑·픽을 모은다 (최대 3건) */
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
      comment: commentLead(prediction.aiCommentary) ?? top.briefComment,
    });
  }
  return picks.slice(0, 3);
}
