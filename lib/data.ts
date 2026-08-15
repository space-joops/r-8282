import { cache } from "react";
import { readFile, readdir } from "node:fs/promises";
import path from "node:path";
import {
  accuracyStatsSchema,
  backtestSchema,
  dataIndexSchema,
  meetSchema,
  raceFileSchema,
  trackSlugSchema,
  type AccuracyStats,
  type Backtest,
  type DataIndex,
  type Meet,
  type RaceFile,
  type TrackSlug,
} from "@/lib/types";

/**
 * data/ 트리의 유일한 읽기 진입점. 모든 읽기는 zod 검증을 거치므로
 * 파이프라인 산출물과 스키마가 어긋나면 next build가 실패한다(의도된 게이트).
 */

const DATA_DIR = path.join(process.cwd(), "data");

async function readJson(...segments: string[]): Promise<unknown> {
  const raw = await readFile(path.join(DATA_DIR, ...segments), "utf-8");
  return JSON.parse(raw);
}

export const getDataIndex = cache(async (): Promise<DataIndex> => {
  return dataIndexSchema.parse(await readJson("index.json"));
});

export const getMeet = cache(async (date: string): Promise<Meet> => {
  return meetSchema.parse(await readJson("meets", date, "meet.json"));
});

export const getRace = cache(
  async (date: string, track: TrackSlug, raceNo: number): Promise<RaceFile> => {
    const fileName = `r${String(raceNo).padStart(2, "0")}.json`;
    return raceFileSchema.parse(await readJson("meets", date, track, fileName));
  },
);

export const getAccuracy = cache(async (): Promise<AccuracyStats> => {
  return accuracyStatsSchema.parse(await readJson("stats", "accuracy.json"));
});

/** 백테스트 결과 — 아직 생성 전이면 null */
export const getBacktest = cache(async (): Promise<Backtest | null> => {
  try {
    return backtestSchema.parse(await readJson("stats", "backtest.json"));
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === "ENOENT") return null;
    throw error;
  }
});

export interface RaceRef {
  date: string;
  track: TrackSlug;
  raceNo: number;
}

/** generateStaticParams·sitemap용 — data/meets 트리를 걸어 전 경주를 열거 */
export const listAllRaces = cache(async (): Promise<RaceRef[]> => {
  const { meetDates } = await getDataIndex();
  const refs: RaceRef[] = [];
  for (const date of meetDates) {
    const meetDir = path.join(DATA_DIR, "meets", date);
    const entries = await readdir(meetDir, { withFileTypes: true });
    for (const entry of entries) {
      if (!entry.isDirectory()) continue;
      const parsed = trackSlugSchema.safeParse(entry.name);
      if (!parsed.success) continue;
      const track = parsed.data;
      const files = await readdir(path.join(meetDir, track));
      for (const file of files) {
        const match = /^r(\d{2})\.json$/.exec(file);
        if (match) refs.push({ date, track, raceNo: Number(match[1]) });
      }
    }
  }
  return refs;
});
