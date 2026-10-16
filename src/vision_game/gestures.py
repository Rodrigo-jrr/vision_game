from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np

# Pastas do dataset de treino em src/image/ (nomes historicos, nao
# renomeados). Fonte unica da verdade: pasta -> gesto semantico (RF-04).
# "move" (mao fechada) e "stop" (dedo indicador) sao os nomes originais do
# notebook; o significado real de cada um e dado por este mapeamento, nao
# pelo nome da pasta.
#
# As 4 direcoes (esquerda/cima/baixo/direita) nao sao mais 4 poses fixas
# treinadas (as pastas esquerda/, cima/, baixo/ continuam no disco mas nao
# entram mais no treino): a pose "stop" (indicador esticado) e unica, e a
# direcao e calculada pelo angulo do dedo apontando (ver `_pointing_direction`).
GESTURE_FOLDERS = ("move", "stop", "acao")

# "stop" nao aparece aqui de proposito: seu gesto final nao e fixo, depende
# do angulo calculado por `_pointing_direction` (ver `GestureClassifier.classify`).
_FOLDER_TO_GESTURE: dict[str, str | None] = {
    "move": None,  # mao fechada -> estado neutro, libera a tecla
    "acao": "acao",  # sinal de paz (indicador + medio) -> tecla Z
}

# Setores de 90 graus, centrados em 0/90/180/270, cobrindo os 360 graus sem
# zona morta. `_direction_from_angle` usa `round(angulo / 90) % 4` para achar
# o setor mais proximo; esta tupla da o gesto de cada setor, na mesma ordem.
#
# "direita" e "esquerda" trocados de posicao (setor 0 -> esquerda, setor 2 ->
# direita) porque `camera.py` nao espelha o frame da webcam (sem cv2.flip).
# Numa camera de frente para o usuario sem espelhamento, a imagem crua e
# como se as duas pessoas estivessem de frente uma pra outra: a direita
# fisica do usuario cai do lado esquerdo da imagem (eixo X maior), e
# vice-versa. So o eixo horizontal e afetado -- cima/baixo (setores 1 e 3)
# ficam sem alteracao.
_DIRECTION_BY_SECTOR = ("esquerda", "cima", "direita", "baixo")

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


def _direction_from_angle(angle_degrees: float) -> str:
    sector = round(angle_degrees / 90.0) % len(_DIRECTION_BY_SECTOR)
    return _DIRECTION_BY_SECTOR[sector]


def _pointing_direction(hand_landmarks, *, mirror_horizontal: bool = False) -> str:
    """Direcao (esquerda/cima/baixo/direita) para onde o indicador apontado.

    Usa o vetor da base do indicador (landmark 5) para a ponta (landmark 8),
    em vez do pulso (landmark 0): isola a direcao do dedo em si, sem o ruido
    da rotacao do pulso/antebraco em relacao a camera.

    O eixo Y das coordenadas do MediaPipe cresce para baixo na imagem, por
    isso o angulo inverte o sinal de Y antes do `atan2`, para que 90 graus
    corresponda a "cima" de verdade.

    `mirror_horizontal` (campo de configuracao, default False = comportamento
    ja testado e funcionando com a webcam atual, que nao vem pre-espelhada)
    compensa trocar de camera por uma que entregue o frame ja espelhado (ex.:
    algumas cameras de celular via Continuity Camera). Quando True, inverte
    a leitura do eixo horizontal (delta_x) antes do calculo do angulo, sem
    duplicar a tabela `_DIRECTION_BY_SECTOR`.
    """
    base = hand_landmarks.landmark[5]
    tip = hand_landmarks.landmark[8]
    delta_x = tip.x - base.x
    if mirror_horizontal:
        delta_x = -delta_x
    delta_y = tip.y - base.y
    angle_degrees = math.degrees(math.atan2(-delta_y, delta_x)) % 360.0
    return _direction_from_angle(angle_degrees)


def predict_knn(
    sample: np.ndarray,
    reference_features: np.ndarray,
    reference_labels: np.ndarray,
    k: int,
) -> tuple[int, float]:
    distances = np.linalg.norm(reference_features - sample, axis=1)
    nearest_indices = np.argsort(distances)[: min(k, len(reference_labels))]
    votes = np.bincount(reference_labels[nearest_indices], minlength=len(GESTURE_FOLDERS))
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

    missing_folders = set(GESTURE_FOLDERS) - set(class_names)
    if missing_folders:
        raise ValueError(f"O modelo precisa conter as classes: {sorted(missing_folders)}.")

    return _Model(features=features, labels=labels, class_names=class_names, k=k)


class GestureClassifier:
    """Interpreta landmarks, aplica limiar de confianca e retorna um gesto conhecido ou neutro (None)."""

    def __init__(self, model_path: Path) -> None:
        self._model = _load_model(Path(model_path))

    def classify(
        self, hand_landmarks, min_confidence: float, *, mirror_horizontal: bool = False
    ) -> str | None:
        rule_based_gesture = classify_hand_gesture(hand_landmarks)
        if rule_based_gesture == "mao_fechada":
            folder_name, confidence = "move", _RULE_BASED_CONFIDENCE
        elif rule_based_gesture == "indicador":
            folder_name, confidence = "stop", _RULE_BASED_CONFIDENCE
        else:
            folder_name, confidence = None, 0.0
            feature = extract_features(hand_landmarks)
            if feature is not None:
                class_id, confidence = predict_knn(
                    feature,
                    self._model.features,
                    self._model.labels,
                    k=self._model.k,
                )
                folder_name = self._model.class_names[class_id]

        if folder_name is None or confidence < min_confidence:
            return None
        if folder_name == "stop":
            return _pointing_direction(hand_landmarks, mirror_horizontal=mirror_horizontal)
        return _FOLDER_TO_GESTURE[folder_name]
