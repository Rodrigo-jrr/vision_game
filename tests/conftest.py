from __future__ import annotations

import sys
from pathlib import Path

# O pacote `vision_game` vive em src/ e nao esta instalado (sem pyproject.toml
# / pip install -e .). Garante que os testes encontrem o pacote sem depender
# do diretorio de onde o pytest e invocado.
SRC_PATH = Path(__file__).resolve().parent.parent / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))
