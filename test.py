# /// script
# requires-python = ">=3.12"
# dependencies = ["requests"]
# ///

import argparse
import json
import os
import sys
from pathlib import Path
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


_PROJECT_ROOT = Path(__file__).resolve().parent


def _safe_resolve_path(path: str) -> Path:
    """
    모델이 지정한 경로를 프로젝트 루트 아래로 제한합니다.
    """
    p = Path(path)
    if not p.is_absolute():
        p = _PROJECT_ROOT / p

    resolved = p.resolve()
    # resolved가 루트 아래에 있을 때만 허용
    if resolved != _PROJECT_ROOT and _PROJECT_ROOT not in resolved.parents:
        raise ValueError(f"허용되지 않은 경로입니다: {path}")
    return resolved


def tool_read_file(*, path: str, max_chars: int) -> str:
    target = _safe_resolve_path(path)
    if not target.exists():
        raise FileNotFoundError(f"파일이 없습니다: {path}")
    content = target.read_text(encoding="utf-8", errors="replace")
    if len(content) > max_chars:
        content = content[:max_chars] + "\n\n...<TRUNCATED>..."
    return content


def tool_write_file(*, path: str, content: str) -> str:
    target = _safe_resolve_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return f"ok (written {len(content)} chars)"


def tool_update_file(*, path: str, old_text: str, new_text: str) -> str:
    target = _safe_resolve_path(path)
    if not target.exists():
        raise FileNotFoundError(f"파일이 없습니다: {path}")
    current = target.read_text(encoding="utf-8", errors="replace")
    if old_text not in current:
        raise ValueError("old_text를 파일에서 찾지 못했습니다(정확한 문자열 필요).")
    updated = current.replace(old_text, new_text, 1)
    target.write_text(updated, encoding="utf-8")
    return "ok (updated 1 occurrence)"


def _extract_tool_call(text: str) -> dict[str, Any] | None:
    """
    LLM 응답에서 아래 형식 1줄을 찾습니다.
      __TOOL_CALL__{"name":"read_file","arguments":{"path":"README.md"}}
    """
    prefix = "__TOOL_CALL__"
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(prefix):
            json_part = stripped[len(prefix) :].strip()
            call = json.loads(json_part)
            if not isinstance(call, dict) or "name" not in call or "arguments" not in call:
                raise ValueError("tool call JSON 형식이 올바르지 않습니다.")
            return call
    return None


def _execute_tool_call(*, call: dict[str, Any], tool_max_chars: int) -> dict[str, Any]:
    tools: dict[str, Any] = {
        "read_file": tool_read_file,
        "write_file": tool_write_file,
        "update_file": tool_update_file,
    }

    name = call.get("name")
    arguments = call.get("arguments") or {}
    if name not in tools:
        return {"ok": False, "error": f"알 수 없는 tool: {name}"}

    try:
        if name == "read_file":
            out = tools[name](path=arguments["path"], max_chars=tool_max_chars)
        elif name == "write_file":
            out = tools[name](path=arguments["path"], content=arguments["content"])
        elif name == "update_file":
            out = tools[name](
                path=arguments["path"],
                old_text=arguments["old_text"],
                new_text=arguments["new_text"],
            )
        else:
            return {"ok": False, "error": "미지원 tool 호출입니다."}
        return {"ok": True, "result": out}
    except Exception as e:
        return {"ok": False, "error": str(e)}


_AGENT_SYSTEM_PROMPT = """\
너는 '파일 도구'를 사용할 수 있는 에이전트다. 필요할 때만 아래 도구를 호출하라.

허용된 도구(프로젝트 루트 아래에서만 동작):
1) read_file
   - arguments: {"path": "<파일 경로>"}
   - 반환: 파일 내용을 문자열로 반환
2) write_file
   - arguments: {"path": "<파일 경로>", "content": "<새 내용>"}
   - 반환: 작성 결과 문자열
3) update_file
   - arguments: {"path": "<파일 경로>", "old_text": "<기존 문자열>", "new_text": "<교체 문자열>"}
   - 반환: 수정 결과 문자열

도구 호출 방식:
- 도구가 필요하면, 응답을 '딱 한 줄'로 끝내고 그 한 줄이 아래 형식을 만족해야 한다.
  __TOOL_CALL__{"name":"read_file","arguments":{"path":"README.md"}}
- 절대 코드블록(```)으로 감싸지 말 것.
- JSON은 valid해야 한다(따옴표 누락/꼬리쉼표 금지).

도구 결과를 받으면(__TOOL_RESULT__...), 그 결과를 근거로 다음 행동을 결정하고,
마지막에는 일반 텍스트로 사용자에게 답을 제공하라.
""".rstrip()


def _print_streaming(text: str) -> None:
    # 터미널에서 실시간 출력되도록 flush
    print(text, end="", flush=True)


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
                    _print_streaming(chunk)
            if data.get("done"):
                break

    if print_stream:
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

    args = parser.parse_args()

    messages: list[dict[str, str]] = []
    if args.agent:
        system_parts: list[str] = []
        if args.system.strip():
            system_parts.append(args.system.strip())
        system_parts.append(_AGENT_SYSTEM_PROMPT)
        messages.append({"role": "system", "content": "\n\n".join(system_parts)})
    else:
        if args.system.strip():
            messages.append({"role": "system", "content": args.system.strip()})

    print(f"Ollama 채팅 시작: model={args.model}")
    print("종료: `exit` 또는 `quit`")
    if args.agent:
        print("모드: 에이전트(파일 tool 사용)")

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
        if not args.agent:
            try:
                assistant_text = chat_ollama_stream(
                    base_url=args.base_url,
                    model=args.model,
                    messages=messages,
                    timeout_s=args.timeout_s,
                    print_stream=True,
                )
            except requests.RequestException as e:
                print("\n[에러] Ollama 요청 실패.")
                print("Ollama 서버가 실행 중인지와 모델 이름을 확인하세요.")
                print(f"상세: {e}")
                return

            messages.append({"role": "assistant", "content": assistant_text})
            continue

        # 에이전트 모드: LLM 응답에 tool call이 있으면 실행하고 결과를 다시 모델에 전달
        for _step in range(args.max_agent_steps):
            try:
                assistant_text = chat_ollama_stream(
                    base_url=args.base_url,
                    model=args.model,
                    messages=messages,
                    timeout_s=args.timeout_s,
                    print_stream=False,
                )
            except requests.RequestException as e:
                print("\n[에러] Ollama 요청 실패.")
                print("Ollama 서버가 실행 중인지와 모델 이름을 확인하세요.")
                print(f"상세: {e}")
                return

            tool_call = None
            try:
                tool_call = _extract_tool_call(assistant_text)
            except Exception:
                tool_call = None

            if tool_call:
                # 로그: 모델이 어떤 도구 호출을 요청했는지/응답 본문은 무엇인지
                try:
                    call_preview = json.dumps(tool_call, ensure_ascii=False)
                except Exception:
                    call_preview = str(tool_call)
                print(f"\n[AGENT][STEP {_step + 1}] tool_call: {call_preview}")
                preview_text = assistant_text.strip()
                if len(preview_text) > 1200:
                    preview_text = preview_text[:1200] + "\n...<TRUNCATED>..."
                print(f"[AGENT][STEP {_step + 1}] assistant_message:\n{preview_text}")

                result = _execute_tool_call(
                    call=tool_call,
                    tool_max_chars=args.tool_max_chars,
                )
                # 로그: 실행 결과(성공/에러 포함)
                try:
                    result_preview = json.dumps(result, ensure_ascii=False)
                except Exception:
                    result_preview = str(result)
                print(f"[AGENT][STEP {_step + 1}] tool_result: {result_preview}")

                messages.append({"role": "assistant", "content": assistant_text})
                messages.append(
                    {
                        "role": "user",
                        "content": "__TOOL_RESULT__" + json.dumps(result, ensure_ascii=False),
                    }
                )
                continue

            # tool call이 아니면 일반 답변
            print(f"\n[AGENT][STEP {_step + 1}] final_response:\n{assistant_text}")
            messages.append({"role": "assistant", "content": assistant_text})
            break
        else:
            print("[에러] tool loop 최대 횟수 초과.")

if __name__ == "__main__":
    main()