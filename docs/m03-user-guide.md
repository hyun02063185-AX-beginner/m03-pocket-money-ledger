# M03 사용설명서 — 나만의 용돈 기입장

이 문서는 [README.md](../README.md)보다 좀 더 친절하게, 처음
프로그램을 쓰는 사람이 그대로 따라 할 수 있도록 쓴 사용설명서다.
모든 명령과 예시는 실제 프로그램(`ledger/cli.py`)과 정확히 일치한다.

## 1. 프로그램 소개

터미널에서 쓰는 개인 수입/지출 기록 프로그램이다. 거래를 추가하고,
목록을 보고, 조건으로 검색하고, 월별로 요약을 보고, 월 예산을
설정하고, 카테고리를 관리하고, 기존 거래를 수정/삭제하고, CSV
파일로 내보내거나 가져올 수 있다. 데이터는 프로그램을 종료해도
파일에 남는다.

## 2. 실행 환경

- Python 3.10 이상
- 표준 라이브러리만 사용 — **`pip install`로 따로 설치할 것이 없다**

## 3. 실행 방법

```bash
python -m ledger --help
```

이것이 표준 실행 방법이다. 다음처럼 짧게 써도 된다(같은 동작):

```bash
python main.py --help
```

Windows PowerShell에서도 동일하게 쓰면 된다:

```powershell
python -m ledger --help
```

프로젝트 루트 디렉터리(`main.py`가 있는 위치)에서 실행해야 한다.

## 4. 데이터 저장 위치

기본 저장 위치는 `./data`다. 세 개의 파일을 쓰며, 파일이 없으면
필요할 때(쓰기가 처음 발생할 때) 자동으로 만든다.

| 파일 | 내용 |
|---|---|
| `data/transactions.jsonl` | 거래 내역 |
| `data/categories.jsonl` | 등록한 카테고리 목록 |
| `data/budgets.jsonl` | 월별 총예산 |

저장 위치를 바꾸려면:

```bash
python -m ledger --data-dir ./my-data list
```

**`--data-dir`은 반드시 서브커맨드(`list`, `add` 등)보다 앞에 와야
한다.** 아래처럼 뒤에 쓰면 동작하지 않는다:

```bash
python -m ledger list --data-dir ./my-data   # 이렇게 쓰지 말 것
```

## 5. 처음 시작하기

이 프로그램은 "식비", "교통" 같은 기본 카테고리를 자동으로 만들어
주지 않는다. **카테고리가 하나도 없으면 거래를 추가할 수 없다.**

**1단계 — 카테고리 등록**

```bash
python -m ledger category add
```

`카테고리명:`이라고 물어보면 원하는 이름(예: `식비`)을 입력한다.

**2단계 — 거래 추가**

```bash
python -m ledger add
```

이제 방금 등록한 카테고리를 입력해 거래를 추가할 수 있다.

## 6. 카테고리 관리

```bash
python -m ledger category add       # 카테고리명을 물어봄
python -m ledger category list      # 등록된 카테고리 한 줄씩 출력
python -m ledger category remove    # 삭제할 카테고리명을 물어봄
```

카테고리를 **이미 사용 중인 거래가 하나라도 있으면 삭제할 수
없다.** 삭제를 시도하면 아래처럼 나온다:

```
[오류] 사용 중인 카테고리는 삭제할 수 없습니다.
[힌트] 해당 거래의 카테고리를 먼저 수정하세요.
```

이 경우 그 카테고리를 쓰는 거래를 먼저 다른 카테고리로 수정하거나
삭제해야 한다.

## 7. 거래 추가

```bash
python -m ledger add
```

옵션 없이 실행하면 순서대로 물어본다:

1. **날짜** (`YYYY-MM-DD` 형식, 예: `2026-09-16`)
2. **타입** (`income` 또는 `expense`만 입력 가능)
3. **카테고리** (미리 등록된 이름만 가능)
4. **금액** (0보다 큰 정수)
5. **메모** (선택 — 그냥 Enter를 치면 건너뜀)
6. **태그** (선택 — 쉼표로 구분, 예: `meal,lunch`)

잘못된 값을 입력하면 원인과 힌트를 보여주고 같은 항목을 다시
물어본다(최대 3번). 3번 모두 실패하면 등록이 취소된다.

**예시 대화**:

```
날짜 (YYYY-MM-DD): 2026-09-16
타입 (income/expense): expense
카테고리: 식비
금액: 15000
메모 (선택, Enter로 건너뛰기): 점심
태그 (쉼표로 구분, 선택): meal,lunch
[저장 완료] id=TX-000001
```

저장된 거래에는 `TX-000001`처럼 화면에 보여줄 때만 번호가 붙는다
(실제로는 내부적으로 1, 2, 3 … 정수로 관리된다).

## 8. 거래 목록

```bash
python -m ledger list
python -m ledger list --limit 5
```

기본으로 최근 10건을 보여주며, `--limit`으로 개수를 바꿀 수 있다.

**주의**: 여기서 "최신"은 **입력한 순서**를 뜻한다 — 거래 날짜
(`date`) 기준으로 다시 정렬하는 것이 아니다. 예를 들어 지난달
영수증을 오늘 뒤늦게 입력하면, 그 거래가 날짜는 과거여도 방금
입력했으니 목록 맨 위에 나온다.

## 9. 검색

```bash
python -m ledger search --category 식비
python -m ledger search --from 2026-09-01 --to 2026-09-30
python -m ledger search --type expense
python -m ledger search --q 점심
python -m ledger search --tag meal
python -m ledger search --category 식비 --type expense --from 2026-09-01 --to 2026-09-30
```

사용 가능한 옵션 6개:

| 옵션 | 의미 |
|---|---|
| `--from YYYY-MM-DD` | 이 날짜 이후(포함) |
| `--to YYYY-MM-DD` | 이 날짜 이전(포함) |
| `--category 이름` | 정확히 일치하는 카테고리 |
| `--type income\|expense` | 정확히 일치하는 타입 |
| `--q 텍스트` | 메모에 포함된 텍스트(대소문자 구분 안 함) |
| `--tag 태그` | 이 태그를 가진 거래 |

여러 옵션을 함께 쓰면 **모두 만족하는(AND)** 거래만 나온다.
아무 옵션도 안 주면 전체 거래를 최신순으로 보여준다.

## 10. 월별 요약

```bash
python -m ledger summary --month 2026-09
python -m ledger summary --month 2026-09 --top 3
```

`--month`는 필수다. `--top`은 지출 상위 카테고리를 몇 개까지
보여줄지 정하며, 생략하면 3개다.

출력에 포함되는 것: 총 수입, 총 지출, 잔액, 지출 상위 카테고리,
그리고 그 달에 예산이 설정돼 있으면 예산 금액/사용률/초과 여부까지.
그 달에 거래가 하나도 없으면 "데이터 없음"만 나온다.

## 11. 예산

```bash
python -m ledger budget set --month 2026-09 --amount 500000
```

**한 달 전체의 총예산**이다(카테고리별 예산이 아니다). 설정 후
`summary --month`를 실행하면 예산 대비 사용률과 초과 여부를 함께
보여준다. **예산을 초과해도 거래 추가는 계속 가능하다** — 예산은
경고용이지, 거래를 막는 기능이 아니다.

## 12. 거래 수정

```bash
python -m ledger update --id 1 --amount 18000
python -m ledger update --id 1 --amount 18000 --category 교통 --memo 택시
```

`--id`는 항상 필요하고, 그 외 `--date`/`--type`/`--category`/
`--amount`/`--memo`/`--tags` 중 **최소 하나**를 지정해야 한다.
지정하지 않은 항목은 원래 값 그대로 유지된다.

**메모/태그를 비우고 싶을 때**는 빈 값을 명시적으로 줘야 한다:

```bash
python -m ledger update --id 1 --memo ""
python -m ledger update --id 1 --tags ""
```

옵션 자체를 아예 쓰지 않으면 "그대로 유지", 빈 값(`""`)을 주면
"비움"이라는 뜻이다 — 이 둘은 다르게 동작한다. 셸(PowerShell,
명령 프롬프트, bash 등)마다 빈 문자열 전달 방식이 조금씩 다를 수
있으니, 위처럼 큰따옴표 두 개(`""`)를 붙여 쓰면 대부분의 환경에서
동작한다.

## 13. 거래 삭제

```bash
python -m ledger delete --id 1
```

**확인 질문 없이 바로 삭제된다.** 존재하지 않는 id를 지정하면
에러가 나고 아무것도 지워지지 않는다.

## 14. CSV로 가져오기 (Import)

```bash
python -m ledger import --from import.csv
```

CSV는 아래 6개 컬럼을 정확히 갖춰야 한다(값은 비어 있어도 되지만
컬럼 이름은 전부 있어야 함):

```
date,type,category,amount,memo,tags
2026-09-16,expense,식비,15000,점심,"meal,lunch"
2026-09-17,income,급여,3000000,급여,
```

- 파일은 UTF-8로 저장해야 한다.
- 헤더(첫 줄) 필수, 6개 컬럼명이 전부 있어야 한다.
- **CSV의 카테고리는 미리 `category add`로 등록돼 있어야 한다** —
  등록 안 된 카테고리를 쓴 행은 건너뛴다.
- 유효한 행은 가져와지고, 문제 있는 행(날짜 형식 오류, 미등록
  카테고리, 잘못된 금액 등)은 건너뛰며, 결과에 몇 건을
  가져왔고(`imported`) 몇 건을 건너뛰었는지(`skipped`) 보여준다.
- 가져온 거래는 **새 id를 자동으로 발급받는다** — CSV에 id가
  있어도 무시된다(애초에 CSV 스키마에 id 컬럼이 없다).

**실행 예시**:

```
[건너뜀] row=3: 등록되지 않은 카테고리입니다.
[완료] imported=4, skipped=1
```

## 15. CSV로 내보내기 (Export)

```bash
python -m ledger export --out export.csv --month 2026-09
python -m ledger export --out export.csv --from 2026-09-01 --to 2026-09-30
```

기간 조건이 **반드시 하나** 있어야 한다 — `--month` 또는
`--from`+`--to`(둘 다 필요) 중 하나만. 조건 없는 export는 거부된다:

```bash
python -m ledger export --out export.csv   # 에러: 기간 조건 없음
```

내보낸 CSV에는 거래 id가 포함되지 않는다.

## 16. 오류 메시지 보는 법

문제가 생기면 항상 아래 형식으로 알려준다:

```
[오류] <무엇이 문제인지>
[힌트] <어떻게 해결할지>
```

프로그램 내부 오류(파이썬 스택트레이스)를 보여주지 않는다 — 예상
가능한 실수는 전부 위 형식으로 안내한다.

**종료 코드**(스크립트에서 활용할 경우):

| 코드 | 의미 |
|---|---|
| 0 | 성공, 또는 `--help` 출력 |
| 1 | 프로그램이 처리 가능한 오류(예: 잘못된 입력, 존재하지 않는 거래) |
| 2 | 명령어 사용법 자체가 잘못됨(필수 옵션 누락 등) |

## 17. 자주 하는 실수

- **카테고리 없이 `add` 실행**: `category add`로 카테고리를 먼저
  등록해야 한다.
- **`--data-dir` 위치**: 서브커맨드보다 반드시 앞에 와야 한다.
- **`summary`에 `--month` 빠뜨림**: `--month`는 필수 옵션이다.
- **`export`에 기간 조건 없음**: `--month` 또는 `--from`+`--to`
  중 하나는 꼭 있어야 한다.
- **금액에 0 이하 값**: 금액은 반드시 0보다 큰 정수여야 한다.
- **타입 오타**: `income` 또는 `expense`만 가능하다(대소문자까지
  정확히 일치해야 함).
- **날짜 형식**: 반드시 `YYYY-MM-DD`(예: `2026-09-16`).
- **월 형식**: 반드시 `YYYY-MM`(예: `2026-09`, `2026-9`는 안 됨).
- **사용 중인 카테고리 삭제 시도**: 그 카테고리를 쓰는 거래를 먼저
  정리해야 한다.
- **import할 CSV의 카테고리 미등록**: import 전에 CSV에 등장하는
  카테고리를 전부 `category add`로 등록해야 한다.
- **태그 안에 쉼표(,) 사용**: 태그는 쉼표로 구분되므로, 태그 이름
  자체에 쉼표를 넣을 수 없다.
- **"최신순"을 날짜순으로 오해**: `list`/`search`의 최신순은
  입력한 순서 기준이다(섹션 8 참고).

## 18. 5분 튜토리얼

한 달(예: `2026-09`)을 기준으로 처음부터 끝까지 따라 해 보는
예시다.

```bash
# 1. 카테고리 등록
python -m ledger category add
# → 카테고리명: 식비

# 2. 지출 추가
python -m ledger add
# → 2026-09-01 / expense / 식비 / 15000 / 점심 / (Enter)

# 3. 수입 추가
python -m ledger add
# → 2026-09-05 / income / 식비 / 300000 / 용돈 / (Enter)

# 4. 목록 확인
python -m ledger list

# 5. 이번 달 예산 설정
python -m ledger budget set --month 2026-09 --amount 200000

# 6. 이번 달 요약 확인
python -m ledger summary --month 2026-09

# 7. 이번 달 거래를 CSV로 내보내기
python -m ledger export --out 2026-09.csv --month 2026-09
```

## 19. 데이터 백업 관련 주의

**이 프로그램에는 자동 백업 기능이 없다.** `data/` 디렉터리(또는
`--data-dir`로 지정한 위치)를 직접 복사해 두는 것이 유일한 백업
방법이다. 백업/복원은 Mission Core 범위 밖이며 이번 버전에 구현돼
있지 않다.

## 20. 알려진 제약

- 태그 안에 리터럴 쉼표(`,`)는 쓸 수 없다 — 쉼표는 항상 태그
  구분자로만 취급된다.
- `list`/`search`의 "최신순"은 입력(기록) 순서 기준이며, 거래
  날짜로 다시 정렬하지 않는다(섹션 8, 17 참고).
- CSV로 가져올 때 내용이 완전히 같은 행이 여러 번 있거나 기존
  거래와 우연히 같아도, 중복 여부를 판단하지 않고 매번 새 거래로
  등록한다.
- 정적 타입 검사 도구(`mypy` 등)는 프로젝트에 포함돼 있지 않다
  (표준 라이브러리만 사용하는 범위 내에서 코드 리뷰로 타입 힌트를
  확인함) — 일반 사용에는 영향이 없다.

더 자세한 설계 배경이 궁금하면
[docs/m03-architecture-design.md](m03-architecture-design.md)를,
최종 검증 결과가 궁금하면
[docs/m03-final-qa-report.md](m03-final-qa-report.md)를 참고하라.
