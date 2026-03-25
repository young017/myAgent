import argparse
import os

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ollama(라마) 모델과 터미널 채팅")
    parser.add_argument(
        "--model",
        default=os.environ.get("OLLAMA_MODEL", "qwen2.5-coder:7b"),
        help="Ollama 모델 이름 (기본: env OLLAMA_MODEL 또는 qwen2.5-coder:7b)",
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
        help="Ollama 서버 주소 (기본: env OLLAMA_BASE_URL 또는 http://localhost:11434)",
    )
    parser.add_argument(
        "--system",
        default=os.environ.get("OLLAMA_SYSTEM", ""),
        help="대화에 사용할 system 프롬프트(선택)",
    )
    parser.add_argument(
        "--timeout-s",
        type=int,
        default=int(os.environ.get("OLLAMA_TIMEOUT_S", "300")),
        help="HTTP 요청 타임아웃(초)",
    )
    parser.add_argument(
        "--agent",
        action="store_true",
        help="에이전트 모드: LLM이 파일 읽기/쓰기/수정을 도구로 호출할 수 있습니다.",
    )
    parser.add_argument(
        "--max-agent-steps",
        type=int,
        default=int(os.environ.get("MAX_AGENT_STEPS", "8")),
        help="한 사용자 입력당 tool loop 최대 횟수",
    )
    parser.add_argument(
        "--tool-max-chars",
        type=int,
        default=int(os.environ.get("TOOL_MAX_CHARS", "20000")),
        help="read_file 결과 최대 글자 수",
    )
    return parser.parse_args()
