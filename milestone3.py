import cv2
import mediapipe as mp
import math
import numpy as np
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume


mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils


devices = AudioUtilities.GetSpeakers()
interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
volume = cast(interface, POINTER(IAudioEndpointVolume))


vol_min, vol_max = volume.GetVolumeRange()[:2]


cap = cv2.VideoCapture(0)

with mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7, min_tracking_confidence=0.7) as hands:
    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            continue

        frame = cv2.flip(frame, 1)
        h, w, c = frame.shape
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(rgb_frame)

        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

                
                x1, y1 = int(hand_landmarks.landmark[4].x * w), int(hand_landmarks.landmark[4].y * h)
                x2, y2 = int(hand_landmarks.landmark[8].x * w), int(hand_landmarks.landmark[8].y * h)

                
                cv2.circle(frame, (x1, y1), 10, (255, 0, 0), -1)
                cv2.circle(frame, (x2, y2), 10, (255, 0, 0), -1)
                cv2.line(frame, (x1, y1), (x2, y2), (0, 255, 0), 3)

                
                length = math.hypot(x2 - x1, y2 - y1)

                
                vol = np.interp(length, [30, 200], [vol_min, vol_max])
                volume.SetMasterVolumeLevel(vol, None)

                
                vol_bar = np.interp(length, [30, 200], [400, 150])
                cv2.rectangle(frame, (50, 150), (85, 400), (0, 255, 0), 3)
                cv2.rectangle(frame, (50, int(vol_bar)), (85, 400), (0, 255, 0), -1)
                cv2.putText(frame, f'{int(np.interp(length, [30,200],[0,100]))} %', (40, 430), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 3)

        cv2.imshow("Hand Volume Control", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

cap.release()
cv2.destroyAllWindows()
