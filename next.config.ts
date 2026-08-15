import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  typedRoutes: true,
  // /admin은 유일한 동적 라우트 — 요청 시 fs로 읽는 data/를 함수 번들에 포함
  outputFileTracingIncludes: {
    "/admin": ["./data/**/*"],
  },
};

export default nextConfig;
