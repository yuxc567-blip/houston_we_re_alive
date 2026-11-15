const startButton = document.getElementById('start-camera');
const stopButton = document.getElementById('stop-camera');
const video = document.getElementById('preview');
const blinkScoreOutput = document.getElementById('blink-score');
const blinkCountOutput = document.getElementById('blink-count');
const status = document.getElementById('status');

const blinkThreshold = 0.4;
const minimumBlinkSeconds = 0.08;
const maximumBlinkSeconds = 0.5;
let stream;
let faceLandmarker;
let animationFrame = 0;
let lastVideoTime = -1;
let blinkCount = 0;
let eyesClosed = false;
let closureStart = null;
let running = false;

function stopCamera() {
    running = false;
    cancelAnimationFrame(animationFrame);
    if (stream) {
        stream.getTracks().forEach(track => track.stop());
        stream = null;
    }
    if (faceLandmarker) {
        faceLandmarker.close();
        faceLandmarker = null;
    }
    video.srcObject = null;
    eyesClosed = false;
    closureStart = null;
    lastVideoTime = -1;
    startButton.disabled = false;
    stopButton.disabled = true;
}

function detectFrame() {
    if (!running || !faceLandmarker) return;

    if (video.readyState >= HTMLMediaElement.HAVE_CURRENT_DATA && video.currentTime !== lastVideoTime) {
        lastVideoTime = video.currentTime;
        const result = faceLandmarker.detectForVideo(video, performance.now());
        const categories = result.faceBlendshapes?.[0]?.categories;

        if (categories?.length) {
            const scores = Object.fromEntries(
                categories.map(category => [category.categoryName, category.score])
            );
            const blinkScore = (
                (scores.eyeBlinkLeft ?? 0) + (scores.eyeBlinkRight ?? 0)
            ) / 2;
            const closed = blinkScore > blinkThreshold;
            const now = performance.now();

            blinkScoreOutput.value = blinkScore.toFixed(2);
            status.textContent = 'Camera is on. Look toward the camera.';

            if (closed && !eyesClosed) {
                closureStart = now;
            }

            if (!closed && eyesClosed && closureStart !== null) {
                const durationSeconds = (now - closureStart) / 1000;
                if (durationSeconds >= minimumBlinkSeconds && durationSeconds <= maximumBlinkSeconds) {
                    blinkCount += 1;
                    blinkCountOutput.value = String(blinkCount);
                }
                closureStart = null;
            }

            eyesClosed = closed;
        } else {
            blinkScoreOutput.value = '—';
            status.textContent = 'No face detected.';
            eyesClosed = false;
            closureStart = null;
        }
    }

    animationFrame = requestAnimationFrame(detectFrame);
}

startButton.addEventListener('click', async () => {
    startButton.disabled = true;
    status.textContent = 'Requesting camera access...';

    try {
        if (!navigator.mediaDevices?.getUserMedia) {
            throw new Error('Camera access requires HTTPS or localhost in a supported browser.');
        }

        stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
        video.srcObject = stream;
        await video.play();

        status.textContent = 'Loading face model...';
        const visionModule = await import(
            'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@latest/vision_bundle.mjs'
        );
        const vision = await visionModule.FilesetResolver.forVisionTasks(
            'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@latest/wasm'
        );
        faceLandmarker = await visionModule.FaceLandmarker.createFromOptions(vision, {
            baseOptions: { modelAssetPath: './face_landmarker.task' },
            runningMode: 'VIDEO',
            numFaces: 1,
            outputFaceBlendshapes: true
        });

        running = true;
        stopButton.disabled = false;
        status.textContent = 'Camera is on. Look toward the camera.';
        detectFrame();
    } catch (error) {
        stopCamera();
        status.textContent = `Could not start blink detection: ${error.message}`;
    }
});

stopButton.addEventListener('click', () => {
    stopCamera();
    status.textContent = 'Camera is off.';
    blinkScoreOutput.value = '—';
});

window.addEventListener('beforeunload', stopCamera);