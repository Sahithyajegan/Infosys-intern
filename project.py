import customtkinter as ctk
from tkinter import messagebox
import cv2
import mediapipe as mp
import math
import numpy as np
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

# User database for demo
user_db = {"Meenakshi": "Sokerr"}

def gesture_volume_control():
    mp_hands = mp.solutions.hands
    mp_drawing = mp.solutions.drawing_utils
    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    volume = cast(interface, POINTER(IAudioEndpointVolume))
    vol_min, vol_max = volume.GetVolumeRange()[:2]
    cap = cv2.VideoCapture(0)
    with mp_hands.Hands(static_image_mode=False,
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
            volume_percent = 0
            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                    x1, y1 = int(hand_landmarks.landmark[4].x * w), int(hand_landmarks.landmark[4].y * h)
                    x2, y2 = int(hand_landmarks.landmark[8].x * w), int(hand_landmarks.landmark[8].y * h)
                    cv2.circle(frame, (x1, y1), 10, (255, 0, 0), -1)
                    cv2.circle(frame, (x2, y2), 10, (255, 0, 0), -1)
                    cv2.line(frame, (x1, y1), (x2, y2), (0, 255, 0), 3)
                    length = math.hypot(x2 - x1, y2 - y1)
                    distance_text = f"Distance: {int(length)} px"
                    if length > 100:
                        gesture_text = "Open Hand"
                    elif 60 < length <= 100:
                        gesture_text = "Thumbs Up Half Open"
                    else:
                        gesture_text = "Fist or Pinch"
                    vol = np.interp(length, [30, 200], [vol_min, vol_max])
                    volume.SetMasterVolumeLevel(vol, None)
                    vol_bar = np.interp(length, [30, 200], [400, 150])
                    volume_percent = int(np.interp(length, [30, 200], [0, 100]))
                    cv2.rectangle(frame, (50, 150), (85, 400), (0, 255, 0), 3)
                    cv2.rectangle(frame, (50, int(vol_bar)), (85, 400), (0, 255, 0), -1)
                    cv2.putText(frame, f'{volume_percent} %', (40, 430), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 3)
            cv2.putText(frame, distance_text, (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            cv2.putText(frame, gesture_text, (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 255, 255), 3)
            cv2.imshow("Hand Detection, Gesture, and Volume Control", frame)
            if cv2.waitKey(30) & 0xFF == ord('q'):   # Increased delay here
                break
    cap.release()
    cv2.destroyAllWindows()


def show_register():
    login_frame.pack_forget()
    register_frame.pack(fill="both", expand=True)

def show_login():
    register_frame.pack_forget()
    login_frame.pack(fill="both", expand=True)

def do_register():
    uname = reg_username.get().strip()
    pwd = reg_password.get().strip()
    if not uname or not pwd:
        messagebox.showerror("Error", "Please fill all fields.")
    elif uname in user_db:
        messagebox.showerror("Error", "Username already exists.")
    else:
        user_db[uname] = pwd
        messagebox.showinfo("Success", "Registration successful! Please login.")
        show_login()

def login():
    username = username_entry.get().strip()
    password = password_entry.get().strip()
    if username in user_db and user_db[username] == password:
        root.destroy()
        gesture_volume_control()
    else:
        messagebox.showerror("Login Failed", "Invalid username or password")

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

root = ctk.CTk()
root.geometry("800x700")
root.title("Gesture Volume Control")

# Login frame
login_frame = ctk.CTkFrame(root,fg_color="black")
login_frame.pack(fill="both", expand=True,)

login_center = ctk.CTkFrame(login_frame, fg_color="white", width=500, height=500)
login_center.pack(expand=True)
login_center.pack_propagate(False)

welcome_label = ctk.CTkLabel(login_center,
                             text="Welcome to Gesture volume control",
                             font=ctk.CTkFont(size=26, weight="bold"),)
welcome_label.pack(pady=(20, 30))

username_entry = ctk.CTkEntry(login_center, width=350, height=45, placeholder_text="User Name")
username_entry.pack(pady=15)
password_entry = ctk.CTkEntry(login_center, width=350, height=45, placeholder_text="Password", show="*")
password_entry.pack(pady=10)
remember_me = ctk.CTkCheckBox(login_center, text="Remember me")
remember_me.pack(pady=(8, 0),padx=(30,0), anchor="w")

login_btn = ctk.CTkButton(login_center, text="Login", width=350, height=45, command=login, fg_color="red")
login_btn.pack(pady=20)

register_container = ctk.CTkFrame(login_center, fg_color="white")
register_container.pack(pady=10)
register_label = ctk.CTkLabel(register_container, text="Don't have an account?")
register_label.pack(side="left", pady=(10, 0))
register_link = ctk.CTkLabel(register_container, text="Register", text_color="blue", cursor="hand2", font=ctk.CTkFont(weight="bold"))
register_link.pack(side="left", padx=(2, 0), pady=(10, 0))
register_link.bind("<Button-1>", lambda e: show_register())

# Register frame
register_frame = ctk.CTkFrame(root,fg_color="black")

register_center = ctk.CTkFrame(register_frame, fg_color="white", width=500, height=500)
register_center.pack(expand=True)
register_center.pack_propagate(False)

register_label = ctk.CTkLabel(register_center, text="Register", font=ctk.CTkFont(size=26, weight="bold"))
register_label.pack(pady=(20, 30))

reg_username = ctk.CTkEntry(register_center, width=350, height=45, placeholder_text="User Name")
reg_username.pack(pady=15)
reg_password = ctk.CTkEntry(register_center, width=350, height=45, placeholder_text="Password", show="*")
reg_password.pack(pady=10)

register_btn = ctk.CTkButton(register_center, text="Register", width=350, height=45, command=do_register, fg_color="green")
register_btn.pack(pady=20)

back_to_login = ctk.CTkLabel(register_center, text="Back to Login", text_color="blue", cursor="hand2", font=ctk.CTkFont(weight="bold"))
back_to_login.pack()
back_to_login.bind("<Button-1>", lambda e: show_login())

root.mainloop()    