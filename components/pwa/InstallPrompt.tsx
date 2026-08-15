"use client";

import { useEffect, useState, useSyncExternalStore } from "react";

const DISMISS_KEY = "install-prompt-dismissed";

interface BeforeInstallPromptEvent extends Event {
  prompt(): Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

const emptySubscribe = () => () => {};

/** SSR에선 false, 하이드레이션 후 클라이언트에선 true */
function useMounted(): boolean {
  return useSyncExternalStore(
    emptySubscribe,
    () => true,
    () => false,
  );
}

export function InstallPrompt() {
  const mounted = useMounted();
  const [dismissed, setDismissed] = useState(false);
  const [installEvent, setInstallEvent] =
    useState<BeforeInstallPromptEvent | null>(null);

  useEffect(() => {
    const onBeforeInstall = (event: Event) => {
      event.preventDefault();
      setInstallEvent(event as BeforeInstallPromptEvent);
    };
    window.addEventListener("beforeinstallprompt", onBeforeInstall);
    return () =>
      window.removeEventListener("beforeinstallprompt", onBeforeInstall);
  }, []);

  if (!mounted || dismissed || localStorage.getItem(DISMISS_KEY)) return null;

  const isStandalone =
    window.matchMedia("(display-mode: standalone)").matches ||
    ("standalone" in navigator &&
      (navigator as { standalone?: boolean }).standalone === true);
  if (isStandalone) return null;

  // iOS Safari에는 beforeinstallprompt가 없어 수동 안내를 띄운다
  const showIosHint = /iPhone|iPad|iPod/i.test(navigator.userAgent);
  if (!showIosHint && !installEvent) return null;

  const dismiss = () => {
    localStorage.setItem(DISMISS_KEY, "1");
    setDismissed(true);
  };

  const install = async () => {
    if (!installEvent) return;
    await installEvent.prompt();
    dismiss();
  };

  return (
    <div className="fixed inset-x-0 bottom-0 z-20 border-t border-border bg-surface p-4 shadow-lg">
      <div className="mx-auto flex max-w-3xl items-center justify-between gap-3">
        <p className="text-sm">
          {installEvent ? (
            <>앱으로 설치하면 더 빠르게 확인할 수 있어요.</>
          ) : (
            <>
              홈 화면에 추가하면 앱처럼 쓸 수 있어요 — Safari{" "}
              <strong>공유</strong> 버튼 → <strong>홈 화면에 추가</strong>
            </>
          )}
        </p>
        <div className="flex shrink-0 gap-2">
          {installEvent && (
            <button
              onClick={install}
              className="rounded-lg bg-brand px-3 py-1.5 text-sm font-medium text-white"
            >
              설치
            </button>
          )}
          <button
            onClick={dismiss}
            className="rounded-lg px-3 py-1.5 text-sm text-muted"
          >
            닫기
          </button>
        </div>
      </div>
    </div>
  );
}
