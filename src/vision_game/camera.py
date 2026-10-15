from __future__ import annotations

import cv2


class CameraError(Exception):
    """Falha ao abrir a camera ou ao ler um quadro."""


class Camera:
    """Encapsula `cv2.VideoCapture`: abrir, ler quadro e liberar."""

    def __init__(self, camera_index: int) -> None:
        self._capture = cv2.VideoCapture(camera_index)
        if not self._capture.isOpened():
            self._capture.release()
            raise CameraError(f"Nao foi possivel abrir a camera de indice {camera_index}.")

    def read(self):
        success, frame = self._capture.read()
        if not success:
            raise CameraError("A camera parou de enviar imagens.")
        return frame

    def release(self) -> None:
        self._capture.release()
