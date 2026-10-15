from __future__ import annotations

import cv2

_WINDOW_NAME = "Controle por gestos | F12 ou q para sair"
_STATUS_POSITION = (20, 40)
_ACTIVE_COLOR = (0, 220, 0)
_INACTIVE_COLOR = (0, 0, 255)
_EXIT_KEYS = (ord("q"), 27)


class Preview:
    """Mostra o quadro e o estado do gesto/comando. Nao controla camera, classificador ou teclado."""

    def render(self, frame, status_text: str, active: bool) -> None:
        color = _ACTIVE_COLOR if active else _INACTIVE_COLOR
        cv2.putText(frame, status_text, _STATUS_POSITION, cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
        cv2.imshow(_WINDOW_NAME, frame)

    def exit_requested(self) -> bool:
        return cv2.waitKey(1) & 0xFF in _EXIT_KEYS

    def close(self) -> None:
        cv2.destroyAllWindows()
