"""개별 flutter test 차단 훅(`.claude/hooks/no_targeted_flutter_test.py`) 검증.

**반례가 이 테스트의 존재 이유다.** 훅은 너무 많이 막으면 도구를 못 쓰게 만든다 —
여기서 반드시 통과해야 하는 것은 **맨몸 `flutter test`** 다. 그게 권장하는 대체 수단이라
그것까지 막으면 고칠 방법이 없어진다(`no_redundant_cd`가 `cd app` 단독을 막으면 안 되는 것과 같다).

실행: python -m pytest tests/test_no_targeted_flutter_test.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / ".claude" / "hooks" / "no_targeted_flutter_test.py"
sys.path.insert(0, str(HOOK.parent))
from no_targeted_flutter_test import blocked  # noqa: E402


# ── 막아야 하는 것 — 2026-08-20 F-032에서 실제로 8번 물었던 형태들 ────────────

@pytest.mark.parametrize("command", [
    "flutter test test/cache_test.dart",                                  # 20.2초
    'flutter test test/ai_model_test.dart --plain-name "요청에 실린다"',    # 205.6초
    "flutter test test/ai_model_test.dart",                               # 178.8초
    'flutter test test/text_size_test.dart --plain-name "다섯 단계 라디오"',  # 158.0초
    "flutter test --plain-name F-032",
    "  flutter test test/foo_test.dart",                                  # 앞 공백
])
def test_인자가_붙으면_막는다(command):
    assert blocked(command)


# ── 막으면 안 되는 것 ────────────────────────────────────────────────────────

@pytest.mark.parametrize("command", [
    "flutter test",                      # ★ 권장하는 대체 수단이다. 막으면 안 된다
    "flutter test ",                     # 뒤 공백만
    "  flutter test  ",
    # ★ 딱 하나 판 예외 — 문자열이 고정이라 정확 일치 규칙으로 덮인다.
    "flutter test --reporter failures-only",
    "  flutter test --reporter failures-only  ",
    "flutter analyze",                   # 다른 하위 명령은 건드리지 않는다
    "flutter build apk --release --split-per-abi",
    "flutter pub get",
    "flutter devices",
    "dart test test/foo_test.dart",      # flutter가 아니다
    "git commit -F .commit_msg.txt",
])
def test_정상_호출은_막지_않는다(command):
    assert not blocked(command)


def test_빈_명령은_막지_않는다():
    assert not blocked("")


# ── 예외가 새지 않는가 — 이 변경의 유일한 위험이다 ──────────────────────────

@pytest.mark.parametrize("command", [
    "flutter test --reporter compact",              # 다른 리포터는 안 된다
    "flutter test --reporter expanded",
    "flutter test --reporter failures-only --plain-name x",   # 뒤에 더 붙으면 안 된다
    "flutter test test/x_test.dart --reporter failures-only",  # 앞에 파일이 붙어도
    "flutter test --reporter failures-only 2>&1",   # 출력 필터가 붙어도
])
def test_예외는_그_한_형태뿐이다(command):
    """`--reporter <아무거나>`를 열면 다시 매번 달라져 프롬프트가 살아난다."""
    assert blocked(command)


# ── 훅을 실제로 파이프로 돌려 본다 (스킬 요구사항) ───────────────────────────

def _run(payload: dict) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def test_훅이_deny를_돌려준다():
    p = _run({"tool_input": {"command": "flutter test test/cache_test.dart"}})
    assert p.returncode == 0, p.stderr
    decision = json.loads(p.stdout)["hookSpecificOutput"]
    assert decision["permissionDecision"] == "deny"
    assert "맨몸" in decision["permissionDecisionReason"]


def test_맨몸_호출에는_아무_말도_안_한다():
    p = _run({"tool_input": {"command": "flutter test"}})
    assert p.returncode == 0, p.stderr
    assert p.stdout.strip() == ""


def test_입력이_깨져도_막지_않는다():
    """훅 결함이 도구 사용을 봉쇄하면 안 된다."""
    p = subprocess.run(
        [sys.executable, str(HOOK)],
        input="{깨진 json",
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert p.returncode == 0
    assert p.stdout.strip() == ""          # deny를 내지 않는다
    assert "통과" in p.stderr              # 조용히 넘기지 않는다 (silent failure 금지)
