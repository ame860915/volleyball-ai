"""骨架煙霧測試：確認套件可匯入、CLI 可執行、FFmpeg 可呼叫。"""

import shutil
import subprocess
import sys

import pytest

import vball
from vball.cli import main


def test_version():
    assert vball.__version__ == "0.0.1"


def test_cli_help_returns_zero(capsys):
    assert main([]) == 0
    assert "vball" in capsys.readouterr().out


def test_cli_version(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert "0.0.1" in capsys.readouterr().out


def test_module_entry():
    result = subprocess.run(
        [sys.executable, "-m", "vball.cli", "--version"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert "vball 0.0.1" in result.stdout


@pytest.mark.parametrize("tool", ["ffmpeg", "ffprobe"])
def test_ffmpeg_tools_on_path(tool):
    assert shutil.which(tool), f"{tool} 不在 PATH，請確認 volleyball 環境"
