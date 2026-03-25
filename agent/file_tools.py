from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FileToolkit:
    project_root: Path

    def _safe_resolve_path(self, path: str) -> Path:
        """
        모델이 지정한 경로를 프로젝트 루트 아래로 제한합니다.
        """
        p = Path(path)
        if not p.is_absolute():
            p = self.project_root / p

        resolved = p.resolve()
        # resolved가 루트 아래에 있을 때만 허용
        if resolved != self.project_root and self.project_root not in resolved.parents:
            raise ValueError(f"허용되지 않은 경로입니다: {path}")
        return resolved

    def read_file(self, *, path: str, max_chars: int) -> str:
        target = self._safe_resolve_path(path)
        if not target.exists():
            raise FileNotFoundError(f"파일이 없습니다: {path}")
        content = target.read_text(encoding="utf-8", errors="replace")
        return content

    def write_file(self, *, path: str, content: str) -> str:
        target = self._safe_resolve_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return f"ok (written {len(content)} chars)"

    def update_file(self, *, path: str, old_text: str, new_text: str) -> str:
        target = self._safe_resolve_path(path)
        if not target.exists():
            raise FileNotFoundError(f"파일이 없습니다: {path}")
        current = target.read_text(encoding="utf-8", errors="replace")
        if old_text not in current:
            raise ValueError("old_text를 파일에서 찾지 못했습니다(정확한 문자열 필요).")
        updated = current.replace(old_text, new_text, 1)
        target.write_text(updated, encoding="utf-8")
        return "ok (updated 1 occurrence)"

