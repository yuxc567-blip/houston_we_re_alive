
import cv2
import mediapipe as mp
import time

# Configure MediaPipe
options = mp.tasks.vision.FaceLandmarkerOptions(
    base_options=mp.tasks.BaseOptions(
        model_asset_path="face_landmarker.task"
    ),
    running_mode=mp.tasks.vision.RunningMode.VIDEO,
    num_faces=1,
    output_face_blendshapes=True
)

cap = cv2.VideoCapture(0)

blinks = 0
blink_durations = []
eyes_closed = False
closure_start = None
start = time.monotonic()
last_timestamp = -1

with mp.tasks.vision.FaceLandmarker.create_from_options(options) as model:
    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            break

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=rgb
        )

        # MediaPipe requires increasing timestamps
        timestamp = max(
            int((time.monotonic() - start) * 1000),
            last_timestamp + 1
        )
        last_timestamp = timestamp

        result = model.detect_for_video(image, timestamp)

        if result.face_blendshapes:
            scores = {
                c.category_name: c.score
                for c in result.face_blendshapes[0]
            }

            blink_score = (
                scores.get("eyeBlinkLeft", 0) +
                scores.get("eyeBlinkRight", 0)
            ) / 2

            # Demonstration threshold; calibrate later
            closed = blink_score > 0.4 #sensitivity threshold for detecting closed eyes
            now = time.monotonic()

            if closed and not eyes_closed:
                closure_start = now

            if not closed and eyes_closed:
                duration = now - closure_start

                # Count plausible short blinks
                if 0.08 <= duration <= 0.5:
                    blinks += 1
                    blink_durations.append(duration)

                closure_start = None

            eyes_closed = closed

            cv2.putText(
                frame, f"Blink score: {blink_score:.2f}",
                (20, 40), cv2.FONT_HERSHEY_SIMPLEX,
                0.7, (0, 255, 0), 2
            )
        else:
            eyes_closed = False
            closure_start = None

        cv2.putText(
            frame, f"Blinks: {blinks}",
            (20, 80), cv2.FONT_HERSHEY_SIMPLEX,
            0.7, (0, 255, 0), 2
        )

        cv2.imshow("Fatigue Monitor", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

cap.release()
cv2.destroyAllWindows()
