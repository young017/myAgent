from __future__ import annotations

import json
from typing import Any

from agent.file_tools import FileToolkit
from agent.ollama_client import chat_ollama_stream
from agent.web_tools import WebToolkit


def extract_tool_call(text: str) -> dict[str, Any] | None:
    """
    LLM 응답에서 아래 형식 1줄을 찾습니다.
      __TOOL_CALL__{"name":"read_file","arguments":{"path":"README.md"}}
    """
    prefix = "__TOOL_CALL__"
    for line in text.splitlines():
        # 툴콜이 코드블록(```) 등으로 감싸져도 파싱되도록,
        # 라인 내에서 prefix 위치를 찾아 JSON 파트를 추출합니다.
        idx = line.find(prefix)
        if idx == -1:
            continue

        json_part = line[idx + len(prefix) :].strip()
        # 코드블록 마커나 남는 백틱 제거
        json_part = json_part.strip("`").strip()
        call = json.loads(json_part)
        if not isinstance(call, dict) or "name" not in call or "arguments" not in call:
            raise ValueError("tool call JSON 형식이 올바르지 않습니다.")
        return call
    return None


def execute_tool_call(
    *,
    call: dict[str, Any],
    toolkit: FileToolkit,
    web_toolkit: WebToolkit,
    tool_max_chars: int,
) -> dict[str, Any]:
    """
    LLM이 생성한 툴 이름(name)과 인자(arguments)를 기반으로
    실제 파이썬 로직(웹 검색, 파일 읽기/쓰기 등)을 실행하고 그 결과를 반환합니다.
    내부적으로 에러가 발생해도 전체 루프가 죽지 않도록 {"ok": False, "error": ...} 형태로 감싸 보호합니다.
    """
    name = call.get("name")
    arguments = call.get("arguments") or {}

    try:
        if name == "read_file":
            out = toolkit.read_file(path=arguments["path"], max_chars=tool_max_chars)
        elif name == "write_file":
            out = toolkit.write_file(path=arguments["path"], content=arguments["content"])
        elif name == "update_file":
            out = toolkit.update_file(
                path=arguments["path"],
                old_text=arguments["old_text"],
                new_text=arguments["new_text"],
            )
        elif name == "fetch_url":
            out = web_toolkit.fetch_url(
                url=arguments["url"],
                timeout_s=int(arguments.get("timeout_s") or 30),
                max_chars=int(arguments.get("max_chars") or 0),
            )
        elif name == "search_namu":
            out = web_toolkit.search_namu(
                keyword=arguments["keyword"],
                timeout_s=int(arguments.get("timeout_s") or 30),
                max_chars=int(arguments.get("max_chars") or 0),
            )
        else:
            return {"ok": False, "error": f"알 수 없는 tool: {name}"}

        return {"ok": True, "result": out}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def run_agent_turn(
    *,
    messages: list[dict[str, str]],
    base_url: str,
    model: str,
    timeout_s: int,
    toolkit: FileToolkit,
    web_toolkit: WebToolkit,
    max_agent_steps: int,
    tool_max_chars: int,
    enable_tool_logs: bool = True,
) -> None:
    """
    한 번의 사용자 입력에 대해 다음의 '도구 호출 루프(Agent Loop)'를 실행합니다:
    1. 현재 messages(대화 컨텍스트)를 기반으로 LLM 호출
    2. 응답 내용에서 tool call 형식을 파싱
    3. tool call이 있다면 해당 도구(웹/파일 도구)를 실행
    4. 실행 결과를 "role": "tool" 형식으로 messages에 주입 후 다시 1번으로 돌아가 LLM 재호출
    5. tool call이 없으면 (최종 답변 제출) 루프 종료
    """
    for step in range(max_agent_steps):
        if enable_tool_logs:
            print(f"\n[AGENT 진행 중 - STEP {step + 1}]", flush=True)
            
        assistant_text = chat_ollama_stream(
            base_url=base_url,
            model=model,
            messages=messages,
            timeout_s=timeout_s,
            print_stream=True,
        )

        tool_call = None
        try:
            tool_call = extract_tool_call(assistant_text)
        except Exception:
            tool_call = None

        if tool_call:
            if enable_tool_logs:
                tool_name = tool_call.get("name", "unknown")
                args_preview = tool_call.get("arguments", {})
                print(f"\n[AGENT Action] 🚀 도구 실행 중: {tool_name}")
                print(f"               파라미터: {args_preview}")

            result = execute_tool_call(
                call=tool_call,
                toolkit=toolkit,
                web_toolkit=web_toolkit,
                tool_max_chars=tool_max_chars,
            )

            if enable_tool_logs:
                # 스트리밍으로 툴 호출 텍스트가 이미 출력되었으므로 결과만 출력
                try:
                    result_preview = json.dumps(result, ensure_ascii=False)
                except Exception:
                    result_preview = str(result)
                
                if len(result_preview) > 500:
                    result_preview = result_preview[:500] + "... (생략됨)"
                print(f"[AGENT] 🛠️ 도구 실행 결과: {result_preview}")

            # 대화에 tool 호출 응답과 결과를 남깁니다.
            tool_name = tool_call.get("name", "unknown_tool")
            messages.append({"role": "assistant", "content": assistant_text})
            messages.append({
                "role": "user",
                "content": f"__TOOL_RESULT__\n{json.dumps(result, ensure_ascii=False)}"
            })
            continue

        # tool call이 아니면 최종 응답 (이미 스트리밍으로 출력됨)
        messages.append({"role": "assistant", "content": assistant_text})
        break
    else:
        print("\n[에러] tool loop 최대 횟수 초과.")

