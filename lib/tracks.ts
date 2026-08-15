import type { TrackSlug } from "@/lib/types";

export interface TrackInfo {
  slug: TrackSlug;
  /** KRA API의 시행경마장 구분 코드 (서울=1, 제주=2, 부산경남=3) */
  meetCode: 1 | 2 | 3;
  name: "서울" | "부산경남" | "제주";
  /** Tailwind 토큰 색상 클래스 (globals.css @theme 정의) */
  colorClass: string;
}

export const TRACKS: Record<TrackSlug, TrackInfo> = {
  seoul: { slug: "seoul", meetCode: 1, name: "서울", colorClass: "text-track-seoul" },
  busan: { slug: "busan", meetCode: 3, name: "부산경남", colorClass: "text-track-busan" },
  jeju: { slug: "jeju", meetCode: 2, name: "제주", colorClass: "text-track-jeju" },
};

/** 화면 표시 순서 */
export const TRACK_ORDER: TrackSlug[] = ["seoul", "busan", "jeju"];

export function trackName(slug: TrackSlug): TrackInfo["name"] {
  return TRACKS[slug].name;
}
