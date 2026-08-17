import sys
import time
import requests
import cv2

# Disable insecure request warnings for self-signed development certificates
requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://127.0.0.1:8000/api/v1/face"
DEVICE_ID = "esp32_01"
DEVICE_TOKEN = "dev_secret_token_esp32_01"

HEADERS = {
    "X-Device-Token": DEVICE_TOKEN
}

def print_menu():
    print("\n" + "="*40)
    print("      ESP32-CAM WebCam Simulator      ")
    print("="*40)
    print("1. Enroll a New Face (Link to RFID Card)")
    print("2. Verify Face (1-to-1 Match)")
    print("3. Exit")
    print("="*40)

def capture_face_gui(prompt_message):
    """
    Opens the PC webcam window. Press SPACE to capture a frame, or ESC to cancel.
    """
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[ERROR] Could not open webcam. Make sure no other app is using it.")
        return None

    print(f"\n[CAMERA] Opening camera window. {prompt_message}")
    print("[CAMERA] Commands: Press [SPACE] to capture frame | Press [ESC] to cancel")

    captured_frame_bytes = None

    while True:
        ret, frame = cap.read()
        if not ret:
            print("[ERROR] Failed to read from webcam.")
            break

        # Display helper overlay text on frame
        display_frame = frame.copy()
        cv2.putText(display_frame, prompt_message, (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        cv2.putText(display_frame, "SPACE: Capture | ESC: Cancel", (10, 450), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

        cv2.imshow("ESP32-CAM Simulation", display_frame)

        key = cv2.waitKey(1) & 0xFF
        if key == 32:  # SPACE key
            # Encode frame to JPEG
            success, jpeg_arr = cv2.imencode('.jpg', frame)
            if success:
                captured_frame_bytes = jpeg_arr.tobytes()
                print("[CAMERA] Image captured successfully.")
            break
        elif key == 27:  # ESC key
            print("[CAMERA] Capture cancelled.")
            break

    cap.release()
    cv2.destroyAllWindows()
    return captured_frame_bytes

def run_enrollment():
    card_uid = input("\nEnter existing RFID Card UID (e.g. E9B3A2C8): ").strip().upper()
    if not card_uid:
        print("[ERROR] Card UID cannot be empty.")
        return

    # 1. Start Enrollment Session
    start_url = f"{BASE_URL}/enroll/start/"
    payload = {
        "card_uid": card_uid,
        "device_id": DEVICE_ID
    }
    
    try:
        response = requests.post(start_url, json=payload, headers=HEADERS, verify=False)
    except Exception as e:
        print(f"[ERROR] Failed to connect to server: {str(e)}")
        return

    if response.status_code != 201:
        print(f"[ERROR] Start Session Failed (HTTP {response.status_code}): {response.text}")
        return

    session_data = response.json()
    session_id = session_data["session_id"]
    images_required = session_data["images_required"]
    username = session_data["username"]

    print(f"\n[SESSION] Started session for User '{username}'.")
    print(f"[SESSION] ID: {session_id}")
    print(f"[SESSION] Needs {images_required} valid face captures.")

    images_collected = 0
    upload_url = f"{BASE_URL}/enroll/upload/"

    while images_collected < images_required:
        prompt = f"Enrollment: Capture frame {images_collected + 1}/{images_required}"
        frame_bytes = capture_face_gui(prompt)
        if frame_bytes is None:
            print("[INFO] Enrollment aborted.")
            return

        # Prepare multipart payload
        files = {
            "image": ("frame.jpg", frame_bytes, "image/jpeg")
        }
        data = {
            "session_id": session_id,
            "device_id": DEVICE_ID
        }

        print("[SERVER] Processing image on backend...")
        try:
            res = requests.post(upload_url, data=data, files=files, headers=HEADERS, verify=False)
        except Exception as e:
            print(f"[ERROR] Connection lost: {str(e)}")
            return

        if res.status_code in [200, 201]:
            res_data = res.json()
            images_collected = res_data["images_collected"]
            print(f"[SUCCESS] Server accepted frame. Progress: {images_collected}/{images_required}")
            time.sleep(1)
        elif res.status_code == 422:
            res_data = res.json()
            print(f"\n[QUALITY WARNING] Face rejected: {res_data['message']}")
            print("Please adjust your lighting/angle and try again.")
            input("Press Enter to retry capturing this frame...")
        else:
            print(f"[ERROR] Server error (HTTP {res.status_code}): {res.text}")
            return

    print("\n" + "*"*40)
    print(f" SUCCESS: Face Enrolled for {username}!")
    print("*"*40)

def run_verification():
    card_uid = input("\nEnter RFID Card UID to verify (e.g. E9B3A2C8): ").strip().upper()
    if not card_uid:
        print("[ERROR] Card UID cannot be empty.")
        return

    prompt = f"Verification: Scan face for card {card_uid}"
    frame_bytes = capture_face_gui(prompt)
    if frame_bytes is None:
        print("[INFO] Verification aborted.")
        return

    # Prepare payload
    verify_url = f"{BASE_URL}/verify/"
    files = {
        "image": ("verify.jpg", frame_bytes, "image/jpeg")
    }
    data = {
        "card_uid": card_uid,
        "device_id": DEVICE_ID
    }

    print("[SERVER] Comparing with enrolled templates...")
    try:
        res = requests.post(verify_url, data=data, files=files, headers=HEADERS, verify=False)
    except Exception as e:
        print(f"[ERROR] Failed to connect to server: {str(e)}")
        return

    if res.status_code == 200:
        res_data = res.json()
        print("\n" + "="*40)
        print(" ACCESS GRANTED ")
        print("="*40)
        print(f"Message:    {res_data['message']}")
        print(f"Confidence: {res_data['confidence']} (Threshold: {res_data['threshold']})")
        print("="*40)
    elif res.status_code == 403:
        res_data = res.json()
        print("\n" + "="*40)
        print(" ACCESS DENIED ")
        print("="*40)
        print(f"Message:    {res_data['message']}")
        if "confidence" in res_data:
            print(f"Confidence: {res_data['confidence']} (Threshold: {res_data['threshold']})")
        print("="*40)
    elif res.status_code == 422:
        res_data = res.json()
        print(f"\n[PIPELINE WARNING] Processing failed: {res_data['message']}")
    else:
        print(f"[ERROR] Request failed (HTTP {res.status_code}): {res.text}")

def main():
    while True:
        print_menu()
        choice = input("Enter option (1-3): ").strip()
        if choice == "1":
            run_enrollment()
        elif choice == "2":
            run_verification()
        elif choice == "3":
            print("\nGoodbye!")
            sys.exit(0)
        else:
            print("[ERROR] Invalid choice. Select 1, 2, or 3.")

if __name__ == "__main__":
    main()
