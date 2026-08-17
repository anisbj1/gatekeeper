import cv2
import time
import logging
import numpy as np
from django.conf import settings
from django.utils import timezone
from .services import BiometricEngine, VerificationService
from .models import FaceProfile, FaceEmbedding

logger = logging.getLogger(__name__)

class BiometricCameraVerificationService:
    @classmethod
    def verify_face_from_webcam(cls, user, device, card) -> bool:
        """
        Opens the local webcam, displays a GUI window, and automatically captures/verifies
        the face of the identified user in a non-blocking loop (up to 5 seconds).
        Returns True if recognized, False otherwise.
        """
        start_time = timezone.now()
        
        try:
            profile = user.face_profile
            if not profile.is_biometric_active:
                logger.warning(f"Biometrics deactivated for user {user.username}")
                return False
        except FaceProfile.DoesNotExist:
            logger.warning(f"No biometric profile enrolled for user {user.username}")
            return False

        stored_embeddings = list(profile.embeddings.filter(model_version='facenet_v1'))
        if not stored_embeddings:
            logger.warning(f"No embeddings found for user {user.username}")
            return False

        # Open WebCam
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            logger.error("Failed to open host webcam. Make sure it is not in use.")
            # Log failure
            VerificationService._log_attempt(
                user=user, card=card, device=device,
                captured_image_bytes=None, confidence=None,
                authorized=False, error_message="WebCam hardware unavailable",
                start_time=start_time
            )
            return False

        window_name = "Face ID Verification"
        threshold = getattr(settings, 'FACE_RECOGNITION_THRESHOLD', 0.65)
        authorized = False
        max_similarity = -1.0
        last_image_bytes = None
        error_msg = "Timeout: No matching face detected within 5 seconds"

        print(f"\n[AUTO-VERIFY] WebCam opened for user {user.username}. Scanning...")
        
        # Scan for up to 5 seconds
        timeout_seconds = 5.0
        loop_start = time.time()

        consecutive_failures = 0

        while (time.time() - loop_start) < timeout_seconds:
            ret, frame = cap.read()
            if not ret:
                consecutive_failures += 1
                if consecutive_failures >= 5:
                    error_msg = "Webcam in use by another app (e.g. browser tab)"
                    print("\n[ERROR] Webcam is already in use by another application. Please close the browser enrollment tab or other camera apps.")
                    break
                time.sleep(0.05)
                continue
            
            consecutive_failures = 0

            # Overlay guide text on the display frame
            display_frame = frame.copy()
            cv2.putText(display_frame, f"Scanning: {user.first_name} {user.last_name}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
            cv2.putText(display_frame, "Please look directly at the camera...", (10, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            cv2.putText(display_frame, "Press ESC to cancel", (10, 450),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

            cv2.imshow(window_name, display_frame)

            # Check if user wants to cancel (ESC key)
            key = cv2.waitKey(1) & 0xFF
            if key == 27:  # ESC
                error_msg = "Verification cancelled by user"
                logger.info("Verification cancelled by user")
                break

            # Convert frame to JPEG bytes for analysis
            success, jpeg_arr = cv2.imencode('.jpg', frame)
            if not success:
                continue
            image_bytes = jpeg_arr.tobytes()
            last_image_bytes = image_bytes

            # Run biometric quality & alignment pipeline
            res = BiometricEngine.process_and_extract(image_bytes)
            if not res["success"]:
                # Frame failed quality check (e.g. blurry, poor lighting, no face).
                # Show quality error code on screen briefly
                cv2.putText(display_frame, f"Quality: {res['message']}", (10, 90),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
                cv2.imshow(window_name, display_frame)
                continue

            # Frame accepted, match embedding (1-to-1)
            test_emb = res["embedding"]
            current_max_sim = -1.0
            for stored_emb_obj in stored_embeddings:
                sim = BiometricEngine.calculate_similarity(test_emb, stored_emb_obj.embedding)
                if sim > current_max_sim:
                    current_max_sim = sim

            if current_max_sim > max_similarity:
                max_similarity = current_max_sim

            if max_similarity >= threshold:
                # Match succeeded!
                authorized = True
                error_msg = None
                print(f"[AUTO-VERIFY] Face match success. Similarity: {max_similarity:.3f}")
                break

        # Release resources
        cap.release()
        cv2.destroyAllWindows()
        # Call cv2.waitKey several times to ensure window closes immediately on Windows
        for _ in range(4):
            cv2.waitKey(1)

        # Log attempt
        VerificationService._log_attempt(
            user=user, card=card, device=device,
            captured_image_bytes=last_image_bytes,
            confidence=max_similarity if max_similarity >= 0 else None,
            authorized=authorized,
            error_message=error_msg,
            start_time=start_time
        )

        return authorized
