import { formatDateKo, formatRaceLabel } from "@/lib/format";
import { SITE_DESCRIPTION, SITE_NAME, SITE_URL } from "@/lib/site";
import type { RaceFile, TrackSlug } from "@/lib/types";

const TRACK_PLACES: Record<TrackSlug, { name: string; address: string }> = {
  seoul: { name: "렛츠런파크 서울", address: "경기도 과천시 경마공원대로 107" },
  busan: { name: "렛츠런파크 부산경남", address: "부산광역시 강서구 가락대로 929" },
  jeju: { name: "렛츠런파크 제주", address: "제주특별자치도 제주시 애월읍 평화로 2144" },
};

/** schema.org JSON-LD를 XSS-안전하게 삽입한다 (`<` 이스케이프) */
export function JsonLd({ data }: { data: object }) {
  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{
        __html: JSON.stringify(data).replace(/</g, "\\u003c"),
      }}
    />
  );
}

export function webSiteJsonLd() {
  return {
    "@context": "https://schema.org",
    "@type": "WebSite",
    name: SITE_NAME,
    url: SITE_URL,
    description: SITE_DESCRIPTION,
    inLanguage: "ko",
  };
}

export function sportsEventJsonLd(race: RaceFile) {
  const place = TRACK_PLACES[race.track];
  return {
    "@context": "https://schema.org",
    "@type": "SportsEvent",
    name: `${formatDateKo(race.date)} ${formatRaceLabel(race.track, race.raceNo)}`,
    description: `${race.distanceM}m ${race.grade} 경주 — 출전표와 AI·통계 예측`,
    sport: "경마",
    startDate: `${race.date}T${race.startTimeKst}:00+09:00`,
    eventStatus: race.canceled
      ? "https://schema.org/EventCancelled"
      : "https://schema.org/EventScheduled",
    location: {
      "@type": "Place",
      name: place.name,
      address: { "@type": "PostalAddress", streetAddress: place.address },
    },
    organizer: { "@type": "Organization", name: SITE_NAME, url: SITE_URL },
    url: `${SITE_URL}/races/${race.date}/${race.track}/${race.raceNo}`,
  };
}
