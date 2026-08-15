import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "오프라인",
  robots: { index: false },
};

export default function OfflinePage() {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center">
      <p className="text-4xl">📡</p>
      <h1 className="mt-4 text-xl font-bold">오프라인 상태입니다</h1>
      <p className="mt-2 text-sm text-muted">
        네트워크 연결을 확인한 뒤 다시 시도해 주세요.
      </p>
    </div>
  );
}
