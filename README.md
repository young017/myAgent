# myAgent

Ollama를 활용한 모듈형 터미널 챗봇 에이전트 프로젝트입니다. 지정한 로컬 환경 및 웹 사이트와 상호작용이 가능하며, 대화 내역(Context)은 자동으로 저장 및 복구되어 에이전트의 기억이 유지됩니다.

## 주요 특징

- **에이전트 모드 지원 (`--agent`)**: `--agent` 플래그로 실행 시 LLM이 스스로 판단하여 파일 작업(읽기/쓰기/수정) 및 웹 도구(URL 내용 가져오기)를 호출합니다.
- **영속성 (대화 기록 유지)**: 매 대화 턴마다 `.chat_history.json` 파일에 대화 내용을 자동으로 저장하고, 다음 실행 시 이를 불러옵니다. 이 덕분에 긴 대화 흐름, 파일 분석 내역, URL 웹 분석 결과 등을 종료 후 재실행 시에도 안전하게 기억합니다.
- **모듈화된 구조**:
  - `test.py`: CLI 실행 진입점 (Entry Point)
  - `agent/cli.py`: 환경변수 및 실행 인수(`argparse`) 파싱
  - `agent/history.py`: 대화 기록 저장/불러오기(영속성) 관리
  - `agent/main.py`: 에이전트 통합 싱글 루프 및 챗봇 실행
  - `agent/file_tools.py` & `agent/web_tools.py`: 프로젝트 내부 파일 통제 및 안전한 외부 웹 페이지 호출

## 실행 방법 (uv 권장)

1) 의존성/환경 동기화 (최초 1회 및 패키지 변경 시)
```bash
uv sync
```

2) 스크립트 실행

**[권장] 에이전트 모드 (파일 / URL 요약 도구 사용 가능):**
```bash
uv run python test.py --agent
```

*기본 일반 채팅 모드:*
```bash
uv run python test.py
```

*특정 모델 지정 (예: llama3):*
```bash
uv run python test.py --agent --model llama3
```

## Ollama(라마) 환경 설정

이 프로젝트는 로컬에 설치된 `Ollama` 서버(`${OLLAMA_BASE_URL}/api/chat`)를 바라보도록 구성되어 있습니다.

### 사전 준비

1) Ollama 설치 및 서버 실행
> 일반적으로 백그라운드에서 실행되나, 꺼져있다면 `ollama serve` 로 명시적 실행 필요
2) 언어 모델 다운로드:
```bash
ollama pull qwen2.5-coder:7b
```

### 환경 변수 / 인자 옵션

- `--base-url` / `OLLAMA_BASE_URL` (기본: `http://localhost:11434`)
- `--model` / `OLLAMA_MODEL` (기본: `qwen2.5-coder:7b`)
- `--system` / `OLLAMA_SYSTEM` (선택, 사용자 지정 시스템 프롬프트)

## IDE 환경 구성 가이드 (선택 사항)

의존성 격리를 위해 uv 모듈로 구성한 `.venv` 가상환경 인터프리터를 IDE에 설정하시면 더 편리합니다.

### 터미널에서 가상환경 직접 활성화
```bash
.\.venv\Scripts\activate
python test.py --agent
```

### 에디터 파이썬 인터프리터 설정
- **VS Code**: `Ctrl+Shift+P` -> `Python: Select Interpreter` -> `.\.venv\Scripts\python.exe` 선택
- **PyCharm**: `Settings` -> `Project: <프로젝트명> -> Python Interpreter` -> `Add Interpreter` -> 가상환경 경로(`.venv`) 지정

## 주의 사항
- **보안 샌드박스**: 모든 파일 읽기/쓰기/수정 도구 작업은 보안상 `test.py`가 위치한 프로젝트 루트 디렉토리 내부로 철저히 제한됩니다.
- **안전장치**: 웹 URL 가져오기 도구는 내부망(로컬호스트 및 프라이빗 IP 등)으로의 접근(SSRF)을 코드 단위에서 원천 차단하도록 구현되어 있습니다.
