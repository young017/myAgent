import sys
from pathlib import Path

import requests

from agent.cli import parse_args
from agent.agent_runner import run_agent_turn
from agent.file_tools import FileToolkit
from agent.history import load_history, save_history
from agent.ollama_client import chat_ollama_stream
from agent.prompts import AGENT_SYSTEM_PROMPT
from agent.web_tools import WebToolkit

def run_cli() -> int:
    args = parse_args()

    project_root = Path(__file__).resolve().parent.parent
    toolkit = FileToolkit(project_root=project_root)
    web_toolkit = WebToolkit()

    history_path = project_root / ".chat_history.json"
    messages = load_history(history_path)

    system_parts: list[str] = []
    if args.system.strip():
        system_parts.append(args.system.strip())
    
    if args.agent:
        system_parts.append(AGENT_SYSTEM_PROMPT)
    
    # 런타임마다 최신 시스템 프롬프트를 0번 인덱스에 삽입합니다.
    system_content = "\n\n".join(system_parts)
    if system_content:
        # 기존에 시스템 프롬프트가 (오류로) 저장되어 있다면 제외시킴
        messages = [m for m in messages if m.get("role") != "system"]
        messages.insert(0, {"role": "system", "content": system_content})

    print(f"Ollama 채팅 시작: model={args.model}")
    print("종료: `exit` 또는 `quit`")
    history_count = len([m for m in messages if m.get("role") != "system"])
    if history_count > 0:
        print(f"히스토리 로드됨 ({history_count} 건의 메시지)")
    else:
        print("새로운 채팅을 시작합니다.")

    if args.agent:
        print("모드: 에이전트(파일/URL tool 사용)")

    while True:
        try:
            user_text = input("\nME:> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n종료합니다.")
            return 0

        if not user_text:
            continue
        if user_text.lower() in {"exit", "quit"}:
            print("종료합니다.")
            return 0

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
                return 1

            messages.append({"role": "assistant", "content": assistant_text})
        else:
            # 에이전트 모드
            try:
                run_agent_turn(
                    messages=messages,
                    base_url=args.base_url,
                    model=args.model,
                    timeout_s=args.timeout_s,
                    toolkit=toolkit,
                    web_toolkit=web_toolkit,
                    max_agent_steps=args.max_agent_steps,
                    tool_max_chars=args.tool_max_chars,
                    enable_tool_logs=True,
                )
            except requests.RequestException as e:
                print("\n[에러] Ollama 요청 실패.")
                print("Ollama 서버가 실행 중인지와 모델 이름을 확인하세요.")
                print(f"상세: {e}")
                return 1
            
        # 매 턴마다 히스토리 저장
        save_history(history_path, messages)

    return 0
