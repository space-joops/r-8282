"""KRA 오픈API 엔드포인트 레지스트리.

경로는 2026-08-15에 더미 키 프로브로 전수 검증함
(SERVICE_KEY_IS_NOT_REGISTERED_ERROR 응답 = 경로 존재).
approved는 현재 개발계정의 활용신청 승인 여부 — 미승인 API 호출 시
게이트웨이가 SERVICE_KEY 오류를 반환한다(KraAuthError).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Endpoint:
    name: str  # 캐시/픽스처 디렉터리명
    path: str  # https://apis.data.go.kr/B551015/ 이후 경로
    key_param: str  # 구세대 API는 대문자 ServiceKey를 쓴다
    approved: bool


# ── 승인 완료 ──────────────────────────────────────────────
# 경주 편성 (meet, rc_year/rc_month/rc_date 선택 — 생략 시 최근 1개월)
RACE_PLAN = Endpoint("racePlan_2", "API72_2/racePlan_2", "ServiceKey", True)
# 당일 경주결과종합: 출주마별 성적·기수/조교사 통산·1년 스탯, 마체중 증감,
# 예정출발시각, 취소 플래그 등 94필드. rc_date로 과거 조회도 가능
RACE_RESULT_TOTAL = Endpoint("Race_Result_total", "API299/Race_Result_total", "serviceKey", True)
# 경주마별 1년간 전적 (rccrs_cd, hr_no 또는 hr_name)
HORSE_1Y_RECORD = Endpoint("rchrLoyRcod", "API145/rchrLoyRcod", "serviceKey", True)
# 당일 기수 변경 상세
JOCKEY_CHANGE = Endpoint("Jockey_Change_Detail", "API300/Jockey_Change_Detail", "serviceKey", True)
# 서울 출전등록현황 (race_dt 필수, race_no 선택)
SEOUL_ENTRY_REG = Endpoint("textDataHoldSeRegInfo", "API323/textDataHoldSeRegInfo", "serviceKey", True)
# 서울 출전마체중 (race_dt·race_no 필수)
SEOUL_HORSE_WEIGHT = Endpoint("textDataHoldSeWegInfo", "API317/textDataHoldSeWegInfo", "serviceKey", True)
# 마필 상세 (혈통 등록 정보)
HORSE_DETAIL = Endpoint("HorseDetailInfo", "API282/HorseDetailInfo", "serviceKey", True)
# AI학습용 경주결과 (rccrs_cd·race_dt 필수) — 백테스트·캘리브레이션용
AI_RACE_RESULT = Endpoint("raceResult", "API155/raceResult", "serviceKey", True)

# ── 추가 신청 대기 (경로는 검증됨) ─────────────────────────
# 출전표정보: 전 경마장 출전표 단일 API (rccrs_cd·race_dt·race_no) — 최우선 신청 대상
CHULMA_INFO = Endpoint("chulmainfo", "API78/chulmainfo", "serviceKey", False)
# AI학습용 경주계획
AI_RACE_PLAN = Endpoint("racePlan", "API154/racePlan", "serviceKey", False)
# 경주성적정보 (과거 상세 + 배당)
RACE_DETAIL_RESULT = Endpoint("RaceDetailResult_1", "API214_1/RaceDetailResult_1", "serviceKey", False)
# 확정배당율종합 (pool: WIN/PLC/QNL/EXA/…)
DIVIDEND_RATE = Endpoint("Dividend_rate_total", "API301/Dividend_rate_total", "serviceKey", False)
# 기수 성적 (jk_name/jk_no, meet)
JOCKEY_RESULT = Endpoint("jockeyResult_1", "API11_1/jockeyResult_1", "ServiceKey", False)
# 경주마 성적 (hr_name/hr_no)
HORSE_RESULT = Endpoint("raceHorseResult_2", "API15_2/raceHorseResult_2", "ServiceKey", False)
# 조교사 정보 (tr_name/tr_no, meet)
TRAINER_INFO = Endpoint("trainerInfo", "API308/trainerInfo", "serviceKey", False)
# 부산경남 출전마현황
BUSAN_ENTRY = Endpoint("textDataHoldBuPtinInfo", "API316/textDataHoldBuPtinInfo", "serviceKey", False)
# 서울/부산경남 경주정보 (경주 조건 상세)
SEOUL_RACE_INFO = Endpoint("textDataHoldSeRaceInfo", "API311/textDataHoldSeRaceInfo", "serviceKey", False)
BUSAN_RACE_INFO = Endpoint("textDataHoldBuRaceInfo", "API313/textDataHoldBuRaceInfo", "serviceKey", False)
