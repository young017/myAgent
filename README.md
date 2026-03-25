# myAgent

## 실행 방법 (uv)

1) 의존성/환경 동기화

`uv sync`

2) 스크립트 실행

`uv run python test.py`

## (선택) 가상환경 직접 활성화

`.\.venv\Scripts\activate`

그 다음

`python test.py`

## 에디터에서 가상환경 인터프리터 선택

`.venv` 안의 파이썬을 에디터 인터프리터로 지정하면, 실행/디버깅 시 같은 환경을 쓰게 됩니다.

### VS Code

1) `Ctrl+Shift+P`를 눌러 Command Palette 열기
2) `Python: Select Interpreter` 검색/선택
3) `...\.venv\Scripts\python.exe` (또는 `...\.venv\python.exe`) 선택

### PyCharm

1) `Settings`(또는 `Preferences`) 열기
2) `Project: <프로젝트명> -> Python Interpreter`
3) `Add Interpreter`(또는 기존 인터프리터 선택)에서 `.venv`를 선택
