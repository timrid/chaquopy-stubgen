import io
import json
import logging
import os
import re
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
    test_code: str,
) -> tuple[str, str]:
    """Run mypy on the given test code and return (mypy_stdout, testfile_name)."""
    testfile_name = "testfile.py"
    with project_dir.joinpath(testfile_name).open("w") as f:
        f.write(test_code)

    with change_dir(project_dir):
        result = mypy.api.run([testfile_name, "--output", "json"])

    mypy_stdout, mypy_stderr, mypy_returncode = result
    logger.debug(f"mypy stdout: {mypy_stdout}")
    logger.debug(f"mypy stderr: {mypy_stderr}")
    logger.debug(f"mypy returncode: {mypy_returncode}")

    return mypy_stdout, testfile_name


def run_and_assert_mypy(
    project_dir: Path,
    test_code: str,
    expected_output: dict[str, str] | dict[str, str | list[str]] | str,
):
    """
    Run mypy on the given test code and assert that the output matches the expected output.

    The expected_output can be either:
    - A dictionary mapping markers like "*1" to expected mypy messages. In this case,
      the function will parse the mypy JSON output and compare the messages for each marked line.
    - A raw string containing the expected mypy output. In this case, the function will compare
      the raw mypy stdout with the expected string.
    """
    mypy_stdout, testfile_name = run_mypy(project_dir, test_code)
    if isinstance(expected_output, dict):
        mypy_output = _parse_mypy_jsonl_output(mypy_stdout)
        assert_mypy_json_output(test_code, mypy_output, expected_output, testfile_name)
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
            # token.string contains the comment including the #
            match = re.search(r"#\s*\*(\d+)", token.string)
            if match:
                marker = f"*{match.group(1)}"
                marked_lines[marker] = token.start[0]  # Line number

    return marked_lines


def assert_mypy_json_output(
    code: str,
    mypy_output: list[MypyMessage],
    expected_output: dict[str, str] | dict[str, str | list[str]],
    testfile_name: str = "testfile.py",
):
    """Assert that the mypy output matches the expected output for the given code."""

    # Parse the code to find the marked lines
    marked_lines: dict[str, int] = _parse_marked_lines_with_tokenize(code)

    # Validate that all expected markers are present in the code
    missing_markers = set(expected_output.keys()) - set(marked_lines.keys())
    if missing_markers:
        assert False, f"Expected markers not found in code: {', '.join(sorted(missing_markers))}"

    # Group messages by line number, ignoring messages from other files
    # (e.g. "defined here" notes that point back to stub definitions).
    result_by_line: dict[int, list[MypyMessage]] = {}
    for msg in mypy_output:
        if msg["file"] != testfile_name:
            continue
        line = msg["line"]
        if line not in result_by_line:
            result_by_line[line] = []
        result_by_line[line].append(msg)

    # Compare the expected output with the actual mypy messages for each marked line
    for marker, line in marked_lines.items():
        expected_msgs = expected_output[marker]
        mypy_msgs: list[MypyMessage] | None = result_by_line.pop(line, None)
        assert mypy_msgs is not None and len(mypy_msgs) > 0, f"Expected mypy messages for marker {marker} on line {line}, but found none."

        if isinstance(expected_msgs, str):
            expected_msgs = [expected_msgs]

        # Check that the number of expected and actual messages match
        if len(expected_msgs) != len(mypy_msgs):
            actual_msgs_formatted = "\n".join(f"  - {_format_mypy_msg(msg)}" for msg in mypy_msgs)
            expected_msgs_formatted = "\n".join(f"  - {msg}" for msg in expected_msgs)
            assert False, (
                f"Number of mypy messages mismatch for marker {marker} on line {line}:\n"
                f"Expected {len(expected_msgs)} message(s):\n{expected_msgs_formatted}\n"
                f"But got {len(mypy_msgs)} message(s):\n{actual_msgs_formatted}"
            )

        for expected_msg, msg in zip(expected_msgs, mypy_msgs, strict=True):
            actual_msg = _format_mypy_msg(msg).strip()
            expected_msg = expected_msg.strip()
            assert expected_msg == actual_msg, (
                f"Mypy message mismatch for marker {marker} on line {line}:\n"
                f"Expected: {expected_msg!r}\n"
                f"Actual:   {actual_msg!r}"
            )

    if len(result_by_line) > 0:
        unexpected_msgs = []
        for line, msgs in result_by_line.items():
            for msg in msgs:
                unexpected_msgs.append(f"{msg['file']}:{line}: {_format_mypy_msg(msg)}")
        assert False, "Unexpected mypy messages:\n" + "\n".join(unexpected_msgs)
