/**
 * 타이머 생존 판정 — 일정의 원천은 scripts/systemd/kyongma-*.timer.
 * 그 파일이 바뀌면 여기 슬롯도 함께 갱신할 것.
 * KST는 DST가 없어 +9h 고정 오프셋 연산이 안전하다.
 */

interface Slot {
  /** KST 요일 (0=일 … 6=토) */
  day: number;
  hour: number;
  minute: number;
}

export const PREDICT_SLOTS: Slot[] = [5, 6, 0].map((day) => ({
  day,
  hour: 7,
  minute: 30,
}));

export const RESULTS_SLOTS: Slot[] = [
  ...[5, 6, 0].map((day) => ({ day, hour: 19, minute: 30 })),
  { day: 1, hour: 10, minute: 0 },
];

/** RandomizedDelaySec(5분) + 실행 시간 여유 */
export const GRACE_MIN = 60;

const HOUR_MS = 3_600_000;
const DAY_MS = 86_400_000;

/** grace가 지난 가장 최근 슬롯의 UTC epoch(ms). 해당 없으면 null */
export function lastDueSlot(slots: Slot[], nowMs: number): number | null {
  let latest: number | null = null;
  for (let back = 0; back < 14; back++) {
    const kst = new Date(nowMs - back * DAY_MS + 9 * HOUR_MS);
    for (const slot of slots) {
      if (slot.day !== kst.getUTCDay()) continue;
      const slotMs = Date.UTC(
        kst.getUTCFullYear(),
        kst.getUTCMonth(),
        kst.getUTCDate(),
        slot.hour - 9,
        slot.minute,
      );
      if (slotMs + GRACE_MIN * 60_000 <= nowMs) {
        latest = Math.max(latest ?? 0, slotMs);
      }
    }
  }
  return latest;
}

/** "3분 전" / "5시간 전" / "2일 전" */
export function formatAgo(fromMs: number, nowMs: number): string {
  const diffMin = Math.max(0, Math.round((nowMs - fromMs) / 60_000));
  if (diffMin < 60) return `${diffMin}분 전`;
  if (diffMin < 60 * 24) return `${Math.round(diffMin / 60)}시간 전`;
  return `${Math.round(diffMin / (60 * 24))}일 전`;
}
