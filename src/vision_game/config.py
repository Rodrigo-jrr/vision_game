from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from vision_game.keyboard import KeyboardError, resolve_key, resolve_special_key


class ConfigError(Exception):
    """Erro de configuracao; identifica o campo invalido (RF-10, sem defaults silenciosos)."""

    def __init__(self, field: str, message: str) -> None:
        super().__init__(f"Campo de configuracao invalido '{field}': {message}")
        self.field = field


@dataclass(frozen=True)
class AppConfig:
    camera_index: int
    min_confidence: float
    model_path: Path
    exit_key: str
    mirror_horizontal: bool
    gestures: dict[str, str]


def _require(data: dict[str, Any], field: str) -> Any:
    if field not in data:
        raise ConfigError(field, "campo obrigatorio ausente")
    return data[field]


def load_config(path: str | Path) -> AppConfig:
    config_path = Path(path)
    try:
        raw_text = config_path.read_text(encoding="utf-8")
    except OSError as error:
        raise ConfigError("__file__", f"nao foi possivel ler {config_path}: {error}") from error

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as error:
        raise ConfigError("__file__", f"JSON invalido em {config_path}: {error}") from error

    if not isinstance(data, dict):
        raise ConfigError("__root__", "o arquivo de configuracao deve conter um objeto JSON")

    camera_index = _require(data, "camera_index")
    if not isinstance(camera_index, int) or isinstance(camera_index, bool) or camera_index < 0:
        raise ConfigError("camera_index", "deve ser um inteiro maior ou igual a 0")

    min_confidence = _require(data, "min_confidence")
    if not isinstance(min_confidence, (int, float)) or isinstance(min_confidence, bool):
        raise ConfigError("min_confidence", "deve ser um numero")
    min_confidence = float(min_confidence)
    if not 0.0 <= min_confidence <= 1.0:
        raise ConfigError("min_confidence", "deve estar entre 0.0 e 1.0")

    model_path_raw = _require(data, "model_path")
    if not isinstance(model_path_raw, str) or not model_path_raw:
        raise ConfigError("model_path", "deve ser uma string nao vazia")

    exit_key = _require(data, "exit_key")
    if not isinstance(exit_key, str) or not exit_key:
        raise ConfigError("exit_key", "deve ser uma string nao vazia")
    try:
        resolve_special_key(exit_key)
    except KeyboardError as error:
        raise ConfigError("exit_key", str(error)) from error

    mirror_horizontal = _require(data, "mirror_horizontal")
    if not isinstance(mirror_horizontal, bool):
        raise ConfigError("mirror_horizontal", "deve ser um booleano (true ou false)")

    gestures = _require(data, "gestures")
    if not isinstance(gestures, dict) or not gestures:
        raise ConfigError("gestures", "deve ser um objeto com ao menos um gesto mapeado")
    for gesture_name, key_name in gestures.items():
        if not isinstance(gesture_name, str) or not gesture_name:
            raise ConfigError("gestures", f"nome de gesto invalido: {gesture_name!r}")
        if not isinstance(key_name, str) or not key_name:
            raise ConfigError(f"gestures.{gesture_name}", "deve ser uma string nao vazia")
        try:
            resolve_key(key_name)
        except KeyboardError as error:
            raise ConfigError(f"gestures.{gesture_name}", str(error)) from error

    return AppConfig(
        camera_index=camera_index,
        min_confidence=min_confidence,
        model_path=Path(model_path_raw),
        exit_key=exit_key,
        mirror_horizontal=mirror_horizontal,
        gestures=dict(gestures),
    )
