import uuid
from PIL import Image
from io import BytesIO
from unittest.mock import patch
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from apps.access_control.models import Device, Card, AccessRule
from .models import EnrollmentSession, FaceProfile, FaceImage, FaceEmbedding, RecognitionAttempt
from .services import BiometricEngine, EnrollmentService, VerificationService

class BiometricTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        
        # Create test user
        self.user = User.objects.create_user(
            username='test_worker',
            email='test@example.com',
            password='password123',
            first_name='Test',
            last_name='Worker'
        )
        
        # Create test card
        self.card = Card.objects.create(
            uid='A1B2C3D4',
            user=self.user,
            is_active=True
        )
        
        # Create test device
        self.device = Device.objects.create(
            device_id='test_esp32_01',
            name='Test ESP32 Controller',
            api_token='supersecrettoken123',
            is_active=True
        )
        
        # Set authorization header in client
        self.client.credentials(HTTP_X_DEVICE_TOKEN=self.device.api_token)

        # Create a real, valid small JPEG image in memory for testing
        img = Image.new('RGB', (100, 100), color='white')
        img_bytes = BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        
        self.dummy_image = SimpleUploadedFile(
            name='test_face.jpg',
            content=img_bytes.read(),
            content_type='image/jpeg'
        )

    def test_enrollment_start_success(self):
        url = reverse('enroll-start')
        data = {
            'card_uid': self.card.uid,
            'device_id': self.device.device_id
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('session_id', response.data)
        self.assertEqual(response.data['status'], 'PENDING')
        self.assertEqual(response.data['username'], self.user.username)
        
        # Check database record
        session = EnrollmentSession.objects.get(id=response.data['session_id'])
        self.assertEqual(session.user, self.user)
        self.assertEqual(session.device, self.device)

    def test_enrollment_start_invalid_card(self):
        url = reverse('enroll-start')
        data = {
            'card_uid': 'FFFFFFFF',  # Unknown card
            'device_id': self.device.device_id
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch('apps.face_recognition.services.BiometricEngine.process_and_extract')
    def test_enrollment_upload_and_complete_workflow(self, mock_process):
        # Setup mock return value for a successful frame extraction
        fake_embedding = [0.1] * 512
        mock_process.return_value = {
            "success": True,
            "error_code": None,
            "message": "Quality checks passed",
            "cropped_face_np": (np := __import__('numpy')).zeros((160, 160, 3), dtype=np.uint8),
            "embedding": fake_embedding,
            "confidence": 0.99
        }

        # Start session
        session = EnrollmentService.start_session(self.user, self.device)
        self.assertEqual(session.status, 'PENDING')

        url = reverse('enroll-upload')
        
        # Upload 4 frames (should keep session COLLECTING)
        for i in range(4):
            data = {
                'session_id': str(session.id),
                'device_id': self.device.device_id,
                'image': self.dummy_image
            }
            # Rewind file pointer
            self.dummy_image.seek(0)
            response = self.client.post(url, data, format='multipart')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data['images_collected'], i + 1)
            self.assertEqual(response.data['status'], 'COLLECTING')

        # Upload 5th frame (should transition to COMPLETED)
        data = {
            'session_id': str(session.id),
            'device_id': self.device.device_id,
            'image': self.dummy_image
        }
        self.dummy_image.seek(0)
        response = self.client.post(url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['images_collected'], 5)
        self.assertEqual(response.data['status'], 'COMPLETED')

        # Verify biometric profile in DB
        profile = FaceProfile.objects.get(user=self.user)
        self.assertTrue(profile.is_biometric_active)
        self.assertEqual(profile.images.count(), 5)
        self.assertEqual(profile.embeddings.count(), 5)

        # Check reference photo set
        ref_image = profile.images.filter(is_reference=True).first()
        self.assertIsNotNone(ref_image)

    @patch('apps.face_recognition.services.BiometricEngine.process_and_extract')
    def test_enrollment_quality_fail_rejection(self, mock_process):
        # Setup mock return value for a blurry frame
        mock_process.return_value = {
            "success": False,
            "error_code": "IMAGE_BLURRY",
            "message": "Image is blurry",
            "cropped_face_np": None,
            "embedding": None,
            "confidence": None
        }

        session = EnrollmentService.start_session(self.user, self.device)
        url = reverse('enroll-upload')
        data = {
            'session_id': str(session.id),
            'device_id': self.device.device_id,
            'image': self.dummy_image
        }
        
        response = self.client.post(url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertEqual(response.data['error_code'], 'IMAGE_BLURRY')
        
        # Verify no images were saved
        session.refresh_from_db()
        self.assertEqual(session.images_collected, 0)
        self.assertEqual(session.status, 'COLLECTING')

    @patch('apps.face_recognition.services.BiometricEngine.process_and_extract')
    @patch('apps.face_recognition.services.BiometricEngine.calculate_similarity')
    def test_biometric_verification_success(self, mock_sim, mock_process):
        # Create a mock profile with embeddings
        profile = FaceProfile.objects.create(user=self.user, is_biometric_active=True)
        FaceEmbedding.objects.create(profile=profile, embedding=[0.1]*512)

        mock_process.return_value = {
            "success": True,
            "error_code": None,
            "message": "Face processed",
            "cropped_face_np": None,
            "embedding": [0.1]*512,
            "confidence": 0.99
        }
        mock_sim.return_value = 0.88  # similarity score

        url = reverse('biometric-verify')
        data = {
            'card_uid': self.card.uid,
            'device_id': self.device.device_id,
            'image': self.dummy_image
        }

        response = self.client.post(url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['authorized'])
        self.assertEqual(response.data['action'], 'unlock')

        # Check RecognitionAttempt log
        attempt = RecognitionAttempt.objects.latest('timestamp')
        self.assertEqual(attempt.user, self.user)
        self.assertTrue(attempt.authorized)
        self.assertEqual(attempt.confidence_score, 0.88)

    @patch('apps.face_recognition.services.BiometricEngine.process_and_extract')
    @patch('apps.face_recognition.services.BiometricEngine.calculate_similarity')
    def test_biometric_verification_mismatch(self, mock_sim, mock_process):
        profile = FaceProfile.objects.create(user=self.user, is_biometric_active=True)
        FaceEmbedding.objects.create(profile=profile, embedding=[0.1]*512)

        mock_process.return_value = {
            "success": True,
            "error_code": None,
            "message": "Face processed",
            "cropped_face_np": None,
            "embedding": [0.2]*512,
            "confidence": 0.99
        }
        mock_sim.return_value = 0.40  # Mismatch score

        url = reverse('biometric-verify')
        data = {
            'card_uid': self.card.uid,
            'device_id': self.device.device_id,
            'image': self.dummy_image
        }

        response = self.client.post(url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(response.data['authorized'])
        self.assertEqual(response.data['action'], 'keep_locked')

        attempt = RecognitionAttempt.objects.latest('timestamp')
        self.assertFalse(attempt.authorized)
        self.assertIn("similarity 0.400 below threshold", attempt.error_message)

    @patch('apps.face_recognition.services.BiometricEngine.process_and_extract')
    def test_biometric_verification_no_face(self, mock_process):
        profile = FaceProfile.objects.create(user=self.user, is_biometric_active=True)
        FaceEmbedding.objects.create(profile=profile, embedding=[0.1]*512)

        mock_process.return_value = {
            "success": False,
            "error_code": "NO_FACE_DETECTED",
            "message": "No face detected in the image",
            "cropped_face_np": None,
            "embedding": None,
            "confidence": None
        }

        url = reverse('biometric-verify')
        data = {
            'card_uid': self.card.uid,
            'device_id': self.device.device_id,
            'image': self.dummy_image
        }

        response = self.client.post(url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertFalse(response.data['authorized'])
        self.assertEqual(response.data['error_code'], 'NO_FACE_DETECTED')

        attempt = RecognitionAttempt.objects.latest('timestamp')
        self.assertFalse(attempt.authorized)
        self.assertEqual(attempt.error_message, "No face detected in the image")

    def test_profile_admin_only_retrieval(self):
        # Create biometric profile
        profile = FaceProfile.objects.create(user=self.user, is_biometric_active=True)
        
        # Test request with standard token (device auth) - should fail because IsAdminUser is required
        url = reverse('biometric-profile', args=[self.user.username])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Authenticate as Django Admin/Superuser
        admin_user = User.objects.create_superuser('admin', 'admin@example.com', 'adminpass')
        self.client.force_authenticate(user=admin_user)
        
        # GET profile details
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], self.user.username)
        self.assertEqual(response.data['embeddings_count'], 0)

        # DELETE profile
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify deleted in DB
        with self.assertRaises(FaceProfile.DoesNotExist):
            FaceProfile.objects.get(user=self.user)

    def test_web_enrollment_start_success(self):
        admin_user = User.objects.create_superuser('admin_enroll', 'admin@example.com', 'adminpass')
        self.client.force_authenticate(user=admin_user)
        
        # Test starting web enrollment
        url = reverse('web-enroll-start')
        data = {
            'username': self.user.username,
            'card_uid': 'E5E5E5E5'  # New Card
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('session_id', response.data)
        self.assertEqual(response.data['images_required'], 3)

        # Check that the card was created
        card = Card.objects.get(uid='E5E5E5E5')
        self.assertEqual(card.user, self.user)

    @patch('apps.face_recognition.services.BiometricEngine.process_and_extract')
    def test_web_enrollment_upload_and_complete_workflow(self, mock_process):
        admin_user = User.objects.create_superuser('admin_upload', 'admin@example.com', 'adminpass')
        self.client.force_authenticate(user=admin_user)

        fake_embedding = [0.1] * 512
        mock_process.return_value = {
            "success": True,
            "error_code": None,
            "message": "Quality checks passed",
            "cropped_face_np": (np := __import__('numpy')).zeros((160, 160, 3), dtype=np.uint8),
            "embedding": fake_embedding,
            "confidence": 0.99
        }

        # Start session
        session = EnrollmentSession.objects.create(
            user=self.user,
            device=self.device,
            status='PENDING',
            images_required=3,
            images_collected=0,
            expires_at=timezone.now() + timezone.timedelta(minutes=2)
        )

        url = reverse('web-enroll-upload')
        
        # Upload 2 frames (COLLECTING)
        for i in range(2):
            data = {
                'session_id': str(session.id),
                'image': self.dummy_image
            }
            self.dummy_image.seek(0)
            response = self.client.post(url, data, format='multipart')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data['images_collected'], i + 1)
            self.assertEqual(response.data['status'], 'COLLECTING')

        # Upload 3rd frame (COMPLETED)
        data = {
            'session_id': str(session.id),
            'image': self.dummy_image
        }
        self.dummy_image.seek(0)
        response = self.client.post(url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['images_collected'], 3)
        self.assertEqual(response.data['status'], 'COMPLETED')

    @patch('apps.face_recognition.web_services.BiometricCameraVerificationService.verify_face_from_webcam')
    def test_access_verify_with_face_trigger_success(self, mock_webcam):
        # Create access rule so RFID passes
        AccessRule.objects.create(card=self.card, device=self.device, is_active=True)
        # Create biometric profile for user
        FaceProfile.objects.create(user=self.user, is_biometric_active=True)

        mock_webcam.return_value = True

        # Call access/verify/ using device token headers
        url = '/api/v1/access/verify/'
        data = {
            'card_uid': self.card.uid,
            'device_id': self.device.device_id
        }

        # Ensure we authenticate using the device token (reset standard auth)
        self.client.force_authenticate(user=None)
        response = self.client.post(
            url, data, format='json', 
            headers={'X-Device-Token': self.device.api_token}
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['authorized'])
        self.assertEqual(response.data['action'], 'unlock')
        mock_webcam.assert_called_once_with(user=self.user, device=self.device, card=self.card)

    @patch('apps.face_recognition.web_services.BiometricCameraVerificationService.verify_face_from_webcam')
    def test_access_verify_with_face_trigger_failure(self, mock_webcam):
        # Create access rule so RFID passes
        AccessRule.objects.create(card=self.card, device=self.device, is_active=True)
        # Create biometric profile for user
        FaceProfile.objects.create(user=self.user, is_biometric_active=True)
        
        mock_webcam.return_value = False

        url = '/api/v1/access/verify/'
        data = {
            'card_uid': self.card.uid,
            'device_id': self.device.device_id
        }

        self.client.force_authenticate(user=None)
        response = self.client.post(
            url, data, format='json', 
            headers={'X-Device-Token': self.device.api_token}
        )
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(response.data['authorized'])
        self.assertEqual(response.data['action'], 'keep_locked')
        self.assertEqual(response.data['message'], 'Face ID Failed')

