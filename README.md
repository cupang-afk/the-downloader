# The Downloader

[![License](https://img.shields.io/github/license/cupang-afk/the-downloader)](https://github.com/cupang-afk/the-downloader/blob/main/LICENSE)

## Overview

The Downloader is a flexible and extensible Python library for downloading files with support for multiple backend providers. It provides a unified interface for various download methods while offering concurrent download capabilities and customizable progress tracking.

### Key Features

- **Multiple Download Providers**: Support for curl, wget, aria2, requests, and pycurl backends
- **Concurrent Downloads**: Built-in queue system for managing multiple simultaneous downloads
- **Progress Tracking**: Flexible callback system for monitoring download progress
- **Customizable**: Easy to extend with custom providers and callbacks
- **Context Manager Support**: Proper resource management with automatic cleanup
- **Cross-platform**: Works on Windows, macOS, and Linux

## Table of Contents

- [The Downloader](#the-downloader)
  - [Overview](#overview)
    - [Key Features](#key-features)
  - [Table of Contents](#table-of-contents)
  - [Installation](#installation)
    - [Installation with Additional Providers](#installation-with-additional-providers)
  - [Quick Start](#quick-start)
    - [Basic Download](#basic-download)
    - [Concurrent Downloads](#concurrent-downloads)
  - [Providers](#providers)
    - [Available Providers](#available-providers)
    - [Creating Custom Providers](#creating-custom-providers)
    - [Example: Git Clone Provider](#example-git-clone-provider)
  - [Callbacks](#callbacks)
    - [Built-in Callbacks](#built-in-callbacks)
    - [Creating Custom Callbacks](#creating-custom-callbacks)
      - [Example: Progress Bars with tqdm](#example-progress-bars-with-tqdm)
  - [Configuration Options](#configuration-options)
    - [Chunk Size Configuration](#chunk-size-configuration)
    - [Provider-Specific Configuration](#provider-specific-configuration)
      - [CurlDownloader](#curldownloader)
      - [Aria2Downloader](#aria2downloader)
      - [WgetDownloader](#wgetdownloader)
      - [PycurlDownloader](#pycurldownloader)
      - [RequestsDownloader](#requestsdownloader)
  - [Error Handling](#error-handling)
  - [Examples](#examples)
    - [Batch Download with Error Recovery](#batch-download-with-error-recovery)
  - [Contributing](#contributing)
  - [License](#license)

## Installation

Since this package is not available on PyPI, you can install directly from the GitHub repository:

```bash
# Install from GitHub using pip
pip install git+https://github.com/cupang-afk/the-downloader.git

# Or clone the repository and install locally
git clone https://github.com/cupang-afk/the-downloader.git
cd the-downloader
pip install .
```

### Installation with Additional Providers

Some providers require additional dependencies:

```bash
# For pycurl support
pip install git+https://github.com/cupang-afk/the-downloader.git[pycurl]
```

> [!NOTE]
> Make sure you have the required command-line tools (like `curl`, `wget`, `aria2c`) installed on your system if you plan to use the corresponding providers.

## Quick Start

### Basic Download

This example demonstrates how to download a single file using the CurlDownloader provider:

```python
from pathlib import Path

from the_downloader import DefaultDownloadCallback, Downloader, DownloadTask
from the_downloader.provider import CurlDownloader

# Create a downloader with a specific provider
downloader = Downloader(DefaultDownloadCallback(), CurlDownloader())

# Create a download task
task = DownloadTask(
    url="https://ash-speed.hetzner.com/100MB.bin",
    dest=Path("100MB.bin"),
)

# Download with context manager (recommended)
with downloader:
    downloader.download(task)
```

### Concurrent Downloads

The library provides a `QueueDownloader` for managing multiple concurrent downloads:

```python
import time
from pathlib import Path

from the_downloader import DefaultDownloadCallback, DownloadTask, QueueDownloader
from the_downloader.provider import CurlDownloader

# Create a queue downloader with 4 worker threads
queue_downloader = QueueDownloader(
    DefaultDownloadCallback(), CurlDownloader(), workers=4
)

tasks = [
    DownloadTask(url="https://ash-speed.hetzner.com/100MB.bin", dest=Path("file1.bin")),
    DownloadTask(url="https://ash-speed.hetzner.com/100MB.bin", dest=Path("file2.bin")),
    DownloadTask(url="https://ash-speed.hetzner.com/100MB.bin", dest=Path("file3.bin")),
]

with queue_downloader:
    # Add tasks to the queue
    queue_downloader.add_tasks(tasks)
    
    # Signal that no more tasks will be added
    queue_downloader.finish()
    
    # Wait for all tasks to complete using polling
    while not queue_downloader.is_finished:
        time.sleep(1)
    
    # Or wait for all tasks to complete by joining the queue
    queue_downloader.download_task.join()
    
    # Get all results at once when complete
    results = queue_downloader.get_all_results()
    print(f"Downloaded {len(results)} files")

# Task objects also hold their results and status
for task in tasks:
    print(f"Task {task.id}: {task.status}")
```

## Providers

The Downloader supports multiple providers for downloading files, allowing you to choose the best backend for your specific use case.

### Available Providers

| Provider             | Backend                                                | Pros                                            | Cons                     |
| -------------------- | ------------------------------------------------------ | ----------------------------------------------- | ------------------------ |
| `CurlDownloader`     | [`curl`](https://curl.se/) command                     | Fast, widely available, supports many protocols | Requires curl binary     |
| `Aria2Downloader`    | [`aria2c`](https://aria2.github.io/) command           | Multi-source downloads, segmented downloads     | Requires aria2c binary   |
| `PycurlDownloader`   | [`pycurl`](http://pycurl.io/) library                  | Native Python integration, high performance     | May require compilation  |
| `RequestsDownloader` | [`requests`](https://requests.readthedocs.io/) library | Easy to use, good for HTTP(S)                   | Limited protocol support |
| `WgetDownloader`     | [`wget`](https://www.gnu.org/software/wget/) command   | Robust, handles network issues well             | Requires wget binary     |

### Creating Custom Providers

To create a custom provider, implement the `DownloadProvider` interface:

```python
from pathlib import Path

from the_downloader import DownloadProvider, DownloadTask
from the_downloader.types import ProgressCallback


class CustomDownloader(DownloadProvider):
    """Custom download provider example."""
    
    def __init__(self, chunk_size: int = 8192):
        super().__init__(chunk_size)
        
    def download(
        self,
        task: DownloadTask,
        dest: Path,
        progress_callback: ProgressCallback,
    ) -> None:
        """
        Implement your download logic here.
        
        Args:
            task: The download task to execute
            dest: The destination path for the downloaded file
            progress_callback: Callback to report progress
        """
        # Your download implementation goes here
        # Call progress_callback periodically to report progress
        # Example:
        # with dest.open('wb') as f:
        #     # Simulate download
        #     downloaded = 0
        #     total = 1000  # Example total
        #     while downloaded < total:
        #         # Download chunk
        #         chunk_size = min(self.chunk_size, total - downloaded)
        #         # Write chunk to file
        #         # f.write(chunk_data)
        #         downloaded += chunk_size
        #         # Report progress
        #         self._handle_progress_callback(
        #             progress_callback,
        #             task,
        #             downloaded,
        #             total
        #         )
        pass


# Usage
from the_downloader import DefaultDownloadCallback, Downloader

downloader = Downloader(
    DefaultDownloadCallback(),
    CustomDownloader()
)
```

### Example: Git Clone Provider

Here's a more complex example showing how to create a provider for cloning Git repositories.

```python
import os
import re
import stat
import subprocess
from collections.abc import Iterator
from contextlib import suppress
from pathlib import Path
from types import MappingProxyType

from the_downloader import (
    DownloadProvider,
    DownloadTask,
    ProviderError,
    SubprocessDownloaderMixin,
)
from the_downloader.constants import CHUNK_SIZE
from the_downloader.types import ProgressCallback


class GitError(ProviderError):
    """Error class for Git download provider exceptions."""

    pass


class GitDownloader(DownloadProvider, SubprocessDownloaderMixin):
    """GitDownloader uses `git` to download repositories."""

    STATUS_MAP = MappingProxyType(
        {
            "enumerating objects": "Enumerating",
            "counting objects": "Counting",
            "compressing objects": "Compressing",
            "writing objects": "Writing",
            "receiving objects": "Receiving",
            "unpacking objects": "Unpacking",
            "resolving deltas": "Resolving",
            "checking connectivity": "Checking",
            "checking out files": "Checkout",
            "updating files": "Updating",
            "filtering content": "Filtering",
        }
    )

    def __init__(
        self,
        chunk_size: int = CHUNK_SIZE,
        git_bin: str | Path | None = None,
    ) -> None:
        super().__init__(chunk_size)
        self.bin = self.resolve_binary(
            git_bin or ("git" if os.name != "nt" else "git.exe")
        )
        self.cmd = [str(self.bin), "clone", "--progress"]

        # Matches progress counters like "(75/177)" in git clone output
        self.git_pattern = re.compile(r"\((\d+)/(\d+)\)")

    def _set_permission(self, dir: Path):
        if not dir.exists():
            return
        with suppress(OSError):
            dir.chmod(stat.S_IWRITE)
        for file in dir.rglob("*"):
            with suppress(OSError):
                file.chmod(stat.S_IWRITE)

    def _iter_process_output(
        self,
        process: subprocess.Popen,
        task: DownloadTask,
    ) -> Iterator[str]:
        while True:
            if process.poll() is not None:
                break
            if task.is_canceled:
                break
            if not process.stdout:
                break
            line: str = process.stdout.readline()
            if not line:
                break
            line = line.strip()

            yield line

    def _detect_git_status(self, line: str) -> str:
        for key, status in self.STATUS_MAP.items():
            if key in line:
                return status
        return "?"

    def _extract_git_speed(self, line: str) -> str:
        if "|" in line:
            return line.split("|", 1)[-1].strip()
        return ""

    def download(
        self,
        task: DownloadTask,
        dest: Path,
        progress_callback: ProgressCallback,
    ) -> None:
        with self.popen_wrapper(
            [*self.cmd, task.url, str(dest.absolute())],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=None,
            universal_newlines=True,
            bufsize=1,
        ) as p:
            try:
                for line in self._iter_process_output(p, task):
                    line_lower = line.lower()

                    if "done" in line_lower:
                        continue

                    matches = self.git_pattern.search(line)
                    if not matches:
                        continue

                    status = self._detect_git_status(line_lower)
                    speed = self._extract_git_speed(line)

                    total = int(matches.group(2))
                    downloaded = int(matches.group(1))
                    self._handle_progress_callback(
                        progress_callback,
                        task,
                        downloaded,
                        total,
                        git=True,
                        git_status=status,
                        git_speed=speed,
                    )
            except Exception as e:
                raise GitError(
                    f"Error downloading {task.url} for {task.dest.name}"
                ) from e
            finally:
                if not task.is_canceled:
                    self._set_permission(dest)
```

## Callbacks

Callbacks provide a way to track and respond to download events such as progress updates, completion, cancellation, and errors.

### Built-in Callbacks

The library includes `DefaultDownloadCallback` which provides basic console output:

```python
from the_downloader import DefaultDownloadCallback, DownloadTask
from the_downloader.provider import CurlDownloader

downloader = Downloader(DefaultDownloadCallback(), CurlDownloader())
task = DownloadTask(url="https://ash-speed.hetzner.com/100MB.bin", dest=Path("100MB.bin"))
with downloader:
    downloader.download(task)
```

### Creating Custom Callbacks

Create your own callback by implementing the `DownloadCallback` interface:

```python
from typing import Any

from the_downloader import DownloadCallback, DownloadTask

class CustomCallback(DownloadCallback):
    def __pre_start__(self) -> None:
        print("Initializing download callback")

    def __post_stop__(self) -> None:
        print("Cleaning up download callback")

    def on_start(self, task: DownloadTask) -> None:
        print(f"Starting download: {task.url}")

    def on_progress(
        self,
        task: DownloadTask,
        downloaded: int,
        total: int,
        **extra: Any,
    ) -> None:
        percentage = (downloaded / total * 100) if total > 0 else 0
        print(f"Progress: {percentage:.1f}% ({downloaded}/{total})")

    def on_complete(self, task: DownloadTask) -> None:
        print(f"Download completed: {task.dest}")

    def on_cancel(self, task: DownloadTask) -> None:
        print(f"Download cancelled: {task.url}")

    def on_error(
        self,
        task: DownloadTask,
        error: Exception,
    ) -> None:
        print(f"Download failed: {task.url} - {error}")

downloader = Downloader(CustomCallback(), CurlDownloader())
task = DownloadTask(url="https://ash-speed.hetzner.com/100MB.bin", dest=Path("100MB.bin"))
with downloader:
    downloader.download(task)
```

> [!WARNING]
> All callbacks should return 0 or `None`; otherwise, a `CallbackNonZeroReturnError` will be raised.

#### Example: Progress Bars with tqdm

Using `tqdm` to display attractive progress bars:

```python
from threading import Lock

from tqdm import tqdm

from the_downloader import DownloadCallback, DownloadTask


class TQDMProgressCallback(DownloadCallback):
    def __init__(self):
        self._bars = {}
        self._lock = Lock()

    def on_start(self, task: DownloadTask) -> None:
        with self._lock:
            bar = tqdm(
                total=task.total or 1,  # because tqdm won't update if total is 0
                desc=f"{task.progress_name}",
                leave=False,
                dynamic_ncols=True,
            )
            self._bars[task.id] = bar

    def on_progress(self, task, downloaded, total, **extra):

        bar = self._bars.get(task.id)

        if not bar:
            return

        with tqdm.get_lock():
            if total and bar.total != total:
                bar.total = total
                bar.refresh()

            delta = downloaded - bar.n
            if delta > 0:
                bar.update(delta)

    def _finish(self, task):

        with self._lock:
            bar = self._bars.pop(task.id, None)

        if bar:
            bar.close()

    def on_complete(self, task):
        self._finish(task)

    def on_error(self, task, error):
        self._finish(task)

    def on_cancel(self, task):
        self._finish(task)
```

## Configuration Options

The downloader supports various configuration options to customize behavior:

### Chunk Size Configuration

Adjust the buffer size used during downloads for optimal performance:

```python
from pathlib import Path

from the_downloader import DefaultDownloadCallback, DownloadTask, Downloader
from the_downloader.provider import CurlDownloader

# Create provider with custom chunk size (in bytes)
provider = CurlDownloader(chunk_size=16384)  # 16KB chunks

task = DownloadTask(
    url="https://example.com/file.zip",
    dest=Path("file.zip"),
)

downloader = Downloader(DefaultDownloadCallback(), provider)

with downloader:
    downloader.download(task)
```

### Provider-Specific Configuration

Some providers offer additional configuration options:

#### CurlDownloader
```python
from the_downloader.provider import CurlDownloader

# Configure custom curl binary path
provider = CurlDownloader(
    chunk_size=8192,
    curl_bin="/path/to/curl"  # Custom path to curl binary
)
```

#### Aria2Downloader
```python
from the_downloader.provider import Aria2Downloader

# Configure custom aria2c binary path and additional options
provider = Aria2Downloader(
    chunk_size=8192,
    aria2c_bin="/path/to/aria2c",  # Custom path to aria2c binary
    aria2c_token="token",          # Authentication token for Aria2 RPC
    max_download=999               # Maximum number of concurrent downloads
)
```

#### WgetDownloader
```python
from the_downloader.provider import WgetDownloader

# Configure custom wget binary path
provider = WgetDownloader(
    chunk_size=8192,
    wget_bin="/path/to/wget"  # Custom path to wget binary
)
```

#### PycurlDownloader
```python
from the_downloader.provider import PycurlDownloader

# PycurlDownloader only supports the standard chunk_size parameter
provider = PycurlDownloader(chunk_size=8192)
```

#### RequestsDownloader
```python
from the_downloader.provider import RequestsDownloader

# The RequestsDownloader only supports the standard chunk_size parameter
provider = RequestsDownloader(chunk_size=8192)
# Additional configuration would be done through custom sessions or headers in the task
```

## Error Handling

The library provides comprehensive error handling through custom exception classes:

- `ProviderError`: Base class for provider-specific errors
- `DownloadError`: General download-related errors
- `CallbackNonZeroReturnError`: Raised when callbacks return non-zero values
- Provider-specific errors (e.g., `GitError` in the example above)

```python
from the_downloader import DefaultDownloadCallback, DownloadTask, Downloader
from the_downloader.error import DownloadError
from the_downloader.provider import CurlDownloader

try:
    downloader = Downloader(DefaultDownloadCallback(), CurlDownloader())
    task = DownloadTask(url="https://invalid-url.example.com", dest=Path("test.bin"))
    
    with downloader:
        downloader.download(task)
except DownloadError as e:
    print(f"Download failed: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Examples

### Batch Download with Error Recovery

Process multiple downloads with error handling:

```python
from pathlib import Path

from the_downloader import DefaultDownloadCallback, DownloadTask, QueueDownloader
from the_downloader.provider import CurlDownloader

queue_downloader = QueueDownloader(
    DefaultDownloadCallback(), CurlDownloader(), workers=2
)

urls = [
    "https://example.com/file1.zip",
    "https://example.com/file2.zip",
    "https://example.com/file3.zip",
]

tasks = [
    DownloadTask(url=url, dest=Path(f"download_{i}.zip"))
    for i, url in enumerate(urls)
]

with queue_downloader:
    queue_downloader.add_tasks(tasks)
    queue_downloader.finish()
    
    # Wait for all tasks to complete
    while not queue_downloader.is_finished:
        import time
        time.sleep(0.1)
    
    # Get all results at once when complete
    results = queue_downloader.get_all_results()
    
    successful_downloads = 0
    failed_downloads = 0
    
    for task_id, task in results.items():
        if task.status.name == 'COMPLETED':
            successful_downloads += 1
        else:
            failed_downloads += 1
            print(f"Failed: {task.url} - Status: {task.status}")

print(f"Successfully downloaded: {successful_downloads}")
print(f"Failed downloads: {failed_downloads}")
```

## Contributing

We welcome contributions to The Downloader! Please see our [CONTRIBUTING.md](CONTRIBUTING.md) file for details on how to get started.

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.
