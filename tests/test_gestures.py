from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pytest

from vision_game.gestures import (
    GESTURE_FOLDERS,
    GestureClassifier,
    _direction_from_angle,
    _pointing_direction,
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
    features distinto por "classe" sintetica em `_build_synthetic_model`.
    """
    hand = _build_hand({4: 0.30, 8: 0.30, 12: 0.30, 16: 0.30, 20: 0.30})
    hand.landmark[5] = _Point(x=0.1, y=0.1, z=variation)
    return hand


def _landmarks_pointing(base: tuple[float, float], tip: tuple[float, float]) -> _HandLandmarks:
    """Lista minima de landmarks com apenas os indices usados por
    `_pointing_direction` preenchidos (5 = base do indicador/MCP, 8 = ponta).
    Os demais pontos sao placeholders em (0, 0): a funcao so le os indices 5 e 8.
    """
    points = [_Point(x=0.0, y=0.0, z=0.0) for _ in range(9)]
    points[5] = _Point(x=base[0], y=base[1], z=0.0)
    points[8] = _Point(x=tip[0], y=tip[1], z=0.0)
    return _HandLandmarks(landmark=points)


# Gestos com saida fixa (nao dependem de angulo): "stop" fica de fora de
# proposito, seu resultado agora e calculado por `_pointing_direction` e e
# testado separadamente (ver `TestGestureClassifierFolderMapping`).
_EXPECTED_FIXED_GESTURE_BY_FOLDER = {
    "move": None,
    "acao": "acao",
}


def _build_synthetic_model(tmp_path: Path) -> tuple[Path, dict[str, _HandLandmarks]]:
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
    """Redesign por angulo: `GESTURE_FOLDERS` caiu de 6 para 3 classes
    (`move`, `stop`, `acao`) -- as 4 direcoes deixaram de ser poses fixas
    treinadas e passaram a ser calculadas pelo angulo do indicador apontando
    (`_pointing_direction`), ver `TestPointingDirection`/`TestDirectionFromAngle`.

    Cobre o caminho que `TestClassifyHandGesture` e `TestPredictKnn` nao
    exercitam: a classificacao fim-a-fim via `GestureClassifier.classify`.
    """

    @pytest.mark.parametrize("folder", sorted(_EXPECTED_FIXED_GESTURE_BY_FOLDER))
    def test_classify_maps_each_fixed_training_folder_to_its_configured_gesture(
        self, tmp_path: Path, folder: str
    ) -> None:
        model_path, hands = _build_synthetic_model(tmp_path)
        classifier = GestureClassifier(model_path)

        result = classifier.classify(hands[folder], min_confidence=0.5)

        assert result == _EXPECTED_FIXED_GESTURE_BY_FOLDER[folder]

    def test_classify_of_stop_pose_delegates_to_computed_pointing_direction(
        self, tmp_path: Path
    ) -> None:
        # Antes do redesign, a pose "stop" (indicador esticado) sempre virava
        # o gesto fixo "direita". Agora o resultado depende do angulo do
        # vetor landmark5->landmark8 (`_pointing_direction`). Para provar que
        # nao sobrou nenhum retorno fixo escondido, monto uma mao cujo
        # indicador aponta deliberadamente para "cima" (nao "direita") e
        # confirmo que `classify` devolve exatamente isso.
        model_path, _ = _build_synthetic_model(tmp_path)
        classifier = GestureClassifier(model_path)

        # Satisfaz a heuristica rapida de `classify_hand_gesture` ("indicador"):
        # ponta do indicador (id 8) bem mais distante do pulso (id 0, que
        # fica na origem por `_build_hand`) que as demais pontas. O vetor
        # landmark5->landmark8 aponta deliberadamente para "cima" (mesma
        # coordenada x, y menor na ponta -- eixo Y do MediaPipe cresce para
        # baixo), sobrepondo a posicao de id 8 definida por `_build_hand`.
        hand = _build_hand({4: 0.03, 12: 0.03, 16: 0.03, 20: 0.03})
        hand.landmark[5] = _Point(x=0.05, y=0.05, z=0.0)  # base do indicador (MCP)
        hand.landmark[8] = _Point(x=0.05, y=-0.35, z=0.0)  # ponta, acima da base

        assert classify_hand_gesture(hand) == "indicador"  # confirma o atalho geometrico usado

        result = classifier.classify(hand, min_confidence=0.5)

        assert result == "cima"

    def test_load_model_rejects_model_missing_required_folders(self, tmp_path: Path) -> None:
        # Simula um model.npz "antigo" (pre-redesign por angulo), com as 2
        # classes originais mas sem "acao" -- a validacao deve rejeitar e
        # nomear exatamente a pasta que falta. Com GESTURE_FOLDERS reduzido a
        # ("move", "stop", "acao"), so "acao" deve aparecer como faltante
        # aqui (esquerda/cima/baixo nao fazem mais parte do modelo).
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
        assert "acao" in message
        for folder_no_longer_required in ("esquerda", "cima", "baixo"):
            assert folder_no_longer_required not in message


class TestDirectionFromAngle:
    """`_direction_from_angle` seteriza 360 graus em 4 setores de 90 graus
    (direita=0, cima=90, esquerda=180, baixo=270) via `round(angulo/90) % 4`.
    """

    @pytest.mark.parametrize(
        ("angle_degrees", "expected_direction"),
        [(0, "direita"), (90, "cima"), (180, "esquerda"), (270, "baixo")],
    )
    def test_cardinal_angles(self, angle_degrees: float, expected_direction: str) -> None:
        assert _direction_from_angle(angle_degrees) == expected_direction

    @pytest.mark.parametrize(
        ("angle_degrees", "expected_direction"),
        [
            # Nos 4 pontos exatos de fronteira entre setores, `round()` usa o
            # desempate "banker's rounding" do Python (arredonda para o
            # inteiro PAR mais proximo): 45/90=0.5 -> round=0 (par) ->
            # "direita"; 135/90=1.5 -> round=2 (par) -> "esquerda";
            # 225/90=2.5 -> round=2 (par) -> "esquerda" (nao "baixo", apesar
            # de 225 estar exatamente entre "esquerda" e "baixo");
            # 315/90=3.5 -> round=4%4=0 -> "direita" (nao "baixo").
            # Resultado pratico: nas 4 fronteiras exatas, o desempate so pode
            # cair em "direita" ou "esquerda" -- nunca em "cima"/"baixo",
            # porque os setores 0 e 2 sao pares e 1/3 sao impares. Isso bate
            # com o que o Back End descreveu como "desempate arbitrario, nao
            # critico" (resumo RF-04/angulo), mas documento aqui o resultado
            # exato para o caso de alguem depender dele no futuro.
            (45, "direita"),
            (135, "esquerda"),
            (225, "esquerda"),
            (315, "direita"),
        ],
    )
    def test_exact_sector_boundaries_use_bankers_rounding(
        self, angle_degrees: float, expected_direction: str
    ) -> None:
        assert _direction_from_angle(angle_degrees) == expected_direction

    def test_angle_above_360_wraps_around(self) -> None:
        # `_pointing_direction` ja normaliza com `% 360` antes de chamar esta
        # funcao, mas `_direction_from_angle` em si nao impõe essa garantia;
        # confirmo que `round()/%4` sozinho tambem se comporta corretamente
        # para um valor equivalente a 90 graus (450 = 360 + 90).
        assert _direction_from_angle(450) == _direction_from_angle(90) == "cima"


class TestPointingDirection:
    """`_pointing_direction` usa o vetor landmark5 (base do indicador) ->
    landmark8 (ponta) e inverte o sinal de Y antes do `atan2` (coordenadas do
    MediaPipe crescem para baixo). Testa os 4 casos cardinais com vetores
    explicitos, sem depender de `classify_hand_gesture` nem de KNN.
    """

    def test_pointing_right(self) -> None:
        hand = _landmarks_pointing(base=(0.0, 0.0), tip=(1.0, 0.0))
        assert _pointing_direction(hand) == "direita"

    def test_pointing_up(self) -> None:
        # Y menor na ponta que na base == "para cima" nas coordenadas do
        # MediaPipe (eixo Y cresce para baixo na imagem).
        hand = _landmarks_pointing(base=(0.0, 0.0), tip=(0.0, -1.0))
        assert _pointing_direction(hand) == "cima"

    def test_pointing_left(self) -> None:
        hand = _landmarks_pointing(base=(0.0, 0.0), tip=(-1.0, 0.0))
        assert _pointing_direction(hand) == "esquerda"

    def test_pointing_down(self) -> None:
        hand = _landmarks_pointing(base=(0.0, 0.0), tip=(0.0, 1.0))
        assert _pointing_direction(hand) == "baixo"
