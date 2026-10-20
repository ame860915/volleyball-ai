"""Task 1.4 驗收：6 支合成測試影片可產生，且規格符合預期。"""

import json
import shutil
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent / "fixtures"))
from make_fixtures import FIXTURES, make_all  # noqa: E402

pytestmark = pytest.mark.skipif(not shutil.which("ffprobe"), reason="ffprobe 不在 PATH")


def _probe(path: Path) -> dict:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json",
         "-show_format", "-show_streams", str(path)],
        capture_output=True, text=True,
    )
    return {"returncode": result.returncode, **(json.loads(result.stdout or "{}"))}


@pytest.fixture(scope="module")
def fixture_dir(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("videos")
    make_all(out, force=True)
    return out


def test_all_six_created(fixture_dir):
    assert len(FIXTURES) == 6
    for fx in FIXTURES:
        assert (fixture_dir / fx.name).exists(), fx.name
    assert (fixture_dir / "manifest.json").exists()


@pytest.mark.parametrize("fx", [f for f in FIXTURES if f.valid], ids=lambda f: f.name)
def test_valid_fixture_matches_spec(fixture_dir, fx):
    info = _probe(fixture_dir / fx.name)
    assert info["returncode"] == 0
    video = [s for s in info["streams"] if s["codec_type"] == "video"]
    audio = [s for s in info["streams"] if s["codec_type"] == "audio"]
    assert len(video) == 1
    assert bool(audio) == fx.has_audio
    assert float(info["format"]["duration"]) == pytest.approx(fx.duration_s, abs=0.1)
    if fx.fps:
        assert video[0]["r_frame_rate"] == fx.fps


def test_vfr_fixture_avg_differs_from_r(fixture_dir):
    v = [s for s in _probe(fixture_dir / "vfr_mixed.mp4")["streams"] if s["codec_type"] == "video"][0]
    r = float(Fraction(v["r_frame_rate"]))
    avg = float(Fraction(v["avg_frame_rate"]))
    assert avg == pytest.approx(20.0, abs=1.0)   # 60 格 / 3 秒
    assert abs(r - avg) > 1.0


@pytest.mark.parametrize("fx", [f for f in FIXTURES if not f.valid], ids=lambda f: f.name)
def test_invalid_fixture_rejected_by_ffprobe(fixture_dir, fx):
    info = _probe(fixture_dir / fx.name)
    assert info["returncode"] != 0 or not info.get("streams")
