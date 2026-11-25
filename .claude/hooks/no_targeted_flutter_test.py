r"""`flutter test`에 승인 창을 만드는 인자를 붙이면 막는다 (PreToolUse 훅).

**열려 있는 형태는 셋이다**:
  - 맨몸 `flutter test` — 전체 실행.
  - `flutter test --reporter failures-only` — 전체 실행, 실패만 출력.
  - `flutter test <테스트 파일 하나>` — **실패를 일부러 보려는 실행**(재현 테스트의 첫 실패·변이 확인)에 쓴다.
    허용 규칙 `flutter test test/*`가 있어야 안 묻는다(`노하우_승인_대기_최소화.md` §5 스타터).

**막는 것**: 그 밖의 인자 전부 — `--plain-name "…"`·`--name`·다른 리포터·파일 여러 개·파일 뒤에 붙는 옵션.
이름 인자는 호출마다 문자열이 달라지고 한글이 들어가 **매번 새 승인 창**이 뜬다.

**왜 훅인가**: 승인 창 실측에서 커밋 직전 8번의 창 대부분이 `flutter test <파일> --plain-name "…"`였고
사용자가 판단할 것은 하나도 없었다. 전체 450건 23~27초 대 이름 인자 실행 158~206초 — **차이는 전부
사람이 클릭하기를 기다린 시간**이지 테스트 시간이 아니다(같은 명령을 승인 뒤 다시 부르면 8초).

**왜 파일 하나는 여는가**: 이 템플릿으로 만든 프로젝트 1곳의 실측(2026-11-25, 앱 테스트 실행 342회)에서
최소 142회가 "테스트 하나의 실패를 보려는" 실행이었고 그중 140회가 전체 실행이었다. 파일 하나를
막아 둔 탓이다. 경로만 붙는 형태는 와일드카드 규칙 한 줄로 덮여 창을 만들지 않는다.
전체 실행은 CLAUDE.md '검증 강도' 표가 요구하는 자리에서 돈다.

**막지 않는 것**: `flutter analyze`·`flutter build apk …` 등 다른 하위 명령(재지 않았다 — YAGNI).

**정말 다른 인자가 필요하면** 사용자에게 말하고 승인을 받는다. 훅을 우회하지 않는다.

**훅이 고장 나면 막지 않고 통과시킨다** — 훅 결함이 도구 사용을 봉쇄하면 안 된다.

Flutter를 안 쓰는 프로젝트면 세 곳에서 지운다 — 이 훅, settings.json의 등록, `tests/test_no_targeted_flutter_test.py`.
"""

import re
import sys

from hook_io import deny, read_command

# `flutter test` 뒤에 **무언가 더 있는** 형태. 맨몸(뒤에 공백뿐)은 통과시킨다.
TARGETED = re.compile(r"^\s*flutter\s+test\s+\S")

# 테스트 파일 **하나**, 경로만. 영문·숫자·`_`·`-`·`.`·`/`만 받는다 — 공백·따옴표·한글·옵션이 끼면
# 안 맞는다(그 형태들이 승인 창을 만든다). `\`는 받지 않는다: 허용 규칙 `test/*`와 문자열이 어긋난다.
SINGLE_FILE = re.compile(r"^\s*flutter\s+test\s+[A-Za-z0-9_\-./]+_test\.dart\s*$")

# 고정 문자열 예외: 실패한 것만 출력하는 리포터. 전체 실행 출력이 길어 어느 테스트가 실패했는지
# 읽기 어려워서 열었다. 문자열이 고정이라 정확 일치 규칙으로 덮인다.
# `--reporter <아무거나>`로 넓히지 말 것 — 다시 매번 달라진다.
ALLOWED_EXACT = {"flutter test --reporter failures-only"}

REASON = (
    "`flutter test`에 이 인자를 붙이지 말 것 — **호출마다 새 확인 창**이 뜬다.\n"
    "  열려 있는 형태는 셋뿐이다:\n"
    "  - `flutter test` — 전체\n"
    "  - `flutter test --reporter failures-only` — 전체, 실패만 출력\n"
    "  - `flutter test test/foo_test.dart` — 파일 하나, 경로만(실패를 일부러 보는 재현·변이 확인용)\n"
    "  `--plain-name`·`--name`·다른 리포터·파일 여러 개·파일 뒤 옵션은 막힌다.\n"
    "  정말 다른 인자가 필요하면 **사용자에게 말하고 승인을 받는다.**"
)


def blocked(command: str) -> bool:
    """이 명령을 막아야 하는가. 테스트가 이 함수를 직접 부른다."""
    if (command or "").strip() in ALLOWED_EXACT:
        return False
    if SINGLE_FILE.match(command or ""):
        return False
    return bool(TARGETED.match(command or ""))


def main() -> int:
    command = read_command("no_targeted_flutter_test")
    if command is None:
        return 0
    if blocked(command):
        deny(REASON)
    return 0


if __name__ == "__main__":
    sys.exit(main())
