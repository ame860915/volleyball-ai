"""共用 pytest fixture。"""

import os
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent / "fixtures"))
from make_fixtures import make_all  # noqa: E402


@pytest.fixture(scope="session")
def videos(tmp_path_factory) -> Path:
    """產生 6 支合成測試影片到暫存資料夾，整個測試期間共用。"""
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg 不在 PATH")
    out = tmp_path_factory.mktemp("videos")
    make_all(out, force=True)
    return out


@pytest.fixture
def real_video() -> Path:
    """本機授權影片。設定環境變數 VBALL_REAL_VIDEO 指向影片才會執行。"""
    value = os.environ.get("VBALL_REAL_VIDEO")
    if not value or not Path(value).is_file():
        pytest.skip("未設定 VBALL_REAL_VIDEO，略過真實影片測試")
    return Path(value)
