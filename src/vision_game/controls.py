from __future__ import annotations

from vision_game.keyboard import KeyboardController


class ControlManager:
    """Converte gesto -> comando -> tecla configurada e gerencia transicoes pressionado/liberado."""

    def __init__(self, gesture_key_map: dict[str, str], keyboard_controller: KeyboardController) -> None:
        self._gesture_key_map = dict(gesture_key_map)
        self._keyboard = keyboard_controller

    def update(self, gesture: str | None) -> None:
        for mapped_gesture, key_name in self._gesture_key_map.items():
            if gesture == mapped_gesture:
                self._keyboard.press(key_name)
            else:
                self._keyboard.release(key_name)

    def release_all(self) -> None:
        self._keyboard.release_all()
