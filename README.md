# The Downloader

A Python library for orchestrating downloads. Takes a URL and a destination,
and handles the download — with support for multiple engines, parallel
downloads, progress tracking, and cleanup.

## Features

- **Pluggable download engines**. Built-in support for:
  - `aria2`
  - `curl` / `pycurl`
  - `wget`
  - `requests`
  - Custom providers via `BaseProvider`.
- **Managers** to control how downloads run:
  - `BasicDownloadManager`: one at a time.
  - `QueueDownloadManager`: multiple downloads in parallel using a thread pool.
  - Custom managers via `BaseManager`.
- **Callbacks** to hook into the download lifecycle:
  - `on_start`, `on_progress`, `on_finish`, `on_cancel`, `on_error`.
- **Process cleanup** — uses `psutil` to clean up subprocess trees on cancel
  or error, so no zombie processes are left behind.

## Install

```bash
uv add the-downloader
```

For `PyCurlProvider`:

```bash
uv add the-downloader[pycurl]
```

## Quick example

Downloads two files in parallel:

```python
from pathlib import Path
from the_downloader.manager import QueueDownloadManager
from the_downloader.provider.requests import RequestsProvider
from the_downloader.callback import BasicDownloadCallback
from the_downloader.task import DownloadTask

provider = RequestsProvider()
callback = BasicDownloadCallback()

with QueueDownloadManager(provider, callback, max_workers=2) as manager:
    task1 = DownloadTask(
        url="https://example.com/file1.zip",
        dest=Path("downloads/file1.zip")
    )
    task2 = DownloadTask(
        url="https://example.com/file2.zip",
        dest=Path("downloads/file2.zip")
    )

    manager.add(task1)
    manager.add(task2)
    manager.wait()
```

## Going further

### Custom provider

```python
from pathlib import PurePath
from the_downloader.provider.base import BaseProvider
from the_downloader.types.protocol import CheckCanceled, UpdateProgress

class MyProvider(BaseProvider):
    def download(
        self,
        url: str,
        dest: PurePath,
        headers: dict[str, str],
        check_canceled: CheckCanceled,
        update_progress: UpdateProgress,
    ) -> None:
        # Call check_canceled() to support cancellation; best practice is to call it in a loop
        # Call update_progress(downloaded, total) to report progress
        pass
```

### Custom manager

```python
from the_downloader.manager import BaseManager
from the_downloader.task import DownloadTask

class MyManager(BaseManager):
    def start(self): ...
    def stop(self): ...
    def cancel(self): ...
    def add(self, task: DownloadTask): ...
    def wait(self): ...
```

### Custom callback

```python
from typing import Any
from the_downloader.callback import BaseCallback
from the_downloader.task import DownloadTask
from the_downloader.types.alias import ExcInfo

class MyCallback(BaseCallback):
    def on_start(self, task: DownloadTask) -> None: ...

    def on_progress(
        self,
        task: DownloadTask,
        downloaded: int,
        total: int,
        **optional_data: Any
    ) -> None: ...

    def on_finish(self, task: DownloadTask) -> None: ...
    def on_cancel(self, task: DownloadTask) -> None: ...
    def on_error(self, task: DownloadTask, exc_info: ExcInfo) -> None: ...
```

## Roadmap

- [ ] **AsyncDownloadManager**: asyncio support for high-concurrency metadata
  fetching and download orchestration.
