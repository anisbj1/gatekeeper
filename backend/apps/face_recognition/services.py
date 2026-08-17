import numpy as np
import cv2
import torch
import logging
from PIL import Image
from io import BytesIO
from django.conf import settings
from django.utils import timezone
from django.core.files.base import ContentFile
from .models import FaceProfile, FaceImage, FaceEmbedding, EnrollmentSession, RecognitionAttempt
from apps.access_control.models import Device, Card

logger = logging.getLogger(__name__)

class BiometricEngine:
    _mtcnn = None
    _resnet = None

    @classmethod
    def get_mtcnn(cls):
        if cls._mtcnn is None:
            from facenet_pytorch import MTCNN
            # Initialize MTCNN on CPU. keep_all=True detects multiple faces.
            cls._mtcnn = MTCNN(keep_all=True, device='cpu')
        return cls._mtcnn

    @classmethod
    def get_resnet(cls):
        if cls._resnet is None:
            from facenet_pytorch import InceptionResnetV1
            # Load InceptionResnetV1 pre-trained on VGGFace2
            cls._resnet = InceptionResnetV1(pretrained='vggface2').eval()
        return cls._resnet

    @classmethod
    def process_and_extract(cls, image_bytes: bytes) -> dict:
        """
        Runs the full face pipeline: detection, quality check, alignment, and embedding extraction.
        Returns:
            dict containing:
                - success: bool
                - error_code: str (or None)
                - message: str
                - cropped_face_np: np.ndarray (or None)
                - embedding: list of 512 floats (or None)
                - confidence: float (detector confidence)
        """
        # Load image with PIL
        try:
            image_pil = Image.open(BytesIO(image_bytes)).convert('RGB')
            image_cv = cv2.cvtColor(np.array(image_pil), cv2.COLOR_RGB2BGR)
        except Exception as e:
            logger.error(f"Failed to decode uploaded image: {str(e)}")
            return {"success": False, "error_code": "INVALID_IMAGE", "message": "Failed to decode image"}

        mtcnn = cls.get_mtcnn()
        
        # Detect faces and landmarks
        # boxes shape: (N, 4), probs shape: (N,), landmarks shape: (N, 5, 2)
        try:
            boxes, probs, landmarks = mtcnn.detect(image_pil, landmarks=True)
        except Exception as e:
            logger.error(f"MTCNN detection error: {str(e)}")
            return {"success": False, "error_code": "DETECTION_ERROR", "message": "Face detector failed"}

        if boxes is None or len(boxes) == 0:
            return {"success": False, "error_code": "NO_FACE_DETECTED", "message": "No face detected in the image"}

        if len(boxes) > 1:
            return {"success": False, "error_code": "MULTIPLE_FACES", "message": "Multiple faces detected. Only one face must be present"}

        box = boxes[0]
        prob = probs[0]
        landmark = landmarks[0]

        # 1. Bounding box size & framing quality check
        h, w, _ = image_cv.shape
        x1, y1, x2, y2 = map(int, box)
        box_w = x2 - x1
        box_h = y2 - y1
        
        if box_w < 80 or box_h < 80:
            return {"success": False, "error_code": "FACE_TOO_SMALL", "message": "Face is too far away or too small"}

        # Border check: reject if face is too close to the borders (cut off)
        if x1 < 2 or y1 < 2 or x2 > w - 2 or y2 > h - 2:
            return {"success": False, "error_code": "FACE_CLIPPED", "message": "Face is cut off by the frame borders"}

        # 2. Blur assessment (Laplacian variance)
        gray = cv2.cvtColor(image_cv, cv2.COLOR_BGR2GRAY)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        if laplacian_var < 30.0:
            return {"success": False, "error_code": "IMAGE_BLURRY", "message": f"Image is too blurry ({laplacian_var:.1f})"}

        # 3. Illumination check
        face_crop_gray = gray[max(0, y1):min(h, y2), max(0, x1):min(w, x2)]
        if face_crop_gray.size > 0:
            brightness = face_crop_gray.mean()
        else:
            brightness = 0
        if brightness < 40.0:
            return {"success": False, "error_code": "POOR_LIGHTING_DARK", "message": f"Lighting is too dark ({brightness:.1f})"}
        if brightness > 220.0:
            return {"success": False, "error_code": "POOR_LIGHTING_BRIGHT", "message": f"Lighting is too bright ({brightness:.1f})"}

        # 4. Symmetry / Yaw check
        # landmarks: [left_eye, right_eye, nose, left_mouth, right_mouth]
        left_eye = landmark[0]
        right_eye = landmark[1]
        nose = landmark[2]
        
        dist_left = np.linalg.norm(left_eye - nose)
        dist_right = np.linalg.norm(right_eye - nose)
        
        if dist_right == 0:
            symmetry_ratio = 99.0
        else:
            symmetry_ratio = dist_left / dist_right

        if symmetry_ratio < 0.5 or symmetry_ratio > 2.0:
            return {"success": False, "error_code": "INCORRECT_ORIENTATION", "message": "Please look directly at the camera"}

        # 5. Affine alignment
        # Align eyes horizontally and crop to 160x160
        dx = right_eye[0] - left_eye[0]
        dy = right_eye[1] - left_eye[1]
        angle = np.degrees(np.arctan2(dy, dx))
        
        eyes_center = ((left_eye[0] + right_eye[0]) / 2.0, (left_eye[1] + right_eye[1]) / 2.0)
        
        # Desired distance between eyes in aligned 160x160 image is 64 pixels (40%)
        current_dist = np.sqrt(dx**2 + dy**2)
        desired_dist = 64.0
        scale = desired_dist / current_dist
        
        # Obtain rotation matrix
        M = cv2.getRotationMatrix2D(eyes_center, angle, scale)
        
        # Translate center of eyes to target position (80, 56)
        M[0, 2] += 80.0 - eyes_center[0]
        M[1, 2] += 56.0 - eyes_center[1]
        
        # Perform warp
        aligned_face = cv2.warpAffine(image_cv, M, (160, 160), flags=cv2.INTER_CUBIC)
        
        # 6. Extract embedding
        try:
            embedding = cls.generate_embedding(aligned_face)
        except Exception as e:
            logger.error(f"Embedding generation error: {str(e)}")
            return {"success": False, "error_code": "EMBEDDING_ERROR", "message": "Failed to generate biometric embedding"}

        return {
            "success": True,
            "error_code": None,
            "message": "Quality checks passed and face aligned successfully",
            "cropped_face_np": aligned_face,
            "embedding": embedding,
            "confidence": float(prob)
        }

    @classmethod
    def generate_embedding(cls, face_np: np.ndarray) -> list:
        """
        Takes a 160x160 BGR face image, normalizes it, and extracts the 512-float embedding.
        """
        resnet = cls.get_resnet()
        # Convert BGR to RGB
        face_rgb = cv2.cvtColor(face_np, cv2.COLOR_BGR2RGB)
        
        # Convert to tensor shape (3, 160, 160) and scale [0, 255] to standard range
        face_tensor = torch.tensor(face_rgb).permute(2, 0, 1).float()
        # Fixed Image Standardization: (x - 127.5) / 128.0
        face_tensor = (face_tensor - 127.5) / 128.0
        face_tensor = face_tensor.unsqueeze(0)  # batch dimension (1, 3, 160, 160)
        
        with torch.no_grad():
            embedding = resnet(face_tensor)
            # L2 Normalize the embedding to unit length (length = 1.0)
            embedding = embedding / embedding.norm(dim=1, keepdim=True)
            embedding_list = embedding[0].tolist()
            
        return embedding_list

    @staticmethod
    def calculate_similarity(emb1: list, emb2: list) -> float:
        """
        Computes cosine similarity between two unit-normalized embeddings.
        Since they are unit vectors, this is simply the dot product.
        Returns value between -1.0 and 1.0 (typically 0.0 to 1.0 for faces).
        """
        a = np.array(emb1)
        b = np.array(emb2)
        return float(np.dot(a, b))


class EnrollmentService:
    @classmethod
    def start_session(cls, user, device) -> EnrollmentSession:
        """
        Initiates a new enrollment session. Invalidates any existing active session.
        """
        # Set all active pending/collecting sessions for this user to expired/failed
        EnrollmentSession.objects.filter(
            user=user,
            status__in=['PENDING', 'COLLECTING']
        ).update(status='EXPIRED')

        expires_at = timezone.now() + timezone.timedelta(minutes=2)
        session = EnrollmentSession.objects.create(
            user=user,
            device=device,
            status='PENDING',
            images_required=5,
            images_collected=0,
            expires_at=expires_at
        )
        return session

    @classmethod
    def process_frame(cls, session: EnrollmentSession, image_bytes: bytes) -> dict:
        """
        Processes a frame submitted for an active enrollment session.
        Returns dict with status, collected count, and errors/warnings if quality fails.
        """
        # Session state check
        if session.status not in ['PENDING', 'COLLECTING']:
            return {"success": False, "error_code": "INVALID_SESSION_STATUS", "message": f"Session status is {session.status}"}
        
        if timezone.now() > session.expires_at:
            session.status = 'EXPIRED'
            session.save()
            return {"success": False, "error_code": "SESSION_EXPIRED", "message": "Enrollment session has expired"}

        # Transition status to collecting on first frame
        if session.status == 'PENDING':
            session.status = 'COLLECTING'
            session.save()

        # Run biometric pipeline
        res = BiometricEngine.process_and_extract(image_bytes)
        if not res["success"]:
            # Frame rejected due to quality check failures
            return {
                "success": False,
                "error_code": res["error_code"],
                "message": res["message"],
                "images_collected": session.images_collected,
                "images_required": session.images_required
            }

        # Quality check passed! Store the face image & embedding
        # Prepare file names
        timestamp_str = timezone.now().strftime('%Y%m%d_%H%M%S')
        username = session.user.username
        
        original_name = f"{username}_orig_{timestamp_str}_{session.images_collected}.jpg"
        cropped_name = f"{username}_face_{timestamp_str}_{session.images_collected}.jpg"

        # Encode cropped BGR image to JPEG bytes
        _, cropped_jpeg = cv2.imencode('.jpg', res["cropped_face_np"])
        cropped_bytes = cropped_jpeg.tobytes()

        # Get or create FaceProfile
        profile, _ = FaceProfile.objects.get_or_create(user=session.user)

        # Create FaceImage
        face_image = FaceImage(profile=profile)
        face_image.original_image.save(original_name, ContentFile(image_bytes), save=False)
        face_image.cropped_image.save(cropped_name, ContentFile(cropped_bytes), save=False)
        
        # Set the first frame as reference image by default
        if session.images_collected == 0:
            face_image.is_reference = True
            # Clear other references just in case
            FaceImage.objects.filter(profile=profile).update(is_reference=False)
            
        face_image.save()

        # Create FaceEmbedding
        FaceEmbedding.objects.create(
            profile=profile,
            embedding=res["embedding"],
            model_version="facenet_v1"
        )

        # Update session
        session.images_collected += 1
        if session.images_collected >= session.images_required:
            session.status = 'COMPLETED'
            profile.is_biometric_active = True
            profile.save()
        session.save()

        return {
            "success": True,
            "message": "Frame accepted successfully",
            "images_collected": session.images_collected,
            "images_required": session.images_required,
            "status": session.status
        }


class VerificationService:
    @classmethod
    def verify_face(cls, card_uid: str, device_id: str, image_bytes: bytes) -> dict:
        """
        Validates the face scan against the user identified by card_uid (1-to-1 matching).
        Logs a RecognitionAttempt.
        """
        start_time = timezone.now()
        
        # 1. Identify User from Card
        try:
            card = Card.objects.select_related('user').get(uid=card_uid)
            user = card.user
        except Card.DoesNotExist:
            # We log the attempt with null user and card, since card is unknown
            # Get device object if exists
            try:
                device = Device.objects.get(device_id=device_id)
            except Device.DoesNotExist:
                return {"authorized": False, "message": "Device not registered", "action": "keep_locked"}

            cls._log_attempt(
                user=None, card=None, device=device,
                captured_image_bytes=image_bytes,
                confidence=None, authorized=False,
                error_message="Unknown Card UID", start_time=start_time
            )
            return {"authorized": False, "message": "Biometric validation failed: card unrecognized", "action": "keep_locked"}

        try:
            device = Device.objects.get(device_id=device_id)
        except Device.DoesNotExist:
            return {"authorized": False, "message": "Device not registered", "action": "keep_locked"}

        # 2. Check if biometric profile exists and is active
        try:
            profile = user.face_profile
            if not profile.is_biometric_active:
                cls._log_attempt(
                    user=user, card=card, device=device,
                    captured_image_bytes=image_bytes,
                    confidence=None, authorized=False,
                    error_message="Biometrics deactivated for user", start_time=start_time
                )
                return {"authorized": False, "message": "Biometric verification disabled for user", "action": "keep_locked"}
        except FaceProfile.DoesNotExist:
            cls._log_attempt(
                user=user, card=card, device=device,
                captured_image_bytes=image_bytes,
                confidence=None, authorized=False,
                error_message="User has no biometric profile enrolled", start_time=start_time
            )
            return {"authorized": False, "message": "Biometric profile not enrolled", "action": "keep_locked"}

        # Fetch stored embeddings
        stored_embeddings = list(profile.embeddings.filter(model_version='facenet_v1'))
        if not stored_embeddings:
            cls._log_attempt(
                user=user, card=card, device=device,
                captured_image_bytes=image_bytes,
                confidence=None, authorized=False,
                error_message="No embeddings found for user", start_time=start_time
            )
            return {"authorized": False, "message": "Biometric profile incomplete", "action": "keep_locked"}

        # 3. Process test frame
        res = BiometricEngine.process_and_extract(image_bytes)
        if not res["success"]:
            cls._log_attempt(
                user=user, card=card, device=device,
                captured_image_bytes=image_bytes,
                confidence=None, authorized=False,
                error_message=res["message"], start_time=start_time
            )
            return {
                "authorized": False,
                "error_code": res["error_code"],
                "message": res["message"],
                "action": "keep_locked"
            }

        # 4. Compare with all user templates (1-to-1 max similarity)
        test_emb = res["embedding"]
        max_similarity = -1.0
        
        for stored_emb_obj in stored_embeddings:
            sim = BiometricEngine.calculate_similarity(test_emb, stored_emb_obj.embedding)
            if sim > max_similarity:
                max_similarity = sim

        threshold = getattr(settings, 'FACE_RECOGNITION_THRESHOLD', 0.65)
        authorized = max_similarity >= threshold

        # Prepare log message
        error_msg = None
        if not authorized:
            error_msg = f"Biometric mismatch: similarity {max_similarity:.3f} below threshold {threshold:.2f}"
            message = "Face verification failed"
        else:
            message = f"Welcome, {user.get_full_name() or user.username}"

        # 5. Log Attempt
        cls._log_attempt(
            user=user, card=card, device=device,
            captured_image_bytes=image_bytes,
            confidence=max_similarity, authorized=authorized,
            error_message=error_msg, start_time=start_time
        )

        return {
            "authorized": authorized,
            "confidence": round(max_similarity, 3),
            "threshold": threshold,
            "action": "unlock" if authorized else "keep_locked",
            "message": message
        }

    @classmethod
    def _log_attempt(cls, user, card, device, captured_image_bytes, confidence, authorized, error_message, start_time):
        """
        Helper method to log attempts in a separate database record.
        """
        elapsed = timezone.now() - start_time
        processing_time_ms = int(elapsed.total_seconds() * 1000.0)

        attempt = RecognitionAttempt(
            user=user,
            card=card,
            device=device,
            confidence_score=confidence,
            authorized=authorized,
            error_message=error_message,
            processing_time_ms=processing_time_ms
        )

        if captured_image_bytes:
            timestamp_str = timezone.now().strftime('%Y%m%d_%H%M%S')
            user_lbl = user.username if user else "unknown"
            filename = f"attempt_{user_lbl}_{timestamp_str}.jpg"
            attempt.captured_image.save(filename, ContentFile(captured_image_bytes), save=False)

        attempt.save()
