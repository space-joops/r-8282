import type { Metadata } from "next";
import Link from "next/link";
import { SITE_NAME } from "@/lib/site";

export const metadata: Metadata = {
  title: "경마 용어 가이드",
  description:
    "단승·연승·복승 등 마권 승식부터 부담중량·마체중·레이팅까지 — 경마 초심자를 위한 용어 설명과 경마픽 화면 읽는 법",
  alternates: { canonical: "/guide" },
};

interface Term {
  term: string;
  description: React.ReactNode;
}

const BETTING_TERMS: Term[] = [
  {
    term: "단승",
    description: (
      <>
        1위 말 하나를 맞히는 가장 기본 승식. {SITE_NAME}의{" "}
        <strong>단승 추천</strong>이 이것입니다.
      </>
    ),
  },
  {
    term: "연승",
    description: "고른 말이 3위 안에만 들면 적중 (출전 7두 이하 경주는 2위 안).",
  },
  { term: "복승", description: "1·2위 두 마리를 순서 상관없이 맞히기." },
  {
    term: "쌍승",
    description: "1·2위를 순서까지 정확히 맞히기. 예측 패널의 쌍승 조합이 이것입니다.",
  },
  { term: "복연승", description: "고른 두 마리가 모두 3위 안에 들면 적중." },
  { term: "삼복승", description: "1~3위 세 마리를 순서 무관하게 맞히기." },
  {
    term: "삼쌍승",
    description:
      "1·2·3위를 순서까지 정확히 맞히기 — 가장 어렵고 배당이 가장 큰 승식.",
  },
  {
    term: "배당률",
    description:
      "적중 시 받는 배수. 2.1배면 1,000원 마권이 2,100원이 됩니다. 많은 사람이 고른(인기 있는) 말일수록 낮아집니다.",
  },
];

const ENTRY_TERMS: Term[] = [
  { term: "출전표(출주표)", description: "그 경주에 나오는 말·기수·조교사 명단." },
  {
    term: "마번(출주번호)",
    description: "말이 배정받은 번호. 출발 게이트 위치와 연결됩니다.",
  },
  {
    term: "출주취소",
    description:
      "검사·부상 등으로 경주 직전에 빠지는 것. 출전표에서 회색으로 표시됩니다.",
  },
  {
    term: "기수",
    description:
      "말을 타는 선수. 같은 말이라도 기수의 기량에 따라 성적 차이가 커서 예측 피처로 씁니다.",
  },
  {
    term: "조교사",
    description: "말을 훈련·관리하는 감독. 마방(팀)의 책임자입니다.",
  },
  {
    term: "기수 변경",
    description:
      "당일 기수가 바뀌는 것. 호흡·전략이 달라지는 변수라 출전표에 '변경' 배지로 표시합니다.",
  },
];

const ABILITY_TERMS: Term[] = [
  {
    term: "레이팅",
    description:
      "한국마사회가 매기는 능력 점수. 높을수록 강한 말이며, 신마 등 미부여 시 '-'로 표시합니다.",
  },
  {
    term: "등급",
    description:
      "경주 수준. '국6'은 국산마 6등급(최하위 신인급)이고 숫자가 작아질수록(국1 방향) 상위 등급입니다.",
  },
  {
    term: "부담중량",
    description:
      "말이 짊어지는 총 무게(기수+장구+납 조끼). 무거울수록 불리하며, 실력 차를 보정하는 핸디캡 수단으로도 쓰입니다.",
  },
  {
    term: "마체중",
    description:
      "당일 아침 잰 말의 몸무게. 괄호 숫자는 직전 경주 대비 증감으로, ±8kg을 넘는 급변은 컨디션 이상 신호로 봅니다.",
  },
  {
    term: "1년 전적",
    description:
      "최근 1년의 '출전–1착–2착–3착' 횟수. '10전 2승'이면 10번 뛰어 2번 우승했다는 뜻입니다.",
  },
  {
    term: "착차",
    description:
      "결승선에서 앞 말과의 거리 차이. 마신(말 몸길이 하나) 단위로, '3'이면 3마신 차이입니다.",
  },
  {
    term: "휴양(출주 간격)",
    description:
      "직전 경주 후 쉰 기간. 보통 2~6주가 최적이며 너무 짧거나 길면 감점 요인으로 봅니다.",
  },
];

const CONDITION_TERMS: Term[] = [
  {
    term: "주로 상태",
    description:
      "모래 주로의 수분 상태. '건조 (3%)'의 퍼센트는 함수율로, 비에 젖을수록 기록과 말별 유불리가 달라집니다.",
  },
  {
    term: "거리",
    description:
      "1000m는 스피드 승부, 1800m 이상은 스태미나 승부. 말마다 잘 뛰는 적성 거리가 다릅니다.",
  },
  {
    term: "별정·마령",
    description:
      "부담중량을 정하는 방식. 마령은 나이·성별 기준, 별정은 상금·성적 조건에 따라 가감합니다.",
  },
  { term: "발주", description: "출발. '13:05 발주'는 경주 시작 시각입니다." },
];

const SITE_TERMS: Term[] = [
  {
    term: "승률(winProb)",
    description:
      "통계+AI 모델이 추정한 그 말의 1착 확률. 한 경주 출전마의 승률을 모두 더하면 100%가 됩니다.",
  },
  {
    term: "예측 순위",
    description: "승률이 높은 순서. 1위가 단승 추천이 됩니다.",
  },
  {
    term: "신뢰도",
    description:
      "예측 1위와 2위의 승률 격차 기준 — 높음(뚜렷한 우세), 보통, 낮음(혼전 예상).",
  },
  {
    term: "AI 총평",
    description:
      "통계 수치를 근거로 AI가 쓴 경주 해설. AI는 통계 순위를 소폭만 보정할 수 있고 뒤집을 수 없습니다.",
  },
  {
    term: "단승 적중 / 연승 적중",
    description:
      "단승 추천마가 실제 1위면 단승 적중, 3위 이내면 연승 적중. 모든 예측은 경주 전에 기록되고 사후 수정하지 않습니다.",
  },
];

const SECTIONS = [
  { id: "betting", title: "베팅 승식 (마권 종류)", terms: BETTING_TERMS },
  { id: "entry", title: "출전 관련", terms: ENTRY_TERMS },
  { id: "ability", title: "능력·컨디션 지표", terms: ABILITY_TERMS },
  { id: "condition", title: "경주 조건", terms: CONDITION_TERMS },
  { id: "site", title: `${SITE_NAME} 지표 읽는 법`, terms: SITE_TERMS },
];

export default function GuidePage() {
  return (
    <article className="space-y-8">
      <header>
        <h1 className="text-2xl font-bold">경마 용어 가이드</h1>
        <p className="mt-1 text-sm text-muted">
          경마가 처음이어도 {SITE_NAME}을 읽을 수 있도록 핵심 용어만 골라
          설명합니다.
        </p>
        <nav className="mt-4 flex flex-wrap gap-2 text-sm">
          {SECTIONS.map((s) => (
            <a
              key={s.id}
              href={`#${s.id}`}
              className="rounded-full border border-border bg-surface px-3 py-1 text-muted hover:border-brand hover:text-brand"
            >
              {s.title}
            </a>
          ))}
        </nav>
      </header>

      <section className="rounded-xl border border-brand bg-surface p-4 text-sm leading-relaxed">
        <h2 className="font-semibold">화면 읽는 법, 30초 요약</h2>
        <p className="mt-2">
          경주 페이지는 위에서부터 <strong>결과</strong>(끝난 경주만) →{" "}
          <strong>AI 경주 브리핑</strong> → <strong>출전표</strong> 순입니다.
          브리핑의 <strong>총평</strong>을 먼저 읽고 경주의 구도를 잡은 뒤,
          말별 한줄평과 승률 막대로 근거를 확인하세요. 모델 상위 후보는
          통계적 후보일 뿐입니다 — 출전표에서 1년 전적, 마체중 증감(급변
          주의), 기수 &lsquo;변경&rsquo; 배지까지 보고 직접 판단하는 것이 이
          서비스의 사용법입니다.
        </p>
      </section>

      {SECTIONS.map((section) => (
        <section key={section.id} id={section.id} className="scroll-mt-20">
          <h2 className="mb-3 text-lg font-semibold">{section.title}</h2>
          <div className="overflow-hidden rounded-xl border border-border bg-surface">
            <dl>
              {section.terms.map((t) => (
                <div
                  key={t.term}
                  className="grid grid-cols-[7rem_1fr] gap-3 border-b border-border p-3 text-sm last:border-0 sm:grid-cols-[9rem_1fr]"
                >
                  <dt className="font-semibold">{t.term}</dt>
                  <dd className="leading-relaxed text-muted">{t.description}</dd>
                </div>
              ))}
            </dl>
          </div>
        </section>
      ))}

      <p className="text-sm text-muted">
        더 자세한 서비스 설명은 <Link href="/about" className="text-brand hover:underline">소개</Link>,
        예측 성적은 <Link href="/results" className="text-brand hover:underline">적중률 추적</Link>에서
        확인할 수 있습니다.
      </p>
    </article>
  );
}
