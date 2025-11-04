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
from collections import deque
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import comtypes

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
        self.root.geometry("1400x900")
        self.root.title("Gesture Volume Control System")
        
        # Variables for gesture control
        self.is_running = False
        self.current_user = None
        self.current_frame = None
        
        # Color scheme
        self.primary_color = "#6161FC"  # RGB(97, 97, 252)
        self.primary_dark = "#4A4AC9"   # Darker shade for hover
        self.primary_light = "#7B7BFF"  # Lighter shade
        
        # Shared data updated by gesture thread
        self.shared_data = {
            'volume_percent': 0,
            'finger_distance': 0,
            'gesture_name': 'No Hand',
            'gesture_color': '#999999',
            'accuracy': 0,
            'response_time': 0,
            'fingers_extended': 0
        }
        
        # Graph data using deque for better performance
        self.volume_history = deque(maxlen=100)
        self.response_time_history = deque(maxlen=100)
        self.accuracy_history = deque(maxlen=100)
        
        # Volume control parameters
        self.vol_min = -65.25
        self.vol_max = 0.0
        
        # Gesture state management
        self.current_gesture = "none"
        self.previous_volume = 0
        self.smoothing_factor = 0.3  # Smooth volume transitions
        
        # Create frames
        self.create_login_frame()
        self.create_register_frame()
        self.create_dashboard_frame()
        
        # Show login frame initially
        self.show_login()
        
        self.root.mainloop()
    
    def create_login_frame(self):
        """Create the login interface"""
        self.login_frame = ctk.CTkFrame(self.root, fg_color="#6161FC")
        
        login_center = ctk.CTkFrame(self.login_frame, fg_color="white", 
                                   width=500, height=550, corner_radius=15)
        login_center.place(relx=0.5, rely=0.5, anchor="center")
        login_center.pack_propagate(False)
        
        ctk.CTkLabel(login_center, 
                    text="Gesture Volume Control",
                    font=ctk.CTkFont(size=32, weight="bold"),
                    text_color="#333333").pack(pady=(40, 10))
        
        ctk.CTkLabel(login_center, 
                    text="Control your system volume with hand gestures",
                    font=ctk.CTkFont(size=14),
                    text_color="#666666").pack(pady=(0, 40))
        
        self.username_entry = ctk.CTkEntry(login_center, width=380, height=50, 
                                          placeholder_text="Username",
                                          font=ctk.CTkFont(size=14),
                                          corner_radius=10)
        self.username_entry.pack(pady=12)
        
        self.password_entry = ctk.CTkEntry(login_center, width=380, height=50, 
                                          placeholder_text="Password",
                                          show="●",
                                          font=ctk.CTkFont(size=14),
                                          corner_radius=10)
        self.password_entry.pack(pady=12)
        
        ctk.CTkCheckBox(login_center, text="Remember me",
                       font=ctk.CTkFont(size=12)).pack(pady=10, padx=60, anchor="w")
        
        ctk.CTkButton(login_center, text="Login", width=380, height=50,
                     command=self.login,
                     fg_color=self.primary_color,
                     hover_color=self.primary_dark,
                     font=ctk.CTkFont(size=16, weight="bold"),
                     corner_radius=10).pack(pady=20)
        
        register_frame = ctk.CTkFrame(login_center, fg_color="white")
        register_frame.pack(pady=15)
        
        ctk.CTkLabel(register_frame, text="Don't have an account?",
                    text_color="#666666",
                    font=ctk.CTkFont(size=13)).pack(side="left")
        
        register_btn = ctk.CTkLabel(register_frame, text="Register",
                                   text_color=self.primary_color,
                                   font=ctk.CTkFont(size=13, weight="bold"),
                                   cursor="hand2")
        register_btn.pack(side="left", padx=(5, 0))
        register_btn.bind("<Button-1>", lambda e: self.show_register())
    
    def create_register_frame(self):
        """Create the registration interface"""
        self.register_frame = ctk.CTkFrame(self.root, fg_color="#1a1a1a")
        
        register_center = ctk.CTkFrame(self.register_frame, fg_color="white", 
                                      width=500, height=550, corner_radius=15)
        register_center.place(relx=0.5, rely=0.5, anchor="center")
        register_center.pack_propagate(False)
        
        ctk.CTkLabel(register_center, 
                    text="Create Account",
                    font=ctk.CTkFont(size=32, weight="bold"),
                    text_color="#333333").pack(pady=(40, 10))
        
        ctk.CTkLabel(register_center, 
                    text="Join us to control volume with gestures",
                    font=ctk.CTkFont(size=14),
                    text_color="#666666").pack(pady=(0, 40))
        
        self.reg_username = ctk.CTkEntry(register_center, width=380, height=50, 
                                        placeholder_text="Username",
                                        font=ctk.CTkFont(size=14),
                                        corner_radius=10)
        self.reg_username.pack(pady=12)
        
        self.reg_password = ctk.CTkEntry(register_center, width=380, height=50, 
                                        placeholder_text="Password",
                                        show="●",
                                        font=ctk.CTkFont(size=14),
                                        corner_radius=10)
        self.reg_password.pack(pady=12)
        
        self.reg_confirm_password = ctk.CTkEntry(register_center, width=380, height=50, 
                                                placeholder_text="Confirm Password",
                                                show="●",
                                                font=ctk.CTkFont(size=14),
                                                corner_radius=10)
        self.reg_confirm_password.pack(pady=12)
        
        ctk.CTkButton(register_center, text="Register", width=380, height=50,
                     command=self.register,
                     fg_color=self.primary_color,
                     hover_color=self.primary_dark,
                     font=ctk.CTkFont(size=16, weight="bold"),
                     corner_radius=10).pack(pady=20)
        
        back_btn = ctk.CTkLabel(register_center, text="← Back to Login",
                               text_color=self.primary_color,
                               font=ctk.CTkFont(size=13, weight="bold"),
                               cursor="hand2")
        back_btn.pack(pady=15)
        back_btn.bind("<Button-1>", lambda e: self.show_login())
    
    def create_dashboard_frame(self):
        """Create the main dashboard interface with tabs"""
        self.dashboard_frame = ctk.CTkFrame(self.root, fg_color="#f5f5f5")
        
        # Header
        header = ctk.CTkFrame(self.dashboard_frame, fg_color=self.primary_color, height=80)
        header.pack(fill="x", padx=0, pady=0)
        header.pack_propagate(False)
        
        ctk.CTkLabel(header, text="Gesture Control Interface",
                    font=ctk.CTkFont(size=28, weight="bold"),
                    text_color="white").pack(side="left", padx=30, pady=20)
        
        # Control buttons
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
                                       fg_color=self.primary_color,
                                       hover_color=self.primary_dark,
                                       corner_radius=8,
                                       state="disabled")
        self.pause_btn.pack(side="left", padx=5)
        
        # Create tab view
        self.tabview = ctk.CTkTabview(self.dashboard_frame, 
                                     fg_color="#f5f5f5",
                                     segmented_button_fg_color=self.primary_color,
                                     segmented_button_selected_color=self.primary_dark,
                                     segmented_button_unselected_color=self.primary_color,
                                     segmented_button_unselected_hover_color=self.primary_dark)
        self.tabview.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Create tabs
        self.live_tab = self.tabview.add("🎥 Live Control")
        self.analytics_tab = self.tabview.add("📊 Analytics")
        
        # Configure tabs to expand
        self.live_tab.grid_columnconfigure(0, weight=1)
        self.live_tab.grid_rowconfigure(1, weight=1)
        self.analytics_tab.grid_columnconfigure(0, weight=1)
        self.analytics_tab.grid_rowconfigure(0, weight=1)
        
        # Setup Live Control Tab
        self.setup_live_control_tab()
        
        # Setup Analytics Tab
        self.setup_analytics_tab()
    
    def setup_live_control_tab(self):
        """Setup the live control tab content"""
        # Main content for live control
        content = ctk.CTkFrame(self.live_tab, fg_color="#f5f5f5")
        content.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Configure grid
        content.grid_columnconfigure(0, weight=3)  # Left panel (video)
        content.grid_columnconfigure(1, weight=1)  # Right panel (controls)
        content.grid_rowconfigure(0, weight=1)
        
        # LEFT PANEL - Video
        left_panel = ctk.CTkFrame(content, fg_color="white", corner_radius=15)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        # Left panel grid configuration
        left_panel.grid_rowconfigure(0, weight=0)  # Title
        left_panel.grid_rowconfigure(1, weight=1)  # Video (gets all space)
        left_panel.grid_rowconfigure(2, weight=0)  # Gesture status
        left_panel.grid_columnconfigure(0, weight=1)
        
        # Title
        ctk.CTkLabel(left_panel, text="🎥 Live Camera Feed",
                    font=ctk.CTkFont(size=18, weight="bold"),
                    text_color="#333333").grid(row=0, column=0, sticky="w", padx=20, pady=15)
        
        # Video display - Centered with proper sizing
        video_container = ctk.CTkFrame(left_panel, fg_color="transparent")
        video_container.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)
        video_container.grid_rowconfigure(0, weight=1)
        video_container.grid_columnconfigure(0, weight=1)
        
        self.video_label = ctk.CTkLabel(video_container, 
                                       text="Camera will appear here\n\nClick 'Start' to begin gesture control",
                                       fg_color="#e0e0e0",
                                       width=640, 
                                       height=480,
                                       font=ctk.CTkFont(size=14),
                                       text_color="#666666",
                                       corner_radius=10)
        self.video_label.grid(row=0, column=0)
        
        # Gesture status badge
        self.gesture_status = ctk.CTkLabel(left_panel, 
                                          text="No Hand Detected",
                                          font=ctk.CTkFont(size=14, weight="bold"),
                                          text_color="white",
                                          fg_color="#999999",
                                          corner_radius=8,
                                          width=180,
                                          height=40)
        self.gesture_status.grid(row=2, column=0, pady=15)
        
        # RIGHT PANEL - Recognition and Metrics
        right_panel = ctk.CTkFrame(content, fg_color="white", corner_radius=15)
        right_panel.grid(row=0, column=1, sticky="nsew")
        
        ctk.CTkLabel(right_panel, text="🎯 Gesture Recognition",
                    font=ctk.CTkFont(size=18, weight="bold"),
                    text_color="#333333").pack(pady=15, padx=20, anchor="w")
        
        # Gesture cards container
        self.gesture_cards_frame = ctk.CTkFrame(right_panel, fg_color="white")
        self.gesture_cards_frame.pack(padx=20, fill="x")
        
        # Create gesture status cards
        self.gesture_cards = {}
        gestures_info = [
            ("Open Hand", "Distance > 100px", "open"),
            ("Pinch", "Distance < 60px", "pinch"),
            ("Closed", "Distance < 30px", "closed")
        ]
        
        for name, desc, key in gestures_info:
            card = self.create_gesture_card_widget(self.gesture_cards_frame, name, desc)
            self.gesture_cards[key] = card
            card.pack(pady=8, fill="x")
        
        # Performance Metrics
        ctk.CTkLabel(right_panel, text="📊 Performance Metrics",
                    font=ctk.CTkFont(size=18, weight="bold"),
                    text_color="#333333").pack(pady=(25, 15), padx=20, anchor="w")
        
        metrics_container = ctk.CTkFrame(right_panel, fg_color="white")
        metrics_container.pack(padx=20, pady=(0, 20), fill="x")
        
        # Create metric displays (2x2 grid)
        self.metric_widgets = {}
        metrics_data = [
            ("Current Volume", "volume", "%", self.primary_color),
            ("Finger Distance", "distance", "px", "#2196F3"),
            ("Accuracy", "accuracy", "%", "#4CAF50"),
            ("Response Time", "time", "ms", self.primary_color)
        ]
        
        for i, (title, key, unit, color) in enumerate(metrics_data):
            row = i // 2
            col = i % 2
            
            metric_frame = ctk.CTkFrame(metrics_container, fg_color="#f5f5f5", 
                                       corner_radius=10)
            metric_frame.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
            
            # Configure grid weights for equal sizing
            metrics_container.grid_rowconfigure(row, weight=1)
            metrics_container.grid_columnconfigure(col, weight=1)
            
            value_label = ctk.CTkLabel(metric_frame, text=f"0{unit}",
                                      font=ctk.CTkFont(size=26, weight="bold"),
                                      text_color=color)
            value_label.pack(pady=(20, 5))
            
            ctk.CTkLabel(metric_frame, text=title,
                        font=ctk.CTkFont(size=11),
                        text_color="#666666").pack(pady=(0, 20))
            
            self.metric_widgets[key] = value_label
    
    def setup_analytics_tab(self):
        """Setup the analytics tab with graphs"""
        # Main content for analytics
        content = ctk.CTkFrame(self.analytics_tab, fg_color="#f5f5f5")
        content.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title
        ctk.CTkLabel(content, text="📈 Performance Analytics",
                    font=ctk.CTkFont(size=24, weight="bold"),
                    text_color="#333333").pack(pady=(0, 20))
        
        # Create graph container with grid
        graphs_container = ctk.CTkFrame(content, fg_color="white", corner_radius=15)
        graphs_container.pack(fill="both", expand=True)
        
        # Configure grid for multiple graphs
        graphs_container.grid_rowconfigure(0, weight=1)  # Volume graph
        graphs_container.grid_rowconfigure(1, weight=1)  # Performance graphs
        graphs_container.grid_columnconfigure(0, weight=1)
        graphs_container.grid_columnconfigure(1, weight=1)
        
        # Volume History Graph (Full width)
        volume_graph_frame = ctk.CTkFrame(graphs_container, fg_color="white", corner_radius=10)
        volume_graph_frame.grid(row=0, column=0, columnspan=2, sticky="nsew", padx=15, pady=10)
        volume_graph_frame.grid_rowconfigure(0, weight=0)  # Title
        volume_graph_frame.grid_rowconfigure(1, weight=1)  # Graph
        volume_graph_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(volume_graph_frame, text="📊 Volume History",
                    font=ctk.CTkFont(size=18, weight="bold"),
                    text_color="#333333").grid(row=0, column=0, sticky="w", padx=20, pady=15)
        
        self.volume_graph_container = ctk.CTkFrame(volume_graph_frame, fg_color="white", height=300)
        self.volume_graph_container.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 15))
        self.volume_graph_container.grid_propagate(False)
        
        # Performance Graphs (2 columns)
        # Response Time Graph
        response_graph_frame = ctk.CTkFrame(graphs_container, fg_color="white", corner_radius=10)
        response_graph_frame.grid(row=1, column=0, sticky="nsew", padx=(15, 7), pady=10)
        response_graph_frame.grid_rowconfigure(0, weight=0)  # Title
        response_graph_frame.grid_rowconfigure(1, weight=1)  # Graph
        response_graph_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(response_graph_frame, text="⏱️ Response Time",
                    font=ctk.CTkFont(size=16, weight="bold"),
                    text_color="#333333").grid(row=0, column=0, sticky="w", padx=20, pady=15)
        
        self.response_graph_container = ctk.CTkFrame(response_graph_frame, fg_color="white", height=250)
        self.response_graph_container.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 15))
        self.response_graph_container.grid_propagate(False)
        
        # Accuracy Graph
        accuracy_graph_frame = ctk.CTkFrame(graphs_container, fg_color="white", corner_radius=10)
        accuracy_graph_frame.grid(row=1, column=1, sticky="nsew", padx=(7, 15), pady=10)
        accuracy_graph_frame.grid_rowconfigure(0, weight=0)  # Title
        accuracy_graph_frame.grid_rowconfigure(1, weight=1)  # Graph
        accuracy_graph_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(accuracy_graph_frame, text="🎯 Detection Accuracy",
                    font=ctk.CTkFont(size=16, weight="bold"),
                    text_color="#333333").grid(row=0, column=0, sticky="w", padx=20, pady=15)
        
        self.accuracy_graph_container = ctk.CTkFrame(accuracy_graph_frame, fg_color="white", height=250)
        self.accuracy_graph_container.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 15))
        self.accuracy_graph_container.grid_propagate(False)
        
        # Statistics Panel
        stats_frame = ctk.CTkFrame(content, fg_color="white", corner_radius=15, height=100)
        stats_frame.pack(fill="x", pady=(10, 0))
        stats_frame.pack_propagate(False)
        
        ctk.CTkLabel(stats_frame, text="📈 Session Statistics",
                    font=ctk.CTkFont(size=16, weight="bold"),
                    text_color="#333333").pack(anchor="w", padx=20, pady=15)
        
        stats_container = ctk.CTkFrame(stats_frame, fg_color="white")
        stats_container.pack(fill="x", padx=20, pady=(0, 15))
        
        # Statistics labels
        self.stats_widgets = {}
        stats_data = [
            ("Total Frames", "frames", "0", "#2196F3"),
            ("Hand Detections", "detections", "0", "#4CAF50"),
            ("Avg Response Time", "avg_response", "0ms", self.primary_color),
            ("Peak Volume", "peak_volume", "0%", self.primary_color)
        ]
        
        for i, (title, key, default, color) in enumerate(stats_data):
            stat_frame = ctk.CTkFrame(stats_container, fg_color="#f5f5f5", corner_radius=8)
            stat_frame.pack(side="left", fill="x", expand=True, padx=5)
            
            value_label = ctk.CTkLabel(stat_frame, text=default,
                                      font=ctk.CTkFont(size=20, weight="bold"),
                                      text_color=color)
            value_label.pack(pady=(10, 5))
            
            ctk.CTkLabel(stat_frame, text=title,
                        font=ctk.CTkFont(size=11),
                        text_color="#666666").pack(pady=(0, 10))
            
            self.stats_widgets[key] = value_label
    
    def create_gesture_card_widget(self, parent, name, description):
        """Create a gesture status card widget"""
        card = ctk.CTkFrame(parent, fg_color="#f5f5f5", corner_radius=10, height=75)
        card.pack_propagate(False)
        
        # Status indicator (changes color when active)
        card.indicator = ctk.CTkFrame(card, fg_color="#d0d0d0", width=8, corner_radius=4)
        card.indicator.pack(side="left", fill="y", padx=(12, 15), pady=12)
        
        # Text content
        text_frame = ctk.CTkFrame(card, fg_color="transparent")
        text_frame.pack(side="left", fill="both", expand=True, pady=10)
        
        card.name_label = ctk.CTkLabel(text_frame, text=name,
                                       font=ctk.CTkFont(size=15, weight="bold"),
                                       text_color="#333333")
        card.name_label.pack(anchor="w", pady=(5, 2))
        
        card.desc_label = ctk.CTkLabel(text_frame, text=description,
                                       font=ctk.CTkFont(size=11),
                                       text_color="#666666")
        card.desc_label.pack(anchor="w")
        
        # Status label
        card.status_label = ctk.CTkLabel(card, text="Inactive",
                                        font=ctk.CTkFont(size=12, weight="bold"),
                                        text_color="#999999")
        card.status_label.pack(side="right", padx=15)
        
        return card
    
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
        # Initialize matplotlib graphs after UI is rendered
        self.root.after(1000, self.init_matplotlib_graphs)
    
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
        """Start gesture control"""
        if not self.is_running:
            self.is_running = True
            self.start_btn.configure(state="disabled")
            self.pause_btn.configure(state="normal")
            
            # Reset gesture state
            self.current_gesture = "none"
            self.previous_volume = 0
            
            # Start gesture detection thread
            threading.Thread(target=self.run_gesture_detection, daemon=True).start()
            
            # Start UI update loop
            self.update_ui()
    
    def pause_gesture_control(self):
        """Pause gesture control"""
        self.is_running = False
        self.start_btn.configure(state="normal")
        self.pause_btn.configure(state="disabled")
    
    def init_matplotlib_graphs(self):
        """Initialize all Matplotlib graphs"""
        self.init_volume_graph()
        self.init_performance_graphs()
    
    def init_volume_graph(self):
        """Initialize the main volume history graph"""
        try:
            for widget in self.volume_graph_container.winfo_children():
                widget.destroy()
            
            self.volume_fig = Figure(figsize=(10, 3), dpi=100)
            self.volume_ax = self.volume_fig.add_subplot(111)
            self.volume_ax.set_facecolor("white")
            self.volume_fig.patch.set_facecolor("white")
            
            # Style the volume graph with new color scheme
            self.volume_ax.set_xlim(0, 100)
            self.volume_ax.set_ylim(0, 100)
            self.volume_ax.grid(True, color="#e8e8e8", linewidth=0.5)
            self.volume_ax.set_xlabel("Time (frames)", fontsize=10, color="#888888")
            self.volume_ax.set_ylabel("Volume %", fontsize=10, color="#888888")
            self.volume_ax.tick_params(axis='both', colors='#888888', labelsize=9)
            self.volume_ax.set_title("Real-time Volume Control", fontsize=12, color="#333333", pad=10)
            
            # Embed into Tkinter
            self.volume_canvas = FigureCanvasTkAgg(self.volume_fig, master=self.volume_graph_container)
            self.volume_canvas.draw()
            self.volume_canvas.get_tk_widget().pack(fill="both", expand=True)
            
        except Exception as e:
            print(f"Volume graph initialization error: {e}")
    
    def init_performance_graphs(self):
        """Initialize response time and accuracy graphs"""
        try:
            # Response Time Graph
            for widget in self.response_graph_container.winfo_children():
                widget.destroy()
            
            self.response_fig = Figure(figsize=(5, 2.5), dpi=100)
            self.response_ax = self.response_fig.add_subplot(111)
            self.response_ax.set_facecolor("white")
            self.response_fig.patch.set_facecolor("white")
            
            self.response_ax.set_xlim(0, 100)
            self.response_ax.set_ylim(0, 100)
            self.response_ax.grid(True, color="#e8e8e8", linewidth=0.5)
            self.response_ax.set_xlabel("Time", fontsize=8, color="#888888")
            self.response_ax.set_ylabel("Response Time (ms)", fontsize=8, color="#888888")
            self.response_ax.tick_params(axis='both', colors='#888888', labelsize=7)
            
            self.response_canvas = FigureCanvasTkAgg(self.response_fig, master=self.response_graph_container)
            self.response_canvas.draw()
            self.response_canvas.get_tk_widget().pack(fill="both", expand=True)
            
            # Accuracy Graph
            for widget in self.accuracy_graph_container.winfo_children():
                widget.destroy()
            
            self.accuracy_fig = Figure(figsize=(5, 2.5), dpi=100)
            self.accuracy_ax = self.accuracy_fig.add_subplot(111)
            self.accuracy_ax.set_facecolor("white")
            self.accuracy_fig.patch.set_facecolor("white")
            
            self.accuracy_ax.set_xlim(0, 100)
            self.accuracy_ax.set_ylim(0, 100)
            self.accuracy_ax.grid(True, color="#e8e8e8", linewidth=0.5)
            self.accuracy_ax.set_xlabel("Time", fontsize=8, color="#888888")
            self.accuracy_ax.set_ylabel("Accuracy %", fontsize=8, color="#888888")
            self.accuracy_ax.tick_params(axis='both', colors='#888888', labelsize=7)
            
            self.accuracy_canvas = FigureCanvasTkAgg(self.accuracy_fig, master=self.accuracy_graph_container)
            self.accuracy_canvas.draw()
            self.accuracy_canvas.get_tk_widget().pack(fill="both", expand=True)
            
        except Exception as e:
            print(f"Performance graphs initialization error: {e}")
    
    def draw_volume_graph(self):
        """Update volume history graph with new color scheme"""
        try:
            if not hasattr(self, "volume_ax"):
                return
            
            data = list(self.volume_history)
            n = len(data)
            
            self.volume_ax.clear()
            self.volume_ax.set_facecolor("white")
            self.volume_ax.grid(True, color="#e8e8e8", linewidth=0.5)
            self.volume_ax.set_xlabel("Time (frames)", fontsize=10, color="#888888")
            self.volume_ax.set_ylabel("Volume %", fontsize=10, color="#888888")
            self.volume_ax.tick_params(axis='both', colors='#888888', labelsize=9)
            self.volume_ax.set_title("Real-time Volume Control", fontsize=12, color="#333333", pad=10)
            
            if n == 0:
                self.volume_ax.text(0.5, 0.5, "Waiting for gesture data...",
                                   ha="center", va="center", color="#aaaaaa",
                                   fontsize=14, transform=self.volume_ax.transAxes)
                self.volume_ax.set_xlim(0, 100)
                self.volume_ax.set_ylim(0, 100)
            else:
                x = list(range(n))
                y = [max(0, min(100, float(v))) for v in data]
                
                self.volume_ax.set_xlim(0, max(100, n))
                self.volume_ax.set_ylim(0, 100)
                
                # Fill area under curve with new color
                self.volume_ax.fill_between(x, y, color="#E0E0FF", alpha=0.6)  # Light blue fill
                
                # Plot the line with new color
                self.volume_ax.plot(x, y, color=self.primary_color, linewidth=2.5)
                
                # Highlight current value with new color
                if y:
                    self.volume_ax.scatter(x[-1], y[-1], color=self.primary_color, s=60,
                                          edgecolor="white", linewidth=2, zorder=5)
                    self.volume_ax.text(x[-1], min(95, y[-1] + 5), f"{int(y[-1])}%",
                                       color=self.primary_color, fontsize=11, ha="center", 
                                       va="bottom", weight="bold")
            
            self.volume_fig.tight_layout()
            self.volume_canvas.draw_idle()
            
        except Exception as e:
            print(f"Volume graph drawing error: {e}")
    
    def draw_performance_graphs(self):
        """Update response time and accuracy graphs with new color scheme"""
        try:
            # Update response time graph
            if hasattr(self, "response_ax") and len(self.response_time_history) > 0:
                self.response_ax.clear()
                self.response_ax.set_facecolor("white")
                self.response_ax.grid(True, color="#e8e8e8", linewidth=0.5)
                self.response_ax.set_xlabel("Time", fontsize=8, color="#888888")
                self.response_ax.set_ylabel("Response Time (ms)", fontsize=8, color="#888888")
                self.response_ax.tick_params(axis='both', colors='#888888', labelsize=7)
                
                response_data = list(self.response_time_history)
                x = list(range(len(response_data)))
                self.response_ax.plot(x, response_data, color=self.primary_color, linewidth=2.0)
                self.response_ax.fill_between(x, response_data, color="#E0E0FF", alpha=0.6)
                self.response_ax.set_ylim(0, max(100, max(response_data) if response_data else 100))
                self.response_ax.set_xlim(0, max(100, len(response_data)))
                
                self.response_fig.tight_layout()
                self.response_canvas.draw_idle()
            
            # Update accuracy graph
            if hasattr(self, "accuracy_ax") and len(self.accuracy_history) > 0:
                self.accuracy_ax.clear()
                self.accuracy_ax.set_facecolor("white")
                self.accuracy_ax.grid(True, color="#e8e8e8", linewidth=0.5)
                self.accuracy_ax.set_xlabel("Time", fontsize=8, color="#888888")
                self.accuracy_ax.set_ylabel("Accuracy %", fontsize=8, color="#888888")
                self.accuracy_ax.tick_params(axis='both', colors='#888888', labelsize=7)
                
                accuracy_data = list(self.accuracy_history)
                x = list(range(len(accuracy_data)))
                self.accuracy_ax.plot(x, accuracy_data, color="#4CAF50", linewidth=2.0)
                self.accuracy_ax.fill_between(x, accuracy_data, color="#C8E6C9", alpha=0.6)
                self.accuracy_ax.set_ylim(0, 100)
                self.accuracy_ax.set_xlim(0, max(100, len(accuracy_data)))
                
                self.accuracy_fig.tight_layout()
                self.accuracy_canvas.draw_idle()
                
        except Exception as e:
            print(f"Performance graphs drawing error: {e}")
    
    def update_statistics(self, frame_count, successful_detections):
        """Update session statistics"""
        try:
            if frame_count > 0:
                avg_response = sum(self.response_time_history) / len(self.response_time_history) if self.response_time_history else 0
                peak_volume = max(self.volume_history) if self.volume_history else 0
                
                self.stats_widgets['frames'].configure(text=str(frame_count))
                self.stats_widgets['detections'].configure(text=str(successful_detections))
                self.stats_widgets['avg_response'].configure(text=f"{avg_response:.1f}ms")
                self.stats_widgets['peak_volume'].configure(text=f"{peak_volume}%")
        except Exception as e:
            print(f"Statistics update error: {e}")
    
    def update_ui(self):
        """Periodic UI update from main thread"""
        if self.is_running:
            # Update video frame
            if self.current_frame is not None:
                try:
                    frame_rgb = cv2.cvtColor(self.current_frame, cv2.COLOR_BGR2RGB)
                    img = Image.fromarray(frame_rgb)
                    img = img.resize((640, 480), Image.Resampling.LANCZOS)
                    photo = ImageTk.PhotoImage(image=img)
                    self.video_label.configure(image=photo, text="")
                    self.video_label.image = photo
                except Exception as e:
                    print("Video update error:", e)
            
            # Update gesture status badge
            self.gesture_status.configure(
                text=self.shared_data['gesture_name'],
                fg_color=self.shared_data['gesture_color']
            )
            
            # Update metrics
            self.metric_widgets['volume'].configure(
                text=f"{self.shared_data['volume_percent']}%")
            self.metric_widgets['distance'].configure(
                text=f"{self.shared_data['finger_distance']}px")
            self.metric_widgets['accuracy'].configure(
                text=f"{self.shared_data['accuracy']}%")
            self.metric_widgets['time'].configure(
                text=f"{self.shared_data['response_time']}ms")
            
            # Update gesture cards
            self.update_gesture_cards_status()
            
            # Update graphs (only if we're on the analytics tab for performance)
            current_tab = self.tabview.get()
            if current_tab == "📊 Analytics":
                self.draw_volume_graph()
                self.draw_performance_graphs()
            
            # Schedule next update
            self.root.after(33, self.update_ui)
    
    def update_gesture_cards_status(self):
        """Update the gesture recognition cards"""
        fingers = self.shared_data['fingers_extended']
        distance = self.shared_data['finger_distance']
        
        # Reset all to inactive
        for card in self.gesture_cards.values():
            card.indicator.configure(fg_color="#d0d0d0")
            card.status_label.configure(text="Inactive", text_color="#999999")
        
        # Set active card based on current gesture
        if fingers >= 3 and distance > 100:
            card = self.gesture_cards['open']
            card.indicator.configure(fg_color="#4CAF50")
            card.status_label.configure(text="Active", text_color="#4CAF50")
        elif distance < 30:
            card = self.gesture_cards['closed']
            card.indicator.configure(fg_color=self.primary_color)
            card.status_label.configure(text="Active", text_color=self.primary_color)
        elif distance < 60:
            card = self.gesture_cards['pinch']
            card.indicator.configure(fg_color=self.primary_color)
            card.status_label.configure(text="Active", text_color=self.primary_color)
    
    def run_gesture_detection(self):
        """Background thread for gesture detection - FIXED VOLUME CONTROL"""
        comtypes.CoInitialize()
        
        try:
            mp_hands = mp.solutions.hands
            mp_drawing = mp.solutions.drawing_utils
            
            # Initialize audio volume control
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            
            # Get actual volume range
            vol_range = volume.GetVolumeRange()
            self.vol_min = vol_range[0]
            self.vol_max = vol_range[1]
            print(f"Volume range: {self.vol_min}dB to {self.vol_max}dB")
            
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
                    process_time = (time.time() - start_time) * 1000
                    
                    frame_count += 1
                    
                    if results.multi_hand_landmarks:
                        successful_detections += 1
                        
                        for hand_landmarks in results.multi_hand_landmarks:
                            mp_drawing.draw_landmarks(frame, hand_landmarks, 
                                                     mp_hands.HAND_CONNECTIONS)
                            
                            landmarks = hand_landmarks.landmark
                            
                            # Get finger positions
                            x1 = int(landmarks[4].x * w)  # Thumb tip
                            y1 = int(landmarks[4].y * h)
                            x2 = int(landmarks[8].x * w)  # Index finger tip
                            y2 = int(landmarks[8].y * h)
                            
                            # Get other finger positions for gesture recognition
                            y_middle = int(landmarks[12].y * h)
                            y_ring = int(landmarks[16].y * h)
                            y_pinky = int(landmarks[20].y * h)
                            wrist_y = int(landmarks[0].y * h)
                            
                            # Draw markers and line
                            cv2.circle(frame, (x1, y1), 12, (255, 0, 255), -1)
                            cv2.circle(frame, (x2, y2), 12, (255, 0, 255), -1)
                            cv2.line(frame, (x1, y1), (x2, y2), (0, 255, 0), 3)
                            
                            # Calculate distance between thumb and index finger
                            length = math.hypot(x2 - x1, y2 - y1)
                            
                            # Count extended fingers
                            fingers_extended = 0
                            finger_threshold = 30  # pixels above wrist
                            if y2 < wrist_y - finger_threshold: fingers_extended += 1
                            if y_middle < wrist_y - finger_threshold: fingers_extended += 1
                            if y_ring < wrist_y - finger_threshold: fingers_extended += 1
                            if y_pinky < wrist_y - finger_threshold: fingers_extended += 1
                            
                            # FIXED: SMOOTH VOLUME CONTROL - No sudden jumps to 100%
                            min_distance = 30    # Minimum distance for 0% volume
                            max_distance = 200   # Maximum distance for 100% volume
                            
                            # Clamp the distance within reasonable bounds
                            clamped_distance = max(min_distance, min(length, max_distance))
                            
                            # Calculate target volume percentage based on distance
                            target_volume_percent = int(np.interp(clamped_distance, 
                                                                [min_distance, max_distance], 
                                                                [0, 100]))
                            
                            # Convert to dB volume level for system
                            target_vol_db = np.interp(target_volume_percent, [0, 100], 
                                                    [self.vol_min, self.vol_max])
                            
                            # Determine gesture type for display purposes only
                            # Volume is now solely controlled by distance, not gesture type
                            if fingers_extended >= 3 and length > 100:
                                gesture_name = "Open Hand"
                                gesture_color = "#4CAF50"
                                # Open hand doesn't force 100% volume anymore
                                # It just allows reaching 100% through distance
                            elif fingers_extended <= 1 or length < 60:
                                gesture_name = "Pinch Gesture"
                                gesture_color = self.primary_color
                                # Pinch gesture doesn't limit volume to low levels
                                # It allows full range control based on distance
                            else:
                                gesture_name = "Half Open"
                                gesture_color = self.primary_light
                            
                            # FIXED: Apply smoothing to prevent sudden jumps
                            current_volume_percent = self.shared_data.get('volume_percent', 0)
                            
                            # Smooth transition between current and target volume
                            if abs(current_volume_percent - target_volume_percent) > 5:  # Only apply smoothing for significant changes
                                smoothed_volume = int(current_volume_percent + 
                                                    (target_volume_percent - current_volume_percent) * self.smoothing_factor)
                            else:
                                smoothed_volume = target_volume_percent
                            
                            # Ensure volume stays within bounds
                            final_volume_percent = max(0, min(100, smoothed_volume))
                            final_vol_db = np.interp(final_volume_percent, [0, 100], 
                                                   [self.vol_min, self.vol_max])
                            
                            # Set system volume only if changed significantly
                            current_vol = volume.GetMasterVolumeLevel()
                            if abs(current_vol - final_vol_db) > 0.5:  # Reduced threshold for smoother changes
                                volume.SetMasterVolumeLevel(final_vol_db, None)
                            
                            # Draw volume bar on frame
                            vol_bar_height = int(np.interp(final_volume_percent, [0, 100], [400, 150]))
                            cv2.rectangle(frame, (50, 150), (85, 400), (0, 255, 0), 3)
                            cv2.rectangle(frame, (50, vol_bar_height), (85, 400), (0, 255, 0), -1)
                            cv2.putText(frame, f'{final_volume_percent}%', (40, 430), 
                                      cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 3)
                            
                            # Update shared data
                            self.shared_data['volume_percent'] = final_volume_percent
                            self.shared_data['finger_distance'] = int(length)
                            self.shared_data['gesture_name'] = gesture_name
                            self.shared_data['gesture_color'] = gesture_color
                            self.shared_data['accuracy'] = int((successful_detections / frame_count) * 100)
                            self.shared_data['response_time'] = int(process_time)
                            self.shared_data['fingers_extended'] = fingers_extended
                            
                            # Add to graph history
                            self.volume_history.append(final_volume_percent)
                            self.response_time_history.append(process_time)
                            self.accuracy_history.append(self.shared_data['accuracy'])
                            
                            # Update statistics
                            self.update_statistics(frame_count, successful_detections)
                            
                    else:
                        # No hand detected
                        self.shared_data['gesture_name'] = "No Hand Detected"
                        self.shared_data['gesture_color'] = "#999999"
                        # Still update accuracy and response time
                        self.shared_data['accuracy'] = int((successful_detections / frame_count) * 100)
                        self.shared_data['response_time'] = int(process_time)
                        self.response_time_history.append(process_time)
                        self.accuracy_history.append(self.shared_data['accuracy'])
                    
                    # Store current frame
                    self.current_frame = frame.copy()
                    
                    # Control frame rate
                    time.sleep(0.03)
            
            cap.release()
        
        except Exception as e:
            print(f"Gesture detection error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            comtypes.CoUninitialize()

# Run the application
if __name__ == "__main__":
    app = GestureControlApp()