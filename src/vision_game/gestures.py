from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

# Rotulos do dataset de treino (pastas em src/image/). O nome da pasta e o
# significado do gesto estao invertidos por historico do notebook original:
# fotos em "move" mostram a mao fechada (acao "stop"); fotos em "stop"
# mostram o indicador estendido (acao "move"). Mantido igual ao notebook.
CLASSES = ("move", "stop")

GESTURE_MOVE = "move"
GESTURE_STOP = "stop"

_RULE_BASED_CONFIDENCE = 0.96


def classify_hand_gesture(hand_landmarks) -> str | None:
    points = np.array(
        [[point.x, point.y, point.z] for point in hand_landmarks.landmark],
        dtype=np.float32,
    )
    if points.shape[0] != 21:
        return None

    fingertip_ids = (4, 8, 12, 16, 20)
    fingertip_reach = [
        float(np.linalg.norm(points[tip_id, :2] - points[0, :2])) for tip_id in fingertip_ids
    ]

    if max(fingertip_reach) < 0.21 and np.median(fingertip_reach) < 0.16:
        return "mao_fechada"

    index_is_longest = (
        fingertip_reach[1] > 0.18
        and fingertip_reach[1] >= fingertip_reach[2] + 0.03
        and fingertip_reach[1] >= fingertip_reach[3] + 0.03
        and fingertip_reach[1] >= fingertip_reach[4] + 0.03
    )
    if index_is_longest:
        return "indicador"

    return None


def extract_features(hand_landmarks) -> np.ndarray | None:
    points = np.array(
        [[point.x, point.y, point.z] for point in hand_landmarks.landmark],
        dtype=np.float32,
    )
    wrist = points[0].copy()
    palm_scale = float(np.linalg.norm(points[9, :2] - wrist[:2]))
    if palm_scale < 1e-6:
        return None

    points -= wrist
    points /= palm_scale
    return np.concatenate((points.reshape(-1), wrist[:2], [palm_scale])).astype(np.float32)


def predict_knn(
    sample: np.ndarray,
    reference_features: np.ndarray,
    reference_labels: np.ndarray,
    k: int,
) -> tuple[int, float]:
    distances = np.linalg.norm(reference_features - sample, axis=1)
    nearest_indices = np.argsort(distances)[: min(k, len(reference_labels))]
    votes = np.bincount(reference_labels[nearest_indices], minlength=len(CLASSES))
    predicted_label = int(np.argmax(votes))
    confidence = float(votes[predicted_label] / len(nearest_indices))
    return predicted_label, confidence


@dataclass(frozen=True)
class _Model:
    features: np.ndarray
    labels: np.ndarray
    class_names: tuple[str, ...]
    k: int


def _load_model(model_path: Path) -> _Model:
    if not model_path.is_file():
        raise FileNotFoundError(f"Modelo de gestos nao encontrado: {model_path}")

    with np.load(model_path, allow_pickle=False) as saved_model:
        features = saved_model["features"].astype(np.float32)
        labels = saved_model["labels"].astype(np.int32)
        class_names = tuple(str(name) for name in saved_model["classes"].tolist())
        k = int(saved_model["k"])

    if "move" not in class_names or "stop" not in class_names:
        raise ValueError("O modelo precisa conter as classes 'move' e 'stop'.")

    return _Model(features=features, labels=labels, class_names=class_names, k=k)


class GestureClassifier:
    """Interpreta landmarks, aplica limiar de confianca e retorna um gesto conhecido ou neutro (None)."""

    def __init__(self, model_path: Path) -> None:
        self._model = _load_model(Path(model_path))

    def classify(self, hand_landmarks, min_confidence: float) -> str | None:
        rule_based_gesture = classify_hand_gesture(hand_landmarks)
        if rule_based_gesture == "mao_fechada":
            detected_class, confidence = GESTURE_STOP, _RULE_BASED_CONFIDENCE
        elif rule_based_gesture == "indicador":
            detected_class, confidence = GESTURE_MOVE, _RULE_BASED_CONFIDENCE
        else:
            detected_class, confidence = None, 0.0
            feature = extract_features(hand_landmarks)
            if feature is not None:
                class_id, confidence = predict_knn(
                    feature,
                    self._model.features,
                    self._model.labels,
                    k=self._model.k,
                )
                detected_class = (
                    GESTURE_STOP if self._model.class_names[class_id] == "move" else GESTURE_MOVE
                )

        if detected_class is None or confidence < min_confidence:
            return None
        return detected_class
