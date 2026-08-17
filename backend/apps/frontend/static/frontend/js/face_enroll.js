let stream = null;
let sessionId = null;
let currentStep = 0; // 0: Front, 1: Left, 2: Right

const stepLabels = ["Front View", "Left Profile View", "Right Profile View"];
const stepInstructions = [
    "Align your face inside the guide box, look directly at the camera, and keep a neutral expression.",
    "Turn your head slightly to the left (profile view) and look towards the left border of the guide.",
    "Turn your head slightly to the right (profile view) and look towards the right border of the guide."
];

document.addEventListener('DOMContentLoaded', () => {
    startWebcam();

    // Event Listeners
    document.getElementById('btn-start').addEventListener('click', startEnrollmentSession);
    document.getElementById('btn-capture').addEventListener('click', captureFrame);
});

// Enable Host Webcam
async function startWebcam() {
    const video = document.getElementById('webcam');
    if (!video) return;

    try {
        stream = await navigator.mediaDevices.getUserMedia({
            video: { width: 640, height: 480, facingMode: 'user' }
        });
        video.srcObject = stream;
    } catch (err) {
        console.error("Webcam initialization failed:", err);
        showStatusBanner("Webcam access denied. Please grant permissions and reload.", "error");
    }
}

function showStatusBanner(text, type) {
    const banner = document.getElementById('status-message');
    if (!banner) return;
    
    banner.textContent = text;
    banner.className = `status-banner ${type}`;
    banner.style.display = 'block';
    
    if (type === 'success') {
        banner.style.backgroundColor = 'var(--success-bg)';
        banner.style.borderColor = 'var(--primary-color)';
        banner.style.color = 'var(--primary-color)';
    } else {
        banner.style.backgroundColor = 'var(--error-bg)';
        banner.style.borderColor = 'var(--error-color)';
        banner.style.color = 'var(--error-color)';
    }
}

function updateStepUI() {
    const instructionBox = document.getElementById('instruction-box');
    const btnCapture = document.getElementById('btn-capture');
    const btnStart = document.getElementById('btn-start');

    if (currentStep < 3) {
        instructionBox.innerHTML = `<strong>Step ${currentStep + 1}: ${stepLabels[currentStep]}</strong><br>${stepInstructions[currentStep]}`;
        btnCapture.disabled = false;
    } else {
        instructionBox.innerHTML = `<strong>Enrollment Completed!</strong><br>The biometric profile is now active. You may register another employee.`;
        btnCapture.disabled = true;
        btnStart.disabled = false;
    }
}

async function startEnrollmentSession() {
    const username = document.getElementById('user-select').value;
    const cardUid = document.getElementById('card-uid').value.trim().toUpperCase();
    const btnStart = document.getElementById('btn-start');

    if (!username || !cardUid) {
        showStatusBanner("Please select an employee and enter a Card UID.", "error");
        return;
    }

    showStatusBanner("Initializing session...", "success");
    btnStart.disabled = true;

    const data = await API.post('/api/v1/face/web-enroll/start/', {
        username: username,
        card_uid: cardUid
    });

    if (data && data.session_id) {
        sessionId = data.session_id;
        currentStep = 0;
        
        // Reset slot containers
        for (let i = 0; i < 3; i++) {
            const slot = document.getElementById(`slot-${i}`);
            slot.className = "slot-card";
            slot.innerHTML = `<span class="slot-title">${i + 1}. ${stepLabels[i]}</span>`;
        }

        document.getElementById('slot-0').className = "slot-card active";
        updateStepUI();
        showStatusBanner(`Session active for ${data.username}.`, "success");
    } else {
        btnStart.disabled = false;
    }
}

function captureFrame() {
    if (!sessionId || currentStep >= 3) return;

    const video = document.getElementById('webcam');
    const canvas = document.getElementById('capture-canvas');
    const btnCapture = document.getElementById('btn-capture');

    const ctx = canvas.getContext('2d');
    
    // Mirror flip frame horizontally to match browser preview
    ctx.translate(canvas.width, 0);
    ctx.scale(-1, 1);
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    ctx.setTransform(1, 0, 0, 1, 0, 0); // reset transform

    canvas.toBlob(async (blob) => {
        const formData = new FormData();
        formData.append('session_id', sessionId);
        formData.append('image', blob, 'frame.jpg');
        formData.append('view_type', ['front', 'left', 'right'][currentStep]);

        showStatusBanner(`Uploading ${stepLabels[currentStep]}...`, "success");
        btnCapture.disabled = true;

        // Custom call since API.js handles JSON, but this requires Multipart Form Data headers
        const csrfToken = getCookie('csrftoken');
        try {
            const response = await fetch('/api/v1/face/web-enroll/upload/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken
                },
                body: formData
            });

            const data = await response.json();

            if (response.status === 200 || response.status === 201) {
                // Success slot marking
                const slot = document.getElementById(`slot-${currentStep}`);
                slot.className = "slot-card completed";
                
                const imgUrl = URL.createObjectURL(blob);
                slot.innerHTML = `<img src="${imgUrl}"><span class="slot-title">${stepLabels[currentStep]}</span>`;

                currentStep++;
                
                // Set next slot as active
                if (currentStep < 3) {
                    document.getElementById(`slot-${currentStep}`).className = "slot-card active";
                }

                updateStepUI();
                if (response.status === 201) {
                    showStatusBanner("Biometric profile successfully registered!", "success");
                } else {
                    showStatusBanner("Frame accepted.", "success");
                }
            } else if (response.status === 422) {
                showStatusBanner(`Rejected: ${data.message}`, "error");
            } else {
                showStatusBanner(data.error || "Upload failed.", "error");
            }
        } catch (err) {
            console.error("Frame upload failed:", err);
            showStatusBanner("Network upload failure.", "error");
        } finally {
            if (currentStep < 3) {
                btnCapture.disabled = false;
            }
        }
    }, 'image/jpeg', 0.95);
}
