r"""PowerShell 호출에 출력 필터(`| Select-String`·`| Select-Object`·`2>&1`)가 붙으면 막는다.

**왜 훅인가**: 2026-08-20 `/approval-audit` 실측에서 **이 습관이 최대 비용**이었다.

| 벽시계 | 호출 | 맨몸으로 불렀을 때 |
|---|---|---|
| 209.0초 | `flutter test 2>&1 \| Select-Object -Last 12` | **27.4초** |
| 89.0초 | `flutter test <파일> 2>&1 \| Select-String …` | 14.0초 |
| 94.7초 | `measure_wait.py --grep "pytest" --slow 60` | — |

**출력을 자르려다 3~7배를 썼다.**

**무엇이 문제인가**: 이 환경의 허용 규칙은 **정확 일치만 걸린다**(와일드카드는 무효 —
2026-08-20 실측, 독립 사례 5건). 그래서 **명령 문자열이 매번 달라지는 것 자체가 비용**이다.
`flutter test`는 규칙에 있지만 `flutter test 2>&1 | Select-Object -Last 12`는 다른 문자열이라
없다. 출력을 자르려고 꼬리를 붙이는 순간 **그 호출은 새 확인 창을 만든다.**

덤으로 `2>&1`은 애초에 불필요하다 — 이 도구는 stderr를 이미 함께 돌려준다.
Windows PowerShell 5.1에서는 네이티브 exe의 stderr를 리다이렉트하면 각 줄이 ErrorRecord로
포장돼 **exit 0인데도 실패로 보이는** 부작용까지 있다.

**막지 않는 것**:
  - `| Out-File`·`| ConvertFrom-Json` 등 **자르기가 아닌** 파이프.
  - Bash 도구의 호출. 여기서 재지 않았으므로 단정하지 않는다(matcher가 PowerShell이다).

**출력이 정말 클 때는 어떻게 하나** — 그냥 받는다. 하네스가 큰 출력을 파일로 떨궈 주고
그 경로를 알려 준다. 그 파일을 `Read`/`Grep`으로 보면 된다(2026-08-20에 `flutter test`
431건 출력을 실제로 그렇게 처리했다). 값 하나만 필요하면 파이썬 한 줄로 계산해 출력한다.

**훅이 고장 나면 막지 않고 통과시킨다** — 훅 결함이 도구 사용을 봉쇄하면 안 된다
(`no_redundant_cd.py`와 같은 원칙).
"""

import json
import re
import sys

# `| Select-String …` / `| Select-Object …` (PowerShell은 대소문자를 안 가린다)
# 그리고 어디에 있든 `2>&1`.
OUTPUT_FILTER = re.compile(
    r"(\|\s*Select-(?:String|Object)\b)|(2>&1)",
    re.IGNORECASE,
)

REASON = (
    "출력 필터(`| Select-String`·`| Select-Object`·`2>&1`)를 붙이지 말 것.\n"
    "  허용 규칙은 **정확 일치만 걸린다.** 꼬리를 붙이면 명령 문자열이 달라져\n"
    "  **그 호출만 새 확인 창을 만든다** (실측: `flutter test`가 27초 → 209초).\n"
    "  → 명령을 **맨몸으로** 부르고 출력은 그냥 받는다.\n"
    "  출력이 크면 하네스가 파일로 떨궈 주므로 그 경로를 `Read`/`Grep`으로 보면 된다.\n"
    "  값 하나만 필요하면 파이썬 한 줄로 계산해서 출력한다.\n"
    "  (`2>&1`은 어차피 불필요하다 — stderr는 이미 함께 돌아온다.)"
)


def blocked(command: str) -> bool:
    """이 명령을 막아야 하는가. 테스트가 이 함수를 직접 부른다."""
    return bool(OUTPUT_FILTER.search(command or ""))


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        # 훅이 입력을 못 읽었다고 도구를 막지 않는다. 조용히 통과시키되 이유를 남긴다.
        print("no_output_filter: 훅 입력을 읽지 못해 통과시킨다", file=sys.stderr)
        return 0

    if blocked((data.get("tool_input") or {}).get("command", "")):
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": REASON,
            }
        }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
