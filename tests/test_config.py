from __future__ import annotations

import json
from pathlib import Path

import pytest

from vision_game.config import ConfigError, load_config

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXAMPLE_CONFIG_PATH = PROJECT_ROOT / "config.example.json"

VALID_CONFIG = {
    "camera_index": 0,
    "min_confidence": 0.80,
    "model_path": "src/image/gesture_model.npz",
    "exit_key": "f12",
    "gestures": {"move": "right"},
}


def _write_config(tmp_path: Path, data: dict) -> Path:
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(data), encoding="utf-8")
    return config_path


def test_loads_the_versioned_example_config_successfully() -> None:
    config = load_config(EXAMPLE_CONFIG_PATH)

    assert config.camera_index == 0
    assert config.min_confidence == pytest.approx(0.80)
    assert config.model_path == Path("src/image/gesture_model.npz")
    assert config.exit_key == "f12"
    # RF-04 completo: 5 comandos ativos (esquerda/direita/cima/baixo/acao).
    assert config.gestures == {
        "esquerda": "left",
        "direita": "right",
        "cima": "up",
        "baixo": "down",
        "acao": "z",
    }


def test_loads_a_valid_config_built_from_scratch(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path, VALID_CONFIG)

    config = load_config(config_path)

    assert config.camera_index == 0
    assert config.min_confidence == pytest.approx(0.80)
    assert config.model_path == Path("src/image/gesture_model.npz")
    assert config.exit_key == "f12"
    assert config.gestures == {"move": "right"}


def test_missing_file_raises_clear_error(tmp_path: Path) -> None:
    with pytest.raises(ConfigError) as excinfo:
        load_config(tmp_path / "does_not_exist.json")

    assert excinfo.value.field == "__file__"


def test_invalid_json_raises_clear_error(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text("{ not valid json", encoding="utf-8")

    with pytest.raises(ConfigError) as excinfo:
        load_config(config_path)

    assert excinfo.value.field == "__file__"


def test_json_array_instead_of_object_raises_clear_error(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text("[1, 2, 3]", encoding="utf-8")

    with pytest.raises(ConfigError) as excinfo:
        load_config(config_path)

    assert excinfo.value.field == "__root__"


@pytest.mark.parametrize(
    "field",
    ["camera_index", "min_confidence", "model_path", "exit_key", "gestures"],
)
def test_missing_required_field_raises_error_naming_that_field(tmp_path: Path, field: str) -> None:
    data = dict(VALID_CONFIG)
    del data[field]
    config_path = _write_config(tmp_path, data)

    with pytest.raises(ConfigError) as excinfo:
        load_config(config_path)

    assert excinfo.value.field == field


@pytest.mark.parametrize(
    "bad_value",
    ["0", -1, True, 1.5],
    ids=["string", "negative", "boolean", "float"],
)
def test_camera_index_with_wrong_type_or_value_raises_error(tmp_path: Path, bad_value) -> None:
    data = dict(VALID_CONFIG)
    data["camera_index"] = bad_value
    config_path = _write_config(tmp_path, data)

    with pytest.raises(ConfigError) as excinfo:
        load_config(config_path)

    assert excinfo.value.field == "camera_index"


@pytest.mark.parametrize(
    "bad_value",
    ["0.8", True, -0.1, 1.1],
    ids=["string", "boolean", "below_range", "above_range"],
)
def test_min_confidence_with_wrong_type_or_out_of_range_raises_error(tmp_path: Path, bad_value) -> None:
    data = dict(VALID_CONFIG)
    data["min_confidence"] = bad_value
    config_path = _write_config(tmp_path, data)

    with pytest.raises(ConfigError) as excinfo:
        load_config(config_path)

    assert excinfo.value.field == "min_confidence"


@pytest.mark.parametrize("bad_value", [123, "", None], ids=["int", "empty_string", "null"])
def test_model_path_with_wrong_type_or_empty_raises_error(tmp_path: Path, bad_value) -> None:
    data = dict(VALID_CONFIG)
    data["model_path"] = bad_value
    config_path = _write_config(tmp_path, data)

    with pytest.raises(ConfigError) as excinfo:
        load_config(config_path)

    assert excinfo.value.field == "model_path"


@pytest.mark.parametrize(
    "bad_value", ["", "not_a_real_key", 123], ids=["empty_string", "unknown_key", "wrong_type"]
)
def test_exit_key_with_invalid_value_raises_error(tmp_path: Path, bad_value) -> None:
    data = dict(VALID_CONFIG)
    data["exit_key"] = bad_value
    config_path = _write_config(tmp_path, data)

    with pytest.raises(ConfigError) as excinfo:
        load_config(config_path)

    assert excinfo.value.field == "exit_key"


def test_exit_key_must_be_a_special_key_not_a_single_character(tmp_path: Path) -> None:
    # "a" e uma tecla valida para `gestures` (letra unica), mas nao e uma
    # tecla especial valida para exit_key (ex: f12) -- resolve_special_key
    # deve rejeitar e o erro deve apontar para "exit_key".
    data = dict(VALID_CONFIG)
    data["exit_key"] = "a"
    config_path = _write_config(tmp_path, data)

    with pytest.raises(ConfigError) as excinfo:
        load_config(config_path)

    assert excinfo.value.field == "exit_key"


@pytest.mark.parametrize("bad_value", [[], "move", 123], ids=["list", "string", "int"])
def test_gestures_with_wrong_type_raises_error(tmp_path: Path, bad_value) -> None:
    data = dict(VALID_CONFIG)
    data["gestures"] = bad_value
    config_path = _write_config(tmp_path, data)

    with pytest.raises(ConfigError) as excinfo:
        load_config(config_path)

    assert excinfo.value.field == "gestures"


def test_empty_gestures_mapping_raises_error(tmp_path: Path) -> None:
    data = dict(VALID_CONFIG)
    data["gestures"] = {}
    config_path = _write_config(tmp_path, data)

    with pytest.raises(ConfigError) as excinfo:
        load_config(config_path)

    assert excinfo.value.field == "gestures"


def test_gesture_mapped_to_empty_key_name_raises_error_naming_that_gesture(tmp_path: Path) -> None:
    data = dict(VALID_CONFIG)
    data["gestures"] = {"move": ""}
    config_path = _write_config(tmp_path, data)

    with pytest.raises(ConfigError) as excinfo:
        load_config(config_path)

    assert excinfo.value.field == "gestures.move"


def test_gesture_mapped_to_unknown_key_raises_error_naming_that_gesture(tmp_path: Path) -> None:
    data = dict(VALID_CONFIG)
    data["gestures"] = {"move": "not_a_real_key"}
    config_path = _write_config(tmp_path, data)

    with pytest.raises(ConfigError) as excinfo:
        load_config(config_path)

    assert excinfo.value.field == "gestures.move"


def test_gesture_mapped_to_non_string_key_raises_error_naming_that_gesture(tmp_path: Path) -> None:
    data = dict(VALID_CONFIG)
    data["gestures"] = {"move": 42}
    config_path = _write_config(tmp_path, data)

    with pytest.raises(ConfigError) as excinfo:
        load_config(config_path)

    assert excinfo.value.field == "gestures.move"
