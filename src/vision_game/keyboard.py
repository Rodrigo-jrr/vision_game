from __future__ import annotations

from pynput import keyboard as pynput_keyboard


class KeyboardError(Exception):
    """Erro ao resolver ou operar uma tecla via pynput."""


def resolve_key(key_name: str):
    if not isinstance(key_name, str) or not key_name:
        raise KeyboardError(f"nome de tecla invalido: {key_name!r}")
    special_key = getattr(pynput_keyboard.Key, key_name.lower(), None)
    if isinstance(special_key, pynput_keyboard.Key):
        return special_key
    if len(key_name) == 1:
        return key_name
    raise KeyboardError(f"tecla desconhecida: {key_name!r}")


def resolve_special_key(key_name: str) -> pynput_keyboard.Key:
    resolved = resolve_key(key_name)
    if not isinstance(resolved, pynput_keyboard.Key):
        raise KeyboardError(f"tecla especial desconhecida: {key_name!r}")
    return resolved


class KeyboardController:
    """Encapsula o `pynput.keyboard.Controller`, isolando a dependencia de SO."""

    def __init__(self) -> None:
        self._controller = pynput_keyboard.Controller()
        self._pressed_keys: set[str] = set()

    def press(self, key_name: str) -> None:
        if key_name in self._pressed_keys:
            return
        self._controller.press(resolve_key(key_name))
        self._pressed_keys.add(key_name)

    def release(self, key_name: str) -> None:
        if key_name not in self._pressed_keys:
            return
        self._controller.release(resolve_key(key_name))
        self._pressed_keys.discard(key_name)

    def release_all(self) -> None:
        for key_name in list(self._pressed_keys):
            self.release(key_name)
