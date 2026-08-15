import type { Metadata } from "next";
import Link from "next/link";
import { SITE_NAME } from "@/lib/site";

export const metadata: Metadata = {
  title: "소개",
  description: `${SITE_NAME} 서비스 소개 — 데이터 출처, 예측 방식, 이용 시 유의사항`,
  alternates: { canonical: "/about" },
};

export default function AboutPage() {
  return (
    <article className="space-y-6 leading-relaxed">
      <h1 className="text-2xl font-bold">{SITE_NAME} 소개</h1>

      <section className="space-y-2">
        <h2 className="text-lg font-semibold">무엇을 제공하나요</h2>
        <p className="text-sm">
          {SITE_NAME}은 서울·부산경남·제주 경마장의 경주 일정과 출전표, 그리고
          통계 모델과 AI 분석을 결합한 경주 예측을 무료로 제공합니다. 경주
          종료 후에는 결과와 예측 적중 여부를 함께 보여주고, 누적 적중률을
          투명하게 공개합니다.
        </p>
      </section>

      <section className="space-y-2">
        <h2 className="text-lg font-semibold">예측은 어떻게 만들어지나요</h2>
        <p className="text-sm">
          출전마의 최근 1년 성적, 레이팅, 마체중 변화, 기수·조교사 성적 등의
          피처를 통계 모델로 점수화한 뒤, AI가 전개 구도와 컨디션 신호를
          검토해 제한된 범위 안에서 보정합니다. 모든 예측은 경주 전에
          생성되어 기록되며 사후에 수정하지 않습니다.
        </p>
      </section>

      <section className="space-y-2">
        <h2 className="text-lg font-semibold">데이터 출처</h2>
        <p className="text-sm">
          본 서비스는 한국마사회가 공공데이터포털(data.go.kr)에 제공한
          공공데이터를 이용합니다. 데이터는 공공누리 조건에 따라 출처를
          표시하고 활용하며, 본 서비스는 한국마사회와 무관한 독립 서비스입니다.
        </p>
      </section>

      <section className="space-y-2">
        <h2 className="text-lg font-semibold">이용 시 유의사항</h2>
        <ul className="list-disc space-y-1 pl-5 text-sm">
          <li>
            예측은 통계·AI 기반 참고 정보이며 적중을 보장하지 않습니다.
          </li>
          <li>
            마권 구매와 그 결과에 대한 책임은 이용자 본인에게 있습니다. 본
            서비스는 베팅을 중개하거나 권유하지 않습니다.
          </li>
          <li>
            「한국마사회법」에 따라 미성년자는 마권을 구매할 수 없습니다.
          </li>
        </ul>
      </section>

      <p className="text-sm text-muted">
        경마 용어가 낯설다면{" "}
        <Link href="/guide" className="text-brand hover:underline">
          경마 용어 가이드
        </Link>
        를 먼저 읽어보세요.
      </p>
    </article>
  );
}
