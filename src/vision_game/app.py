from __future__ import annotations

import sys
from pathlib import Path

from pynput import keyboard as pynput_keyboard

from vision_game.camera import Camera, CameraError
from vision_game.config import AppConfig, ConfigError, load_config
from vision_game.controls import ControlManager
from vision_game.gestures import GestureClassifier
from vision_game.hand_tracking import HandTracker
from vision_game.keyboard import KeyboardController, resolve_special_key
from vision_game.preview import Preview

_DEFAULT_CONFIG_FILENAME = "config.json"
_EXAMPLE_CONFIG_FILENAME = "config.example.json"


def resolve_config_path() -> Path:
    default_path = Path(_DEFAULT_CONFIG_FILENAME)
    if default_path.is_file():
        return default_path
    example_path = Path(_EXAMPLE_CONFIG_FILENAME)
    if example_path.is_file():
        return example_path
    raise ConfigError(
        "__file__",
        f"nenhum arquivo de configuracao encontrado ({_DEFAULT_CONFIG_FILENAME} ou {_EXAMPLE_CONFIG_FILENAME})",
    )


def _status_text(hand_detected: bool, gesture: str | None) -> str:
    if not hand_detected:
        return "Sem mao detectada - tecla solta"
    if gesture is not None:
        return f"Comando: {gesture} - tecla mantida"
    return "Gesto neutro ou incerto - tecla solta"


def run(config: AppConfig) -> None:
    gesture_classifier = GestureClassifier(config.model_path)
    keyboard_controller = KeyboardController()
    control_manager = ControlManager(config.gestures, keyboard_controller)
    preview = Preview()

    exit_key = resolve_special_key(config.exit_key)
    exit_requested_by_hotkey = {"flag": False}

    def _on_press(key):
        if key == exit_key:
            exit_requested_by_hotkey["flag"] = True
            return False
        return None

    listener = pynput_keyboard.Listener(on_press=_on_press)
    listener.start()

    camera = Camera(config.camera_index)
    hand_tracker = HandTracker()

    try:
        while not exit_requested_by_hotkey["flag"]:
            frame = camera.read()
            hand_landmarks = hand_tracker.process(frame)

            gesture = None
            if hand_landmarks is not None:
                hand_tracker.draw_landmarks(frame, hand_landmarks)
                gesture = gesture_classifier.classify(
                    hand_landmarks,
                    config.min_confidence,
                    mirror_horizontal=config.mirror_horizontal,
                )

            control_manager.update(gesture)

            status = _status_text(hand_landmarks is not None, gesture)
            preview.render(frame, status, active=gesture is not None)

            if preview.exit_requested():
                break
    finally:
        control_manager.release_all()
        camera.release()
        hand_tracker.close()
        preview.close()
        listener.stop()
        if listener.is_alive():
            listener.join(timeout=1)


def main() -> int:
    try:
        config_path = resolve_config_path()
        config = load_config(config_path)
    except ConfigError as error:
        print(f"Erro de configuracao: {error}", file=sys.stderr)
        return 1

    try:
        run(config)
    except CameraError as error:
        print(f"Erro de camera: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Execucao interrompida pelo usuario.")
        return 0

    print("Controle encerrado; tecla e camera liberadas.")
    return 0
