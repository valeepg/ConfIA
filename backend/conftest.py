"""Deja `backend/` en el path para poder importar `app.personal_data` desde los tests.

El backend no tenía tests. Este archivo es lo mínimo para que correr `pytest backend/` funcione
desde la raíz del repo, sin instalar el paquete ni tocar `requirements.txt`.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
