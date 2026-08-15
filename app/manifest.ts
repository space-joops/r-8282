import type { MetadataRoute } from "next";
import { SITE_DESCRIPTION, SITE_NAME } from "@/lib/site";

export default function manifest(): MetadataRoute.Manifest {
  return {
    id: "/",
    name: `${SITE_NAME} — 한국경마 예측`,
    short_name: SITE_NAME,
    description: SITE_DESCRIPTION,
    lang: "ko",
    start_url: "/",
    display: "standalone",
    background_color: "#fafaf9",
    theme_color: "#15803d",
    icons: [
      { src: "/icon-192.png", sizes: "192x192", type: "image/png" },
      { src: "/icon-512.png", sizes: "512x512", type: "image/png" },
      {
        src: "/icon-maskable-192.png",
        sizes: "192x192",
        type: "image/png",
        purpose: "maskable",
      },
      {
        src: "/icon-maskable-512.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "maskable",
      },
    ],
    shortcuts: [
      {
        name: "적중률 추적",
        url: "/results",
        icons: [{ src: "/icon-192.png", sizes: "192x192" }],
      },
    ],
  };
}
