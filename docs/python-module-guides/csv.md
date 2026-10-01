# `csv` 모듈 사용 흐름

이 문서는 M03의 CSV 가져오기·내보내기에서 **CSV 행 → dict → Transaction**으로 이어지는
방향과 그 반대 방향을 설명한다.

## 1. import와 M03에서의 역할

```python
# ledger/services.py
import csv

CSV_FIELDNAMES = ["date", "type", "category", "amount", "memo", "tags"]
```

`csv`는 Python 표준 모듈이다. CSV는 열 이름이 있는 표 형식이고, M03는 내부 JSONL과
별도로 다른 프로그램과 주고받을 교환 형식으로 사용한다. CSV에는 내부 `id`를 넣지
않는다.

## 2. 실제로 쓰는 핵심 기능

```python
reader = csv.DictReader(handle)
writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
writer.writeheader()
writer.writerow({...})
```

- `DictReader`: 헤더를 키로 하여 한 행을 `dict`로 준다.
- `reader.fieldnames`: 헤더가 여섯 필드를 모두 갖췄는지 확인한다.
- `DictWriter`: 정한 열 순서로 `dict` 한 개를 CSV 한 행으로 쓴다.
- `writeheader()`: `date,type,...` 헤더 행을 쓴다.

## 3. 가져오기 흐름

```text
입력 CSV의 한 행
↓ DictReader
{"date": "2026-09-01", "amount": "12000", ...}  (모든 값은 우선 글자)
↓ validate_amount(), parse_tags()
amount: int, tags: list[str]
↓ LedgerService.add_transaction(...)
↓
새 Transaction 객체 → transactions.jsonl
```

`import_csv()`는 `row.get(...)`으로 값을 꺼내고 같은 `add_transaction()`을 호출한다.
따라서 화면에서 거래를 추가할 때와 동일한 날짜·금액·카테고리 검증을 거친다. 행 하나가
틀리면 그 행만 `ImportResult.errors`에 기록하고 건너뛴다. 헤더 누락 같은 파일 전체 문제는
`CSVFormatError`로 중단한다.

## 4. 내보내기 흐름

```text
TransactionRepository.iter_all()
↓ Transaction 객체 하나씩
transaction.date.isoformat(), ",".join(transaction.tags)
↓
CSV용 dict
↓ DictWriter.writerow()
CSV 한 행
```

`export_csv()`는 조건에 맞는 거래를 한 건씩 바로 `DictWriter`에 보낸다. 모든 거래를
목록으로 만들 필요가 없다. 날짜는 `date` 객체에서 문자열로, 태그 목록은 쉼표 문자열로
바뀐다.

## 5. 만들어지는 객체·구조

CSV 행은 `dict[str, str]`처럼 시작한다. 검증 뒤에는 `Transaction` 객체가 되고, 가져오기
결과는 `ImportResult(imported, skipped, errors)` 객체가 된다. `Transaction`은 M03가 만든
모델이고, `DictReader`·`DictWriter`는 Python `csv`가 제공한다.

## 6. M03 코드와 연결

`ledger/services.py`의 `import_csv()`와 `export_csv()`가 이 흐름의 중심이다. CLI는
`cmd_import()`/`cmd_export()`에서 Path를 서비스로 전달할 뿐이고, CSV 규칙은 Service에 있다.

## 외워둘 5줄

```text
DictReader는 CSV 한 행을 헤더 이름 기반 dict로 읽는다.
CSV에서 읽은 값은 처음에는 글자이므로 검증·변환이 필요하다.
add_transaction()을 재사용해 CSV도 같은 업무 규칙을 지킨다.
DictWriter는 dict 한 개를 정해진 열 순서의 CSV 행으로 쓴다.
M03 CSV에는 내부 Transaction id를 넣지 않는다.
```

