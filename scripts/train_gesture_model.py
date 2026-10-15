"""Treina o modelo KNN de gestos a partir das pastas em GESTURE_FOLDERS (src/image/)."""

from __future__ import annotations

import sys
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np

_SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from vision_game.gestures import GESTURE_FOLDERS, extract_features, predict_knn

K_NEIGHBORS = 3
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "src" / "image"
MODEL_PATH = DATA_DIR / "gesture_model.npz"


def _extract_dataset() -> tuple[np.ndarray, np.ndarray]:
    if not DATA_DIR.is_dir():
        raise FileNotFoundError(f"Pasta do dataset nao encontrada: {DATA_DIR}")

    features = []
    labels = []
    skipped_images = []

    with mp.solutions.hands.Hands(
        static_image_mode=True,
        max_num_hands=1,
        min_detection_confidence=0.35,
    ) as hand_detector:
        for label_id, label in enumerate(GESTURE_FOLDERS):
            class_dir = DATA_DIR / label
            image_files = sorted(
                path
                for path in class_dir.iterdir()
                if path.suffix.lower() in {".jpg", ".jpeg", ".png"}
            )
            if not image_files:
                raise ValueError(f"Nenhuma imagem encontrada em {class_dir}")

            for image_path in image_files:
                image = cv2.imread(str(image_path))
                if image is None:
                    skipped_images.append((image_path, "arquivo nao pode ser lido"))
                    continue

                result = hand_detector.process(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
                if not result.multi_hand_landmarks:
                    skipped_images.append((image_path, "mao nao detectada"))
                    continue

                feature = extract_features(result.multi_hand_landmarks[0])
                if feature is None:
                    skipped_images.append((image_path, "landmarks invalidos"))
                    continue

                features.append(feature)
                labels.append(label_id)

    features_array = np.asarray(features, dtype=np.float32)
    labels_array = np.asarray(labels, dtype=np.int32)

    if not len(features_array):
        raise ValueError("Nao foi possivel extrair landmarks de nenhuma imagem.")

    for label_id, label in enumerate(GESTURE_FOLDERS):
        count = int(np.sum(labels_array == label_id))
        print(f"{label}: {count} imagens validas")
    print(f"Formato das caracteristicas: {features_array.shape}")
    print(f"Imagens ignoradas: {len(skipped_images)}")

    return features_array, labels_array


def _evaluate_leave_one_out(features: np.ndarray, labels: np.ndarray) -> None:
    leave_one_out_predictions = []
    for index, sample in enumerate(features):
        training_mask = np.arange(len(labels)) != index
        prediction, _ = predict_knn(
            sample,
            features[training_mask],
            labels[training_mask],
            k=K_NEIGHBORS,
        )
        leave_one_out_predictions.append(prediction)

    confusion = np.zeros((len(GESTURE_FOLDERS), len(GESTURE_FOLDERS)), dtype=np.int32)
    for actual, predicted in zip(labels, leave_one_out_predictions):
        confusion[actual, predicted] += 1

    accuracy = float(np.mean(labels == leave_one_out_predictions))
    print(f"Acuracia leave-one-out (indicativa): {accuracy:.1%}")
    print("Matriz de confusao (linhas=real, colunas=previsto):")
    print(confusion)


def main() -> int:
    features, labels = _extract_dataset()
    _evaluate_leave_one_out(features, labels)

    np.savez_compressed(
        MODEL_PATH,
        features=features,
        labels=labels,
        classes=np.asarray(GESTURE_FOLDERS),
        k=np.asarray(K_NEIGHBORS),
    )
    print(f"Modelo salvo em: {MODEL_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
