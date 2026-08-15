import { NextResponse, type NextRequest } from "next/server";

/**
 * /admin 전용 Basic Auth 게이트 (사용자: admin, 암호: env ADMIN_PASSWORD).
 * matcher가 /admin 경로만 잡으므로 공개 페이지의 정적 서빙에는 영향이 없다.
 */
export function proxy(request: NextRequest) {
  const password = process.env.ADMIN_PASSWORD;
  if (!password) {
    return new NextResponse(
      "관리자 기능이 비활성 상태입니다 (ADMIN_PASSWORD 미설정)",
      { status: 503 },
    );
  }

  const expected =
    "Basic " + Buffer.from(`admin:${password}`).toString("base64");
  if (request.headers.get("authorization") !== expected) {
    return new NextResponse("인증이 필요합니다", {
      status: 401,
      headers: {
        "WWW-Authenticate": 'Basic realm="kyongmapick-admin", charset="UTF-8"',
      },
    });
  }
  return NextResponse.next();
}

export const config = {
  matcher: "/admin/:path*",
};
