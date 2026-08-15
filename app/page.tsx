import { getDataIndex, getMeet } from "@/lib/data";
import { formatFullDateKo } from "@/lib/format";
import { TRACKS } from "@/lib/tracks";

export default async function Home() {
  const index = await getDataIndex();
  const meet = await getMeet(index.latestMeetDate);

  return (
    <div className="space-y-6">
      <section>
        <h1 className="text-2xl font-bold">
          {formatFullDateKo(meet.date)} 경마
        </h1>
        <p className="mt-1 text-sm text-muted">
          최신 개최일 기준 출전표와 예측을 제공합니다.
        </p>
      </section>

      <section className="space-y-3">
        {meet.tracks.map((trackMeet) => (
          <div
            key={trackMeet.track}
            className="rounded-xl border border-border bg-surface p-4"
          >
            <h2
              className={`text-lg font-semibold ${TRACKS[trackMeet.track].colorClass}`}
            >
              {trackMeet.trackName}
            </h2>
            <p className="mt-1 text-sm text-muted">
              총 {trackMeet.races.length}개 경주 ·{" "}
              {trackMeet.races.filter((r) => r.hasPrediction).length}건 예측
              제공
            </p>
          </div>
        ))}
      </section>

      <p className="text-sm text-muted">
        경주별 상세 페이지는 준비 중입니다.
      </p>
    </div>
  );
}
