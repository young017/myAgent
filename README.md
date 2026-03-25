# myAgent

## 실행 방법 (uv)

1) 의존성/환경 동기화

`uv sync`

2) 스크립트 실행

기본:

`uv run python test.py`

모델 지정(예: llama3):

`uv run python test.py --model llama3`

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

## Ollama(라마) 터미널 채팅

이 프로젝트의 `test.py`는 로컬 `Ollama`의 `/api/chat`을 호출해서 채팅을 합니다.

사전 준비:

1) Ollama 설치
2) 모델 받기(예: `llama3`):

`ollama pull llama3`

예시(요청하신 모델):

`ollama pull qwen2.5-coder:7b`

3) Ollama 서버 실행(설치 시 자동 실행되는 경우가 많지만, 아니라면):

`ollama serve`

실행 시 사용하는 환경/옵션:

`OLLAMA_BASE_URL` (기본: `http://localhost:11434`)
`OLLAMA_MODEL` (기본: `qwen2.5-coder:7b`)
`OLLAMA_SYSTEM` (선택, system 프롬프트)
