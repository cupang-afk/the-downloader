<!-- cSpell:disable -->
# AGENTS.md

## Scope

This file defines Python code style and docstring rules for this
repository.

Focus on readable, predictable declarations. Keep examples minimal. Follow
these rules for new code and for touched code when practical.

## Python Style Priorities

1. Correctness first.
2. Clear type hints for public APIs and non-trivial internals.
3. Google style docstrings for modules, classes, functions, methods,
   properties, and important attributes.
4. Stable declaration ordering.
5. Simple, explicit Python over clever compact code.

## Naming

Use standard Python naming unless an existing API requires otherwise.

- Constants: `UPPER_SNAKE_CASE`.
- Variables: `snake_case`.
- Functions and methods: `snake_case`.
- Classes and exceptions: `PascalCase`.
- Private names: single leading underscore, e.g. `_parse_url`.
- Protected/internal-reserved names: double leading underscore, e.g.
  `__build_headers`.
- Dunder names: double leading and trailing underscores, e.g. `__init__`.

## Global Naming Order

When a category can contain private, protected, and public names, order by
naming tier first:

1. `_private`
2. `__protected`
3. `public`

Inside each tier, sort names A-Z, case-insensitive.

Sort A-Z unless doing so conflicts with a runtime, inheritance, or dependency
requirement. When a dependency requirement exists, keep the required declaration
before its dependents.

Dunder names do not use this naming order.

## Module Declaration Order

Order top-level declarations by category:

1. Constants
2. Variables
3. Functions
4. Classes
5. `if __name__ == "__main__":`

Within each category, apply global naming order, then A-Z case-insensitive order
unless a runtime, inheritance, or dependency requirement needs a different
order.

```python
_PRIVATE_TIMEOUT = 5
__PROTECTED_RETRIES = 3
PUBLIC_CHUNK_SIZE = 8192

_private_cache = {}
__protected_session = None
public_default_headers = {}


def _build_path() -> str: ...


def __normalize_url() -> str: ...


def download() -> None: ...


class DownloadTask: ...


if __name__ == "__main__":
    download()
```

## Class Declaration Order

Order declarations inside classes by category:

1. Constants
2. Variables
3. Dunder methods
4. Methods, static methods, and class methods
5. Properties

Within constants, variables, methods, static methods, class methods, and
properties:

1. Apply global naming order when applicable.
2. Sort A-Z case-insensitive inside each naming tier unless a runtime,
   inheritance, or dependency requirement needs a different order.

Dunder methods are ordered separately:

1. `__init__` first.
2. Builtin/override dunders A-Z, case-insensitive.
3. Custom dunders A-Z, case-insensitive.

```python
class DownloadTask:
    _PRIVATE_LIMIT = 1
    PUBLIC_LIMIT = 10

    _private_state: str
    public_url: str

    def __init__(self, url: str) -> None:
        self.public_url = url
        self._private_state = "pending"

    def __repr__(self) -> str:
        return f"DownloadTask(url={self.public_url!r})"

    def __custom_hook__(self) -> None: ...

    def _private_method(self) -> None: ...

    @classmethod
    def from_url(cls, url: str) -> "DownloadTask":
        return cls(url)

    @property
    def status(self) -> str:
        return self._private_state
```

## Docstring Style

Use Google style docstrings compatible with `sphinx.ext.napoleon` and Ruff
pydocstyle convention `google`.

General rules:

- Start with a one-line imperative or descriptive summary.
- Add a blank line before sections.
- Use sections only when needed: `Args`, `Returns`, `Yields`, `Raises`,
  `Attributes`, `Examples`, `Note`.
- Do not document `self` or `cls` in `Args`.
- If PEP 484 annotations already show types clearly, omit repeated types in
  docstrings.
- Document exceptions that are part of the interface.
- Document properties in the getter docstring.
- For `__init__`, document initialization either in the class docstring or in
  `__init__`, not both.

```python
def fetch(url: str, timeout: float) -> bytes:
    """Fetch bytes from a URL.

    Args:
        url: URL to fetch.
        timeout: Request timeout in seconds.

    Returns:
        Response body bytes.

    Raises:
        TimeoutError: If the request exceeds `timeout`.
    """
```

```python
class DownloadError(Exception):
    """Raised when a download fails.

    Args:
        message: Human-readable failure message.
        url: URL that failed.

    Attributes:
        message: Human-readable failure message.
        url: URL that failed.
    """
```

```python
@property
def progress(self) -> float:
    """Download progress from 0.0 to 1.0."""
```

## Type Hints

- Annotate all public functions, methods, and class attributes.
- Annotate non-trivial private helpers.
- Prefer built-in generics: `list[str]`, `dict[str, int]`, `tuple[str, ...]`.
- Use `| None` instead of `Optional`.
- Avoid `Any` unless the value is intentionally unconstrained.
- Keep docstrings focused on behavior, not duplicated type info.

## Agentic Workflow

Before running any check workflow, first ensure the code style rules above are
applied to the relevant source files. Use the helper snippets below when
declaration order, docstrings, or other style requirements are hard to inspect
manually. After code style is applied, continue with the BasedPyright, Ruff,
and Pytest check workflows.

Use BasedPyright for type checking. Use Ruff for linting, fixing, and
formatting. Use Pytest for tests.

BasedPyright, Ruff, and Pytest are development dependencies in
`pyproject.toml`. They are expected to be installed in the active development
environment. If all command forms for a tool fail, stop work, treat the check
as failed, and ask the user to install development tools with `uv sync --dev`
or another environment-specific method.

Project source code lives under `src/`. Run BasedPyright and Ruff against
`src/` only unless the user asks to check another path.

### BasedPyright Workflow

BasedPyright command priority:

1. `uv run basedpyright`.
2. `python -m basedpyright` if `uv run basedpyright` fails.
3. `basedpyright` if `python -m basedpyright` fails.
4. If BasedPyright is unavailable through all options, stop work, treat the
   check as failed, and ask the user to install development tools with
   `uv sync --dev` or another environment-specific method.

Type checking workflow:

1. Run `uv run basedpyright src/` and record the initial errors.
2. If errors exist, fix the troubled code manually.
3. Never suppress BasedPyright errors with comments, ignore directives, or rule
   configuration changes unless the user explicitly approves that exact
   suppression.
4. Never modify BasedPyright rules to make errors disappear.
5. Run BasedPyright again.
6. If the check still fails, repeat manual fixes and checks, up to 5 attempts.
7. After 5 failed manual attempts, stop and ask the user for guidance. Include
   the remaining error output, affected code context, what was tried, and
   suggested fixes.

When using fallback commands, keep the same check intent:

```bash
uv run basedpyright src/
```

```bash
python -m basedpyright src/
```

```bash
basedpyright src/
```

### Pytest Workflow

Pytest command priority:

1. `uv run pytest`.
2. `python -m pytest` if `uv run pytest` fails.
3. `pytest` if `python -m pytest` fails.
4. If Pytest is unavailable through all options, stop work, treat the check as
   failed, and ask the user to install development tools with `uv sync --dev`
   or another environment-specific method.

Testing workflow:

1. Run `uv run pytest` and record the initial failures.
2. If failures exist, fix the troubled code manually.
3. Run Pytest again.
4. If the check still fails, repeat manual fixes and checks, up to 5 attempts.
5. After 5 failed manual attempts, stop and ask the user for guidance. Include
   the remaining failure output, affected code context, what was tried, and
   suggested fixes.

When using fallback commands, keep the same check intent:

```bash
uv run pytest
```

```bash
python -m pytest
```

```bash
pytest
```

### Ruff Workflow

Ruff command priority:

1. `uv run ruff`.
2. `python -m ruff` if `uv run ruff` fails.
3. `ruff` if `python -m ruff` fails.
4. If Ruff is unavailable through all options, stop work, treat the check as
   failed, and ask the user to install development tools with `uv sync --dev`
   or another environment-specific method.

Code checking workflow:

1. Run `uv run ruff check src/` and record the initial errors.
2. Run `uv run ruff check src/ --fix`.
3. Run `uv run ruff format src/`.
4. Run `uv run ruff check src/` again and compare remaining errors with the
   initial errors.
5. If errors remain, fix the troubled code manually.
6. Never suppress Ruff errors with `# noqa`, disable comments, or rule
   configuration changes unless the user explicitly approves that exact
   suppression.
7. Never modify Ruff rules to make errors disappear.
8. Run a final `ruff check src/`.
9. If the final check still fails, repeat manual fixes and final checks, up to
   5 attempts.
10. After 5 failed manual attempts, stop and ask the user for guidance. Include
    the remaining error output, affected code context, what was tried, and
    suggested fixes.

When using fallback commands, keep the same arguments:

```bash
uv run ruff check src/
uv run ruff check src/ --fix
uv run ruff format src/
```

```bash
python -m ruff check src/
python -m ruff check src/ --fix
python -m ruff format src/
```

```bash
ruff check src/
ruff check src/ --fix
ruff format src/
```

## AST Helper Snippets

Use `ast` for quick checks when declaration order is hard to inspect manually.
These snippets are written exclusively for the current project Python version:
Python 3.14.5.

List top-level declarations:

```python
import ast
from pathlib import Path

TARGET = Path("src/the_downloader/task.py")
module = ast.parse(TARGET.read_text(encoding="utf-8"), filename=str(TARGET))

for node in module.body:
    match node:
        case ast.Assign():
            print("variable", node.lineno)
        case ast.AnnAssign(target=ast.Name(id=name)):
            print("variable", name, node.lineno)
        case ast.AsyncFunctionDef(name=name) | ast.FunctionDef(name=name):
            print("function", name, node.lineno)
        case ast.ClassDef(name=name):
            print("class", name, node.lineno)
```

List class declarations:

```python
import ast
from pathlib import Path

TARGET = Path("src/the_downloader/task.py")
module = ast.parse(TARGET.read_text(encoding="utf-8"), filename=str(TARGET))

for node in module.body:
    if isinstance(node, ast.ClassDef):
        print(node.name)
        for item in node.body:
            match item:
                case ast.Assign():
                    print("  variable", item.lineno)
                case ast.AnnAssign(target=ast.Name(id=name)):
                    print("  variable", name, item.lineno)
                case (
                    ast.AsyncFunctionDef(name=name)
                    | ast.FunctionDef(name=name)
                ):
                    print("  method", name, item.lineno)
```

Find missing docstrings:

```python
import ast
from pathlib import Path

TARGET = Path("src/the_downloader/task.py")
module = ast.parse(TARGET.read_text(encoding="utf-8"), filename=str(TARGET))

if ast.get_docstring(module) is None:
    print("missing docstring", "module", 1)

for node in ast.walk(module):
    if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
        if ast.get_docstring(node) is None:
            print("missing docstring", node.name, node.lineno)
```

Print existing docstring summaries:

```python
import ast
from pathlib import Path

TARGET = Path("src/the_downloader/task.py")
module = ast.parse(TARGET.read_text(encoding="utf-8"), filename=str(TARGET))

module_docstring = ast.get_docstring(module)
if module_docstring:
    print("module", 1, module_docstring.splitlines()[0])

for node in ast.walk(module):
    if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
        docstring = ast.get_docstring(node)
        if docstring:
            print(node.name, node.lineno, docstring.splitlines()[0])
```

Find Google-style section headers:

```python
import ast
from pathlib import Path

SECTION_HEADERS = {
    "Args:",
    "Returns:",
    "Yields:",
    "Raises:",
    "Attributes:",
    "Examples:",
    "Note:",
}
TARGET = Path("src/the_downloader/task.py")
module = ast.parse(TARGET.read_text(encoding="utf-8"), filename=str(TARGET))

for node in ast.walk(module):
    if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
        docstring = ast.get_docstring(node) or ""
        headers = [
            line.strip()
            for line in docstring.splitlines()
            if line.strip() in SECTION_HEADERS
        ]
        if headers:
            print(node.name, node.lineno, headers)
```

Sketch a sorting helper:

```python
def naming_tier(name: str) -> int:
    if name.startswith("__") and name.endswith("__"):
        return 99
    if name.startswith("__"):
        return 1
    if name.startswith("_"):
        return 0
    return 2


def name_key(name: str) -> tuple[int, str]:
    return naming_tier(name), name.casefold()
```

Sketch dunder ordering:

```python
BUILTIN_DUNDERS = {
    "__aenter__",
    "__aexit__",
    "__bool__",
    "__enter__",
    "__eq__",
    "__exit__",
    "__hash__",
    "__iter__",
    "__len__",
    "__repr__",
    "__str__",
}


def dunder_key(name: str) -> tuple[int, str]:
    if name == "__init__":
        return 0, name
    if name in BUILTIN_DUNDERS:
        return 1, name.casefold()
    return 2, name.casefold()
```
