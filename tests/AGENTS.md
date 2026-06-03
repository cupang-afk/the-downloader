<!-- cSpell: disable -->
# AGENTS.md

## Scope

This file applies to tests under `tests/`. Follow the root `AGENTS.md` for
repository-wide Python style, docstrings, type hints, and check workflows.

Use this file when adding or changing pytest tests. The goal is to document
meaningful public behavior without over-testing implementation details.

## Test Layout

Mirror the `src/the_downloader/` package structure under `tests/`.

Examples:

```text
src/the_downloader/utils/file.py
tests/utils/test_file.py

src/the_downloader/manager/queue.py
tests/manager/test_queue.py

src/the_downloader/provider/requests.py
tests/provider/test_requests.py
```

Prefer one test file per source module. Do not create one test file per code
unit unless the module becomes too large to keep readable.

Use `tests/builtin/` for project-provided concrete implementations that are
built from a base or abstract contract.

Examples:

```text
src/the_downloader/callback.py
tests/test_callback.py
tests/builtin/test_callback.py

src/the_downloader/provider/base.py
tests/provider/test_base.py
tests/builtin/provider/test_base.py
```

Use the normal mirrored `tests/` root for abstract contracts, protocols, base
behavior, helpers, and public module behavior. Use `tests/builtin/` for
concrete implementations shipped by the project.

## Test Naming

Use `test_<code_unit>_<case>()`.

The case name should describe the branch, outcome, or misuse being tested.

Examples:

```python
def test_subject_accepts_valid_input() -> None:
    """Accept input that matches the public contract."""


def test_subject_rejects_invalid_category() -> None:
    """Reject a realistic caller mistake."""
```

For class behavior, include the relevant class or method name only when it is
needed to make the report clear. Keep file names based on source modules.

Example:

```python
def test_queue_manager_rejects_add_before_start() -> None:
    """Reject adding work before the manager is started."""
```

## Test Scope

Cover behavior in this order:

1. Branches that the project code explicitly owns.
2. Likely caller mistakes that are realistic for library users.
3. Rare edge cases only when the behavior should become public contract.

Do not test random invalid inputs just because they are possible. Do not test
Python standard library internals unless the project intentionally promises
that behavior.

Every meaningful code branch should have a test when it affects public
behavior. Use separate tests when separate reports are useful in pytest output.

Avoid combining unrelated branches into one broad test when a failure would be
hard to diagnose.

## Abstract Classes

Abstract class tests should focus on the contract itself.

Cover these behaviors when relevant:

1. Direct abstract class instantiation is rejected.
2. Incomplete subclasses are rejected.
3. Complete subclasses can be created.
4. Complete subclasses can receive calls through the abstract interface.

Keep abstract contract tests under the normal mirrored `tests/` root.

Static type checkers may reject direct abstract instantiation in tests. In that
case, create the abstract or incomplete class dynamically with `type(...)` so
the runtime behavior is tested without static abstract-usage errors.

Example:

```python
def test_base_subject_rejects_direct_instantiation() -> None:
    """Reject direct instantiation of the abstract contract."""
    subject_type = type("RuntimeBaseSubject", (BaseSubject,), {})

    with pytest.raises(TypeError, match="abstract"):
        subject_type()
```

## Builtin Implementations

Builtin implementation tests cover concrete project-provided classes that
implement base or abstract contracts.

Place these tests under `tests/builtin/` while preserving the source module
path. Verify concrete behavior, not abstract contract mechanics.

Good builtin behavior tests:

```python
def test_basic_subject_emits_start_message() -> None:
    """Emit the expected start message."""


def test_null_subject_ignores_progress() -> None:
    """Ignore progress callbacks without output or errors."""
```

Avoid placing concrete implementation tests in the abstract contract test file
unless the concrete class is only a tiny local fake used to prove the abstract
contract.

## Realistic Misuse

Add uncommon-case tests only when the mistake is likely for a caller to make or
when the behavior should be documented.

Name misuse tests after the misuse category.

Examples:

```python
def test_subject_rejects_directory_path() -> None:
    """Reject a directory where a file path is required."""


def test_subject_rejects_invalid_url() -> None:
    """Reject a URL that cannot identify a network location."""
```

If a misuse case is only rejected because a dependency raises internally,
decide whether that behavior is part of the project contract before testing it.

## Runtime Types

Type hints are checked by BasedPyright, but Python does not enforce them at
runtime.

Only test invalid runtime types when the code explicitly validates those types
or the project wants to document the raised exception as public behavior.

Behavior worth testing:

```python
def test_subject_rejects_non_string_identifier() -> None:
    """Reject non-string identifiers because type validation is explicit."""
    with pytest.raises(TypeError):
        subject(123)
```

Usually not worth testing:

```python
def test_subject_rejects_object() -> None:
    """This only proves a dependency rejects object()."""
```

## Test Structure

Use arrange, act, assert spacing for readability.

```python
def test_subject_case(tmp_path: Path) -> None:
    """Describe the behavior being tested."""
    source = tmp_path / "source.txt"
    source.write_text("hello", encoding="utf-8")

    result = subject(source)

    assert result == "hello"
```

Use `tmp_path` for filesystem tests. Use `monkeypatch` for environment
variables, process `PATH`, or dependency seams. Avoid mocks unless they isolate
an external system or nondeterministic behavior.

Use `pytest.mark.parametrize` when cases are the same behavior with different
data.

```python
@pytest.mark.parametrize("value", ["a", "b", "c"])
def test_subject_accepts_known_values(value: str) -> None:
    """Accept known values."""
    assert subject(value) == value
```

Do not use parametrization to hide different branches behind one vague test
name.

## TDD Workflow

Follow red, green, refactor for new production behavior or bug fixes.

1. Write the failing test under `tests/`.
2. Run the focused test and verify RED.
3. Write minimal production code.
4. Run the focused test and verify GREEN.
5. Run the relevant test file.
6. Run source checks when production source changes.

Focused test command:

```bash
uv run pytest tests/path/to/test_file.py::test_name -v
```

Relevant test file command:

```bash
uv run pytest tests/path/to/test_file.py -v
```

RED should fail for the expected behavior reason, not import errors, typos, or
invalid test setup.

## Existing Code Tests

When adding tests for already-written code, the initial tests may pass
immediately. That is acceptable only because production behavior already
exists.

Still verify that each test would fail if the tested branch were wrong. Check
that each assertion is specific and tied to expected public behavior. If a test
only imports a code unit or checks a broad truth, rewrite it.

Good existing-code test:

```python
def test_subject_rejects_empty_text() -> None:
    """Reject empty text with a clear exception."""
    with pytest.raises(ValueError, match="empty"):
        subject("")
```

Weak existing-code test:

```python
def test_subject() -> None:
    """This does not document meaningful behavior."""
    assert subject
```

## Tool Commands

`uv`, `pytest`, `ruff`, and `basedpyright` are development dependencies in
`pyproject.toml`. They are expected to be installed in the active development
environment.

Pytest command priority:

1. `uv run pytest`.
2. `python -m pytest` if `uv run pytest` fails.
3. `pytest` if `python -m pytest` fails.

Ruff command priority:

1. `uv run ruff`.
2. `python -m ruff` if `uv run ruff` fails.
3. `ruff` if `python -m ruff` fails.

BasedPyright command priority:

1. `uv run basedpyright`.
2. `python -m basedpyright` if `uv run basedpyright` fails.
3. `basedpyright` if `python -m basedpyright` fails.

If all command forms for a tool fail, stop work, treat the check as failed,
and ask the user to install development tools with `uv sync --dev` or another
environment-specific method.

When production source changes, run:

```bash
uv run ruff check src/
uv run ruff check src/ --fix
uv run ruff format src/
uv run ruff check src/
uv run basedpyright src/
```

## Completion Checklist

- [ ] Test file path mirrors the source module path.
- [ ] Test names identify the code unit and behavior case.
- [ ] Meaningful project-owned branches are covered.
- [ ] Realistic misuse tests are intentional and not random invalid input
  checks.
- [ ] Tests use real code where practical.
- [ ] Filesystem tests use `tmp_path`.
- [ ] Environment or `PATH` tests use `monkeypatch`.
- [ ] Focused pytest command has been run.
- [ ] Relevant test file has been run.
- [ ] Ruff and BasedPyright checks have been run when source code changes.
