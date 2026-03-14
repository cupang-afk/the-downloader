# AGENTS.md

## Purpose

This document defines mandatory coding standards for this Python project. All contributors—human and AI—must follow these rules without exception.

---

# AI Agent Instructions

## Mandatory Compliance

AI agents working on this codebase MUST:

1. Read this document before making any code changes
2. Apply all rules consistently to every file modified or created
3. Run `ruff format .` and `ruff check . --fix` after making changes
4. Verify zero lint errors before completing any task
5. Follow the exact templates provided for docstrings

## Prohibited Actions

AI agents MUST NOT:

1. Skip or ignore any rule in this document
2. Deviate from the defined module and class structure
3. Commit code with remaining lint errors

---

# Documentation Rules

## 1. Docstring Standard

All Python source code must use Google-style docstrings.

Reference: [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings)

## 2. Docstring Requirements

| Element                           | Requirement                          |
| --------------------------------- | ------------------------------------ |
| Public classes                    | Required                             |
| Public functions                  | Required                             |
| Public methods                    | Required                             |
| Module-level (`__init__.py` only) | Required                             |
| Module-level (other files)        | Forbidden                            |
| Magic methods (`__dunder__`)      | Optional (unless linter throw error) |
| Private functions (`_prefix`)     | Optional (add for complex logic)     |

> **Note:** If a method or function body contains only `pass`, `...`, or
> `return`, it is likely an interface, hook, or template method. These
> require a docstring to document the expected behavior for implementers.

### Docstring Format

- Use triple double quotes (`"""`)
- All docstrings in English
- Maximum line length: 88 characters
- One-line docstrings: opening and closing quotes on the same line
- Multi-line docstrings: opening quotes on the first line, closing
  quotes on their own line

#### Summary Line

- First line: concise imperative summary (e.g., "Fetch rows")
- No period at the end of the summary
- Must fit on one line (max 88 characters including quotes)
- The summary line is the only required part of a docstring
- Only add an extended description if the object does something
  complex or non-obvious; straightforward code needs only the summary
- Separated from the rest of the docstring by a blank line

#### Sections

Use the following sections in order when applicable:

| Section   | Description                                       |
| --------- | ------------------------------------------------- |
| `Args`    | List each parameter by name with its description  |
| `Returns` | Describe the return value and type                |
| `Yields`  | For generators, describe the yielded value        |
| `Raises`  | List each exception and the condition that raises |
| `Note`    | Additional information or caveats                 |
| `Example` | Usage example (optional)                          |

#### Section Formatting

- Section header followed by a colon (e.g., `Args:`)
- Each entry indented 4 spaces under the section header
- Entry format: `name: Description starting with uppercase`
- Multi-line descriptions indented to align with the first line
- Blank line between sections

## 3. Function Docstring Template

```python
def function_name(param1: str, param2: int) -> bool:
    """Short description of the function.

    Args:
        param1: Description of param1.
        param2: Description of param2.

    Returns:
        Description of the returned value.

    Raises:
        ValueError: When param2 is negative.
    """
```

> **Note:** Only add an extended description between the summary and
> sections if the function does something complex. For straightforward
> functions, the summary line alone is sufficient.

## 4. Class Docstring Template

```python
class ExampleClass:
    """Short description of the class.

    Attributes:
        attr1: Description of attr1.
        attr2: Description of attr2.
    """

    def __init__(self, attr1: str, attr2: int) -> None:
        """Initialize the class instance.

        Args:
            attr1: Description of attr1.
            attr2: Description of attr2.
        """
        self.attr1 = attr1
        self.attr2 = attr2
```

## 5. Module Docstring Template (`__init__.py` only)

```python
"""Short description of the module.

This module provides ...
"""
```

## 6. Commenting Guidelines

- Prefer clear names over comments
- Document complex algorithms and non-obvious logic
- Explain workarounds with reasoning
- Keep comments current; remove outdated ones
- Use inline comments sparingly

---

# Code Quality Rules

## 7. Ruff Tooling

This project uses Ruff for formatting and linting.

**Before committing, run:**

```bash
ruff format .
ruff check . --fix
ruff check .  # Must show zero errors
```

## 8. Ruff Configuration

All Ruff settings must be defined in `pyproject.toml`.

## 9. Lint Error Handling

1. Fix errors with `ruff check --fix` first
2. Never disable lint rules without documented justification
3. Document justification before ignoring any rule
4. Refactor code instead of disabling rules
5. Never suppress exceptions without documented reason

## 10. Line Length

Maximum: 88 characters (applies to code, docstrings, and comments).

## 11. Trailing Commas

For multi-line collections (lists, tuples, sets, dicts, function args)
with more than 3 items, include a trailing comma:

```python
# Correct
items = [
    "first",
    "second",
    "third",
]

# Also correct (single line, no trailing comma needed)
items = ["first", "second", "third"]
```

This allows Ruff to auto-format correctly and improves diff readability.

## 12. Python Version

Minimum: Python 3.12. Do not use incompatible features.

## 13. Exception Handling

- Raise specific exceptions (e.g., `ValueError`, `TypeError`)
- Never suppress exceptions without documentation
- Use custom exceptions from the project's `error.py`

## 14. Testing (Currently not used)

Run tests before submitting:

```bash
pytest
```

All existing tests must pass. New functionality requires appropriate tests.

## 15. Git Commits (Currently not used)

- Use present tense ("Add feature" not "Added feature")
- Keep messages concise and descriptive

## 16. Pre-commit Hooks (Currently not used)

```bash
pip install pre-commit
pre-commit install
```

Configuration: `.pre-commit-config.yaml`

---

# Code Structure Rules

## 17. Module Structure

Modules must follow this order:

| Order | Element           | Description                          |
| ----- | ----------------- | ------------------------------------ |
| 1     | Module docstring  | Only in `__init__.py`                |
| 2     | Imports           | Standard library, third-party, local |
| 3     | Module constants  | `UPPERCASE` names                    |
| 4     | Module variables  | Shared state/config                  |
| 5     | Classes           | Class definitions                    |
| 6     | Functions         | Standalone functions                 |
| 7     | `main()` function | Script entry point                   |
| 8     | Execution block   | `if __name__ == "__main__":`         |

## 18. Class Structure

Class members must follow this order:

| Order | Element                                     |
| ----- | ------------------------------------------- |
| 1     | Class constants (`UPPERCASE`)               |
| 2     | Class attributes                            |
| 3     | `__init__`                                  |
| 4     | Magic methods (`__repr__`, `__str__`, etc.) |
| 5     | Instance methods                            |
| 6     | Properties (`@property`)                    |
| 7     | Class methods (`@classmethod`)              |
| 8     | Static methods (`@staticmethod`)            |
| 9     | Abstract methods (`@abstractmethod`)        |

## 19. Naming Order

Within each member group, order by visibility:

```python
# Correct order
value = 1        # Public
_value = 2       # Protected
__value = 3      # Private
```

This applies to: variables, functions, methods, and attributes.

---

# Enforcement

## Mandatory Checks

All contributions must pass:

- [ ] Google-style docstrings applied
- [ ] `ruff format .` executed
- [ ] `ruff check .` shows zero errors
- [ ] Ruff config in `pyproject.toml`
- [ ] Module structure followed (Rule 17)
- [ ] Class structure followed (Rule 18)
- [ ] Naming order followed (Rule 19)
- [ ] Only `__init__.py` has module docstring

Pull requests failing these checks must be rejected.
