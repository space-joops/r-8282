# 한국마사회(KRA) Open API 레퍼런스

> data.go.kr에 등록된 한국마사회 공공데이터 Open API(서비스 `B551015`) 사용법 정리. 실제 사용 서비스와 무관하게, 이 API 자체를 호출하려는 누구나(다른 프로젝트·다른 AI 포함) 그대로 참고할 수 있도록 작성했다. 필드 목록은 대부분 실제 호출로 관측된 라이브 응답에서 추출한 값이며(추정으로 넣은 서류상 필드가 아님), 공식 문서에서 확인하지 못한 항목은 그렇게 표시했다.
>
> 검증 시점: 2026-08-22 (경로·응답 구조는 2026-08-15 재검증 기준).

## 1. 개요

- **제공처**: 공공데이터포털([data.go.kr](https://www.data.go.kr)), 서비스명 `B551015`(한국마사회_경마정보)
- **방식**: REST, 요청 시 `_type=json`을 붙이면 대체로 JSON 응답(단, 4번 항목의 예외 있음), 붙이지 않으면 XML
- **Base URL**: `https://apis.data.go.kr/B551015`
- **엔드포인트 URL 형식**: `{Base URL}/{API번호}/{API명}` (예: `https://apis.data.go.kr/B551015/API78/chulmainfo`)
- **비용**: 무료
- **활용신청**: data.go.kr 마이페이지 → 개발계정 상세 → API마다 개별로 "활용신청" 승인이 필요함. 미승인 API를 호출하면 게이트웨이가 인증 오류를 반환한다(§4 참고). 승인은 API 단위이며, 승인된 계정이라도 신규 API는 별도 신청이 필요하다.

## 2. 인증

- 서비스키를 **쿼리 파라미터**로 전달한다. 파라미터 이름이 API마다 다르다:
  - 최신 API 대부분: `serviceKey` (소문자)
  - 구세대 API(`racePlan_2`, `jockeyResult_1`, `raceHorseResult_2`): `ServiceKey` (대문자 시작)
  - 어느 것을 쓰는지는 §5 엔드포인트 표의 "인증 파라미터" 열 참고. 틀린 대소문자로 보내면 서비스키 자체가 무시되어 인증 오류가 난다.
- data.go.kr은 키를 두 형태로 보여준다 — **Encoding**(URL 인코딩된 형태, `%2B` 등 포함)과 **Decoding**(원본). HTTP 클라이언트가 쿼리 파라미터를 보낼 때 자동으로 다시 인코딩하므로, **Decoding(원본) 키를 사용해야 한다.** Encoding 키를 그대로 붙여넣으면 이중 인코딩되어 인증 오류가 난다.
- 인증 실패 시 두 가지 형태로 응답이 온다:
  1. HTTP 401/403 (게이트웨이가 요청 자체를 거부)
  2. HTTP 200이지만 바디가 `OpenAPI_ServiceResponse` 래퍼(§4 참고) — 이 경우도 인증/승인 오류로 취급해야 함

## 3. 공통 요청 규칙

| 파라미터 | 설명 |
|---|---|
| `_type` | `json` 고정 권장(생략 시 XML). 단, 자료실 계열(§4 XML 폴백 참고)은 이 값을 무시하고 XML을 줄 때가 있다 |
| `pageNo` | 1부터 시작하는 페이지 번호 |
| `numOfRows` | 페이지당 건수(대부분 API 기본값을 지원하지만 명시 권장, 100~999까지 관측됨) |
| `meet` / `rccrs_cd` | 경마장 코드 — API에 따라 파라미터명이 `meet` 또는 `rccrs_cd`로 다르다(같은 코드 체계). `1`=서울, `2`=제주, `3`=부산경남 (`4`=영천은 코드상 존재하나 실질적으로 데이터가 없음) |
| 날짜 파라미터 (`rc_date`, `race_dt` 등) | `YYYYMMDD` 8자리 숫자 문자열 (예: `20260822`) |
| 월 파라미터 (`rc_month`) | `YYYYMM` 6자리 (일부 API가 일자 대신 월 단위 조회를 지원 — §5 참고) |

## 4. 공통 응답 규칙

### 정상 응답 envelope

```json
{
  "response": {
    "header": { "resultCode": "00", "resultMsg": "NORMAL SERVICE." },
    "body": {
      "items": { "item": [ { "...": "..." } ] },
      "numOfRows": 100,
      "pageNo": 1,
      "totalCount": 95
    }
  }
}
```

- `header.resultCode`: `"00"` = 정상. `"03"` 또는 `"NODATA_ERROR"` = 데이터 없음(오류 아님, 빈 결과로 처리하면 됨). 그 외 코드는 실제 오류.
- `body.items`: **결과가 1건이면 `item`이 dict, 2건 이상이면 `item`이 list** — 클라이언트에서 항상 list로 정규화해서 다뤄야 한다. 결과 0건이면 `items`가 빈 문자열(`""`)로 오는 경우도 있다.
- `body.totalCount`: 전체 건수. 응답 자체에는 "마지막 페이지" 표시가 없으므로, `pageNo * numOfRows >= totalCount`가 될 때까지 페이지를 순회해야 전체를 수집할 수 있다.

### 게이트웨이 오류 envelope (인증/승인 문제)

정상 요청 처리 이전 단계(인증 실패, 미등록 키, 일일 트래픽 초과 등)에서는 위와 다른 래퍼로 응답한다:

```json
{
  "OpenAPI_ServiceResponse": {
    "cmmMsgHeader": {
      "errMsg": "SERVICE ERROR",
      "returnAuthMsg": "SERVICE_KEY_IS_NOT_REGISTERED_ERROR",
      "returnReasonCode": "30"
    }
  }
}
```

이 형태가 오면 `resultCode`가 아니라 `returnReasonCode`/`returnAuthMsg`를 봐야 한다. 대표적인 사유: 서비스키 미등록, 활용신청 미승인, 일일 트래픽 초과, 파라미터 누락.

### JSON 요청해도 XML이 오는 경우

`_type=json`을 요청해도 **일부 "자료실"(text-data) 계열 API**(`textDataHold*` 등)는 XML로 응답할 때가 있다. 응답 문자열이 `<`로 시작하면 JSON 파서 대신 XML 파서로 폴백해야 한다(XML 구조는 대체로 위 JSON envelope와 동일한 계층을 따름).

### `meet` 필드의 요청/응답 비대칭

요청 파라미터의 `meet`/`rccrs_cd`는 숫자 코드(`1`/`2`/`3`)이지만, **응답 바디의 `meet` 필드는 한글 트랙명 문자열**("서울"/"제주"/"부산경남")로 온다. 요청값과 응답값의 타입·형식이 다르다는 점에 주의.

## 5. 엔드포인트 레퍼런스

승인 상태는 **API 자체의 존재·경로 여부와 무관** — 계정별로 개별 활용신청이 필요하다는 뜻이며, 아래는 한 개발계정 기준 승인 현황 스냅샷이다.

### 5.1 API72_2 — `racePlan_2` (경주 편성)

경주 일정·조건(등급·거리·부담중량·상금) 정보.

- 인증 파라미터: `ServiceKey` (대문자)
- 요청: `GET /API72_2/racePlan_2?ServiceKey=...&meet=1&rc_date=20260822&pageNo=1&numOfRows=100&_type=json`
- 파라미터: `meet`(선택), `rc_year`/`rc_month`/`rc_date`(모두 선택 — 생략 시 최근 1개월 범위 반환)
- 응답 필드(실관측): `rcDate`, `rcNo`, `rcName`, `rcDist`(경주거리·m), `rank`(등급), `budam`(부담중량 구분), `ageCond`(연령조건), `sexCond`(성별조건), `schStTime`(예정 발주시각), `ilsu`(휴양일수 관련 조건), `meet`, `spRating`/`stRating`(레이팅 하한/상한), `buga1`~`buga3`, `chaksun1`~`chaksun5`(착순별 상금)

### 5.2 API299 — `Race_Result_total` (경주결과종합)

경주 종료 후 출주마별 성적을 기수/조교사 통산·1년 스탯, 마체중 증감까지 포함해 종합 제공하는 최대 필드 수 API(~90필드).

- 인증 파라미터: `serviceKey`
- 요청: `GET /API299/Race_Result_total?serviceKey=...&meet=1&rc_date=20260822&pageNo=1&numOfRows=100&_type=json`
- 파라미터: `meet`(필수), `rc_date`(선택 — 생략 시 최근, 과거 일자 조회도 가능)
- 응답 필드(실관측, 대분류로 묶어서 표기):
  - 기본: `rcDate`, `rcNo`, `chulNo`, `hrNo`, `hrName`, `age`, `sex`, `wgHr`(마체중), `wgBudam`(부담중량), `winOdds`/`plcOdds`, `ord`(착순), `rcTime`(완주기록), `track`, `schStTime`, `startTimeChg`/`stTimeChgReason`(발주시각 변경), `noraceFlag`(경주 취소 등), `rank`, `prdName`(산지)
  - 마필 통산: `hrRcCntT`/`hrOrd1CntT`/`hrOrd2CntT`(통산 출주·1착·2착 수)
  - 기수: `jkNo`, `jkName`, `jkAge`, `jkCareer`, `rcCntT`/`rcCntY`, `ord1CntT`/`ord1CntY`, `ord2CntT`/`ord2CntY`(통산/1년 성적)
  - 조교사: `trNo`, `trName`, `trAge`, `trCareer`, `trRcCntT`/`trRcCntY`, `trOrd1CntT`/`trOrd1CntY`, `trOrd2CntT`/`trOrd2CntY`
  - 구간 통과기록 계열(공식 필드 설명 미확인 — 명명 규칙만 참고): `buG1fAccTime`/`buG2fAccTime`/`buG3fAccTime`/`buG4fAccTime`/`buG6fAccTime`/`buG8fAccTime`, `buS1fAccTime`/`buS1fTime`, `bu_1fGTime`/`bu_2fGTime`/`bu_4_2fTime`/`bu_6_4fTime`/`bu_8_6fTime`/`bu_10_8fTime`, `seG1fAccTime`/`seG3fAccTime`/`seS1fAccTime`, `se_1cAccTime`~`se_4cAccTime`, `sjG1fOrd`/`sjG3fOrd`/`sjS1fOrd`, `sj_1cOrd`~`sj_4cOrd`, `jeG1fTime`/`jeG3fTime`/`jeS1fTime`, `je_1cTime`~`je_4cTime`, `finalBit`
- 참고: `T` 접미사=통산(all-time), `Y` 접미사=최근 1년

### 5.3 API145 — `rchrLoyRcod` (경주마 1년간 전적)

- 인증 파라미터: `serviceKey`
- 요청: `GET /API145/rchrLoyRcod?serviceKey=...&rccrs_cd=1&hr_name=화이트선더&pageNo=1&numOfRows=100&_type=json`
- 파라미터: `rccrs_cd`(경마장코드), `hr_name` 또는 `hr_no`(마명/마번호 — 조회 대상 지정용)
- 응답 필드: `hrno`, `hrnm`, `rccrsNm`, `lstPtinDt`(최근 출주일), `loyPtinTcnt`(1년 출주횟수), `loyFcmTcnt`/`loyScmTcnt`/`loyTcmTcnt`(1착/2착/3착 횟수), `loyFocmTcnt`/`loyFvcmTcnt`(4착/5착), `loyCnpmAmt`/`loyPlcpmAmt`(단승/연승 상금 관련 금액)

### 5.4 API300 — `Jockey_Change_Detail` (당일 기수 변경)

- 인증 파라미터: `serviceKey`
- 요청: `GET /API300/Jockey_Change_Detail?serviceKey=...&meet=1&rc_date=20260822&pageNo=1&numOfRows=100&_type=json`
- 파라미터: `meet`, `rc_date`
- 응답 필드: **실관측 데이터 없음** — 캐시에 남은 요청은 모두 기수 변경이 없던 날이라 빈 응답(`items` 없음)만 확인됨. 필드 스키마는 미확인.

### 5.5 API323 — `textDataHoldSeRegInfo` (서울 출전등록현황)

- 인증 파라미터: `serviceKey`
- 요청: `GET /API323/textDataHoldSeRegInfo?serviceKey=...&race_dt=20260822&pageNo=1&numOfRows=100&_type=json`
- 파라미터: `race_dt`(필수), `race_no`(선택)
- 응답 필드: `raceDt`, `raceNo`, `rcptNo`(접수번호/마번), `hrnm`, `ag`(연령), `gndr`(성별), `prds`(산지), `ratg`(레이팅), `ownerNm`(마주명), `trarNm`(조교사명), `loyProdNm`, `erngSump`/`erngLsxt`/`erngLtht`(상금 관련), `multl`, `raceDotw`(요일)
- 비고: `CHULMA_INFO`(§5.9)가 비어 있을 때 서울 지역 폴백 소스로 쓰인다.

### 5.6 API317 — `textDataHoldSeWegInfo` (서울 출전마체중)

- 인증 파라미터: `serviceKey`
- 요청: `GET /API317/textDataHoldSeWegInfo?serviceKey=...&race_dt=20260822&race_no=1&pageNo=1&numOfRows=100&_type=json`
- 파라미터: `race_dt`, `race_no` (둘 다 필수 — 경주 단위로만 조회 가능)
- 응답 필드: `raceDt`, `raceNo`, `pthrNo`(마번), `hrnm`, `hrWeg`(마체중, kg), `indec`(전주 대비 증감), `lstPtinDy`(최근 출주일)

### 5.7 API282 — `HorseDetailInfo` (마필 상세/혈통)

- 인증 파라미터: `serviceKey` — **승인됨, 그러나 실호출 기록 없음**
- 파라미터/응답 필드: 미확인 (호출 이력이 없어 라이브 응답을 관측하지 못함)

### 5.8 API155 — `raceResult` (AI학습용 경주결과)

- 인증 파라미터: `serviceKey` — **승인됨, 그러나 실호출 기록 없음**
- 파라미터: `rccrs_cd`, `race_dt` 필수(문서상 확인, 실호출 없음)
- 응답 필드: 미확인

### 5.9 API78 — `chulmainfo` (출전표정보 — 전 경마장 통합)

경마장별로 나뉘어 있던 출전표 계열 API를 대체하는 통합 API. 마명·기수·부담중량·순위상금까지 한 번에 제공.

- 인증 파라미터: `serviceKey`
- 요청: `GET /API78/chulmainfo?serviceKey=...&rccrs_cd=1&race_dt=20260822&pageNo=1&numOfRows=100&_type=json`
- 파라미터: `rccrs_cd`(경마장코드), `race_dt`(경주일자) — 둘 다 필수. `race_no` 파라미터도 존재(경주 단위 조회)
- 응답 필드: `raceDt`, `raceNo`, `raceNm`, `raceDyCnt`(개최 회차), `gtno`(게이트번호), `hrnm`, `hrsAg`(마령), `gndrNm`(성별), `prdsNm`(산지), `burdWgt`(부담중량), `wgtIndec`(체중증감), `rating`, `jckyNm`(기수명), `trarNm`(조교사명), `ownerNm`(마주명), `equipCrs`(장구), `ptinCycl`(출주주기), `trngTcnt`(조교횟수), `spn`(주로 구분), `strtTim`(발주시각), `raceCnd1`/`raceCnd2`/`raceCnd3`(경주조건), `ord1AdmnyAmt`~`ord10RpmAmt`(착순별 배당·상금 계열, 1~10착)

### 5.10 API154 — `racePlan` (AI학습용 경주계획)

- 인증 파라미터: `serviceKey` — **미승인(신청대기)**. 호출 시 게이트웨이 인증 오류(§4)가 반환된다.
- 파라미터/응답 필드: 미확인

### 5.11 API214_1 — `RaceDetailResult_1` (경주성적정보 — 과거 상세)

`Race_Result_total`과 유사하지만 월 단위(`rc_month`) 조회에 최적화되어 있어 과거 데이터 대량 수집(백테스트 등)에 적합. 필드 구성은 §5.2와 거의 동일 + 일부 추가 필드.

- 인증 파라미터: `serviceKey`
- 요청: `GET /API214_1/RaceDetailResult_1?serviceKey=...&meet=1&rc_month=202607&pageNo=1&numOfRows=100&_type=json`
- 파라미터: `meet`(필수), `rc_month`(YYYYMM — 월 단위 조회) 또는 `rc_date`
- 응답 필드: §5.2와 대부분 겹침 + `birthday`(생년월일), `hrTool`(장구), `owName`/`owNo`(마주명/번호), `ordBigo`(착순 비고), `rankRise`(등급 승급 여부), `diffUnit`, `prizeCond`, `wgBudamBigo`, `weather`(날씨)

### 5.12 API301 — `Dividend_rate_total` (확정배당율종합)

전 승식의 확정 배당률을 조회. 승식(`pool`)마다 필요한 출주번호 열의 개수가 다르다.

- 인증 파라미터: `serviceKey`
- 요청: `GET /API301/Dividend_rate_total?serviceKey=...&meet=1&rc_date=20260822&pool=WIN&pageNo=1&numOfRows=100&_type=json`
- 파라미터: `meet`(필수), `rc_date` 또는 `rc_month`, `pool`(필수 — 아래 표)
- `pool` 값과 의미:

  | pool | 승식 | 필요 출주번호 열 |
  |---|---|---|
  | `WIN` | 단승 | `chulNo` |
  | `PLC` | 연승 | `chulNo` |
  | `QNL` | 복승 | `chulNo`, `chulNo2` |
  | `EXA` | 쌍승 | `chulNo`, `chulNo2` |
  | `QPL` | 복연승 | `chulNo`, `chulNo2` |
  | `TLA` | 삼복승 | `chulNo`, `chulNo2`, `chulNo3` |
  | `TRI` | 삼쌍승 | `chulNo`, `chulNo2`, `chulNo3` |

- 응답 필드: `rcDate`, `rcNo`, `meet`(한글 트랙명), `pool`, `chulNo`/`chulNo2`/`chulNo3`(해당 승식에 쓰이지 않는 열은 `0`으로 채워짐), `odds`(확정 배당률). 무효/미발매 조합은 `odds`가 `9999.9`로 오는 경우가 있음(발매 자체가 없었다는 마커로 해석해야 함 — 배당 0으로 오인하지 말 것).

### 5.13 API11_1 — `jockeyResult_1` (기수 성적)

- 인증 파라미터: `ServiceKey` (대문자)
- 요청: `GET /API11_1/jockeyResult_1?ServiceKey=...&meet=1&pageNo=1&numOfRows=100&_type=json`
- 파라미터: `meet`(트랙별 전체 목록 조회), 또는 `jk_name`/`jk_no`(특정 기수 단건 조회)
- 응답 필드: `jkNo`, `jkName`, `meet`, `rcCntT`/`rcCntY`(통산/1년 출주수), `ord1CntT`/`ord1CntY`, `ord2CntT`/`ord2CntY`, `winRateT`/`winRateY`(승률), `qnlRateT`/`qnlRateY`(연대율)

### 5.14 API15_2 — `raceHorseResult_2` (경주마 성적)

- 인증 파라미터: `ServiceKey` (대문자)
- 요청: `GET /API15_2/raceHorseResult_2?ServiceKey=...&hr_name=화이트선더&pageNo=1&numOfRows=100&_type=json`
- 파라미터: `hr_name` 또는 `hr_no`(마명/마번호 — 단건 조회 위주로 관측됨)
- 응답 필드: `hrNo`, `hrName`, `age`, `sex`, `debut`(데뷔일), `rcCntT`/`rcCntY`, `ord1CntT`/`ord1CntY`, `ord2CntT`/`ord2CntY`, `winRateT`/`winRateY`, `qnlRateT`/`qnlRateY`, `chaksunT`/`chaksunY`/`chaksun_6`(상금 관련), `recentRcDate`/`recentRcName`/`recentRcNo`/`recentRcDist`/`recentRcTime`/`recentOrd`/`recentRank`/`recentRating`/`recentBudam`/`recentWgHr`/`recentWgBudam`(가장 최근 출주 상세)

### 5.15 API308 — `trainerInfo` (조교사 정보)

- 인증 파라미터: `serviceKey`
- 요청: `GET /API308/trainerInfo?serviceKey=...&meet=1&pageNo=1&numOfRows=100&_type=json`
- 파라미터: `meet`, 또는 `tr_name`/`tr_no`(특정 조교사)
- 응답 필드: `trNo`, `trName`, `trNameEn`, `meet`, `meetEn`, `part`(소속), `stDate`/`spDate`(개업/휴업일), `rcCntT`/`rcCntY`, `ord1CntT`/`ord1CntY`, `ord2CntT`/`ord2CntY`, `ord3CntT`/`ord3CntY`, `winRateT`/`winRateY`, `qnlRateT`/`qnlRateY`, `plcRateT`/`plcRateY`(복승률)

### 5.16 API316 — `textDataHoldBuPtinInfo` (부산경남 출전마현황)

- 인증 파라미터: `serviceKey`
- 요청: `GET /API316/textDataHoldBuPtinInfo?serviceKey=...&race_dt=20260822&pageNo=1&numOfRows=100&_type=json`
- 파라미터: `race_dt`(필수)
- 응답 필드: `raceDt`, `raceNo`, `pthrNo`(마번), `hrnm`, `ag`, `gndr`, `prds`, `ratg`, `burdWgt`, `jckyNm`, `trarNm`, `ownerNm`, `asisEquip1`~`asisEquip5`(장구 5종), `latstBledg1`/`latstBledg2`(최근 혈통 관련), `latstTrea1Txt`/`latstTrea2Txt`(최근 처치 텍스트), `erngLoy`/`erngLsm`/`erngSump`(상금), `loyRcodFplc`/`loyRcodSplc`/`loyRcodTplc`/`loyRcodSum`, `sumpRcodFplc`/`sumpRcodSplc`/`sumpRcodTplc`/`sumpRcodSum`(착순 관련 통계)
- 비고: `CHULMA_INFO`(§5.9)가 비어 있을 때 부산경남 지역 폴백 소스로 쓰인다.

### 5.17 API311 — `textDataHoldSeRaceInfo` (서울 경주정보 — 날씨·주로)

- 인증 파라미터: `serviceKey`
- 요청: `GET /API311/textDataHoldSeRaceInfo?serviceKey=...&race_dt=20260822&pageNo=1&numOfRows=100&_type=json`
- 파라미터: `race_dt`(필수)
- 응답 필드: `raceDt`, `raceNo`, `raceNm`, `raceDyCnt`, `raceDotw`(요일), `raceDs`(거리), `raceClas`/`rcgrd`(등급), `going`(주로 상태), `wetr`(날씨), `strtTm`/`strtPargTm`(발주시각), `ptinNhr`(출주두수), `cndtsAg`/`cndtsGndr`/`cndtsBurdWgt`/`cndtsNcmr`/`cndtsPtctRcod`/`cndtsPurse`/`cndtsRatg`(경주 조건 상세), `admnyFplc`/`admnySplc`/`admnyTplc`(1·2·3착 상금), `rpmFplc`/`rpmSplc`/`rpmTplc`/`rpmFoplc`/`rpmFvplc`(순위별 배당 관련)
- 비고: **제주는 이 계열 API가 없다** — 날씨/주로 정보는 서울·부산경남만 제공됨.

### 5.18 API313 — `textDataHoldBuRaceInfo` (부산경남 경주정보)

§5.17과 완전히 동일한 필드 스키마. `race_dt` 파라미터만 다르게 부산경남 개최일을 조회.

---

## 6. 필드명 표기 규칙 (약어 해설)

정식 필드 설명 문서가 배포되지 않아, 실관측 값과 문맥으로 유추한 규칙이다. 완전히 확신하기 어려운 것은 "(추정)"으로 표시.

| 접두/접미사 | 의미 |
|---|---|
| `hr` / `Hr` (예: `hrName`, `hrnm`) | 말(horse) |
| `jk` / `jcky` (예: `jkName`, `jckyNm`) | 기수(jockey) |
| `tr` / `trar` (예: `trName`, `trarNm`) | 조교사(trainer) |
| `rc` (예: `rcDate`, `rcNo`, `rcDist`) | 경주(race) |
| `ord` | 착순(finish order/place) |
| `T` 접미사 (예: `rcCntT`) | 통산(all-time total) |
| `Y` 접미사 (예: `rcCntY`) | 최근 1년(year) |
| `budam` / `burdWgt` / `wgBudam` | 부담중량(handicap weight) |
| `gndr` / `sex` | 성별 |
| `ag` / `age` / `hrsAg` | 연령 |
| `chulNo` / `gtno` / `pthrNo` | 출주번호·게이트번호(마번과 유사하게 쓰임) |
| `odds` | 배당률 |
| `pool` | 승식 구분(§5.12 표) |
| `meet` / `rccrs_cd` | 경마장 구분(1=서울, 2=제주, 3=부산경남) |
| `going` / `wetr` | 주로 상태 / 날씨 |
| `prds` / `prdsNm` | 산지(원산지) |
| `winRate` / `qnlRate` / `plcRate` | 승률 / 연대율(2착 이내) / 복승률(3착 이내) (추정) |
| `bu`/`se`/`sj`/`je` 접두 구간기록 필드(예: `buG1fAccTime`, `seG3fAccTime`, `sjG1fOrd`, `je_1cTime`) | 경주 구간별(펄롱·코너 단위) 통과기록 계열로 추정되나, 정확한 산식·기준은 공식 문서 미제공 (추정) |

## 7. 알려진 이슈·특이사항 체크리스트

- [ ] `items.item`은 결과 건수에 따라 dict/list가 바뀐다 — 항상 list로 정규화할 것
- [ ] `resultCode`가 `"03"`/`"NODATA_ERROR"`면 오류가 아니라 "데이터 없음" — 빈 목록으로 처리
- [ ] `_type=json`을 지정해도 자료실(`textDataHold*`) 계열은 XML을 줄 수 있음 — 응답 첫 글자로 분기 필요
- [ ] 게이트웨이 오류(`OpenAPI_ServiceResponse` 래퍼)는 `resultCode`가 아니라 `returnReasonCode`/`returnAuthMsg`를 봐야 함
- [ ] `meet`은 요청 시 숫자, 응답 필드에서는 한글 트랙명 문자열 — 타입이 다름
- [ ] 서비스키는 Decoding(원본) 형태로 사용 — Encoding 키를 그대로 넣으면 이중 인코딩됨
- [ ] 서비스키 파라미터명이 API마다 `serviceKey`/`ServiceKey`로 다름(§5 각 항목 확인)
- [ ] `totalCount`로 직접 페이지 순회 종료를 계산해야 함(응답에 "마지막 페이지" 플래그 없음)
- [ ] `Dividend_rate_total`의 `odds=9999.9`는 무효/미발매 마커 — 실제 배당 0으로 오인하지 말 것
- [ ] 날씨·주로 정보(API311/313)는 서울·부산경남만 제공, 제주는 대응 API 없음
- [ ] 에러 메시지·로그에 인증키가 포함된 요청 URL을 그대로 남기지 않도록 주의(쿼리 파라미터에 키가 노출됨)
