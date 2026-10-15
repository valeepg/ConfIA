"""What the image must carry for the documented container command to work.

Measured: the first containerised run ingested the 2,459 prospects and then died with a
bare ENOENT on `/app/templates/outreach-oaas.md`, because the Containerfile copied
`scraper/` and forgot `templates/`. The command the recipe documents has to work, so the
coupling between the image and the paths the application reads at run time is asserted
here instead of being discovered in production.
"""

from pathlib import Path

import pytest

from scraper.config import OUTREACH_TEMPLATE
from scraper.copilot import load_template

ROOT = Path(__file__).resolve().parents[1]


def test_the_containerfile_copies_every_path_read_at_runtime():
    containerfile = (ROOT / "Containerfile").read_text(encoding="utf-8").lower()
    for folder in ("scraper", "templates"):
        assert f"copy {folder}" in containerfile, f"la imagen no copia {folder}/"


def test_the_dockerignore_keeps_credentials_out_of_the_image():
    ignored = (ROOT / ".dockerignore").read_text(encoding="utf-8")
    assert ".env" in ignored


def test_the_default_template_is_in_the_repository():
    assert OUTREACH_TEMPLATE.exists()


def test_load_template_says_what_to_do_when_the_file_is_missing(tmp_path):
    """A bare ENOENT sent nobody anywhere: name the folder and the option."""
    with pytest.raises(FileNotFoundError, match="templates"):
        load_template(tmp_path / "no-existe.md")
