"use client";

import { useEffect, useState } from "react";

const DISMISS_KEY = "install-prompt-dismissed";

interface BeforeInstallPromptEvent extends Event {
  prompt(): Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

export function InstallPrompt() {
  const [installEvent, setInstallEvent] =
    useState<BeforeInstallPromptEvent | null>(null);
  const [showIosHint, setShowIosHint] = useState(false);

  useEffect(() => {
    if (localStorage.getItem(DISMISS_KEY)) return;

    const isStandalone =
      window.matchMedia("(display-mode: standalone)").matches ||
      ("standalone" in navigator &&
        (navigator as { standalone?: boolean }).standalone === true);
    if (isStandalone) return;

    // iOS Safari에는 beforeinstallprompt가 없어 수동 안내를 띄운다
    const isIos = /iPhone|iPad|iPod/i.test(navigator.userAgent);
    if (isIos) {
      setShowIosHint(true);
      return;
    }

    const onBeforeInstall = (event: Event) => {
      event.preventDefault();
      setInstallEvent(event as BeforeInstallPromptEvent);
    };
    window.addEventListener("beforeinstallprompt", onBeforeInstall);
    return () =>
      window.removeEventListener("beforeinstallprompt", onBeforeInstall);
  }, []);

  const dismiss = () => {
    localStorage.setItem(DISMISS_KEY, "1");
    setInstallEvent(null);
    setShowIosHint(false);
  };

  const install = async () => {
    if (!installEvent) return;
    await installEvent.prompt();
    dismiss();
  };

  if (!installEvent && !showIosHint) return null;

  return (
    <div className="fixed inset-x-0 bottom-0 z-20 border-t border-border bg-surface p-4 shadow-lg">
      <div className="mx-auto flex max-w-3xl items-center justify-between gap-3">
        <p className="text-sm">
          {showIosHint ? (
            <>
              홈 화면에 추가하면 앱처럼 쓸 수 있어요 — Safari{" "}
              <strong>공유</strong> 버튼 →{" "}
              <strong>홈 화면에 추가</strong>
            </>
          ) : (
            <>앱으로 설치하면 더 빠르게 확인할 수 있어요.</>
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
