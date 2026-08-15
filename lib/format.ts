import type { TrackSlug } from "@/lib/types";
import { trackName } from "@/lib/tracks";

/**
 * 렌더링은 항상 데이터의 KST 문자열 기준. 빌드 머신 타임존(UTC 가능)에
 * 의존하지 않도록 `new Date()`(현재 시각)는 사용 금지 — Date는 파싱 용도로만.
 */

function toKstDate(dateStr: string): Date {
  return new Date(dateStr + "T00:00:00+09:00");
}

const dateFormatter = new Intl.DateTimeFormat("ko-KR", {
  timeZone: "Asia/Seoul",
  month: "long",
  day: "numeric",
  weekday: "short",
});

const fullDateFormatter = new Intl.DateTimeFormat("ko-KR", {
  timeZone: "Asia/Seoul",
  year: "numeric",
  month: "long",
  day: "numeric",
  weekday: "short",
});

/** "2026-08-15" → "8월 15일 (토)" */
export function formatDateKo(dateStr: string): string {
  return dateFormatter.format(toKstDate(dateStr));
}

/** "2026-08-15" → "2026년 8월 15일 (토)" */
export function formatFullDateKo(dateStr: string): string {
  return fullDateFormatter.format(toKstDate(dateStr));
}

/** 승률 0.234 → "23.4%" */
export function formatPercent(rate: number): string {
  return `${(rate * 100).toFixed(1)}%`;
}

/** "seoul" + 5 → "서울 5경주" */
export function formatRaceLabel(track: TrackSlug, raceNo: number): string {
  return `${trackName(track)} ${raceNo}경주`;
}
