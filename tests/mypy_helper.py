import io
import json
import logging
import os
import textwrap
import tokenize
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Literal, Optional, TypedDict

import mypy.api

logger = logging.getLogger(__name__)


class MypyMessage(TypedDict):
    file: str
    line: int
    column: int
    message: str
    hint: Optional[str]
    code: Optional[str]
    severity: Literal["error", "note", "warning"]


@contextmanager
def change_dir(path: Path) -> Generator[None, None, None]:
    """Temporary change the current working directory."""
    old = Path.cwd()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(old)


def _parse_mypy_jsonl_output(mypy_stdout: str) -> list[MypyMessage]:
    """Parse mypy's JSONL output into a list of MypyMessage objects."""
    messages = []
    for line in mypy_stdout.strip().split("\n"):
        if line:  # Skip empty lines
            messages.append(json.loads(line))
    return messages


def run_mypy(
    project_dir: Path,
    extra_stub: Path,
    test_code: str,
) -> str:
    """Run mypy on the given test code and return the mypy stdout."""
    with project_dir.joinpath("pyproject.toml").open("w") as f:
        f.write(
            textwrap.dedent(
                f"""\
                [tool.mypy]
                mypy_path = "{extra_stub.absolute()}"

                [[tool.mypy.overrides]]
                module = "java.*"
                ignore_errors = true
                """
            )
        )

    testfile_name = "testfile.py"
    with project_dir.joinpath(testfile_name).open("w") as f:
        f.write(test_code)

    with change_dir(project_dir):
        result = mypy.api.run([testfile_name, "--output", "json"])

    mypy_stdout, mypy_stderr, mypy_returncode = result
    logger.debug(f"mypy stdout: {mypy_stdout}")
    logger.debug(f"mypy stderr: {mypy_stderr}")
    logger.debug(f"mypy returncode: {mypy_returncode}")

    return mypy_stdout


def run_and_assert_mypy(
    project_dir: Path,
    extra_stub: Path,
    test_code: str,
    expected_output: dict[str, str] | str,
):
    """
    Run mypy on the given test code and assert that the output matches the expected output.

    The expected_output can be either:
    - A dictionary mapping markers like "*1" to expected mypy messages. In this case,
      the function will parse the mypy JSON output and compare the messages for each marked line.
    - A raw string containing the expected mypy output. In this case, the function will compare
      the raw mypy stdout with the expected string.
    """
    mypy_stdout = run_mypy(project_dir, extra_stub, test_code)
    if isinstance(expected_output, dict):
        mypy_output = _parse_mypy_jsonl_output(mypy_stdout)
        assert_mypy_json_output(test_code, mypy_output, expected_output)
    else:
        # some errors like syntax errors are not returned as json message. In
        # this case, we just check the raw stdout for the expected error message.
        assert expected_output.strip() == mypy_stdout.strip()


def _format_mypy_msg(msg: MypyMessage) -> str:
    """Format a mypy message into a human-readable string, including hints if present."""
    formatted_msg = f"{msg['severity']}: {msg['message']}"
    if hints := msg.get("hint"):
        for hint in hints.splitlines():
            formatted_msg += f"\nhint: {hint}"
    return formatted_msg


def _parse_marked_lines_with_tokenize(code: str) -> dict[str, int]:
    """Parse the code to find all lines with markers like *1, *2, etc. in comments."""
    marked_lines = {}

    # Tokenize the code
    tokens = tokenize.generate_tokens(io.StringIO(code).readline)

    for token in tokens:
        if token.type == tokenize.COMMENT:
            # Token.string contains the comment including the #
            import re

            match = re.search(r"#\s*\*(\d+)", token.string)
            if match:
                marker = f"*{match.group(1)}"
                marked_lines[marker] = token.start[0]  # Line number

    return marked_lines


def assert_mypy_json_output(
    code: str,
    mypy_output: list[MypyMessage],
    expected_output: dict[str, str],
):
    """Assert that the mypy output matches the expected output for the given code."""

    # Parse the code to find the marked lines
    marked_lines: dict[str, int] = _parse_marked_lines_with_tokenize(code)

    # Group messages by line number
    result_by_line: dict[int, list[MypyMessage]] = {}
    for msg in mypy_output:
        line = msg["line"]
        if line not in result_by_line:
            result_by_line[line] = []
        result_by_line[line].append(msg)

    # Compare the expected output with the actual mypy messages for each marked line
    for marker, line in marked_lines.items():
        expected_msgs = expected_output[marker]
        mypy_msgs: list[MypyMessage] | None = result_by_line.pop(line)
        assert mypy_msgs is not None and len(mypy_msgs) > 0

        if isinstance(expected_msgs, str):
            expected_msgs = [expected_msgs]

        for expected_msg, msg in zip(expected_msgs, mypy_msgs, strict=True):
            actual_msg = _format_mypy_msg(msg)
            assert expected_msg.strip() == actual_msg.strip()

    if len(result_by_line) > 0:
        unexpected_msgs = []
        for line, msgs in result_by_line.items():
            for msg in msgs:
                unexpected_msgs.append(_format_mypy_msg(msg))
            assert False, f"Unexpected mypy message in line {line}:\n{unexpected_msgs}"
