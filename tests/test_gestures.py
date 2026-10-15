from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pytest

from vision_game.gestures import (
    GESTURE_FOLDERS,
    GestureClassifier,
    classify_hand_gesture,
    extract_features,
    predict_knn,
)

NUM_LANDMARKS = 21


@dataclass
class _Point:
    x: float
    y: float
    z: float = 0.0


@dataclass
class _HandLandmarks:
    """Imita o objeto `NormalizedLandmarkList` do mediapipe: so precisa expor `.landmark`."""

    landmark: list[_Point]


def _build_hand(fingertip_reach: dict[int, float]) -> _HandLandmarks:
    """Monta 21 landmarks sinteticos com o pulso (id 0) na origem.

    `fingertip_reach` mapeia o id da ponta do dedo (4, 8, 12, 16, 20) para a
    distancia desejada (no plano xy) entre essa ponta e o pulso. Os demais
    pontos (incluindo o id 9, usado como escala da palma) ficam perto do
    pulso para nao interferir na logica de `classify_hand_gesture`.
    """
    points = [_Point(x=0.0, y=0.0, z=0.0) for _ in range(NUM_LANDMARKS)]
    points[9] = _Point(x=0.05, y=0.0, z=0.0)  # referencia de escala da palma
    for landmark_id, reach in fingertip_reach.items():
        points[landmark_id] = _Point(x=reach, y=0.0, z=0.0)
    return _HandLandmarks(landmark=points)


def _build_ambiguous_hand(variation: float) -> _HandLandmarks:
    """Mao com geometria ambigua (todos os dedos igualmente estendidos), que
    forca `classify_hand_gesture` a devolver `None` e cair no fallback KNN.
    `variation` desloca o landmark 5 (fora do calculo geometrico e da
    referencia de escala) para gerar, via `extract_features`, um vetor de
    features distinto por "classe" sintetica em `_build_six_class_model`.
    """
    hand = _build_hand({4: 0.30, 8: 0.30, 12: 0.30, 16: 0.30, 20: 0.30})
    hand.landmark[5] = _Point(x=0.1, y=0.1, z=variation)
    return hand


_EXPECTED_GESTURE_BY_FOLDER = {
    "move": None,
    "stop": "direita",
    "esquerda": "esquerda",
    "cima": "cima",
    "baixo": "baixo",
    "acao": "acao",
}


def _build_six_class_model(tmp_path: Path) -> tuple[Path, dict[str, _HandLandmarks]]:
    """Gera um model.npz sintetico com uma amostra por pasta de `GESTURE_FOLDERS`
    (k=1), permitindo testar `GestureClassifier`/`_FOLDER_TO_GESTURE` sem
    depender do modelo real treinado em `src/image/gesture_model.npz`.
    """
    hands = {folder: _build_ambiguous_hand(variation=index) for index, folder in enumerate(GESTURE_FOLDERS)}
    features = np.stack([extract_features(hands[folder]) for folder in GESTURE_FOLDERS])
    labels = np.arange(len(GESTURE_FOLDERS), dtype=np.int32)

    model_path = tmp_path / "model.npz"
    np.savez_compressed(
        model_path,
        features=features,
        labels=labels,
        classes=np.asarray(GESTURE_FOLDERS),
        k=np.asarray(1),
    )
    return model_path, hands


class TestClassifyHandGesture:
    def test_closed_hand_returns_mao_fechada(self) -> None:
        # Todas as pontas dos dedos proximas do pulso -> mao fechada.
        hand = _build_hand({4: 0.05, 8: 0.06, 12: 0.05, 16: 0.04, 20: 0.03})

        assert classify_hand_gesture(hand) == "mao_fechada"

    def test_extended_index_finger_returns_indicador(self) -> None:
        # Indicador (id 8) bem mais distante do pulso que os outros dedos.
        hand = _build_hand({4: 0.08, 8: 0.40, 12: 0.08, 16: 0.07, 20: 0.06})

        assert classify_hand_gesture(hand) == "indicador"

    def test_all_fingers_extended_returns_none(self) -> None:
        # Nenhum dedo se destaca o suficiente dos demais -> gesto neutro (nao reconhecido).
        hand = _build_hand({4: 0.30, 8: 0.30, 12: 0.30, 16: 0.30, 20: 0.30})

        assert classify_hand_gesture(hand) is None

    def test_wrong_landmark_count_returns_none(self) -> None:
        hand = _HandLandmarks(landmark=[_Point(x=0.0, y=0.0, z=0.0) for _ in range(5)])

        assert classify_hand_gesture(hand) is None


class TestPredictKnn:
    """Dataset fixo e pequeno: 2 classes (0 e 1) separadas, k=3."""

    reference_features = np.array(
        [[0.0], [0.3], [5.0], [5.3], [5.6]], dtype=np.float32
    )
    reference_labels = np.array([0, 0, 1, 1, 1], dtype=np.int32)

    def test_sample_near_class_zero_cluster(self) -> None:
        # Vizinhos mais proximos (k=3): distancias 0.1, 0.2, 4.9 -> labels [0, 0, 1].
        sample = np.array([0.1], dtype=np.float32)

        label, confidence = predict_knn(sample, self.reference_features, self.reference_labels, k=3)

        assert label == 0
        assert confidence == pytest.approx(2 / 3)

    def test_sample_near_class_one_cluster(self) -> None:
        # Vizinhos mais proximos (k=3): distancias 0.1, 0.2, 0.5 -> labels [1, 1, 1].
        sample = np.array([5.1], dtype=np.float32)

        label, confidence = predict_knn(sample, self.reference_features, self.reference_labels, k=3)

        assert label == 1
        assert confidence == pytest.approx(1.0)


class TestGestureClassifierFolderMapping:
    """RF-04: o modelo generaliza de 2 para 6 classes via `GESTURE_FOLDERS` /
    `_FOLDER_TO_GESTURE`. Cobre o caminho que `TestClassifyHandGesture` e
    `TestPredictKnn` nao exercitam: a classificacao fim-a-fim via KNN
    (`GestureClassifier.classify`) e o mapeamento pasta -> gesto semantico
    para as 4 poses novas (esquerda/cima/baixo/acao), alem de "move"/"stop".
    """

    @pytest.mark.parametrize("folder", GESTURE_FOLDERS)
    def test_classify_maps_each_training_folder_to_its_configured_gesture(
        self, tmp_path: Path, folder: str
    ) -> None:
        model_path, hands = _build_six_class_model(tmp_path)
        classifier = GestureClassifier(model_path)

        result = classifier.classify(hands[folder], min_confidence=0.5)

        assert result == _EXPECTED_GESTURE_BY_FOLDER[folder]

    def test_load_model_rejects_model_missing_new_rf04_folders(self, tmp_path: Path) -> None:
        # Simula um model.npz "antigo" (pre-RF-04), com so as 2 classes
        # originais -- a validacao generalizada deve rejeitar e nomear as
        # pastas que faltam, nao so aceitar silenciosamente um modelo
        # incompleto para os 5 comandos atuais.
        model_path = tmp_path / "old_two_class_model.npz"
        np.savez_compressed(
            model_path,
            features=np.zeros((2, 66), dtype=np.float32),
            labels=np.array([0, 1], dtype=np.int32),
            classes=np.asarray(["move", "stop"]),
            k=np.asarray(1),
        )

        with pytest.raises(ValueError) as excinfo:
            GestureClassifier(model_path)

        message = str(excinfo.value)
        for missing_folder in ("esquerda", "cima", "baixo", "acao"):
            assert missing_folder in message
