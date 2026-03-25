import json
from pathlib import Path

def load_history(file_path: Path) -> list[dict[str, str]]:
    """히스토리 파일에서 대화 기록을 불러옵니다."""
    if not file_path.exists():
        return []
    try:
        content = file_path.read_text(encoding="utf-8")
        if not content.strip():
            return []
        data = json.loads(content)
        if isinstance(data, list):
            return data
    except Exception as e:
        print(f"[경고] 히스토리 파일 읽기 실패: {str(e)}")
    return []

def save_history(file_path: Path, messages: list[dict[str, str]]) -> None:
    """대화 기록을 히스토리 파일에 저장합니다. (시스템 프롬프트는 제외)"""
    # role이 "system"인 메시지는 런타임에 동적으로 주입되므로 제외
    filtered = [m for m in messages if m.get("role") != "system"]
    try:
        file_path.write_text(json.dumps(filtered, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[경고] 히스토리 파일 저장 실패: {str(e)}")
