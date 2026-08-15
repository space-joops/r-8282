import type { Metadata } from "next";
import Link from "next/link";
import { getAccuracy } from "@/lib/data";
import { formatDateKo, formatPercent } from "@/lib/format";
import { TRACKS, TRACK_ORDER } from "@/lib/tracks";
import type { AccuracyBucket } from "@/lib/types";

export const metadata: Metadata = {
  title: "적중률 추적",
  description:
    "AI·통계 예측의 누적 적중률 — 단승·연승 적중률과 개최일별 기록을 투명하게 공개합니다",
  alternates: { canonical: "/results" },
};

export default async function ResultsPage() {
  const accuracy = await getAccuracy();

  return (
    <div className="space-y-6">
      <section>
        <h1 className="text-2xl font-bold">적중률 추적</h1>
        <p className="mt-1 text-sm text-muted">
          모든 예측은 경주 전에 기록되며 사후 수정하지 않습니다.
        </p>
      </section>

      <BucketCard title="전체" bucket={accuracy.overall} highlight />

      <section>
        <h2 className="mb-3 text-lg font-semibold">경마장별</h2>
        <div className="grid gap-2 sm:grid-cols-3">
          {TRACK_ORDER.map((slug) => (
            <BucketCard
              key={slug}
              title={TRACKS[slug].name}
              titleClass={TRACKS[slug].colorClass}
              bucket={accuracy.byTrack[slug]}
            />
          ))}
        </div>
      </section>

      {accuracy.history.length > 0 && (
        <section>
          <h2 className="mb-3 text-lg font-semibold">개최일별 기록</h2>
          <div className="overflow-hidden rounded-xl border border-border bg-surface">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-xs text-muted">
                  <th className="p-3 font-medium">개최일</th>
                  <th className="p-3 font-medium">평가 경주</th>
                  <th className="p-3 font-medium">단승 적중</th>
                  <th className="p-3 font-medium">연승 적중</th>
                </tr>
              </thead>
              <tbody>
                {[...accuracy.history].reverse().map((h) => (
                  <tr key={h.date} className="border-b border-border last:border-0">
                    <td className="p-3">
                      <Link
                        href={`/races/${h.date}`}
                        className="font-medium hover:text-brand"
                      >
                        {formatDateKo(h.date)}
                      </Link>
                    </td>
                    <td className="p-3 tabular-nums">{h.races}</td>
                    <td className="p-3 tabular-nums">
                      {h.winHits} ({formatPercent(h.races ? h.winHits / h.races : 0)})
                    </td>
                    <td className="p-3 tabular-nums">
                      {h.placeHits} ({formatPercent(h.races ? h.placeHits / h.races : 0)})
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      <p className="text-xs text-muted">
        단승 적중 = 단승 픽이 1위 · 연승 적중 = 단승 픽이 3위 이내
      </p>
    </div>
  );
}

function BucketCard({
  title,
  titleClass = "",
  bucket,
  highlight = false,
}: {
  title: string;
  titleClass?: string;
  bucket: AccuracyBucket;
  highlight?: boolean;
}) {
  return (
    <div
      className={`rounded-xl border bg-surface p-4 ${
        highlight ? "border-brand" : "border-border"
      }`}
    >
      <h3 className={`text-sm font-semibold ${titleClass}`}>{title}</h3>
      {bucket.races === 0 ? (
        <p className="mt-2 text-sm text-muted">아직 평가된 경주가 없습니다.</p>
      ) : (
        <dl className="mt-2 grid grid-cols-3 gap-2 text-center">
          <div>
            <dt className="text-xs text-muted">단승</dt>
            <dd className="mt-0.5 text-lg font-bold text-brand">
              {formatPercent(bucket.winRate)}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-muted">연승</dt>
            <dd className="mt-0.5 text-lg font-bold">
              {formatPercent(bucket.placeRate)}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-muted">경주</dt>
            <dd className="mt-0.5 text-lg font-bold tabular-nums">
              {bucket.races}
            </dd>
          </div>
        </dl>
      )}
    </div>
  );
}
