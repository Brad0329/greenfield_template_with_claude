"""100줄 넘는 플레이북은 `## 목차`를 두고, 목차가 실제 `##` 제목과 일치해야 한다.

긴 참조 파일은 앞부분만 읽히고 뒤쪽(최신 실측·결정)이 놓인다 — 목차가 전체 지도 역할을 한다.
목차는 손으로 만든 목록이라 제목을 고치거나 절을 추가하면 어긋난다(CLAUDE.md 불변 규칙
"손으로 만든 데이터에는 자동 검증") — 그래서 존재만이 아니라 제목 집합과 대조한다.

실행: python -m pytest tests/test_playbook_toc.py
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLAYBOOKS = ROOT / "docs" / "playbooks"
LINE_LIMIT = 100
TOC_HEADING = "## 목차"


def headings(text: str, marker: str) -> list[str]:
    """코드 펜스 밖에서 `marker`(예: "## ")로 시작하는 제목 텍스트. 목차 제목 자신은 제외."""
    found = []
    in_fence = False
    for line in text.splitlines():
        if line.startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence and line.startswith(marker) and line != TOC_HEADING:
            found.append(line[len(marker):].strip())
    return found


def toc_entries(text: str) -> list[str] | None:
    """`## 목차` 아래 글머리 항목(들여쓰기 무시). 목차가 없으면 None."""
    lines = text.splitlines()
    if TOC_HEADING not in lines:
        return None
    entries = []
    for line in lines[lines.index(TOC_HEADING) + 1:]:
        stripped = line.strip()
        if stripped.startswith("#") or stripped == "---":
            break
        if stripped.startswith("- "):
            entries.append(stripped[2:].strip())
    return entries


def test_제목_추출은_코드펜스_안을_무시한다():
    text = "## 가\n```\n## 코드 안\n```\n## 나\n## 목차\n"
    assert headings(text, "## ") == ["가", "나"]


def test_목차_항목은_다음_구분선에서_끝난다():
    text = "# 제목\n## 목차\n- 가\n  - 나\n---\n- 본문 글머리\n"
    assert toc_entries(text) == ["가", "나"]


def test_긴_플레이북은_목차가_제목과_일치한다():
    long_files = [p for p in sorted(PLAYBOOKS.glob("*.md"))
                  if len(p.read_text(encoding="utf-8").splitlines()) > LINE_LIMIT]
    assert long_files, "100줄 넘는 플레이북이 하나도 없다 — 측정 대상이 사라졌는지 확인"
    problems = []
    for path in long_files:
        text = path.read_text(encoding="utf-8")
        entries = toc_entries(text)
        if entries is None:
            problems.append(f"{path.name}: `{TOC_HEADING}` 없음")
            continue
        # `##` 절은 전부 목차에 있어야 한다. `#` 부 제목(1부·2부)은 묶음용으로 넣어도 되고 빼도 된다.
        sections = headings(text, "## ")
        parts = headings(text, "# ")[1:]  # 첫 `#`은 문서 제목
        missing = [h for h in sections if h not in entries]
        stale = [e for e in entries if e not in sections and e not in parts]
        if missing:
            problems.append(f"{path.name}: 목차에 없는 제목 {missing}")
        if stale:
            problems.append(f"{path.name}: 제목에 없는 목차 항목 {stale}")
    assert not problems, "\n".join(problems)
