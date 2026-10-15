from __future__ import annotations

import cv2
import mediapipe as mp

# NOTA: usa a API legada `mp.solutions.hands`, nao a `mediapipe.tasks` (Hand
# Landmarker) citada em doc/tecnologias-arquitetura.md. Divergencia
# confirmada com o usuario: e a mesma API ja validada no notebook original.

_DRAWING_UTILS = mp.solutions.drawing_utils
_HAND_CONNECTIONS = mp.solutions.hands.HAND_CONNECTIONS


class HandTracker:
    """Recebe um quadro BGR e devolve os landmarks da mao, ou None. Nao decide tecla nenhuma."""

    def __init__(self) -> None:
        self._hands = mp.solutions.hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            model_complexity=0,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )

    def process(self, frame_bgr):
        result = self._hands.process(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB))
        if not result.multi_hand_landmarks:
            return None
        return result.multi_hand_landmarks[0]

    def draw_landmarks(self, frame_bgr, hand_landmarks) -> None:
        _DRAWING_UTILS.draw_landmarks(frame_bgr, hand_landmarks, _HAND_CONNECTIONS)

    def close(self) -> None:
        self._hands.close()
