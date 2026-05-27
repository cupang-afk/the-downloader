# The Downloader

The Downloader is a modern, modular download orchestrator for Python 3.14+, designed to provide a high-level API for managing complex download tasks. It features pluggable **Providers** (Engines) and flexible orchestration logic through **Managers**, making it suitable for everything from simple file fetching to high-performance download queuing.

## Features

- **Pluggable Providers**: Use any engine to perform the actual download. Built-in support for:
    - `aria2`
    - `curl` / `pycurl`
    - `wget`
    - `requests`
    - Custom providers via `BaseProvider`.
- **Custom Managers**: Orchestrate how downloads are processed:
    - `BasicDownloadManager`: Sequential execution.
    - `QueueDownloadManager`: Parallel execution using a thread pool.
    - Custom managers via `BaseManager`.
- **Lifecycle Callbacks**: Hooks for granular monitoring and control:
    - `on_start`, `on_progress`, `on_finish`, `on_cancel`, `on_error`.
- **Modern Standards**: Built for Python 3.14+, leveraging modern type safety and the `uv` package manager.
- **Robust Subprocess Management**: Advanced process tree cleanup using `psutil` to ensure no zombie processes remain after cancellation or errors.

## Installation

Install The Downloader using `uv`:

```bash
uv add the-downloader
```

To include optional dependencies (e.g., for `PyCurlProvider`):

```bash
uv add the-downloader[curl]
```

## Quick Start

The following example demonstrates how to use the `QueueDownloadManager` with the `RequestsProvider` and a `BasicDownloadCallback` to download multiple files in parallel.

```python
from pathlib import Path
from the_downloader.manager import QueueDownloadManager
from the_downloader.provider.requests import RequestsProvider
from the_downloader.callback import BasicDownloadCallback
from the_downloader.task import DownloadTask

# 1. Initialize the provider and callback
provider = RequestsProvider()
callback = BasicDownloadCallback()

# 2. Use a manager as a context manager
with QueueDownloadManager(provider, callback, max_workers=2) as manager:
    # 3. Create download tasks
    task1 = DownloadTask(
        url="https://example.com/file1.zip",
        dest=Path("downloads/file1.zip")
    )
    task2 = DownloadTask(
        url="https://example.com/file2.zip",
        dest=Path("downloads/file2.zip")
    )

    # 4. Add tasks to the manager
    manager.add(task1)
    manager.add(task2)

    # 5. Wait for all downloads to complete
    manager.wait()
```

## Extensibility

### Creating a Custom Provider

You can implement your own download logic by inheriting from `BaseProvider`.

```python
from pathlib import PurePath
from the_downloader.provider.base import BaseProvider
from the_downloader.types.protocol import CheckCanceled, UpdateProgress

class MyCustomProvider(BaseProvider):
    def download(
        self,
        url: str,
        dest: PurePath,
        headers: dict[str, str],
        check_canceled: CheckCanceled,
        update_progress: UpdateProgress,
    ) -> None:
        # Your custom download logic here
        # Frequently call check_canceled() to support interruption
        # Call update_progress(downloaded_bytes, total_bytes) to report progress
        pass
```

### Creating a Custom Manager

Inherit from `BaseManager` to define custom orchestration logic.

```python
from the_downloader.manager import BaseManager
from the_downloader.task import DownloadTask

class MySequentialManager(BaseManager):
    def start(self):
        print("Manager started")

    def stop(self):
        print("Manager stopped")

    def cancel(self):
        # Logic to cancel all active tasks
        pass

    def add(self, task: DownloadTask):
        # Execute download immediately or queue it
        self._handle_download(task)

    def wait(self):
        # Wait for completion
        pass
```

### Creating a Custom Callback

You can monitor download events by inheriting from `BaseCallback`.

```python
from typing import Any
from the_downloader.callback import BaseCallback
from the_downloader.task import DownloadTask
from the_downloader.types.alias import ExcInfo

class MyCustomCallback(BaseCallback):
    def on_start(self, task: DownloadTask) -> None:
        print(f"Starting: {task.progress_name}")

    def on_progress(
        self,
        task: DownloadTask,
        downloaded: int,
        total: int,
        **optional_data: Any
    ) -> None:
        # Update your UI or custom logger here
        pass

    def on_finish(self, task: DownloadTask) -> None: ...
    def on_cancel(self, task: DownloadTask) -> None: ...
    def on_error(self, task: DownloadTask, exc_info: ExcInfo) -> None: ...
```

## Roadmap

- [ ] **AsyncDownloadManager**: Native `asyncio` support for high-concurrency metadata fetching and download orchestration.
