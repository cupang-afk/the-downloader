# the-downloader

A small Python download orchestration library with pluggable providers, task state, retry handling, and callback-based progress reporting.

## Features

- Pluggable download providers:
  - `RequestsProvider`
  - `Aria2Provider`
  - `CurlProvider`
  - `WgetProvider`
  - `PycurlProvider` when `pycurl` is installed
- `BasicDownloadManager` for queueing and running `DownloadTask` objects.
- Callback hooks for start, progress, finish, cancel, and error events.
- Retry handling with final retry status via `RetryResult`.
- Provider-owned configuration for shared provider settings such as `chunk_size`, `timeout`, and `ca_cert_path`.
- Public and private `unittest` suites.

## Requirements

- Python `>=3.14`
- `uv`
- Runtime dependencies are declared in `pyproject.toml`.

Optional provider requirements:

- `Aria2Provider` requires `aria2c` on `PATH` or an explicit binary path.
- `CurlProvider` requires `curl` on `PATH` or an explicit binary path.
- `WgetProvider` requires `wget` on `PATH` or an explicit binary path.
- `PycurlProvider` requires the optional `pycurl` dependency.

## Basic usage

```python
from the_downloader import BasicDownloadCallback, BasicDownloadManager, DownloadTask
from the_downloader.provider import RequestsProvider

manager = BasicDownloadManager(
    provider=RequestsProvider(),
    callback=BasicDownloadCallback(),
)

with manager:
    task = DownloadTask(
        "https://example.com/file.bin",
        "file.bin",
    )
    manager.add(task)
    manager.wait()
```

## Provider configuration

Provider-specific settings belong to the provider constructor.

Shared provider settings are keyword-only and readonly after construction:

```python
from the_downloader.provider import Aria2Provider

provider = Aria2Provider(
    "aria2c",
    chunk_size=1024 * 64,
    timeout=30,
    ca_cert_path="path/to/cacert.pem",
)
```

The provider-specific argument comes first, then shared `BaseProvider` settings:

```text
Aria2Provider(aria2c_bin_path, *, chunk_size, timeout, ca_cert_path)
CurlProvider(curl_bin_path, *, chunk_size, timeout, ca_cert_path)
WgetProvider(wget_bin_path, *, chunk_size, timeout, ca_cert_path)
RequestsProvider(*, chunk_size, timeout, ca_cert_path)
```

## Manager retry configuration

Retry settings belong to the manager because retries are orchestration behavior:

```python
manager = BasicDownloadManager(
    provider=RequestsProvider(),
    callback=BasicDownloadCallback(),
    max_retries=3,
    retry_delay=1,
    retry_backoff_factor=2.0,
)
```

The retry utility returns a `RetryResult` with:

```python
result.result
result.exceptions
result.succeeded
result.attempts
```

This lets the manager distinguish:

```text
failed once, later succeeded -> succeeded=True
all attempts failed          -> succeeded=False
```

## Cancellation behavior

`DownloadTask.cancel()` marks a task as canceled and sets its status to `DownloadStatus.CANCELED`.

`KeyboardInterrupt` is allowed to propagate out of providers so the manager can handle cancellation consistently. Provider cleanup should not turn expected shutdown races, such as refused aria2 RPC cleanup connections, into user-visible tracebacks.

## Tests

This project uses the standard library `unittest` runner.

Run public tests:

```sh
uv run python -m unittest discover -s tests/public -p "test_*.py"
```

Run private/internal tests:

```sh
uv run python -m unittest discover -s tests/private -p "test_*.py"
```

Run all tests:

```sh
uv run python -m unittest discover -s tests -p "test_*.py"
```

Run linting:

```sh
uv run ruff check src tests
```

Run compile check:

```sh
uv run python -m compileall src tests
```

## Test layout

```text
tests/
  public/
    test_constructors_base_provider.py
    test_constructors_manager.py
    test_constructors_providers.py
    test_constructors_task.py
    test_flows_manager_lifecycle.py
    test_flows_manager_retry.py
    test_utils_retry.py

  private/
    test_base_provider_internal.py
    test_manager_internal.py
    test_task_internal.py
```

Public tests cover user-facing behavior and API shape. Private tests cover intentionally internal implementation details that should still be watched during development and CI.

## Development

Install/sync dependencies:

```sh
uv sync
```

Run the validation suite:

```sh
uv run python -m unittest discover -s tests -p "test_*.py"
uv run ruff check src tests
uv run python -m compileall src tests
```
