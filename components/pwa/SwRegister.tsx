"use client";

import { useEffect } from "react";

export function SwRegister() {
  useEffect(() => {
    if (!("serviceWorker" in navigator)) return;
    navigator.serviceWorker
      .register(new URL("../../lib/service-worker.js", import.meta.url), {
        scope: "/",
      })
      .catch((error) => {
        console.warn("서비스워커 등록 실패:", error);
      });
  }, []);
  return null;
}
