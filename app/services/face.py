import numpy as np
import cv2
import mediapipe as mp
import face_recognition
from app.core.config import settings
from app.core.errors import AppError

mp_face_mesh = mp.solutions.face_mesh.FaceMesh(static_image_mode=False, max_num_faces=2, refine_landmarks=True)

def decode_image(file_bytes: bytes) -> np.ndarray:
    arr = np.frombuffer(file_bytes, dtype=np.uint8)
    bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if bgr is None:
        raise AppError("BAD_IMAGE", "Не удалось декодировать изображение.")
    return bgr

def image_quality_checks(bgr: np.ndarray, bbox_ltrb) -> None:
    left, top, right, bottom = bbox_ltrb
    h, w = bgr.shape[:2]
    area = max(0, right-left) * max(0, bottom-top)
    if area < (w*h)*0.05:
        raise AppError("FACE_TOO_SMALL", "Подойдите ближе к камере.")
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    mean = float(np.mean(gray))
    if mean < 35:
        raise AppError("LOW_LIGHT", "Слишком темно. Улучшите освещение.")
    blur = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    if blur < 60:
        raise AppError("BLURRY", "Изображение размыто. Не двигайтесь и повторите.")

def detect_single_face_and_encoding(bgr: np.ndarray):
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    locs = face_recognition.face_locations(rgb, model="hog")
    if len(locs) == 0:
        raise AppError("FACE_NOT_FOUND", "Лицо не найдено. Встаньте в кадр.")
    if len(locs) > 1:
        raise AppError("MULTIPLE_FACES", "В кадре несколько лиц. Останьтесь один в кадре.")
    (top, right, bottom, left) = locs[0]
    image_quality_checks(bgr, (left, top, right, bottom))
    encs = face_recognition.face_encodings(rgb, known_face_locations=locs)
    if not encs:
        raise AppError("NO_FACE_ENCODING", "Не удалось построить биометрический шаблон.")
    return (left, top, right, bottom), encs[0].astype(np.float32)

def l2_dist(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.linalg.norm(a - b))

def estimate_pose_and_blink(bgr: np.ndarray):
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    res = mp_face_mesh.process(rgb)
    if not res.multi_face_landmarks or len(res.multi_face_landmarks) == 0:
        raise AppError("FACE_NOT_FOUND", "Лицо не найдено.")
    if len(res.multi_face_landmarks) > 1:
        raise AppError("MULTIPLE_FACES", "В кадре несколько лиц.")

    lm = res.multi_face_landmarks[0].landmark
    h, w = bgr.shape[:2]

    def pt(i):
        return np.array([lm[i].x * w, lm[i].y * h], dtype=np.float64)

    image_points = np.array([pt(1), pt(152), pt(33), pt(263), pt(61), pt(291)], dtype=np.float64)
    model_points = np.array([
        (0.0, 0.0, 0.0),
        (0.0, -63.6, -12.5),
        (-43.3, 32.7, -26.0),
        (43.3, 32.7, -26.0),
        (-28.9, -28.9, -24.1),
        (28.9, -28.9, -24.1)
    ], dtype=np.float64)

    focal_length = w
    center = (w / 2, h / 2)
    camera_matrix = np.array([
        [focal_length, 0, center[0]],
        [0, focal_length, center[1]],
        [0, 0, 1]
    ], dtype=np.float64)
    dist_coeffs = np.zeros((4, 1), dtype=np.float64)

    ok, rvec, tvec = cv2.solvePnP(model_points, image_points, camera_matrix, dist_coeffs, flags=cv2.SOLVEPNP_ITERATIVE)
    if not ok:
        raise AppError("POSE_FAIL", "Не удалось оценить поворот головы.")

    rmat, _ = cv2.Rodrigues(rvec)
    sy = np.sqrt(rmat[0,0]**2 + rmat[1,0]**2)
    singular = sy < 1e-6
    if not singular:
        x = np.arctan2(rmat[2,1], rmat[2,2])
        y = np.arctan2(-rmat[2,0], sy)
        z = np.arctan2(rmat[1,0], rmat[0,0])
    else:
        x = np.arctan2(-rmat[1,2], rmat[1,1])
        y = np.arctan2(-rmat[2,0], sy)
        z = 0

    pitch = float(np.degrees(x))
    yaw = float(np.degrees(y))
    roll = float(np.degrees(z))

    def ear(indices):
        p = [pt(i) for i in indices]
        v1 = np.linalg.norm(p[1]-p[5])
        v2 = np.linalg.norm(p[2]-p[4])
        hdist = np.linalg.norm(p[0]-p[3])
        return float((v1 + v2) / (2.0 * max(hdist, 1e-6)))

    left_ear = ear([33,160,158,133,153,144])
    right_ear = ear([263,387,385,362,380,373])
    ear_avg = (left_ear + right_ear) / 2.0
    blink = ear_avg < 0.18

    return {"yaw": yaw, "pitch": pitch, "roll": roll}, blink

def face_match(stored_embedding: np.ndarray, current_embedding: np.ndarray):
    dist = l2_dist(stored_embedding, current_embedding)
    return (dist <= settings.FACE_DIST_THRESHOLD), dist
