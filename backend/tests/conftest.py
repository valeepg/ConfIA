import os
import shutil
import sys
import tempfile
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

# Almacenamiento aislado para las pruebas; debe fijarse antes de importar app.storage.
_TEST_STORAGE = Path(tempfile.mkdtemp(prefix="confia_tests_"))
os.environ["CONFIA_STORAGE_DIR"] = str(_TEST_STORAGE)

import firebase_admin  # noqa: E402

# Evita inicializar Firebase con credenciales reales al importar app.main.
firebase_admin._apps["[DEFAULT]"] = object()

import pytest  # noqa: E402

from app import storage  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def storage_with_template():
    storage.ensure_storage_dirs()
    templates = BACKEND_DIR / "app" / "storage" / "input" / "templates"
    shutil.copy(templates / "dossier_template.md", storage.DOSSIER_TEMPLATE_PATH)
    shutil.copy(templates / "propuesta_template.md", storage.PROPOSAL_TEMPLATE_PATH)
    yield
    shutil.rmtree(_TEST_STORAGE, ignore_errors=True)
