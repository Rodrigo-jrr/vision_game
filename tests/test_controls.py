from __future__ import annotations

from vision_game.controls import ControlManager


class FakeKeyboardController:
    """Substitui o pynput real. Espelha o contrato de `KeyboardController`:
    `press`/`release` sao idempotentes (nao emitem evento repetido se a tecla
    ja estiver no estado pedido) e so o evento efetivo e registrado em `events`.
    Isso permite verificar, sem SO nem pynput, que o ControlManager nao repete
    o "key down" a cada quadro enquanto o gesto se mantem.
    """

    def __init__(self) -> None:
        self.events: list[tuple[str, str]] = []
        self._pressed: set[str] = set()

    def press(self, key_name: str) -> None:
        if key_name in self._pressed:
            return
        self._pressed.add(key_name)
        self.events.append(("press", key_name))

    def release(self, key_name: str) -> None:
        if key_name not in self._pressed:
            return
        self._pressed.discard(key_name)
        self.events.append(("release", key_name))

    def release_all(self) -> None:
        for key_name in list(self._pressed):
            self.release(key_name)


def test_pressed_when_move_gesture_active() -> None:
    keyboard = FakeKeyboardController()
    manager = ControlManager({"move": "right"}, keyboard)

    manager.update("move")

    assert keyboard.events == [("press", "right")]


def test_key_stays_pressed_without_repeating_press_event() -> None:
    keyboard = FakeKeyboardController()
    manager = ControlManager({"move": "right"}, keyboard)

    manager.update("move")
    manager.update("move")
    manager.update("move")

    assert keyboard.events == [("press", "right")]
    assert "right" in keyboard._pressed


def test_key_released_when_gesture_becomes_neutral() -> None:
    keyboard = FakeKeyboardController()
    manager = ControlManager({"move": "right"}, keyboard)

    manager.update("move")
    manager.update(None)

    assert keyboard.events == [("press", "right"), ("release", "right")]
    assert keyboard._pressed == set()


def test_key_released_when_gesture_becomes_stop() -> None:
    keyboard = FakeKeyboardController()
    manager = ControlManager({"move": "right"}, keyboard)

    manager.update("move")
    manager.update("stop")

    assert keyboard.events == [("press", "right"), ("release", "right")]


def test_no_release_event_when_already_neutral() -> None:
    keyboard = FakeKeyboardController()
    manager = ControlManager({"move": "right"}, keyboard)

    manager.update(None)
    manager.update(None)

    assert keyboard.events == []


def test_switching_between_two_mapped_gestures_releases_the_other() -> None:
    keyboard = FakeKeyboardController()
    manager = ControlManager({"move": "right", "jump": "space"}, keyboard)

    manager.update("move")
    manager.update("jump")

    assert keyboard.events == [
        ("press", "right"),
        ("release", "right"),
        ("press", "space"),
    ]
    assert keyboard._pressed == {"space"}


def test_release_all_releases_every_pressed_key_on_shutdown() -> None:
    keyboard = FakeKeyboardController()
    manager = ControlManager({"move": "right", "jump": "space"}, keyboard)

    manager.update("move")
    manager.update("jump")
    manager.release_all()

    assert keyboard._pressed == set()
    assert ("release", "space") in keyboard.events
