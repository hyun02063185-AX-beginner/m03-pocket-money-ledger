# m03-pocket-money-ledger

Codyssey M03 — 나만의 용돈 기입장 프로그램 만들기.

터미널에서 쓰는 개인 수입/지출 기록 프로그램. Python 3.10+ 표준
라이브러리만 사용하며, 서드파티 패키지·GUI/웹 UI·데이터베이스를
쓰지 않는다.

## 요구사항

- Python 3.10 이상
- 표준 라이브러리 외 의존성 없음 (설치 과정 없음)

## 실행 방법

```bash
python -m ledger --help   # 권장 실행 형태
python main.py --help     # 동일 동작의 보조 진입점
```

모든 명령은 `--data-dir`보다 뒤에, 서브커맨드 이름보다 **앞에** 전역
옵션을 붙인다:

```bash
python -m ledger --data-dir ./mydata list
```

## 데이터 저장

기본 저장 위치는 `./data`이며, `--data-dir <path>`로 언제든 바꿀 수
있다. 세 개의 JSONL 파일을 쓰며, 파일이 없으면 필요한 시점(쓰기
발생 시)에 자동으로 만든다 — 읽기만 하는 명령은 파일/디렉터리가
없어도 빈 상태로 정상 동작하고, 아무것도 새로 만들지 않는다.

| 파일 | 내용 |
|---|---|
| `data/transactions.jsonl` | 거래 내역 (한 줄 = 거래 1건) |
| `data/categories.jsonl` | 등록된 카테고리 목록 |
| `data/budgets.jsonl` | 월별 총예산 |

## 명령 개요

| 명령 | 설명 |
|---|---|
| `add` | 거래 추가 (대화형) |
| `list [--limit N]` | 최근 거래 조회 (최신순, 기본 10건) |
| `search [필터...]` | 조건에 맞는 거래 검색 |
| `summary --month YYYY-MM [--top N]` | 월간 요약(수입/지출/잔액/카테고리 TOP N/예산 현황) |
| `budget set --month YYYY-MM --amount N` | 월 총예산 설정 |
| `category add` / `list` / `remove` | 카테고리 등록/조회/삭제 |
| `update --id N [필드...]` | 거래 일부 필드 수정 |
| `delete --id N` | 거래 삭제 |
| `import --from FILE` | CSV 파일에서 거래 가져오기 |
| `export --out FILE (--month YYYY-MM \| --from ... --to ...)` | CSV로 거래 내보내기 |

## 주요 명령 예시

```bash
# 카테고리 먼저 등록 (대화형 — 카테고리명을 물어봄)
python -m ledger category add

# 거래 추가 (대화형)
python -m ledger add

# 최근 5건 조회
python -m ledger list --limit 5

# 9월 식비만 검색
python -m ledger search --category 식비 --from 2026-09-01 --to 2026-09-30

# 9월 요약(상위 3개 카테고리)
python -m ledger summary --month 2026-09 --top 3

# 9월 총예산 50만원 설정
python -m ledger budget set --month 2026-09 --amount 500000

# id=12 거래의 금액과 메모만 수정
python -m ledger update --id 12 --amount 20000 --memo 저녁

# id=12 거래 삭제
python -m ledger delete --id 12
```

## `add` 대화형 입력

옵션 없이 `add`를 실행하면 순서대로 물어본다: **날짜(YYYY-MM-DD) →
타입(income/expense) → 카테고리 → 금액 → 메모(선택) → 태그(선택,
쉼표로 구분)**. 잘못된 값을 입력하면 원인과 힌트를 보여주고 다시
물어보며(최대 3회), 3회 모두 실패하면 등록을 중단하고 0이 아닌
종료 코드로 끝난다. 메모/태그는 그냥 Enter를 치면 생략할 수 있다.

## `update` 방식

`update`는 대화형이 아니라 **옵션 기반**이다 — `--id`는 항상
필수이고, 그 외 `--date/--type/--category/--amount/--memo/--tags` 중
**최소 1개**를 지정해야 한다(아무 필드도 안 주면 에러). 지정하지
않은 필드는 그대로 유지된다. `--memo ""`나 `--tags ""`처럼 **빈
값을 명시적으로 주면** 해당 필드를 비운다 — 옵션 자체를 생략하는
것과는 다르게 동작한다.

## 카테고리 초기화 정책

앱이 기본 카테고리를 자동으로 만들어주지 않는다. `add`를 실행했는데
등록된 카테고리가 하나도 없으면 에러+힌트를 보여주며, `category add`로
먼저 카테고리를 등록해야 한다. 이미 거래에서 쓰이고 있는 카테고리는
삭제할 수 없다(삭제 시도 시 에러).

## CSV import/export

가져오기/내보내기는 아래 6개 컬럼을 쓴다(내부 거래 id는 CSV에 없음 —
가져올 때마다 새 id를 발급한다):

```
date,type,category,amount,memo,tags
2026-09-16,expense,식비,15000,점심,"meal,lunch"
2026-09-17,income,급여,3000000,급여,
```

- UTF-8, 헤더 필수. 6개 컬럼 이름이 전부 있어야 한다(값은 memo/tags만
  비워도 됨). 헤더가 없거나 필수 컬럼이 빠지면 파일 전체를 거부한다
  (아무 것도 가져오지 않음).
- 개별 데이터 행이 잘못된 경우(날짜 형식 오류, 등록 안 된 카테고리
  등)는 그 행만 건너뛰고 나머지는 계속 처리한다 — 몇 건 가져왔고
  몇 건 건너뛰었는지 마지막에 보여준다.
- `tags`는 쉼표로 구분한 값이며, 값 안에 쉼표가 있으면(예:
  `"meal,lunch"`) CSV 표준 quoting으로 감싼다.
- `export`는 `--month` 또는 `--from`+`--to` 중 정확히 하나의 기간
  조건이 있어야 한다(조건 없는 export는 거부).

```bash
# 9월 거래를 export.csv로 내보내기
python -m ledger export --out export.csv --month 2026-09

# export.csv를 다시 가져오기
python -m ledger import --from export.csv
```

## 알려진 단순화/제약

- 태그 안에 리터럴 쉼표(`,`)는 지원하지 않는다 — 대화형 입력과 CSV
  둘 다 쉼표를 구분자로만 취급한다(이스케이프 문법 없음).
- `list`/`search`의 "최신순"은 **입력한 순서** 기준이다(가장 최근에
  추가된 거래가 먼저 나옴) — 거래 `date` 값으로 다시 정렬하지
  않는다. 과거 날짜의 거래를 나중에 입력해도 방금 입력한 항목이
  맨 위에 나온다.
- CSV import/export에 동일 내용의 중복 여부를 판단하는 기능은 없다
  — CSV의 유효한 각 행은 항상 새 거래로 등록된다.
- 백업, 반복 거래, 표 정렬 등 Mission Core 밖의 기능은 구현하지
  않았다.

## 관련 문서

- [docs/m03-user-guide.md](docs/m03-user-guide.md) — 이 README보다
  친절한 사용설명서(단계별 튜토리얼, 자주 하는 실수 포함)
- [docs/m03-architecture-design.md](docs/m03-architecture-design.md) —
  디렉터리 구조, 모듈/클래스 책임, 데이터 스키마, CLI 설계, 공식
  요구사항 ↔ 구현 위치 매핑
- [docs/m03-final-qa-report.md](docs/m03-final-qa-report.md) — 최종
  감사 결과(공식 요구사항 PASS/BLOCKED 표, 자동/수동 검증 근거)
- [docs/m03-peer-evaluation-guide.md](docs/m03-peer-evaluation-guide.md) —
  동료평가 대비 자료(핵심 개념 설명, 예상 질문, 시연 순서)

## 테스트

```bash
python -m compileall .
python -m unittest discover -s tests -t . -v
```

217개 단위/통합 테스트가 있으며 실제 임시 디렉터리를 쓰는 리포지토리
/서비스/CLI 계층을 함께 검증한다(모킹 최소화).
