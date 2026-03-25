import json
from typing import Any

import requests


def chat_ollama_stream(
    *,
    base_url: str,
    model: str,
    messages: list[dict[str, str]],
    timeout_s: int,
    print_stream: bool = True,
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
                if print_stream:
                    print(chunk, end="", flush=True)
            if data.get("done"):
                break

    if print_stream:
        print()
    return "".join(assistant_text_parts)

