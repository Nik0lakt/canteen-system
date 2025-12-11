import io
import base64
from typing import List, Optional

import numpy as np
import face_recognition
from sqlalchemy.orm import Session

from app.db import models


def compute_embedding_from_images(image_bytes_list: List[bytes]) -> np.ndarray:
    embeddings = []

    for img_bytes in image_bytes_list:
        image = face_recognition.load_image_file(io.BytesIO(img_bytes))
        face_locations = face_recognition.face_locations(image)

        if len(face_locations) != 1:
            # пропускаем кадры, где лиц нет или их несколько
            continue

        encodings = face_recognition.face_encodings(image, face_locations)
        if not encodings:
            continue

        embeddings.append(encodings[0])

    if not embeddings:
        raise ValueError("NO_VALID_FACE_FRAMES")

    mean_embedding = np.mean(embeddings, axis=0)
    return mean_embedding.astype("float32")


def embedding_to_str(embedding: np.ndarray) -> str:
    return base64.b64encode(embedding.tobytes()).decode("ascii")


def embedding_from_str(s: str) -> np.ndarray:
    raw = base64.b64decode(s.encode("ascii"))
    return np.frombuffer(raw, dtype="float32")


def get_active_face_embedding(db: Session, employee_id: int) -> Optional[np.ndarray]:
    face = (
        db.query(models.Face)
        .filter(models.Face.employee_id == employee_id, models.Face.is_active == True)
        .first()
    )
    if not face:
        return None
    return embedding_from_str(face.embedding)
