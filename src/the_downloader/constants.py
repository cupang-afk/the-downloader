from collections.abc import Mapping
from pathlib import Path
from types import MappingProxyType

import certifi

# Module constants
CHUNK_SIZE: int = 8192  # Default chunk size for reading download data
DEFAULT_HEADERS: Mapping[str, str] = MappingProxyType({"User-Agent": "Downloader/1.0"})
CA_CERT_PATH: str = str(Path(certifi.where()).absolute())
TMP_FILE_PREFIX: str = "dl_temp_"
