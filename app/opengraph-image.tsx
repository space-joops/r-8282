import { readFile } from "node:fs/promises";
import path from "node:path";
import { ImageResponse } from "next/og";
import { SITE_NAME } from "@/lib/site";

export const size = { width: 1200, height: 630 };
export const contentType = "image/png";
export const alt = `${SITE_NAME} — 한국경마 예측·출전표·적중률`;

export default async function OgImage() {
  const font = await readFile(
    path.join(process.cwd(), "assets", "fonts", "og-kr-bold.otf"),
  );

  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          background: "linear-gradient(135deg, #14532d 0%, #166534 55%, #15803d 100%)",
          color: "#ffffff",
          fontFamily: "og",
        }}
      >
        <div style={{ display: "flex", fontSize: 110, fontWeight: 700 }}>
          {SITE_NAME}
        </div>
        <div
          style={{
            display: "flex",
            marginTop: 28,
            fontSize: 42,
            color: "#dcfce7",
          }}
        >
          한국경마 예측 · 출전표 · 적중률
        </div>
        <div
          style={{
            display: "flex",
            marginTop: 44,
            gap: 18,
            fontSize: 30,
          }}
        >
          {["서울", "부산경남", "제주"].map((track) => (
            <div
              key={track}
              style={{
                display: "flex",
                padding: "10px 28px",
                borderRadius: 9999,
                background: "rgba(255,255,255,0.14)",
              }}
            >
              {track}
            </div>
          ))}
        </div>
      </div>
    ),
    {
      ...size,
      fonts: [{ name: "og", data: font, weight: 700, style: "normal" }],
    },
  );
}
