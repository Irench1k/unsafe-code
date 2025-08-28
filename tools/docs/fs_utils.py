import hashlib
from pathlib import Path
from typing import Dict, Iterable, List, Optional


BUFFER_SIZE = 1024 * 1024


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(BUFFER_SIZE)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def compute_fingerprint(strings: Iterable[str]) -> str:
    h = hashlib.sha256()
    for s in strings:
        h.update(s.encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()


def find_files_by_name(root: Path, name: str) -> List[Path]:
    return [p for p in root.rglob(name) if p.is_file()]


def read_text_lines(path: Path) -> List[str]:
    with path.open("r", encoding="utf-8") as f:
        return f.read().splitlines()


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        f.write(content)


def backup_file(path: Path, suffix: str = ".bak") -> Optional[Path]:
    if not path.exists():
        return None
    idx = 1
    while True:
        candidate = path.with_suffix(path.suffix + suffix if idx == 1 else f"{path.suffix}{suffix}.{idx}")
        if not candidate.exists():
            content = path.read_bytes()
            candidate.write_bytes(content)
            return candidate
        idx += 1
