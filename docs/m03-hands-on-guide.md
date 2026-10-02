# B2-1 직접 써보는 용돈 기입장

이 문서가 **첫 번째 문서**다. 먼저 프로그램을 실제로 사용하고, 각 실습의
`내부 파일` 링크를 따라 [코드 읽기 가이드](m03-code-reading-guide.md)에서
방금 쓴 기능을 이해한다. 설계·QA·평가 준비는 마지막에
[B2-1 Reference](m03-reference.md)를 본다.

```text
명령 실행 → data/에 내 데이터 생성 → 화면 확인 → 코드 흐름 읽기 → Python 개념 이해
```

저장소 루트(`main.py`와 `ledger/`가 보이는 위치)에서 실행한다. macOS/Linux는
`python3`, Windows는 예시의 `python3`를 `python`으로 바꾼다.

## 시작 전: 내 기존 데이터 보호

이 가이드는 기본 저장소인 `./data`를 사용한다. 즉, 아래의 카테고리·거래·예산은
동료평가 때도 쓸 수 있는 실제 데이터가 된다. Codex나 이 문서는 데이터를 미리
만들지 않는다.

기존 `data/*.jsonl`이 있다면 절대 지우거나 덮어쓰지 말고, 먼저 상태를 확인한다.
아래 예시의 날짜·금액·ID는 자신의 데이터와 충돌하면 바꾸어도 된다. `delete`와
`update`는 뒤에서 별도의 연습 거래만 대상으로 한다. export 파일은 동명 파일을
덮어쓸 수 있으므로 이름도 확인한다.

```bash
python3 -m ledger category list
python3 -m ledger list
```

처음에는 각각 `등록된 카테고리가 없습니다.`와 `거래 내역이 없습니다.`라는 안내가
나올 수 있다. 읽기 명령은 아직 `data/`가 없어도 실패하거나 빈 파일을 만들지 않는다.

## 프로그램을 여는 법

```bash
python3 -m ledger --help
python3 -m ledger category --help
python3 -m ledger add --help
```

지금은 `-m`을 “Python에게 `ledger`라는 package를 실행해 달라는 옵션”이라고만
기억하면 충분하다. 왜 가능한지는 [실행 시작점](m03-code-reading-guide.md#1-python-프로그램은-어떻게-시작될까)에서 배운다.

일상적인 실습에서는 `--data-dir`을 쓰지 않는다. 기본값이 `./data`이기 때문이다.
별도 폴더가 필요할 때만 **명령 앞**에 둔다.

```bash
python3 -m ledger --data-dir ./my-demo list
```

`python3 -m ledger list --data-dir ./my-demo`는 전역 옵션 위치가 틀린 명령이며
argparse 사용법 오류(exit code 2)가 난다.

## 실습 1: 시연용 기본 데이터 만들기

완료 목표는 카테고리 6개, 수입 2건 이상, 지출 8건 이상, 두 달 이상의 날짜,
검색 가능한 메모·태그, 월 예산이다. 이 데이터는 이후 검색·요약·export 시연에도
그대로 쓴다.

### Scenario 1 — 빈 상태를 본다

```bash
python3 -m ledger category list
python3 -m ledger list
```

화면에서 확인할 것: 빈 데이터도 오류가 아니라 안내로 표시된다.

내부 파일: `cli.py → services.py → repository.py → data/*.jsonl`.

### Scenario 2 — 카테고리 없이 add를 시도한다

```bash
python3 -m ledger add
```

날짜 `2026-09-01`, 타입 `expense`, 카테고리 `food`를 입력한다. 등록되지 않은
카테고리라면 오류·힌트 후 카테고리를 다시 묻는다(최대 세 번). 이 실습은 거래 전에
카테고리가 필요함을 보여 준다. 이미 `food`가 있다면 목록에 없는 이름을 쓴다.

내부 파일: `cli.py → LedgerService.add_transaction() → CategoryRepository.exists()`.

### Scenario 3 — 카테고리 6개를 만든다

각 명령에서 프롬프트에 한 이름씩 입력한다. 이미 있는 이름은 건너뛰고 부족한 것만
추가한다.

```bash
python3 -m ledger category add   # food
python3 -m ledger category add   # transport
python3 -m ledger category add   # salary
python3 -m ledger category add   # hobby
python3 -m ledger category add   # education
python3 -m ledger category add   # etc
python3 -m ledger category list
```

내부 파일: `cli.py → services.py(add_category) → repository.py → categories.jsonl`.

### Scenario 4 — 중복 카테고리 오류를 본다

```bash
python3 -m ledger category add   # food 입력
```

`[오류]`와 `[힌트]`가 나오며 같은 이름은 저장되지 않는다. 여기서는 트레이스백이
아닌 사용자가 읽을 메시지를 확인한다. 더 깊은 이유는 [Decorator](m03-code-reading-guide.md#6-오류를-통해-decorator를-배운다)에서 본다.

### Scenario 5 — 첫 지출을 추가한다

```bash
python3 -m ledger add
```

```text
날짜: 2026-09-01
타입: expense
카테고리: food
금액: 12000
메모: 점심
태그: lunch,weekday
```

`[저장 완료] id=TX-000001` 같은 화면 ID를 기록한다. 화면의 `TX-000001`은 표시용이고
update/delete에는 숫자 `1`을 쓴다. 내부 파일:
`cli.py → validators.py → services.py → models.py → repository.py → transactions.jsonl`.

### Scenario 6 — 9월의 수입을 추가한다

```bash
python3 -m ledger add
```

`2026-09-05 / income / salary / 3000000 / 9월 급여 / salary` 순서로 입력한다.

### Scenario 7 — 9월 지출을 더 추가한다

다음 네 거래를 `python3 -m ledger add`로 각각 입력한다.

| 날짜 | 타입 | 카테고리 | 금액 | 메모 | 태그 |
|---|---|---:|---:|---|---|
| 2026-09-06 | expense | transport | 2500 | 버스 | commute,bus |
| 2026-09-08 | expense | food | 18000 | 친구와 저녁 | dinner,friend |
| 2026-09-10 | expense | education | 35000 | Python 책 | study,python |
| 2026-09-12 | expense | hobby | 15000 | 영화 | movie,weekend |

### Scenario 8 — 두 번째 달 거래를 추가한다

다음 세 거래도 각각 add한다. 두 달 검색·요약을 위한 기준 데이터다.

| 날짜 | 타입 | 카테고리 | 금액 | 메모 | 태그 |
|---|---|---:|---:|---|---|
| 2026-08-25 | income | salary | 3000000 | 8월 급여 | salary |
| 2026-08-27 | expense | food | 8000 | 저녁 | dinner |
| 2026-08-30 | expense | transport | 1500 | 지하철 | commute |

### Scenario 9 — 목록과 최근 N건을 본다

```bash
python3 -m ledger list
python3 -m ledger list --limit 5
```

화면에서 확인할 것: `--limit 5`는 최근에 **입력한** 5건을 뜻한다. 날짜순 정렬이
아니라 파일에 추가된 순서의 역순이다.

내부 파일: `__main__.py → cli.py → LedgerService.list_transactions() → TransactionRepository.iter_all() → transactions.jsonl`.
더 알고 싶다면: [list, Generator, deque](m03-code-reading-guide.md#4-list로-generator와-deque를-배운다).

### Scenario 10 — 검색 조건 하나씩 써 본다

```bash
python3 -m ledger search --category food
python3 -m ledger search --type expense
python3 -m ledger search --q 점심
python3 -m ledger search --tag commute
python3 -m ledger search --from 2026-09-01
python3 -m ledger search --to 2026-09-30
```

`--q`는 memo의 대소문자 구별 없는 부분 검색이고, `--tag`는 정확히 일치하는 태그다.

### Scenario 11 — 검색 조건을 조합한다

```bash
python3 -m ledger search --from 2026-09-01 --to 2026-09-30 --type expense
python3 -m ledger search --category food --tag dinner
```

옵션은 모두 AND 조건이다. 내부 파일: `cli.py → services.py(search) → repository.py(iter_all)`.

### Scenario 12 — 9월 요약을 본다

```bash
python3 -m ledger summary --month 2026-09
python3 -m ledger summary --month 2026-09 --top 2
python3 -m ledger summary --month 2025-01
```

수입·지출·잔액·지출 카테고리 TOP을 확인한다. 데이터가 없는 달은 `데이터 없음`이다.

### Scenario 13 — 월 예산을 설정한다

```bash
python3 -m ledger budget set --month 2026-09 --amount 500000
python3 -m ledger summary --month 2026-09
```

정상 예산 상태의 `예산`, `사용률`, `예산 초과: 아니오`를 확인한다. 내부 파일:
`cli.py → services.py(monthly_summary/set_budget) → budgets.jsonl`.

### Scenario 14 — 예산 초과도 시연한다

```bash
python3 -m ledger budget set --month 2026-09 --amount 10000
python3 -m ledger summary --month 2026-09
python3 -m ledger budget set --month 2026-09 --amount 500000
```

중간 요약에서 경고를 본 뒤 마지막 명령으로 정상 예산을 복구한다. 예산은 추가를 막는
규칙이 아니라 요약에 표시하는 기준이다.

## 실습 2: 기준 데이터를 해치지 않는 CRUD

여기서는 위 기준 데이터가 아닌 “연습용” 거래 하나만 만든다. 먼저 현재 목록에서 그
거래의 숫자 ID를 확인하고, 아래 `<연습-ID>`만 바꾼다.

### Scenario 15 — 연습 거래를 추가한다

```bash
python3 -m ledger add
```

`2026-09-20 / expense / etc / 1000 / 수정삭제 연습 / practice`를 입력한 뒤:

```bash
python3 -m ledger list --limit 3
```

### Scenario 16 — 연습 거래를 수정한다

```bash
python3 -m ledger update --id <연습-ID> --amount 2000 --memo "수정된 연습"
python3 -m ledger list --limit 3
```

### Scenario 17 — memo와 tags를 비운다

```bash
python3 -m ledger update --id <연습-ID> --memo ""
python3 -m ledger update --id <연습-ID> --tags ""
```

옵션 생략은 유지, 빈 값을 명시하면 비움이다. [UNSET과 안전 저장](m03-code-reading-guide.md#8-update--delete의-안전-저장)을 참고한다.

### Scenario 18 — update 오류를 확인한다

```bash
python3 -m ledger update --id <연습-ID>
python3 -m ledger update --id 999999 --amount 10000
python3 -m ledger update --id <연습-ID> --category unknown
```

두 번째 ID는 실제 없는 숫자로 바꾼다. 세 명령 모두 애플리케이션 오류는 exit code 1,
사용법 자체가 틀린 argparse 오류는 exit code 2라는 점을 구별한다.

### Scenario 19 — 사용 중인 카테고리 삭제는 막힌다

```bash
python3 -m ledger category remove   # food 입력
```

`food` 거래가 있으므로 삭제가 거절된다. 이유: 존재하는 거래가 사라진 카테고리를
가리키지 않게 하기 위해서다.

### Scenario 20 — 연습 거래만 삭제한다

```bash
python3 -m ledger delete --id <연습-ID>
python3 -m ledger list --limit 3
```

기준 거래는 남고 연습 거래만 없어진 것을 확인한다. update/delete는
`repository.py`에서 임시 파일을 완성한 뒤 교체한다.

## 실습 3: CSV, 오류, 별도 데이터 폴더

### Scenario 21 — 월별 CSV를 export한다

```bash
python3 -m ledger export --out ./m03-september.csv --month 2026-09
```

파일 첫 줄은 `date,type,category,amount,memo,tags`다. CSV에는 내부 ID가 없다.

### Scenario 22 — 날짜 범위로 export한다

```bash
python3 -m ledger export --out ./m03-range.csv --from 2026-09-01 --to 2026-09-30
```

양 끝 날짜를 포함한다.

### Scenario 23 — export 입력 오류를 본다

```bash
python3 -m ledger export --out ./invalid.csv
python3 -m ledger export --out ./invalid.csv --from 2026-09-01
python3 -m ledger export --out ./invalid.csv --month 2026-09 --from 2026-09-01 --to 2026-09-30
```

기간 조건은 `--month` 하나 또는 `--from`과 `--to` 한 쌍 중 정확히 하나여야 한다.

### Scenario 24 — export한 CSV를 import한다

```bash
python3 -m ledger import --from ./m03-september.csv
python3 -m ledger list --limit 5
```

같은 파일을 가져오면 유효 행마다 새 ID를 받아 거래가 추가된다. 중복 제거 기능은 없다.

### Scenario 25 — 잘못된 CSV 행의 결과를 이해한다

CSV 헤더가 없거나 필수 컬럼이 빠지면 파일 전체가 거절된다. 반면 헤더는 맞지만 날짜·금액·카테고리가 틀린 행은
그 행만 `[건너뜀]`으로 세고 나머지는 계속 가져온다. 직접 파일을 만들 필요는 없다.

### Scenario 26 — 데이터가 남는지 확인한다

새 터미널을 열거나 같은 명령을 다시 실행한다.

```bash
python3 -m ledger list --limit 5
python3 -m ledger summary --month 2026-09
```

프로세스 메모리는 끝났지만 `data/transactions.jsonl` 등이 남아 다시 읽힌다.

### Scenario 27 — `--data-dir`을 별도 기능으로 쓴다

```bash
python3 -m ledger --data-dir ./sandbox-data category list
python3 -m ledger --data-dir ./sandbox-data list
```

기본 `data/`와 분리되어 있으므로 기존 동료평가 데이터에 영향을 주지 않는다.

### Scenario 28 — 도움말과 parser 오류를 구분한다

```bash
python3 -m ledger search --help
python3 -m ledger list --limit nope
```

첫 명령은 도움말(exit 0), 두 번째는 `nope`를 int로 바꾸지 못한 argparse 오류(exit 2)다.

### Scenario 29 — 애플리케이션 오류의 종료 코드를 본다

```bash
python3 -m ledger list --limit 0
```

양수가 아닌 limit은 프로그램 규칙 위반이다. `[오류]`, `[힌트]`, exit 1을 확인한다.

### Scenario 30 — 동료평가 리허설

```bash
python3 -m ledger list --limit 5
python3 -m ledger search --tag lunch
python3 -m ledger summary --month 2026-09
python3 -m ledger export --out ./m03-demo.csv --month 2026-09
```

설명 순서: 목록 → 검색 → 요약/예산 → CSV → `cli → service → repository → JSONL`.
10초/30초 답변과 체크 항목은 [Peer Evaluation Guide](m03-peer-evaluation-guide.md)를,
코드 설명은 [Code Reading Guide](m03-code-reading-guide.md)를 사용한다.

## 빠른 명령표

| 목적 | 명령 |
|---|---|
| 거래 추가 | `python3 -m ledger add` |
| 최근 N건 | `python3 -m ledger list --limit 5` |
| 검색 | `python3 -m ledger search --q 점심 --tag lunch` |
| 월 요약 | `python3 -m ledger summary --month 2026-09` |
| 예산 | `python3 -m ledger budget set --month 2026-09 --amount 500000` |
| 수정/삭제 | `update --id N --amount N`, `delete --id N` |
| CSV | `import --from FILE`, `export --out FILE --month YYYY-MM` |

다음: [방금 실행한 명령을 코드에서 따라가기](m03-code-reading-guide.md).
