import cv2
import mediapipe as mp
import math


mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils


cap = cv2.VideoCapture(0)


with mp_hands.Hands(
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7) as hands:

    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            print("Ignoring empty frame.")
            continue

        
        frame = cv2.flip(frame, 1)
        h, w, c = frame.shape

        
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(rgb_frame)

        gesture_text = "No Hand Detected"
        distance_text = ""

        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                
                mp_drawing.draw_landmarks(
                    frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

                
                landmarks = hand_landmarks.landmark

                
                x1, y1 = int(landmarks[4].x * w), int(landmarks[4].y * h)
                x2, y2 = int(landmarks[8].x * w), int(landmarks[8].y * h)

                
                cv2.circle(frame, (x1, y1), 8, (255, 0, 0), -1)
                cv2.circle(frame, (x2, y2), 8, (255, 0, 0), -1)
                cv2.line(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

                
                distance = math.hypot(x2 - x1, y2 - y1)
                distance_text = f"Distance: {int(distance)} px"

              
                if distance > 100:
                    gesture_text = "Open Hand"
                elif 60 < distance <= 100:
                    gesture_text = "Thumbs Up / Half Open"
                else:
                    gesture_text = "Fist or Pinch"

                
                cv2.putText(frame, distance_text, (20, 60),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

        
        cv2.putText(frame, gesture_text, (20, 100),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 255, 255), 3)

        
        cv2.imshow('Gesture Recognition & Distance Measurement', frame)

        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

cap.release()
cv2.destroyAllWindows()
