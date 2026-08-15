import type { Metadata, Viewport } from "next";
import Link from "next/link";
import { SITE_DESCRIPTION, SITE_NAME, SITE_URL } from "@/lib/site";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: `${SITE_NAME} — 한국경마 예측·출전표·적중률`,
    template: `%s | ${SITE_NAME}`,
  },
  description: SITE_DESCRIPTION,
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#fafaf9" },
    { media: "(prefers-color-scheme: dark)", color: "#0c0a09" },
  ],
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="ko" className="h-full antialiased">
      <body className="min-h-full flex flex-col">
        <header className="sticky top-0 z-10 border-b border-border bg-surface/90 backdrop-blur">
          <div className="mx-auto flex h-14 w-full max-w-3xl items-center justify-between px-4">
            <Link href="/" className="text-lg font-bold text-brand">
              {SITE_NAME}
            </Link>
            <nav className="flex gap-4 text-sm">
              <Link href="/results" className="text-muted hover:text-foreground">
                적중률
              </Link>
              <Link href="/about" className="text-muted hover:text-foreground">
                소개
              </Link>
            </nav>
          </div>
        </header>
        <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-6">
          {children}
        </main>
        <footer className="border-t border-border bg-surface">
          <div className="mx-auto w-full max-w-3xl space-y-2 px-4 py-6 text-xs text-muted">
            <p>
              본 서비스는 한국마사회가 공공데이터포털(data.go.kr)에 제공한
              데이터를 이용합니다.
            </p>
            <p>
              예측은 통계·AI 기반 참고 정보이며 적중을 보장하지 않습니다. 마권
              구매와 그 결과에 대한 책임은 이용자 본인에게 있으며, 본 서비스는
              베팅을 중개·권유하지 않습니다. 미성년자는 마권을 구매할 수
              없습니다.
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}
