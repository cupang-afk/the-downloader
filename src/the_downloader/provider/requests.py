from pathlib import PurePath
from typing import override

from ..constants import DEFAULT_CA_CERT_PATH, DEFAULT_CHUNK_SIZE, DEFAULT_TIMEOUT
from ..exceptions import DownloadProviderError
from ..types.protocol import CheckCanceled, UpdateProgress
from ..utils.session import get_requests_session
from .base import BaseProvider


class RequestsError(DownloadProviderError):
    pass


class RequestsProvider(BaseProvider):
    def __init__(
        self,
        *,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        timeout: int = DEFAULT_TIMEOUT,
        ca_cert_path: str = DEFAULT_CA_CERT_PATH,
    ) -> None:
        super().__init__(
            chunk_size=chunk_size,
            timeout=timeout,
            ca_cert_path=ca_cert_path,
        )

    @override
    def download(
        self,
        url: str,
        dest: PurePath,
        headers: dict[str, str],
        check_canceled: CheckCanceled,
        update_progress: UpdateProgress,
    ) -> None:
        if check_canceled():
            return

        try:
            session = get_requests_session()
            res = session.get(
                url,
                headers=headers,
                stream=True,
                allow_redirects=True,
                timeout=self.timeout,
                verify=self.ca_cert_path,
            )
            res.raise_for_status()
            downloaded: int = 0
            total: int = int(res.headers.get("Content-Length", -1))
            with open(dest, "wb") as f:
                for chunk in res.iter_content(self.chunk_size):
                    if check_canceled():
                        return
                    if not chunk:
                        continue
                    f.write(chunk)
                    downloaded += len(chunk)
                    update_progress(downloaded, total)
        except Exception as e:
            if check_canceled():
                return
            raise RequestsError(f"Download failed: {e}") from e
