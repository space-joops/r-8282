import { z } from "zod";

/**
 * 데이터 계약 (TS측 원천) — pipeline/schemas/*.schema.json 과 항상 동기화할 것.
 * 규칙: camelCase, 키 생략 금지(null 명시), 날짜·시각은 KST 로컬 문자열,
 * 기계 타임스탬프만 +09:00 ISO. 변경 시 schemaVersion 범프.
 */

export const TRACK_SLUGS = ["seoul", "busan", "jeju"] as const;
export const trackSlugSchema = z.enum(TRACK_SLUGS);
export type TrackSlug = z.infer<typeof trackSlugSchema>;

const dateStr = z.string().regex(/^\d{4}-\d{2}-\d{2}$/, "YYYY-MM-DD");
const timeStr = z.string().regex(/^\d{2}:\d{2}$/, "HH:MM (KST)");

export const dataIndexSchema = z.object({
  schemaVersion: z.literal(1),
  updatedAt: z.string(),
  latestMeetDate: dateStr,
  nextMeetDate: dateStr.nullable(),
  meetDates: z.array(dateStr),
});
export type DataIndex = z.infer<typeof dataIndexSchema>;

export const raceSummarySchema = z.object({
  raceNo: z.number().int().positive(),
  startTimeKst: timeStr,
  distanceM: z.number().int().positive(),
  grade: z.string(),
  raceName: z.string().nullable(),
  entryCount: z.number().int().nonnegative(),
  hasPrediction: z.boolean(),
  hasResult: z.boolean(),
  canceled: z.boolean(),
});
export type RaceSummary = z.infer<typeof raceSummarySchema>;

export const meetSchema = z.object({
  schemaVersion: z.literal(1),
  date: dateStr,
  tracks: z.array(
    z.object({
      track: trackSlugSchema,
      trackName: z.enum(["서울", "부산경남", "제주"]),
      meetCode: z.union([z.literal(1), z.literal(2), z.literal(3)]),
      races: z.array(raceSummarySchema),
    }),
  ),
});
export type Meet = z.infer<typeof meetSchema>;

export const entrySchema = z.object({
  /** 출주 번호(마번) */
  gateNo: z.number().int().positive(),
  horseId: z.string(),
  horseName: z.string(),
  age: z.number().int().positive(),
  sex: z.enum(["수", "암", "거"]),
  rating: z.number().nullable(),
  jockey: z.object({
    id: z.string(),
    name: z.string(),
    winRate1y: z.number().nullable(),
  }),
  trainer: z.object({
    id: z.string(),
    name: z.string(),
    winRate1y: z.number().nullable(),
  }),
  /** 부담중량(kg) — 서울 사전 출전 데이터엔 없어 null 가능 */
  weightCarriedKg: z.number().nullable(),
  /** 마체중(kg) — 미발표 트랙은 null */
  bodyWeightKg: z.number().nullable(),
  bodyWeightDiffKg: z.number().nullable(),
  record1y: z
    .object({
      starts: z.number().int().nonnegative(),
      wins: z.number().int().nonnegative(),
      seconds: z.number().int().nonnegative(),
      thirds: z.number().int().nonnegative(),
    })
    .nullable(),
  /** 최근 출주 이력 (최신순, 최대 5회) */
  recentRuns: z.array(
    z.object({
      date: dateStr,
      track: trackSlugSchema,
      finishPos: z.number().int().positive(),
      entryCount: z.number().int().positive(),
      distanceM: z.number().int().positive(),
      timeSec: z.number().nullable(),
    }),
  ),
  scratched: z.boolean(),
  jockeyChanged: z.boolean(),
});
export type Entry = z.infer<typeof entrySchema>;

export const predictionSchema = z.object({
  generatedAt: z.string(),
  model: z.object({
    statVersion: z.string(),
    /** AI 분석 결합 시 모델명, 통계 단독이면 null */
    aiModel: z.string().nullable(),
  }),
  rankings: z.array(
    z.object({
      gateNo: z.number().int().positive(),
      predictedRank: z.number().int().positive(),
      score: z.number(),
      winProb: z.number().min(0).max(1),
      briefComment: z.string().nullable(),
    }),
  ),
  /** 경주 총평 (markdown) */
  aiCommentary: z.string().nullable(),
  confidence: z.enum(["high", "medium", "low"]),
  topPicks: z.object({
    win: z.number().int().positive(),
    place: z.array(z.number().int().positive()),
    exacta: z.tuple([z.number().int().positive(), z.number().int().positive()]).nullable(),
  }),
});
export type Prediction = z.infer<typeof predictionSchema>;

export const raceResultSchema = z.object({
  fetchedAt: z.string(),
  order: z.array(
    z.object({
      finishPos: z.number().int().positive(),
      gateNo: z.number().int().positive(),
      horseName: z.string(),
      timeSec: z.number().nullable(),
      margin: z.string().nullable(),
    }),
  ),
  /** 확정배당율 — 배당 API 승인 전엔 null */
  payouts: z
    .object({
      win: z.number().nullable(),
      place: z.array(z.number()).nullable(),
    })
    .nullable(),
});
export type RaceResult = z.infer<typeof raceResultSchema>;

export const raceFileSchema = z.object({
  schemaVersion: z.literal(1),
  date: dateStr,
  track: trackSlugSchema,
  raceNo: z.number().int().positive(),
  startTimeKst: timeStr,
  distanceM: z.number().int().positive(),
  grade: z.string(),
  canceled: z.boolean(),
  ageCond: z.string().nullable(),
  weather: z.string().nullable(),
  trackCond: z.string().nullable(),
  entries: z.array(entrySchema),
  prediction: predictionSchema.nullable(),
  result: raceResultSchema.nullable(),
});
export type RaceFile = z.infer<typeof raceFileSchema>;

export const accuracyBucketSchema = z.object({
  races: z.number().int().nonnegative(),
  winHits: z.number().int().nonnegative(),
  winRate: z.number().min(0).max(1),
  placeHits: z.number().int().nonnegative(),
  placeRate: z.number().min(0).max(1),
  top3ExactHits: z.number().int().nonnegative(),
});
export type AccuracyBucket = z.infer<typeof accuracyBucketSchema>;

export const backtestMetricSchema = z.object({
  races: z.number().int().nonnegative(),
  winHits: z.number().int().nonnegative(),
  winRate: z.number().min(0).max(1),
  placeHits: z.number().int().nonnegative(),
  placeRate: z.number().min(0).max(1),
  top3ExactHits: z.number().int().nonnegative(),
  logLoss: z.number().nullable(),
  roiWin: z.number().nullable(),
  roiPlace: z.number().nullable(),
});
export type BacktestMetric = z.infer<typeof backtestMetricSchema>;

export const bettingEntrySchema = z.object({
  pool: z.enum(["WIN", "PLC", "QNL", "EXA", "QPL", "TLA", "TRI"]),
  label: z.string(),
  bets: z.number().int().nonnegative(),
  hits: z.number().int().nonnegative(),
  hitRate: z.number().min(0).max(1),
  stakeKrw: z.number().int().nonnegative(),
  returnedKrw: z.number().int().nonnegative(),
  profitKrw: z.number().int(),
  roi: z.number().nullable(),
});
export type BettingEntry = z.infer<typeof bettingEntrySchema>;

export const backtestModelSchema = z.object({
  version: z.string(),
  generatedAt: z.string(),
  periodFrom: dateStr,
  periodTo: dateStr,
  note: z.string(),
  overall: backtestMetricSchema,
  byTrack: z.record(trackSlugSchema, backtestMetricSchema),
  byConfidence: z.object({
    high: backtestMetricSchema,
    medium: backtestMetricSchema,
    low: backtestMetricSchema,
  }),
  monthly: z.array(
    backtestMetricSchema.extend({ month: z.string().regex(/^\d{4}-\d{2}$/) }),
  ),
  betting: z.array(bettingEntrySchema),
});
export type BacktestModel = z.infer<typeof backtestModelSchema>;

export const backtestSchema = z.object({
  schemaVersion: z.literal(1),
  models: z.array(backtestModelSchema),
});
export type Backtest = z.infer<typeof backtestSchema>;

export const POOL_CODES = ["WIN", "PLC", "QNL", "EXA", "QPL", "TLA", "TRI"] as const;
export type PoolCode = (typeof POOL_CODES)[number];

/** [staked, hit, returnKrw] 압축 배열 — backtest_races.schema.json과 동기 */
const poolResultSchema = z.tuple([
  z.number().int().min(0).max(1),
  z.number().int().min(0).max(1),
  z.number().int().nonnegative(),
]);
export type PoolResult = z.infer<typeof poolResultSchema>;

const gateTripleSchema = z.tuple([
  z.number().int().positive(),
  z.number().int().positive(),
  z.number().int().positive(),
]);

export const backtestRaceRowSchema = z.object({
  date: dateStr,
  track: trackSlugSchema,
  raceNo: z.number().int().positive(),
  confidence: z.enum(["high", "medium", "low"]),
  picks: gateTripleSchema,
  actual: gateTripleSchema,
  pools: z.object({
    WIN: poolResultSchema,
    PLC: poolResultSchema,
    QNL: poolResultSchema,
    EXA: poolResultSchema,
    QPL: poolResultSchema,
    TLA: poolResultSchema,
    TRI: poolResultSchema,
  }),
});
export type BacktestRaceRow = z.infer<typeof backtestRaceRowSchema>;

export const backtestRacesSchema = z.object({
  schemaVersion: z.literal(1),
  models: z.array(
    z.object({
      version: z.string(),
      races: z.array(backtestRaceRowSchema),
    }),
  ),
});
export type BacktestRaces = z.infer<typeof backtestRacesSchema>;

export const accuracyStatsSchema = z.object({
  schemaVersion: z.literal(1),
  updatedAt: z.string(),
  overall: accuracyBucketSchema,
  byTrack: z.record(trackSlugSchema, accuracyBucketSchema),
  history: z.array(
    z.object({
      date: dateStr,
      races: z.number().int().nonnegative(),
      winHits: z.number().int().nonnegative(),
      placeHits: z.number().int().nonnegative(),
    }),
  ),
});
export type AccuracyStats = z.infer<typeof accuracyStatsSchema>;
