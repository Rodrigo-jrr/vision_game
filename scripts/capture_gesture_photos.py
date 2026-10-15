"""Captura fotos de uma pose da mao para treinar um novo gesto.

Uso:
    python scripts/capture_gesture_photos.py <nome_da_pose> [--count N] [--camera-index 0]

Abre a webcam, mostra uma pre-visualizacao com os landmarks da mao detectados
(apenas como ajuda visual, sem validar o gesto) e salva uma foto limpa (sem
nenhum desenho ou texto) a cada vez que a tecla ESPACO e pressionada, em
src/image/<nome_da_pose>/<nome_da_pose>_NN.jpeg. Pressione ESC para sair
antes de completar as capturas.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import cv2

_SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from vision_game.camera import Camera, CameraError
from vision_game.hand_tracking import HandTracker

_POSE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")
_IMAGE_SUFFIX = ".jpeg"
_SAVED_FEEDBACK_FRAMES = 20
_WINDOW_NAME = "Captura de fotos | ESPACO para salvar, ESC para sair"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Captura fotos da webcam para treinar um novo gesto."
    )
    parser.add_argument("pose_name", help="Nome da pose/gesto (ex: esquerda, cima)")
    parser.add_argument(
        "--count", type=int, default=25, help="Quantidade de fotos a capturar (padrao: 25)"
    )
    parser.add_argument(
        "--camera-index", type=int, default=0, help="Indice da camera (padrao: 0)"
    )
    return parser.parse_args()


def _existing_indices(output_dir: Path, pose_name: str) -> list[int]:
    pattern = re.compile(rf"^{re.escape(pose_name)}_(\d+)\.(jpeg|jpg|png)$", re.IGNORECASE)
    indices = []
    for path in output_dir.iterdir():
        match = pattern.match(path.name)
        if match:
            indices.append(int(match.group(1)))
    return indices


def _draw_overlay(frame, pose_name: str, captured: int, total: int, hand_detected: bool) -> None:
    cv2.putText(
        frame,
        f"Pose: {pose_name} - Capturas: {captured}/{total}",
        (20, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2,
    )
    cv2.putText(
        frame,
        "ESPACO = capturar foto | ESC = sair",
        (20, 60),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (255, 255, 255),
        2,
    )
    status_text = "Mao detectada" if hand_detected else "Mao NAO detectada"
    status_color = (0, 220, 0) if hand_detected else (0, 0, 255)
    cv2.putText(frame, status_text, (20, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 2)


def _draw_feedback(frame, message: str) -> None:
    cv2.putText(frame, message, (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 220, 0), 2)


def main() -> int:
    args = _parse_args()
    pose_name = args.pose_name

    if not _POSE_NAME_PATTERN.match(pose_name):
        print(
            f"Nome de pose invalido: {pose_name!r}. Use apenas letras, numeros, '_' ou '-'.",
            file=sys.stderr,
        )
        return 1

    if args.count <= 0:
        print("--count deve ser maior que zero.", file=sys.stderr)
        return 1

    output_dir = Path(__file__).resolve().parent.parent / "src" / "image" / pose_name
    output_dir.mkdir(parents=True, exist_ok=True)

    existing = _existing_indices(output_dir, pose_name)
    start_index = max(existing, default=0) + 1
    end_index = start_index + args.count - 1
    index_width = max(2, len(str(end_index)))

    print(f"Pose: {pose_name}")
    print(f"Fotos ja existentes nesta pasta: {len(existing)}")
    print(f"Vou capturar {args.count} foto(s) nova(s), comecando em "
          f"{pose_name}_{start_index:0{index_width}d}{_IMAGE_SUFFIX}")
    print("Posicione a mao na frente da camera, fazendo a pose desejada.")
    print("Pressione ESPACO para capturar uma foto, ESC para sair antes de terminar.")

    try:
        camera = Camera(args.camera_index)
    except CameraError as error:
        print(f"Erro de camera: {error}", file=sys.stderr)
        return 1

    hand_tracker = HandTracker()
    captured = 0
    current_index = start_index
    feedback_message = ""
    feedback_frames_left = 0

    try:
        while captured < args.count:
            frame = camera.read()
            display_frame = frame.copy()

            hand_landmarks = hand_tracker.process(frame)
            hand_detected = hand_landmarks is not None
            if hand_detected:
                hand_tracker.draw_landmarks(display_frame, hand_landmarks)

            _draw_overlay(display_frame, pose_name, captured, args.count, hand_detected)
            if feedback_frames_left > 0:
                _draw_feedback(display_frame, feedback_message)
                feedback_frames_left -= 1

            cv2.imshow(_WINDOW_NAME, display_frame)
            key = cv2.waitKey(1) & 0xFF

            if key == 27:
                print("Captura interrompida pelo usuario (ESC).")
                break

            if key == 32:
                file_name = f"{pose_name}_{current_index:0{index_width}d}{_IMAGE_SUFFIX}"
                file_path = output_dir / file_name
                cv2.imwrite(str(file_path), frame)
                captured += 1
                current_index += 1
                feedback_message = f"Salvo: {file_name}"
                feedback_frames_left = _SAVED_FEEDBACK_FRAMES
                print(f"Foto {captured}/{args.count} salva em {file_path}")
    finally:
        camera.release()
        hand_tracker.close()
        cv2.destroyAllWindows()

    print(f"Concluido: {captured} foto(s) salva(s) em {output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
