import unittest
from pathlib import PurePath
from typing import override

from src.the_downloader.provider import BaseProvider
from src.the_downloader.types.protocol import CheckCanceled, UpdateProgress


class ExampleProvider(BaseProvider):
    @override
    def download(
        self,
        url: str,
        dest: PurePath,
        headers: dict[str, str],
        check_canceled: CheckCanceled,
        update_progress: UpdateProgress,
    ) -> None:
        return None


class BaseProviderInternalTests(unittest.TestCase):
    def test_base_provider_stores_shared_settings_in_private_attributes(self) -> None:
        provider = ExampleProvider(
            chunk_size=123,
            timeout=45,
            ca_cert_path="cert.pem",
        )

        self.assertEqual(provider._chunk_size, 123)  # pyright: ignore[reportPrivateUsage]
        self.assertEqual(provider._timeout, 45)  # pyright: ignore[reportPrivateUsage]
        self.assertEqual(provider._ca_cert_path, "cert.pem")  # pyright: ignore[reportPrivateUsage]


if __name__ == "__main__":
    unittest.main()
