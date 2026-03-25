# /// script
# requires-python = ">=3.12"
# dependencies = ["requests"]
# ///

import argparse
import json
import os
import sys
from typing import Any

import requests


if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def _print_streaming(text: str) -> None:
    # 터미널에서 실시간 출력되도록 flush
    print(text, end="", flush=True)


def chat_ollama_stream(
    *,
    base_url: str,
    model: str,
    messages: list[dict[str, str]],
    timeout_s: int,
) -> str:
    """
    Ollama의 /api/chat 스트리밍 엔드포인트를 사용해 응답을 받습니다.
    """
    url = f"{base_url.rstrip('/')}/api/chat"
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": True,
    }

    assistant_text_parts: list[str] = []
    with requests.post(url, json=payload, stream=True, timeout=timeout_s) as resp:
        resp.raise_for_status()
        for raw_line in resp.iter_lines(decode_unicode=True):
            if not raw_line:
                continue
            data = json.loads(raw_line)
            # stream=True일 때는 청크마다 message.content가 들어옵니다.
            chunk = data.get("message", {}).get("content")
            if chunk:
                assistant_text_parts.append(chunk)
                _print_streaming(chunk)
            if data.get("done"):
                break

    print()  # 마지막 줄바꿈
    return "".join(assistant_text_parts)


def main() -> None:
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

    args = parser.parse_args()

    messages: list[dict[str, str]] = []
    if args.system.strip():
        messages.append({"role": "system", "content": args.system.strip()})

    print(f"Ollama 채팅 시작: model={args.model}")
    print("종료: `exit` 또는 `quit`")

    while True:
        try:
            user_text = input("\nME:> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n종료합니다.")
            return

        if not user_text:
            continue
        if user_text.lower() in {"exit", "quit"}:
            print("종료합니다.")
            return

        messages.append({"role": "user", "content": user_text})
        try:
            assistant_text = chat_ollama_stream(
                base_url=args.base_url,
                model=args.model,
                messages=messages,
                timeout_s=args.timeout_s,
            )
        except requests.RequestException as e:
            print("\n[에러] Ollama 요청 실패.")
            print("Ollama 서버가 실행 중인지와 모델 이름을 확인하세요.")
            print(f"상세: {e}")
            return

        messages.append({"role": "assistant", "content": assistant_text})

if __name__ == "__main__":
    main()