import customtkinter as ctk
from tkinter import messagebox
import cv2
import mediapipe as mp
import math
import numpy as np
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
import sqlite3
from PIL import Image, ImageTk
import threading
import time

# Database Setup
def init_database():
    """Initialize SQLite database with users table"""
    conn = sqlite3.connect('gesture_control.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def register_user(username, password):
    """Register a new user in the database"""
    try:
        conn = sqlite3.connect('gesture_control.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', 
                      (username, password))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False

def verify_user(username, password):
    """Verify user credentials"""
    conn = sqlite3.connect('gesture_control.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ? AND password = ?', 
                  (username, password))
    user = cursor.fetchone()
    conn.close()
    return user is not None

class GestureControlApp:
    def __init__(self):
        # Initialize database
        init_database()
        
        # Setup main window
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")
        
        self.root = ctk.CTk()
        self.root.geometry("1200x800")
        self.root.title("Gesture Volume Control System")
        
        # Variables for gesture control
        self.is_running = False
        self.current_user = None
        
        # Performance metrics
        self.metrics = {
            'accuracy': 0,
            'response_time': 0,
            'finger_distance': 0,
            'current_volume': 0
        }
        
        # Graph data for volume history
        self.volume_history = []
        self.max_history_points = 50  # Keep last 50 data points
        
        # Flag to track if graph updates are active
        self.graph_update_active = False
        
        # Create frames
        self.create_login_frame()
        self.create_register_frame()
        self.create_dashboard_frame()
        
        # Show login frame initially
        self.show_login()
        
        self.root.mainloop()
    
    def create_login_frame(self):
        """Create the login interface"""
        self.login_frame = ctk.CTkFrame(self.root, fg_color="#1a1a1a")
        
        # Center container
        login_center = ctk.CTkFrame(self.login_frame, fg_color="white", 
                                   width=500, height=550, corner_radius=15)
        login_center.place(relx=0.5, rely=0.5, anchor="center")
        login_center.pack_propagate(False)
        
        # Welcome message
        ctk.CTkLabel(login_center, 
                    text="Gesture Volume Control",
                    font=ctk.CTkFont(size=32, weight="bold"),
                    text_color="#333333").pack(pady=(40, 10))
        
        ctk.CTkLabel(login_center, 
                    text="Control your system volume with hand gestures",
                    font=ctk.CTkFont(size=14),
                    text_color="#666666").pack(pady=(0, 40))
        
        # Username entry
        self.username_entry = ctk.CTkEntry(login_center, width=380, height=50, 
                                          placeholder_text="Username",
                                          font=ctk.CTkFont(size=14),
                                          corner_radius=10)
        self.username_entry.pack(pady=12)
        
        # Password entry
        self.password_entry = ctk.CTkEntry(login_center, width=380, height=50, 
                                          placeholder_text="Password",
                                          show="●",
                                          font=ctk.CTkFont(size=14),
                                          corner_radius=10)
        self.password_entry.pack(pady=12)
        
        # Remember me checkbox
        ctk.CTkCheckBox(login_center, text="Remember me",
                       font=ctk.CTkFont(size=12)).pack(pady=10, padx=60, anchor="w")
        
        # Login button
        ctk.CTkButton(login_center, text="Login", width=380, height=50,
                     command=self.login,
                     fg_color="#FF5722",
                     hover_color="#E64A19",
                     font=ctk.CTkFont(size=16, weight="bold"),
                     corner_radius=10).pack(pady=20)
        
        # Register link
        register_frame = ctk.CTkFrame(login_center, fg_color="white")
        register_frame.pack(pady=15)
        
        ctk.CTkLabel(register_frame, text="Don't have an account?",
                    text_color="#666666",
                    font=ctk.CTkFont(size=13)).pack(side="left")
        
        register_btn = ctk.CTkLabel(register_frame, text="Register",
                                   text_color="#2196F3",
                                   font=ctk.CTkFont(size=13, weight="bold"),
                                   cursor="hand2")
        register_btn.pack(side="left", padx=(5, 0))
        register_btn.bind("<Button-1>", lambda e: self.show_register())
    
    def create_register_frame(self):
        """Create the registration interface"""
        self.register_frame = ctk.CTkFrame(self.root, fg_color="#1a1a1a")
        
        # Center container
        register_center = ctk.CTkFrame(self.register_frame, fg_color="white", 
                                      width=500, height=550, corner_radius=15)
        register_center.place(relx=0.5, rely=0.5, anchor="center")
        register_center.pack_propagate(False)
        
        # Title
        ctk.CTkLabel(register_center, 
                    text="Create Account",
                    font=ctk.CTkFont(size=32, weight="bold"),
                    text_color="#333333").pack(pady=(40, 10))
        
        ctk.CTkLabel(register_center, 
                    text="Join us to control volume with gestures",
                    font=ctk.CTkFont(size=14),
                    text_color="#666666").pack(pady=(0, 40))
        
        # Username entry
        self.reg_username = ctk.CTkEntry(register_center, width=380, height=50, 
                                        placeholder_text="Username",
                                        font=ctk.CTkFont(size=14),
                                        corner_radius=10)
        self.reg_username.pack(pady=12)
        
        # Password entry
        self.reg_password = ctk.CTkEntry(register_center, width=380, height=50, 
                                        placeholder_text="Password",
                                        show="●",
                                        font=ctk.CTkFont(size=14),
                                        corner_radius=10)
        self.reg_password.pack(pady=12)
        
        # Confirm password entry
        self.reg_confirm_password = ctk.CTkEntry(register_center, width=380, height=50, 
                                                placeholder_text="Confirm Password",
                                                show="●",
                                                font=ctk.CTkFont(size=14),
                                                corner_radius=10)
        self.reg_confirm_password.pack(pady=12)
        
        # Register button
        ctk.CTkButton(register_center, text="Register", width=380, height=50,
                     command=self.register,
                     fg_color="#4CAF50",
                     hover_color="#45a049",
                     font=ctk.CTkFont(size=16, weight="bold"),
                     corner_radius=10).pack(pady=20)
        
        # Back to login link
        back_btn = ctk.CTkLabel(register_center, text="← Back to Login",
                               text_color="#2196F3",
                               font=ctk.CTkFont(size=13, weight="bold"),
                               cursor="hand2")
        back_btn.pack(pady=15)
        back_btn.bind("<Button-1>", lambda e: self.show_login())
    
    def create_dashboard_frame(self):
        """Create the main dashboard interface"""
        self.dashboard_frame = ctk.CTkFrame(self.root, fg_color="#f5f5f5")
        
        # Header
        header = ctk.CTkFrame(self.dashboard_frame, fg_color="#FF5722", height=80)
        header.pack(fill="x", padx=0, pady=0)
        header.pack_propagate(False)
        
        ctk.CTkLabel(header, text="Gesture Control Interface",
                    font=ctk.CTkFont(size=28, weight="bold"),
                    text_color="white").pack(side="left", padx=30, pady=20)
        
        # Control buttons in header
        button_frame = ctk.CTkFrame(header, fg_color="transparent")
        button_frame.pack(side="right", padx=30)
        
        self.start_btn = ctk.CTkButton(button_frame, text="▶ Start", width=100, height=35,
                                       command=self.start_gesture_control,
                                       fg_color="#4CAF50",
                                       hover_color="#45a049",
                                       corner_radius=8)
        self.start_btn.pack(side="left", padx=5)
        
        self.pause_btn = ctk.CTkButton(button_frame, text="⏸ Pause", width=100, height=35,
                                       command=self.pause_gesture_control,
                                       fg_color="#FF9800",
                                       hover_color="#F57C00",
                                       corner_radius=8,
                                       state="disabled")
        self.pause_btn.pack(side="left", padx=5)
        
        # Add a test button to manually test the graph
        ctk.CTkButton(button_frame, text="📊 Test Graph", width=100, height=35,
                     command=self.test_graph,
                     fg_color="#9C27B0",
                     hover_color="#7B1FA2",
                     corner_radius=8).pack(side="left", padx=5)
        
        ctk.CTkButton(button_frame, text="⚙ Settings", width=100, height=35,
                     fg_color="#607D8B",
                     hover_color="#546E7A",
                     corner_radius=8).pack(side="left", padx=5)
        
        # Main content area
        content = ctk.CTkFrame(self.dashboard_frame, fg_color="#f5f5f5")
        content.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Left side - Live Gesture Control
        left_panel = ctk.CTkFrame(content, fg_color="white", corner_radius=15)
        left_panel.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        ctk.CTkLabel(left_panel, text="🎥 Live Gesture Control",
                    font=ctk.CTkFont(size=18, weight="bold"),
                    text_color="#333333").pack(pady=15, padx=20, anchor="w")
        
        # Video display area
        self.video_label = ctk.CTkLabel(left_panel, text="", fg_color="#e0e0e0")
        self.video_label.pack(padx=20, pady=(0, 20), fill="both", expand=True)
        
        # Gesture status
        self.gesture_status = ctk.CTkLabel(left_panel, 
                                          text="Pinch Gesture",
                                          font=ctk.CTkFont(size=14),
                                          text_color="white",
                                          fg_color="#FF5722",
                                          corner_radius=8,
                                          width=150,
                                          height=35)
        self.gesture_status.pack(pady=(0, 15))
        
        # Add graph canvas below video
        graph_frame = ctk.CTkFrame(left_panel, fg_color="#f5f5f5", corner_radius=10, height=150)
        graph_frame.pack(padx=20, pady=(0, 20), fill="x")
        graph_frame.pack_propagate(False)
        
        ctk.CTkLabel(graph_frame, text="📈 Volume History",
                    font=ctk.CTkFont(size=14, weight="bold"),
                    text_color="#333333").pack(pady=(10, 5), padx=15, anchor="w")
        
        # Add status label for graph debugging
        self.graph_status_label = ctk.CTkLabel(graph_frame, 
                                               text="Ready - waiting for data",
                                               font=ctk.CTkFont(size=10),
                                               text_color="#666666")
        self.graph_status_label.pack(pady=(0, 5), padx=15, anchor="w")
        
        # Canvas for drawing the graph - give it a fixed size initially
        from tkinter import Canvas
        self.graph_canvas = Canvas(graph_frame, bg="white", highlightthickness=0, 
                                   height=90, width=800)
        self.graph_canvas.pack(fill="both", expand=True, padx=15, pady=(0, 10))
        
        # Force canvas to update and get proper dimensions
        self.graph_canvas.update_idletasks()
        
        # Draw initial empty graph
        self.root.after(100, self.draw_volume_graph)
        
        # Right side - Gesture Recognition & Metrics
        right_panel = ctk.CTkFrame(content, fg_color="white", 
                                  corner_radius=15, width=350)
        right_panel.pack(side="right", fill="y", padx=(10, 0))
        right_panel.pack_propagate(False)
        
        ctk.CTkLabel(right_panel, text="🎯 Gesture Recognition",
                    font=ctk.CTkFont(size=18, weight="bold"),
                    text_color="#333333").pack(pady=15, padx=20, anchor="w")
        
        # Gesture status cards
        self.create_gesture_card(right_panel, "Open Hand", "Distance > 100px", "Inactive", "#e0e0e0")
        self.create_gesture_card(right_panel, "Pinch", "Distance < 60px", "Active", "#4CAF50")
        self.create_gesture_card(right_panel, "Closed", "Distance < 30px", "Inactive", "#e0e0e0")
        
        # Performance Metrics section
        ctk.CTkLabel(right_panel, text="📊 Performance Metrics",
                    font=ctk.CTkFont(size=18, weight="bold"),
                    text_color="#333333").pack(pady=(20, 15), padx=20, anchor="w")
        
        # Metrics grid
        metrics_container = ctk.CTkFrame(right_panel, fg_color="white")
        metrics_container.pack(padx=20, pady=(0, 20), fill="x")
        
        # Create metric displays
        self.metric_labels = {}
        metrics_data = [
            ("Current Volume", "current_volume", "%", "#FF5722"),
            ("Finger Distance", "finger_distance", "mm", "#2196F3"),
            ("Accuracy", "accuracy", "%", "#4CAF50"),
            ("Response Time", "response_time", "ms", "#FF9800")
        ]
        
        for i, (title, key, unit, color) in enumerate(metrics_data):
            row = i // 2
            col = i % 2
            metric_frame = ctk.CTkFrame(metrics_container, fg_color="#f5f5f5", 
                                       corner_radius=10, width=145, height=100)
            metric_frame.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
            metric_frame.grid_propagate(False)
            
            value_label = ctk.CTkLabel(metric_frame, text="0" + unit,
                                      font=ctk.CTkFont(size=24, weight="bold"),
                                      text_color=color)
            value_label.pack(pady=(15, 5))
            
            ctk.CTkLabel(metric_frame, text=title,
                        font=ctk.CTkFont(size=11),
                        text_color="#666666").pack()
            
            self.metric_labels[key] = value_label
    
    def create_gesture_card(self, parent, gesture_name, distance_info, status, color):
        """Create a gesture status card"""
        card = ctk.CTkFrame(parent, fg_color="#f5f5f5", corner_radius=10, height=70)
        card.pack(padx=20, pady=8, fill="x")
        card.pack_propagate(False)
        
        # Status indicator
        indicator = ctk.CTkFrame(card, fg_color=color, width=8, corner_radius=4)
        indicator.pack(side="left", fill="y", padx=(10, 15), pady=10)
        
        # Text content
        text_frame = ctk.CTkFrame(card, fg_color="transparent")
        text_frame.pack(side="left", fill="both", expand=True)
        
        ctk.CTkLabel(text_frame, text=gesture_name,
                    font=ctk.CTkFont(size=14, weight="bold"),
                    text_color="#333333").pack(anchor="w", pady=(8, 2))
        
        ctk.CTkLabel(text_frame, text=distance_info,
                    font=ctk.CTkFont(size=11),
                    text_color="#666666").pack(anchor="w")
        
        # Status label
        ctk.CTkLabel(card, text=status,
                    font=ctk.CTkFont(size=11, weight="bold"),
                    text_color="#666666").pack(side="right", padx=15)
    
    def show_login(self):
        """Display login frame"""
        self.register_frame.pack_forget()
        self.dashboard_frame.pack_forget()
        self.login_frame.pack(fill="both", expand=True)
    
    def show_register(self):
        """Display register frame"""
        self.login_frame.pack_forget()
        self.dashboard_frame.pack_forget()
        self.register_frame.pack(fill="both", expand=True)
    
    def show_dashboard(self):
        """Display dashboard frame"""
        self.login_frame.pack_forget()
        self.register_frame.pack_forget()
        self.dashboard_frame.pack(fill="both", expand=True)
    
    def login(self):
        """Handle user login"""
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        
        if not username or not password:
            messagebox.showerror("Error", "Please fill all fields.")
            return
        
        if verify_user(username, password):
            self.current_user = username
            messagebox.showinfo("Success", f"Welcome {username}!")
            self.show_dashboard()
        else:
            messagebox.showerror("Login Failed", "Invalid username or password")
    
    def register(self):
        """Handle user registration"""
        username = self.reg_username.get().strip()
        password = self.reg_password.get().strip()
        confirm_password = self.reg_confirm_password.get().strip()
        
        if not username or not password or not confirm_password:
            messagebox.showerror("Error", "Please fill all fields.")
            return
        
        if password != confirm_password:
            messagebox.showerror("Error", "Passwords do not match.")
            return
        
        if len(password) < 6:
            messagebox.showerror("Error", "Password must be at least 6 characters.")
            return
        
        if register_user(username, password):
            messagebox.showinfo("Success", "Registration successful! Please login.")
            self.show_login()
        else:
            messagebox.showerror("Error", "Username already exists.")
    
    def start_gesture_control(self):
        """Start the gesture control system"""
        if not self.is_running:
            self.is_running = True
            self.start_btn.configure(state="disabled")
            self.pause_btn.configure(state="normal")
            
            # Start the graph update timer in the main thread
            if not self.graph_update_active:
                self.graph_update_active = True
                self.update_graph_periodically()
            
            # Start gesture detection in a separate thread
            self.detection_thread = threading.Thread(target=self.run_gesture_detection, daemon=True)
            self.detection_thread.start()
    
    def update_graph_periodically(self):
        """Update the graph periodically from the main thread"""
        if self.graph_update_active:
            # Update the graph if we have data
            if len(self.volume_history) > 0:
                self.draw_volume_graph()
                # Update status label
                self.graph_status_label.configure(
                    text=f"Data points: {len(self.volume_history)} | Active"
                )
            
            # Schedule the next update in 100ms (10 times per second)
            self.root.after(100, self.update_graph_periodically)
    
    def pause_gesture_control(self):
        """Pause the gesture control system"""
        self.is_running = False
        self.graph_update_active = False
        self.start_btn.configure(state="normal")
        self.pause_btn.configure(state="disabled")
        self.graph_status_label.configure(text="Paused")
    
    def test_graph(self):
        """Test function to add sample data to the graph"""
        import random
        # Add 20 random volume values to test the graph
        for i in range(20):
            random_volume = random.randint(20, 90)
            self.volume_history.append(random_volume)
            if len(self.volume_history) > self.max_history_points:
                self.volume_history.pop(0)
        
        # Update the graph
        self.draw_volume_graph()
        print(f"Test data added. Volume history now has {len(self.volume_history)} points")
    
    def run_gesture_detection(self):
        """Run gesture detection loop"""
        # CRITICAL: Initialize COM for this thread before using audio controls
        # COM (Component Object Model) must be initialized in each thread that uses it
        import comtypes
        comtypes.CoInitialize()
        
        try:
            mp_hands = mp.solutions.hands
            mp_drawing = mp.solutions.drawing_utils
            
            # Initialize audio control - now COM is properly initialized
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            vol_min, vol_max = volume.GetVolumeRange()[:2]
        
            cap = cv2.VideoCapture(0)
            
            with mp_hands.Hands(static_image_mode=False,
                            max_num_hands=1,
                            min_detection_confidence=0.7,
                            min_tracking_confidence=0.7) as hands:
                
                frame_count = 0
                successful_detections = 0
                
                while self.is_running and cap.isOpened():
                    success, frame = cap.read()
                    if not success:
                        continue
                    
                    frame = cv2.flip(frame, 1)
                    h, w, c = frame.shape
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    
                    start_time = time.time()
                    results = hands.process(rgb_frame)
                    process_time = (time.time() - start_time) * 1000  # Convert to ms
                    
                    frame_count += 1
                    
                    if results.multi_hand_landmarks:
                        successful_detections += 1
                        
                        for hand_landmarks in results.multi_hand_landmarks:
                            mp_drawing.draw_landmarks(frame, hand_landmarks, 
                                                    mp_hands.HAND_CONNECTIONS)
                            
                            # Get thumb and index finger positions
                            x1 = int(hand_landmarks.landmark[4].x * w)
                            y1 = int(hand_landmarks.landmark[4].y * h)
                            x2 = int(hand_landmarks.landmark[8].x * w)
                            y2 = int(hand_landmarks.landmark[8].y * h)
                            
                            # Draw circles and line
                            cv2.circle(frame, (x1, y1), 12, (255, 0, 255), -1)
                            cv2.circle(frame, (x2, y2), 12, (255, 0, 255), -1)
                            cv2.line(frame, (x1, y1), (x2, y2), (0, 255, 0), 3)
                            
                            # Calculate distance
                            length = math.hypot(x2 - x1, y2 - y1)
                            
                            # Update volume
                            vol = np.interp(length, [30, 200], [vol_min, vol_max])
                            volume.SetMasterVolumeLevel(vol, None)
                            
                            # Update metrics
                            volume_percent = int(np.interp(length, [30, 200], [0, 100]))
                            accuracy = int((successful_detections / frame_count) * 100)
                            
                            self.metrics['current_volume'] = volume_percent
                            self.metrics['finger_distance'] = int(length / 10)  # Convert to approximate mm
                            self.metrics['accuracy'] = accuracy
                            self.metrics['response_time'] = int(process_time)
                            
                            # Update UI metrics
                            self.root.after(0, self.update_metrics)
                            
                            # Determine gesture
                            if length > 100:
                                gesture = "Open Hand"
                                color = "#4CAF50"
                            elif 60 < length <= 100:
                                gesture = "Half Open"
                                color = "#FF9800"
                            else:
                                gesture = "Pinch Gesture"
                                color = "#FF5722"
                            
                            self.root.after(0, lambda g=gesture, c=color: 
                                        self.gesture_status.configure(text=g, fg_color=c))
                            
                            # Draw volume bar
                            vol_bar = int(np.interp(length, [30, 200], [400, 150]))
                            cv2.rectangle(frame, (50, 150), (85, 400), (0, 255, 0), 3)
                            cv2.rectangle(frame, (50, vol_bar), (85, 400), (0, 255, 0), -1)
                            cv2.putText(frame, f'{volume_percent}%', (40, 430), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 3)
                    
                    # Convert frame for display
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    img = Image.fromarray(frame_rgb)
                    img = img.resize((640, 480), Image.Resampling.LANCZOS)
                    photo = ImageTk.PhotoImage(image=img)
                    
                    # Update video display
                    self.root.after(0, lambda p=photo: self.update_video(p))
                    
                    time.sleep(0.03)  # ~30 FPS
                
                cap.release()
            
        finally:
            # IMPORTANT: Always uninitialize COM when done
            # This properly cleans up Windows resources
            comtypes.CoUninitialize()
    
    def update_video(self, photo):
        """Update video display in UI"""
        self.video_label.configure(image=photo)
        self.video_label.image = photo  # Keep a reference
    
    def update_metrics(self):
        """Update metric displays"""
        self.metric_labels['current_volume'].configure(
            text=f"{self.metrics['current_volume']}%")
        self.metric_labels['finger_distance'].configure(
            text=f"{self.metrics['finger_distance']}mm")
        self.metric_labels['accuracy'].configure(
            text=f"{self.metrics['accuracy']}%")
        self.metric_labels['response_time'].configure(
            text=f"{self.metrics['response_time']}ms")
    
    def update_graph_display(self):
        """Wrapper function to safely update the graph from any thread"""
        try:
            # Update status label
            data_count = len(self.volume_history)
            self.graph_status_label.configure(
                text=f"Data points: {data_count} | Last update: {time.strftime('%H:%M:%S')}"
            )
            self.draw_volume_graph()
        except Exception as e:
            print(f"Error updating graph display: {e}")
            import traceback
            traceback.print_exc()
    
    def draw_volume_graph(self):
        """Draw the volume history graph on the canvas"""
        try:
            # Clear the entire canvas
            self.graph_canvas.delete("all")
            
            # Get canvas dimensions
            canvas_width = self.graph_canvas.winfo_width()
            canvas_height = self.graph_canvas.winfo_height()
            
            # Use minimum dimensions if canvas not fully initialized
            if canvas_width < 100:
                canvas_width = 800
            if canvas_height < 50:
                canvas_height = 90
            
            # Calculate padding
            padding_left = 40
            padding_right = 15
            padding_top = 15
            padding_bottom = 15
            
            graph_width = canvas_width - padding_left - padding_right
            graph_height = canvas_height - padding_top - padding_bottom
            
            # Draw white background
            self.graph_canvas.create_rectangle(
                0, 0, canvas_width, canvas_height,
                fill="white", outline=""
            )
            
            # Draw grid lines and labels
            for i in range(0, 101, 25):
                y_pos = padding_top + graph_height - (i / 100 * graph_height)
                # Horizontal grid line
                self.graph_canvas.create_line(
                    padding_left, y_pos, 
                    canvas_width - padding_right, y_pos, 
                    fill="#e8e8e8", width=1
                )
                # Percentage label
                self.graph_canvas.create_text(
                    padding_left - 8, y_pos, 
                    text=f"{i}%", 
                    anchor="e", fill="#888888", 
                    font=("Arial", 8)
                )
            
            # Draw border
            self.graph_canvas.create_rectangle(
                padding_left, padding_top,
                canvas_width - padding_right, canvas_height - padding_bottom,
                outline="#d0d0d0", width=1
            )
            
            # Get the data
            data_count = len(self.volume_history)
            
            if data_count >= 1:
                # We have data to display
                points = []
                
                for i, vol in enumerate(self.volume_history):
                    # Calculate x position - spread points across the width
                    if data_count == 1:
                        x = padding_left + graph_width / 2
                    else:
                        x = padding_left + (i / (data_count - 1)) * graph_width
                    
                    # Calculate y position based on volume (0-100%)
                    y = padding_top + graph_height - (vol / 100 * graph_height)
                    points.append((x, y))
                
                if data_count >= 2:
                    # Draw filled area under the line
                    fill_coords = []
                    for x, y in points:
                        fill_coords.extend([x, y])
                    
                    # Close the polygon at the bottom
                    fill_coords.extend([points[-1][0], canvas_height - padding_bottom])
                    fill_coords.extend([points[0][0], canvas_height - padding_bottom])
                    
                    self.graph_canvas.create_polygon(
                        fill_coords,
                        fill="#FFE0DD",
                        outline="",
                        smooth=False
                    )
                    
                    # Draw the line
                    line_coords = []
                    for x, y in points:
                        line_coords.extend([x, y])
                    
                    self.graph_canvas.create_line(
                        line_coords,
                        fill="#FF5722",
                        width=3,
                        smooth=True
                    )
                
                # Draw current point marker (last point)
                last_x, last_y = points[-1]
                self.graph_canvas.create_oval(
                    last_x - 6, last_y - 6,
                    last_x + 6, last_y + 6,
                    fill="#FF5722",
                    outline="white",
                    width=2
                )
                
                # Show current volume value
                current_vol = int(self.volume_history[-1])
                self.graph_canvas.create_text(
                    last_x, last_y - 18,
                    text=f"{current_vol}%",
                    fill="#FF5722",
                    font=("Arial", 11, "bold")
                )
            else:
                # No data yet - show waiting message
                self.graph_canvas.create_text(
                    canvas_width // 2,
                    canvas_height // 2,
                    text="Move your hand to see the graph",
                    fill="#aaaaaa",
                    font=("Arial", 12)
                )
            
        except Exception as e:
            print(f"Graph error: {e}")
            import traceback
            traceback.print_exc()
    
    def update_gesture_cards(self, current_gesture):
        """Update the gesture recognition cards to show which gesture is active"""
        # This would update the gesture cards in the right panel
        # For now, the gesture status label shows the current gesture
        pass

# Run the application
if __name__ == "__main__":
    app = GestureControlApp()