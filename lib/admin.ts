import { cache } from "react";
import { getRace, listAllRaces } from "@/lib/data";
import type { Prediction, TrackSlug } from "@/lib/types";

/**
 * 관리자 대시보드 전용 로더 — /admin(동적 라우트)에서만 사용한다.
 * Supabase 접근은 서버 전용 service 키로만 하며 브라우저에 노출되지 않는다.
 */

export interface JudgedRace {
  date: string;
  track: TrackSlug;
  raceNo: number;
  confidence: Prediction["confidence"];
  winHit: boolean;
  placeHit: boolean;
}

/** 예측·결과가 모두 있는 경주를 pipeline/accuracy.py와 같은 규칙으로 판정 */
export const listJudgedRaces = cache(async (): Promise<JudgedRace[]> => {
  const refs = await listAllRaces();
  const judged: JudgedRace[] = [];
  for (const ref of refs) {
    const race = await getRace(ref.date, ref.track, ref.raceNo);
    // 결과 백필 경주는 prediction이 null — 취소 경주와 함께 평가 제외
    if (race.canceled || !race.prediction || !race.result) continue;
    const order = [...race.result.order].sort((a, b) => a.finishPos - b.finishPos);
    if (order.length === 0) continue;
    const winPick = race.prediction.topPicks.win;
    judged.push({
      date: race.date,
      track: race.track,
      raceNo: race.raceNo,
      confidence: race.prediction.confidence,
      winHit: order[0].gateNo === winPick,
      placeHit: order.slice(0, 3).some((o) => o.gateNo === winPick),
    });
  }
  return judged;
});

/** kyongma_ops_runs 행 — Supabase 컬럼명(snake_case) 그대로 */
export interface OpsRun {
  id: number;
  kind: "predict" | "results";
  target_date: string;
  status: "success" | "no_change" | "no_races" | "error";
  source: "timer" | "manual";
  host: string | null;
  started_at: string;
  finished_at: string;
  duration_sec: number | null;
  metrics: Record<string, unknown>;
  error: string | null;
}

/** 최근 실행 이력 조회 — env 미구성/오류 시 null (페이지는 안내문 표시) */
export async function getOpsRuns(limit = 30): Promise<OpsRun[] | null> {
  const url = process.env.SUPABASE_URL?.replace(/\/+$/, "");
  const key =
    process.env.SUPABASE_SERVICE_KEY ?? process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !key) return null;
  try {
    const res = await fetch(
      `${url}/rest/v1/kyongma_ops_runs?select=*&order=started_at.desc&limit=${limit}`,
      {
        headers: { apikey: key, Authorization: `Bearer ${key}` },
        cache: "no-store",
        signal: AbortSignal.timeout(8000),
      },
    );
    if (!res.ok) return null;
    return (await res.json()) as OpsRun[];
  } catch {
    return null;
  }
}
