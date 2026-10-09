"""Check photo persistence and rejection of unsafe upload/path inputs."""

import io
import re

import pytest
from PIL import Image

import app
import catalog


@pytest.fixture(autouse=True)
def isolated_paths(tmp_path, monkeypatch):
    monkeypatch.setenv("RACKET_GO_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setattr(app, "ROOT", tmp_path / "project")


def test_png_upload_becomes_a_readable_jpeg_in_persistent_storage():
    uploaded = io.BytesIO()
    Image.new("RGBA", (2, 2), (45, 130, 70, 255)).save(uploaded, "PNG")

    relative_path = app.save_upload(uploaded)
    assert re.fullmatch(r"uploads/[0-9a-f]{32}\.jpg", relative_path)
    stored = catalog.get_data_dir() / relative_path
    assert app.image_path(relative_path) == stored
    with Image.open(stored) as image:
        assert image.format == "JPEG"
        assert image.mode == "RGB"
        assert image.size == (2, 2)
        image.load()
    assert list((catalog.get_data_dir() / "uploads").iterdir()) == [stored]


def test_invalid_image_bytes_are_rejected_without_persisting_a_file():
    with pytest.raises(ValueError, match="image JPEG, PNG ou WebP valide"):
        app.save_upload(io.BytesIO(b"This is not an image."))
    assert not catalog.get_data_dir().exists()


def test_upload_above_eight_megabytes_is_rejected_before_decoding():
    with pytest.raises(ValueError, match="moins de 8 Mo"):
        app.save_upload(io.BytesIO(b"x" * (8 * 1024 * 1024 + 1)))
    assert not catalog.get_data_dir().exists()


def test_image_paths_cannot_follow_symlinks_outside_their_allowed_directory(tmp_path):
    outside = tmp_path / "private.jpg"
    Image.new("RGB", (2, 2), "white").save(outside, "JPEG")

    for relative_directory, directory in (
        ("assets", app.ROOT / "assets"),
        ("uploads", catalog.get_data_dir() / "uploads"),
    ):
        directory.mkdir(parents=True)
        escaped_image = directory / "external.jpg"
        escaped_image.symlink_to(outside)
        assert app.image_path(f"{relative_directory}/external.jpg") is None

        safe_image = directory / "local.jpg"
        safe_image.write_bytes(outside.read_bytes())
        assert app.image_path(f"{relative_directory}/local.jpg") == safe_image

    assert app.image_path(str(outside)) is None
    assert app.image_path("uploads/../private.jpg") is None
    assert app.image_path("uploads/missing.jpg") is None
