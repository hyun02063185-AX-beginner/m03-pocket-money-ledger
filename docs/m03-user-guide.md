# M03 사용설명서 — 나만의 용돈 기입장

> **Historical/reference document.** 처음 실습하는 경우에는 기본 `./data`로
> 동료평가 데이터까지 만드는 [M03 Hands-on Guide](m03-hands-on-guide.md)를 먼저 읽는다.
> 코드와 Python 기초는 [M03 Code Reading Guide](m03-code-reading-guide.md)를 참고한다.

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

---

## 21. 직접 따라 해보는 M03 기능 실습

> 이 실습은 실제 사용 데이터를 건드리지 않고 M03의 기능을 하나씩
> 직접 실행해보기 위한 연습입니다. 모든 명령은 `./practice-data`
> (일부는 `./practice-import-data`)를 사용합니다. 위에서 아래로
> 순서대로 실행하면 됩니다.

**실행 명령 표기 안내**: macOS/Linux에서는 `python3`, Windows에서는
`python`을 쓸 수 있다(섹션 3 참고). 이 실습 섹션의 모든 예시는
`python3` 기준으로 적었으니, Windows에서는 `python`으로 바꿔
읽으면 된다.

### 21.1 사전 확인

현재 위치 확인:

```bash
pwd
```

프로젝트 파일 확인:

```bash
ls
```

다음 항목이 보여야 한다:

- `ledger/`
- `main.py`
- `README.md`
- `docs/`
- `tests/`

전체 도움말:

```bash
python3 -m ledger --help
```

각 명령의 도움말도 하나씩 직접 확인해본다:

```bash
python3 -m ledger add --help
python3 -m ledger list --help
python3 -m ledger search --help
python3 -m ledger summary --help
python3 -m ledger budget --help
python3 -m ledger category --help
python3 -m ledger update --help
python3 -m ledger delete --help
python3 -m ledger import --help
python3 -m ledger export --help
```

간단히 정리하면:

- `-m`은 Python 자체 옵션("뒤의 이름을 module/package로 실행하라").
- `ledger`는 이 프로젝트의 package.
- `--data-dir`은 M03에서 정의한 전역 옵션(섹션 4 참고).
- `--help`는 argparse가 기본 제공하는 도움말 기능.

### 21.2 실습 데이터 폴더 원칙

모든 실습 명령에서 아래 옵션을 사용한다:

```bash
--data-dir ./practice-data
```

**`--data-dir`은 반드시 subcommand보다 앞에 와야 한다**(섹션 4).

정상:

```bash
python3 -m ledger --data-dir ./practice-data list
```

잘못된 예:

```bash
python3 -m ledger list --data-dir ./practice-data
```

한 번 직접 실행해서 argparse 오류를 눈으로 확인해 보자:

```bash
python3 -m ledger list --data-dir ./practice-data
echo $?
```

`unrecognized arguments: --data-dir ./practice-data`라는 usage
오류와 함께 **exit code 2**로 끝나는 것을 확인한다(Scenario 30에서
exit code를 다시 정리한다).

### Scenario 1 — 빈 상태 확인

```bash
python3 -m ledger --data-dir ./practice-data category list
python3 -m ledger --data-dir ./practice-data list
```

확인 포인트:

- 처음에는 `[안내] 등록된 카테고리가 없습니다.` /
  `[안내] 거래 내역이 없습니다.`만 나오고, 데이터가 없다고 해서
  오류가 나지는 않는다.
- 아직 `./practice-data` 폴더 자체가 없어도 읽기 명령은 실패하지
  않는다 — 데이터 디렉터리/파일은 **쓰기가 처음 필요한 시점에**
  만들어지는 정책이다(섹션 4).

### Scenario 2 — 카테고리 없이 거래 추가 시도

```bash
python3 -m ledger --data-dir ./practice-data add
```

프롬프트 예:

```text
날짜 (YYYY-MM-DD): 2026-09-22
타입 (income/expense): expense
카테고리: food
```

아직 `food` 카테고리가 없으므로 아래와 같은 오류가 나오고 다시
카테고리를 물어본다(최대 3번):

```text
[오류] 등록되지 않은 카테고리입니다.
[힌트] category list로 확인하거나 category add로 먼저 등록하세요.
카테고리:
```

계속 `food`를 입력하면 3번째 실패 후 자동으로 등록이 취소되며
exit code 1로 끝난다. 다음 단계로 바로 넘어가고 싶다면 `Ctrl+C`로
중간에 종료해도 된다.

이 실습의 목적:

- 거래는 **이미 등록된 카테고리만** 쓸 수 있다.
- M03은 "식비", "교통" 같은 기본 카테고리를 자동으로 만들어주지
  않는다(섹션 5, `Option B` 정책).

### Scenario 3 — 카테고리 만들기

```bash
python3 -m ledger --data-dir ./practice-data category add
```

입력: `food`

```bash
python3 -m ledger --data-dir ./practice-data category add
```

입력: `salary`

```bash
python3 -m ledger --data-dir ./practice-data category add
```

입력: `transport`

목록 확인:

```bash
python3 -m ledger --data-dir ./practice-data category list
```

확인 포인트: `food`, `salary`, `transport` 세 줄이 순서대로 나온다.

### Scenario 4 — 중복 카테고리 오류

```bash
python3 -m ledger --data-dir ./practice-data category add
```

입력: `food`

확인:

```text
[오류] 이미 등록된 카테고리입니다.
[힌트] category list로 기존 카테고리를 확인하세요.
```

- 중복 카테고리가 추가되지 않는다.
- `[오류]`/`[힌트]` 두 줄 형식이며, Python 트레이스백은 나오지
  않는다(섹션 16).

### Scenario 5 — 첫 지출 거래 추가

```bash
python3 -m ledger --data-dir ./practice-data add
```

예제 입력:

```text
날짜 (YYYY-MM-DD): 2026-09-22
타입 (income/expense): expense
카테고리: food
금액: 15000
메모 (선택, Enter로 건너뛰기): 점심
태그 (쉼표로 구분, 선택): meal,lunch
```

성공하면 `[저장 완료] id=TX-000001`처럼 나온다.

- 내부 저장 id는 정수(1, 2, 3…)다.
- `TX-000001`은 화면에 보여줄 때만 붙는 표시용 형식이다(섹션 7).

### Scenario 6 — 수입 거래 추가

```bash
python3 -m ledger --data-dir ./practice-data add
```

입력:

```text
날짜 (YYYY-MM-DD): 2026-09-22
타입 (income/expense): income
카테고리: salary
금액: 3000000
메모 (선택, Enter로 건너뛰기): 9월 급여
태그 (쉼표로 구분, 선택): salary
```

### Scenario 7 — 다른 날짜의 지출 추가

```bash
python3 -m ledger --data-dir ./practice-data add
```

입력:

```text
날짜 (YYYY-MM-DD): 2026-09-20
타입 (income/expense): expense
카테고리: transport
금액: 2500
메모 (선택, Enter로 건너뛰기): 버스
태그 (쉼표로 구분, 선택): commute,bus
```

지난달 거래도 하나 더 추가한다:

```bash
python3 -m ledger --data-dir ./practice-data add
```

입력:

```text
날짜 (YYYY-MM-DD): 2026-08-31
타입 (income/expense): expense
카테고리: food
금액: 8000
메모 (선택, Enter로 건너뛰기): 저녁
태그 (쉼표로 구분, 선택): dinner
```

### Scenario 8 — 목록 확인

전체 기본 목록:

```bash
python3 -m ledger --data-dir ./practice-data list
```

최근 2건만:

```bash
python3 -m ledger --data-dir ./practice-data list --limit 2
```

확인 포인트:

- "최신순"은 `Transaction.date` 기준 정렬이 아니라 **입력한(파일에
  기록된) 순서의 역순**이다 — 그래서 방금 넣은 8월 31일 거래가
  9월 20일 거래보다 위에 나온다(섹션 8).
- `--limit 2`는 가장 최근에 입력한 2건만 보여준다.
- 내부적으로는 Generator로 파일을 한 줄씩 읽으며
  `deque(maxlen=2)`에 채우는 방식이다 — 더 깊은 기술 설명은
  [동료평가 가이드 5~6번 섹션](m03-peer-evaluation-guide.md)을
  참고.

### Scenario 9 — 검색 옵션 하나씩 사용

```bash
python3 -m ledger --data-dir ./practice-data search --category food
python3 -m ledger --data-dir ./practice-data search --type expense
python3 -m ledger --data-dir ./practice-data search --q 점심
python3 -m ledger --data-dir ./practice-data search --tag commute
python3 -m ledger --data-dir ./practice-data search --from 2026-09-01
python3 -m ledger --data-dir ./practice-data search --to 2026-09-21
```

각 옵션의 의미는 섹션 9의 표를 참고.

### Scenario 10 — 검색 조건 조합

```bash
python3 -m ledger --data-dir ./practice-data search \
  --from 2026-09-01 \
  --to 2026-09-30 \
  --type expense
```

```bash
python3 -m ledger --data-dir ./practice-data search \
  --category food \
  --type expense
```

검색 옵션은 전부 **AND**로 조합된다(섹션 9).

### Scenario 11 — 월별 요약

```bash
python3 -m ledger --data-dir ./practice-data summary --month 2026-09
```

확인: 총 수입, 총 지출, 잔액, 카테고리별 지출 TOP N.

TOP 개수 지정:

```bash
python3 -m ledger --data-dir ./practice-data summary \
  --month 2026-09 \
  --top 2
```

데이터 없는 달:

```bash
python3 -m ledger --data-dir ./practice-data summary --month 2025-01
```

확인: `데이터 없음`만 출력된다.

### Scenario 12 — 월 예산 설정

```bash
python3 -m ledger --data-dir ./practice-data budget set \
  --month 2026-09 \
  --amount 500000
```

다시 요약:

```bash
python3 -m ledger --data-dir ./practice-data summary --month 2026-09
```

확인: `예산`, `사용률`, `예산 초과: 아니오`가 함께 나온다.

### Scenario 13 — 예산 초과 테스트

일부러 작은 예산으로 다시 설정:

```bash
python3 -m ledger --data-dir ./practice-data budget set \
  --month 2026-09 \
  --amount 10000
```

다시 요약:

```bash
python3 -m ledger --data-dir ./practice-data summary --month 2026-09
```

확인:

- `[경고] 이번 달 예산을 N원 초과했습니다.`가 나온다.
- 예산을 초과해도 이미 추가된 거래가 지워지거나, 앞으로 거래
  추가가 막히지 않는다(섹션 11) — 방금 전 Scenario들처럼 거래를
  더 추가해도 정상적으로 저장된다.

### Scenario 14 — 거래 수정

먼저 id 확인:

```bash
python3 -m ledger --data-dir ./practice-data list
```

예를 들어 1번 거래의 금액만 수정:

```bash
python3 -m ledger --data-dir ./practice-data update \
  --id 1 \
  --amount 18000
```

여러 필드를 한 번에:

```bash
python3 -m ledger --data-dir ./practice-data update \
  --id 1 \
  --amount 20000 \
  --memo "친구와 점심"
```

다시 목록으로 반영 확인:

```bash
python3 -m ledger --data-dir ./practice-data list
```

### Scenario 15 — memo/tags 비우기

```bash
python3 -m ledger --data-dir ./practice-data update --id 1 --memo ""
python3 -m ledger --data-dir ./practice-data update --id 1 --tags ""
```

확인:

- 옵션 자체를 생략하면 기존 값이 그대로 유지된다.
- 빈 문자열(`""`)을 명시하면 값이 비워진다.

이 동작은 Service 내부의 **`UNSET` sentinel**로 "생략함"과
"명시적으로 비움"을 구분하기 때문이다(섹션 12 —
[동료평가 가이드 12번 섹션](m03-peer-evaluation-guide.md)에 구현
상세가 있다).

### Scenario 16 — update 오류

수정할 필드를 아예 지정하지 않음:

```bash
python3 -m ledger --data-dir ./practice-data update --id 1
```

존재하지 않는 거래:

```bash
python3 -m ledger --data-dir ./practice-data update \
  --id 999 \
  --amount 10000
```

존재하지 않는 카테고리:

```bash
python3 -m ledger --data-dir ./practice-data update \
  --id 1 \
  --category unknown
```

세 경우 모두 `[오류]`/`[힌트]` 형식으로 원인과 해결 방법을 보여주고,
Python 트레이스백은 나오지 않으며 exit code는 1이다.

### Scenario 17 — 사용 중인 카테고리 삭제 시도

```bash
python3 -m ledger --data-dir ./practice-data category remove
```

입력: `food`

`food`를 쓰는 거래가 아직 남아 있으므로 삭제가 차단된다:

```text
[오류] 사용 중인 카테고리는 삭제할 수 없습니다.
[힌트] 해당 거래의 카테고리를 먼저 수정하세요.
```

이 동작이 바로 섹션 6에서 설명한 **참조 무결성(referential
integrity)** 규칙이다 — 카테고리를 지워버리면 그 카테고리를
가리키는 거래가 존재하지 않는 카테고리를 참조하게 되기 때문이다.

### Scenario 18 — CSV Export (월 기준)

```bash
python3 -m ledger --data-dir ./practice-data export \
  --out ./practice-september.csv \
  --month 2026-09
```

파일 확인(macOS/Linux):

```bash
cat ./practice-september.csv
```

또는:

```bash
head ./practice-september.csv
```

확인할 CSV 헤더:

```text
date,type,category,amount,memo,tags
```

CSV에 거래 id 컬럼이 없는 것이 정상이다(섹션 15).

### Scenario 19 — CSV Export (기간 기준)

```bash
python3 -m ledger --data-dir ./practice-data export \
  --out ./practice-range.csv \
  --from 2026-09-01 \
  --to 2026-09-30
```

확인: `--from`/`--to`는 둘 다 **포함(inclusive)** 경계다(섹션 9의
검색 `--from`/`--to`와 동일한 규칙).

### Scenario 20 — Export 오류 테스트

기간 조건 없이:

```bash
python3 -m ledger --data-dir ./practice-data export --out ./invalid.csv
```

`--from`만 주고 `--to` 없이:

```bash
python3 -m ledger --data-dir ./practice-data export \
  --out ./invalid.csv \
  --from 2026-09-01
```

`--month`와 기간을 동시에:

```bash
python3 -m ledger --data-dir ./practice-data export \
  --out ./invalid.csv \
  --month 2026-09 \
  --from 2026-09-01 \
  --to 2026-09-30
```

기간이 거꾸로 된 경우:

```bash
python3 -m ledger --data-dir ./practice-data export \
  --out ./invalid.csv \
  --from 2026-09-30 \
  --to 2026-09-01
```

네 경우 모두 `[오류]` 한 줄과 `[힌트] 입력값을 다시 확인하세요.`가
나오고 exit code는 1이다. **참고**: 이 네 가지 오류는 아직
`ledger/decorators.py`에 한국어 문구가 따로 등록돼 있지 않아서,
`[오류]` 메시지 자체가 영어 원문(`export requires --month or both
--from and --to` 등)으로 나온다 — 오역이 아니라 실제 그렇게
동작하는 것이니 당황하지 않아도 된다.

### Scenario 21 — Import용 별도 데이터셋 만들기

Import는 카테고리가 미리 등록돼 있어야 한다. 원본 `practice-data`와
섞이지 않도록 새 데이터 폴더를 쓴다:

```bash
python3 -m ledger --data-dir ./practice-import-data category add
```

입력: `food`

```bash
python3 -m ledger --data-dir ./practice-import-data category add
```

입력: `salary`

```bash
python3 -m ledger --data-dir ./practice-import-data category add
```

입력: `transport`

### Scenario 22 — CSV Import

```bash
python3 -m ledger --data-dir ./practice-import-data import \
  --from ./practice-september.csv
```

목록 확인:

```bash
python3 -m ledger --data-dir ./practice-import-data list
```

확인 포인트:

- CSV에는 id가 없었지만 import된 거래는 **새 내부 id**를 자동으로
  받는다.
- 날짜/타입/카테고리/금액/메모/태그 값은 그대로 유지된다.
- `practice-data`와 `practice-import-data`는 완전히 별개의
  데이터셋이다.

### Scenario 23 — 잘못된 CSV 행 스킵

아래 내용을 `practice-bad-row.csv`라는 파일로 저장한다:

```csv
date,type,category,amount,memo,tags
2026-09-01,expense,food,10000,정상 거래,meal
2026-09-02,expense,food,-5000,잘못된 금액,bad
2026-09-03,expense,food,7000,다시 정상,meal
```

가져오기:

```bash
python3 -m ledger --data-dir ./practice-import-data import \
  --from ./practice-bad-row.csv
```

확인:

- 첫 번째 행(10000원)은 import된다.
- 두 번째 행은 금액이 음수(`-5000`)라 `[건너뜀] row=2: 금액은
  0보다 큰 정수여야 합니다.`로 건너뛴다.
- 세 번째 행(7000원)은 다시 import된다.
- 마지막 줄에 `[완료] imported=2, skipped=1`처럼 결과 개수가
  나온다.

### Scenario 24 — Import 파일 오류

존재하지 않는 파일:

```bash
python3 -m ledger --data-dir ./practice-import-data import \
  --from ./does-not-exist.csv
```

헤더가 잘못된 CSV도 하나 만들어 본다. 아래 내용을
`practice-bad-header.csv`로 저장:

```csv
date,type,amount
2026-09-01,expense,10000
```

```bash
python3 -m ledger --data-dir ./practice-import-data import \
  --from ./practice-bad-header.csv
```

확인:

- 파일이 없으면 `[오류] cannot open ...`처럼 파일을 열 수 없다는
  메시지가 나온다.
- 필수 컬럼(`category`, `memo`, `tags`)이 빠진 CSV는
  `[오류] CSV 형식이 올바르지 않습니다.`와 함께 **행 단위 스킵이
  아니라 명령 전체가 실패**한다 — 한 행도 가져오지 않는다.
- 두 경우 모두 exit code 1이고 트레이스백은 나오지 않는다.

### Scenario 25 — 거래 삭제

먼저 목록:

```bash
python3 -m ledger --data-dir ./practice-data list
```

삭제(예: 1번):

```bash
python3 -m ledger --data-dir ./practice-data delete --id 1
```

다시 목록으로 확인:

```bash
python3 -m ledger --data-dir ./practice-data list
```

없는 id 삭제 시도:

```bash
python3 -m ledger --data-dir ./practice-data delete --id 999
```

확인: 존재하면 확인 질문 없이 바로 삭제되고, 없으면 `[오류]`/
`[힌트]`가 나오고 아무것도 지워지지 않는다(섹션 13).

### Scenario 26 — 카테고리 생명주기 마무리

`food`를 쓰는 거래가 남아 있다면 먼저 전부 삭제하거나 다른
카테고리로 수정한다. 그런 다음:

```bash
python3 -m ledger --data-dir ./practice-data category remove
```

입력: `food`

목록으로 확인:

```bash
python3 -m ledger --data-dir ./practice-data category list
```

확인: 더 이상 어떤 거래도 쓰지 않는 카테고리는 정상적으로
삭제된다 — Scenario 17에서 차단됐던 것과 대조해서 이해하면 된다.

### Scenario 27 — 실제 저장 파일 확인

실습 후 데이터 폴더 안을 들여다본다:

```bash
ls practice-data
```

다음 세 파일이 보여야 한다:

```text
transactions.jsonl
categories.jsonl
budgets.jsonl
```

macOS/Linux에서 내용도 확인해본다:

```bash
cat practice-data/transactions.jsonl
cat practice-data/categories.jsonl
cat practice-data/budgets.jsonl
```

각 줄이 JSON 객체 하나(JSONL)이고, `transactions.jsonl`의 각
줄에는 `id`/`type`/`date`/`amount`/`category`/`memo`/`tags` 필드가,
`categories.jsonl`에는 `name` 필드가 들어 있는 것을 확인한다.

**주의**: 이 파일을 텍스트 에디터로 직접 고쳐 쓰라는 뜻이 아니다
— 프로그램이 실제로 어떤 형태로 데이터를 저장하는지 **관찰**하는
용도다.

### Scenario 28 — 영속성 확인

터미널을 새로 열거나, 같은 명령을 여러 번 다시 실행해도:

```bash
python3 -m ledger --data-dir ./practice-data list
```

데이터가 그대로 남아 있는지 확인한다. 프로그램이 메모리에만
데이터를 들고 있는 게 아니라 매번 JSONL 파일을 읽고 쓰기 때문에,
프로세스가 끝났다 다시 시작해도 내용이 유지된다.

### Scenario 29 — 실제 data와 practice-data 비교

```bash
python3 -m ledger list
```

와:

```bash
python3 -m ledger --data-dir ./practice-data list
```

를 나란히 비교해본다(둘의 결과가 다르게 나와야 정상이다). 이
비교로 `--data-dir`이 정확히 어떤 역할을 하는지 직접 체감할 수
있다(섹션 4).

### Scenario 30 — 종료 코드(exit code) 확인

정상 명령:

```bash
python3 -m ledger --data-dir ./practice-data list
echo $?
```

예상: `0`

애플리케이션 오류(존재하지 않는 id):

```bash
python3 -m ledger --data-dir ./practice-data delete --id 999
echo $?
```

예상: `1`

argparse 사용법 오류(`--data-dir` 위치 잘못):

```bash
python3 -m ledger list --data-dir ./practice-data
echo $?
```

예상: `2`

`--help`:

```bash
python3 -m ledger --help
echo $?
```

예상: `0`

이 네 가지로 CLI의 exit code 0/1/2를 직접 눈으로 확인한다(섹션 16).
Windows PowerShell을 쓴다면 `echo $?` 대신 `echo $LASTEXITCODE`를
사용하면 된다.

### QA 재현용 명령 모음

위에서 실행한 명령 중 핵심만 설명 없이 바로 복사해서 다시 테스트할
수 있도록 모아 둔 것이다. 순서대로 실행하면 위 실습을 처음부터
다시 재현할 수 있다.

**Help**

```bash
python3 -m ledger --help
python3 -m ledger add --help
python3 -m ledger export --help
```

**Category**

```bash
python3 -m ledger --data-dir ./practice-data category add
python3 -m ledger --data-dir ./practice-data category list
python3 -m ledger --data-dir ./practice-data category remove
```

**Add**

```bash
python3 -m ledger --data-dir ./practice-data add
```

**List / Search**

```bash
python3 -m ledger --data-dir ./practice-data list
python3 -m ledger --data-dir ./practice-data list --limit 2
python3 -m ledger --data-dir ./practice-data search --category food
python3 -m ledger --data-dir ./practice-data search --type expense
python3 -m ledger --data-dir ./practice-data search --q 점심
python3 -m ledger --data-dir ./practice-data search --tag commute
python3 -m ledger --data-dir ./practice-data search --from 2026-09-01 --to 2026-09-30
```

**Budget / Summary**

```bash
python3 -m ledger --data-dir ./practice-data budget set --month 2026-09 --amount 500000
python3 -m ledger --data-dir ./practice-data summary --month 2026-09
python3 -m ledger --data-dir ./practice-data summary --month 2026-09 --top 2
```

**Update / Delete**

```bash
python3 -m ledger --data-dir ./practice-data update --id 1 --amount 18000
python3 -m ledger --data-dir ./practice-data update --id 1 --memo ""
python3 -m ledger --data-dir ./practice-data update --id 1 --tags ""
python3 -m ledger --data-dir ./practice-data delete --id 1
```

**Export**

```bash
python3 -m ledger --data-dir ./practice-data export --out ./practice-september.csv --month 2026-09
python3 -m ledger --data-dir ./practice-data export --out ./practice-range.csv --from 2026-09-01 --to 2026-09-30
```

**Import**

```bash
python3 -m ledger --data-dir ./practice-import-data import --from ./practice-september.csv
python3 -m ledger --data-dir ./practice-import-data import --from ./practice-bad-row.csv
```

**Error cases**

```bash
python3 -m ledger --data-dir ./practice-data update --id 999 --amount 10000
python3 -m ledger --data-dir ./practice-data delete --id 999
python3 -m ledger --data-dir ./practice-data export --out ./invalid.csv
python3 -m ledger --data-dir ./practice-import-data import --from ./does-not-exist.csv
```

**Exit code**

```bash
python3 -m ledger --data-dir ./practice-data list; echo $?
python3 -m ledger --data-dir ./practice-data delete --id 999; echo $?
python3 -m ledger list --data-dir ./practice-data; echo $?
```

### 실습 완료 체크리스트

```text
[ ] --help 확인
[ ] category add/list
[ ] 거래 add
[ ] list / --limit
[ ] search 필터
[ ] monthly summary
[ ] budget set
[ ] budget exceeded
[ ] update
[ ] memo/tags clear
[ ] used category remove 차단
[ ] export month
[ ] export date range
[ ] import
[ ] invalid row skip
[ ] delete
[ ] JSONL 파일 직접 확인
[ ] 프로그램 재실행 후 persistence 확인
[ ] exit code 0/1/2 확인
```

### 기존 문서와의 역할

이 문서의 **5분 튜토리얼**(섹션 18)과 이번 **기능 실습**(섹션 21)은
서로 다른 목적을 갖는다 — 하나를 다른 하나로 합치지 않는다.

| 문서 | 목적 |
|---|---|
| 5분 튜토리얼(섹션 18) | 처음 써 보는 빠른 첫 체험 |
| 직접 따라 해보는 M03 기능 실습(섹션 21) | 전체 기능 학습, 동료평가/QA 재현용 |
