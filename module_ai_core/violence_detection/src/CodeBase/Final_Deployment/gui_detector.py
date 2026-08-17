#!/usr/bin/env python3
"""
==============================================================================
Interactive GUI Violence Detector with Bounding Box Annotation & Real-time ONNX
Children Observer AI Core - Embedded Edge & Desktop Deployment
==============================================================================
Features:
  • Real-time Violence Detection with ONNX Runtime (Quantized INT8 Model)
  • Synchronized with full_evaluation_results.json Benchmark Dataset Records
  • Whole-Video Full Evaluation (Uniform 16-Frame Sampling - Exact Benchmark Match)
  • Real-Time Sliding-Window Playback Stream Detection
  • Built-in Dataset Explorer with Benchmark Scores & Filters
  • Interactive Bounding Box / ROI Drawing (Click & drag on video to inspect ROI)
  • Auto Motion & Activity Bounding Box Overlays (Green for Safe, Red for Alert)
  • Asynchronous Background Inference (Zero UI lag or playback stutter)
  • Full Video Controls: Play/Pause, Step, Seek Bar, Stride, Threshold, Speed
  • Detection Timeline Log with Jump-to-Timestamp
  • Export Annotated Video & Snapshot Capture
==============================================================================
"""

import os
import sys
import time
import json
import threading
from collections import deque
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import cv2
import numpy as np
from PIL import Image, ImageTk, ImageDraw
import onnxruntime as ort

# UTF-8 encoding support on Windows terminal
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Default Paths Configuration
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "..", ".."))

# Candidate default paths for model_int8.onnx
CANDIDATE_MODEL_PATHS = [
    os.path.join(SCRIPT_DIR, "model_int8.onnx"),
    os.path.join(PROJECT_ROOT, "module_ai_core", "violence_detection", "src", "CodeBase", "Final_Deployment", "model_int8.onnx"),
    os.path.join(SCRIPT_DIR, "model_embedded_int8.onnx"),
    os.path.join(SCRIPT_DIR, "model_embedded_simplified.onnx"),
    os.path.join(SCRIPT_DIR, "model.onnx"),
]

# Candidate dataset root paths
CANDIDATE_DATASET_DIRS = [
    os.path.join(PROJECT_ROOT, "module_ai_core", "violence_detection", "archive", "Real Life Violence Dataset"),
    os.path.join(SCRIPT_DIR, "..", "..", "archive", "Real Life Violence Dataset"),
    os.path.join(PROJECT_ROOT, "module_ai_core", "violence_detection", "archive", "real life violence situations", "Real Life Violence Dataset"),
]

# Candidate benchmark json report paths
CANDIDATE_REPORT_PATHS = [
    os.path.join(SCRIPT_DIR, "full_evaluation_results.json"),
    os.path.join(PROJECT_ROOT, "module_ai_core", "violence_detection", "src", "CodeBase", "Final_Deployment", "full_evaluation_results.json"),
    os.path.join(SCRIPT_DIR, "final_evaluation_report.json"),
]

def find_default_model_path():
    for p in CANDIDATE_MODEL_PATHS:
        if os.path.exists(p):
            return os.path.abspath(p)
    return CANDIDATE_MODEL_PATHS[0]

def find_default_dataset_dir():
    for d in CANDIDATE_DATASET_DIRS:
        if os.path.exists(d):
            return os.path.abspath(d)
    return ""

def find_default_report_path():
    for r in CANDIDATE_REPORT_PATHS:
        if os.path.exists(r):
            return os.path.abspath(r)
    return ""


class ONNXViolenceDetector:
    """
    High-performance ONNX Runtime inference engine for 3D CNN (PyTorch X3D)
    quantized into INT8. Zero PyTorch dependency.
    """
    def __init__(self, model_path, spatial_size=224, num_threads=4):
        self.model_path = model_path
        self.spatial_size = spatial_size
        
        # ImageNet normalization constants (Precomputed CHW arrays)
        self.mean = np.array([0.485, 0.456, 0.406], dtype=np.float32).reshape(3, 1, 1)
        self.std = np.array([0.229, 0.224, 0.225], dtype=np.float32).reshape(3, 1, 1)
        
        session_opt = ort.SessionOptions()
        session_opt.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        session_opt.intra_op_num_threads = num_threads
        session_opt.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        
        available = ort.get_available_providers()
        providers = []
        for prov in ["CUDAExecutionProvider", "TensorrtExecutionProvider", "DirectMLExecutionProvider", "CPUExecutionProvider"]:
            if prov in available:
                providers.append(prov)
        if not providers:
            providers = ["CPUExecutionProvider"]
            
        self.session = ort.InferenceSession(model_path, session_opt, providers=providers)
        self.input_name = self.session.get_inputs()[0].name
        self.output_name = self.session.get_outputs()[0].name
        self.provider = self.session.get_providers()[0]
        print(f"[ONNX Detector] Loaded: {os.path.basename(model_path)} (Provider: {self.provider})")

    def preprocess_frame(self, frame_bgr, crop_roi=None):
        """
        Fast frame preprocessing: Crop ROI (if any) -> Resize (224x224) -> BGR2RGB -> Normalize -> CHW
        """
        if crop_roi is not None:
            x1, y1, x2, y2 = crop_roi
            h, w = frame_bgr.shape[:2]
            x1, x2 = max(0, min(x1, x2)), min(w, max(x1, x2))
            y1, y2 = max(0, min(y1, y2)), min(h, max(y1, y2))
            if (x2 - x1) > 10 and (y2 - y1) > 10:
                frame_bgr = frame_bgr[y1:y2, x1:x2]
                
        resized = cv2.resize(frame_bgr, (self.spatial_size, self.spatial_size), interpolation=cv2.INTER_LINEAR)
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        chw = np.transpose(rgb, (2, 0, 1))
        return (chw - self.mean) / self.std

    def predict_clip(self, clip_tensor):
        """
        clip_tensor: shape (1, 3, 16, 224, 224) as float32 np.ndarray
        returns: (prob_non_violence, prob_violence, latency_ms)
        """
        t0 = time.perf_counter()
        outputs = self.session.run([self.output_name], {self.input_name: clip_tensor})[0]
        latency_ms = (time.perf_counter() - t0) * 1000.0
        prob_non_violence = float(outputs[0][0])
        prob_violence = float(outputs[0][1])
        return prob_non_violence, prob_violence, latency_ms

    def evaluate_video_uniform(self, video_path, num_frames=16, crop_roi=None):
        """
        Whole-video uniform 16-frame evaluation pipeline.
        Matches evaluate_all.py / fast_eval_all.py / full_evaluation_results.json exactly.
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return 0.5, 0.5, 0.0
        
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames <= 0:
            cap.release()
            return 0.5, 0.5, 0.0
            
        if total_frames <= num_frames:
            target_indices = set(range(total_frames))
        else:
            target_indices = set(np.linspace(0, total_frames - 1, num_frames, dtype=int))
            
        frames = []
        frame_idx = 0
        while cap.isOpened() and len(frames) < num_frames:
            ret, frame = cap.read()
            if not ret:
                break
            if frame_idx in target_indices:
                chw = self.preprocess_frame(frame, crop_roi=crop_roi)
                frames.append(chw)
            frame_idx += 1
        cap.release()
        
        if not frames:
            return 0.5, 0.5, 0.0
            
        while len(frames) < num_frames:
            frames.append(frames[-1])
            
        clip = np.expand_dims(np.stack(frames[:num_frames], axis=1), axis=0).astype(np.float32)
        return self.predict_clip(clip)


class ViolenceDetectorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Children Observer - Violence Detection GUI Studio")
        self.root.geometry("1320x840")
        self.root.minsize(1100, 740)
        self.root.configure(bg="#18191c")
        
        # State Variables
        self.model_path = find_default_model_path()
        self.dataset_dir = find_default_dataset_dir()
        self.report_path = find_default_report_path()
        self.benchmark_records = {}
        self.load_benchmark_report(self.report_path)
        
        self.detector = None
        self.load_model_engine(self.model_path)
        
        self.cap = None
        self.video_path = None
        self.is_playing = False
        self.is_webcam = False
        self.current_frame_idx = 0
        self.total_frames = 0
        self.fps = 30.0
        self.playback_speed = 1.0
        
        self.clip_length = 16
        self.frame_stride = 4
        self.infer_step = 4
        self.violence_threshold = 0.50
        
        # Ring buffer for sliding window frames
        self.frame_ring = deque(maxlen=self.clip_length * self.frame_stride)
        
        # Interactive Bounding Box (ROI) state
        self.user_bbox = None          # (x1, y1, x2, y2) in original video coords
        self.is_drawing_bbox = False
        self.draw_start_pt = None      # (canvas_x, canvas_y)
        self.draw_cur_pt = None
        self.roi_mode = tk.StringVar(value="full") # "full" or "roi"
        self.auto_bbox_enabled = tk.BooleanVar(value=True) # Auto motion/activity bbox
        
        # Motion & Activity Bounding Box Detector
        self.bg_subtractor = None
        self.prev_gray_frame = None
        self.auto_detected_boxes = []
        self._init_motion_detector()
        
        # Whole-video Evaluation Cache
        self.whole_video_prob_v = None
        self.whole_video_prob_nv = None
        self.whole_video_latency = None
        
        # Live sliding window inference result cache
        self.last_prob_v = 0.0
        self.last_prob_nv = 1.0
        self.last_latency_ms = 0.0
        self.last_fps = 0.0
        self.last_infer_time = time.time()
        self.alert_flash_count = 0
        
        # Inference threading state
        self.is_inferring = False
        self.infer_thread = None

        # Timeline / History event records: list of dicts
        self.history_events = []
        
        # Canvas display scaling geometry
        self.disp_scale = 1.0
        self.disp_pad_x = 0
        self.disp_pad_y = 0
        self.disp_w = 640
        self.disp_h = 480
        self.current_raw_frame = None
        
        # Build UI layout
        self.setup_ui()
        
        # Initial dataset load
        if self.dataset_dir and os.path.exists(self.dataset_dir):
            self.refresh_dataset_list()
            
        # Start GUI update loop
        self.root.after(20, self.gui_loop)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def load_benchmark_report(self, path):
        if path and os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                res_list = data.get("results", []) or data.get("detailed_predictions", [])
                self.benchmark_records = {item.get("filename", ""): item for item in res_list if item.get("filename")}
                print(f"[Benchmark Report] Loaded {len(self.benchmark_records)} evaluations from: {os.path.basename(path)}")
            except Exception as e:
                print(f"[Benchmark Report Warning] Failed to parse report {path}: {e}")
                self.benchmark_records = {}

    def _init_motion_detector(self):
        """Initialize motion/activity background subtractor safely."""
        try:
            if hasattr(cv2, "createBackgroundSubtractorMOG2"):
                self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(history=40, varThreshold=25, detectShadows=False)
            elif hasattr(cv2, "createBackgroundSubtractorKNN"):
                self.bg_subtractor = cv2.createBackgroundSubtractorKNN(history=40, dist2Threshold=400, detectShadows=False)
            else:
                self.bg_subtractor = None
        except Exception:
            self.bg_subtractor = None

    def load_model_engine(self, path):
        if not os.path.exists(path):
            print(f"[Warning] ONNX model not found at: {path}")
            self.detector = None
            return False
        try:
            self.detector = ONNXViolenceDetector(path)
            self.model_path = path
            return True
        except Exception as e:
            messagebox.showerror("Model Load Error", f"Failed to load ONNX model:\n{e}")
            self.detector = None
            return False

    # --------------------------------------------------------------------------
    # UI SETUP & STYLING
    # --------------------------------------------------------------------------
    def setup_ui(self):
        style = ttk.Style()
        style.theme_use("clam")
        
        # Colors
        BG_DARK = "#18191c"
        BG_PANEL = "#222428"
        BG_CARD = "#2c2e33"
        FG_TEXT = "#e1e3e6"
        ACCENT_BLUE = "#3b82f6"
        ACCENT_RED = "#ef4444"
        ACCENT_GREEN = "#10b981"
        
        style.configure(".", background=BG_PANEL, foreground=FG_TEXT, font=("Segoe UI", 9))
        style.configure("TFrame", background=BG_PANEL)
        style.configure("TLabel", background=BG_PANEL, foreground=FG_TEXT)
        style.configure("Header.TLabel", font=("Segoe UI", 12, "bold"), foreground="#ffffff")
        style.configure("Alert.TLabel", font=("Segoe UI", 14, "bold"), foreground=ACCENT_RED)
        style.configure("Safe.TLabel", font=("Segoe UI", 14, "bold"), foreground=ACCENT_GREEN)
        style.configure("TProgressbar", thickness=14, troughcolor="#33373e")
        style.configure("TNotebook", background=BG_PANEL)
        style.configure("TNotebook.Tab", background=BG_CARD, foreground=FG_TEXT, padding=[10, 4], font=("Segoe UI", 9, "bold"))
        style.map("TNotebook.Tab", background=[("selected", ACCENT_BLUE)], foreground=[("selected", "#ffffff")])

        # Master Container
        main_container = tk.Frame(self.root, bg=BG_DARK)
        main_container.pack(fill="both", expand=True)

        # ---------------- TOP HEADER BAR ----------------
        top_bar = tk.Frame(main_container, bg=BG_PANEL, height=48, padx=12, pady=6)
        top_bar.pack(fill="x", side="top")
        
        title_lbl = tk.Label(top_bar, text="🛡️ CHILDREN OBSERVER — REAL-TIME VIOLENCE DETECTOR", font=("Segoe UI", 12, "bold"), fg="#60a5fa", bg=BG_PANEL)
        title_lbl.pack(side="left")
        
        self.model_info_lbl = tk.Label(top_bar, text=f"Model: {os.path.basename(self.model_path)} (INT8)", font=("Segoe UI", 9), fg="#9ca3af", bg=BG_PANEL)
        self.model_info_lbl.pack(side="left", padx=20)

        # Benchmark report badge
        report_text = f"Benchmark: {os.path.basename(self.report_path)} ({len(self.benchmark_records)} vids)" if self.benchmark_records else "Benchmark: No JSON Report"
        self.report_info_lbl = tk.Label(top_bar, text=report_text, font=("Segoe UI", 8, "italic"), fg="#a78bfa", bg=BG_PANEL)
        self.report_info_lbl.pack(side="left", padx=10)

        change_model_btn = tk.Button(top_bar, text="📂 Change Model", font=("Segoe UI", 8, "bold"), bg="#374151", fg="#ffffff", activebackground="#4b5563", relief="flat", padx=8, pady=2, command=self.browse_model)
        change_model_btn.pack(side="right", padx=5)

        # ---------------- MAIN CONTENT SPLIT ----------------
        content_frame = tk.Frame(main_container, bg=BG_DARK)
        content_frame.pack(fill="both", expand=True, padx=8, pady=8)

        # LEFT SIDEBAR: Dataset & Video Browser
        left_panel = tk.Frame(content_frame, bg=BG_PANEL, width=320, padx=8, pady=8)
        left_panel.pack(side="left", fill="y", padx=(0, 8))
        left_panel.pack_propagate(False)
        self.setup_dataset_panel(left_panel)

        # RIGHT PANEL: Player & Analytics & Controls
        right_panel = tk.Frame(content_frame, bg=BG_PANEL, padx=8, pady=8)
        right_panel.pack(side="right", fill="both", expand=True)
        self.setup_player_panel(right_panel)

    def setup_dataset_panel(self, parent):
        lbl = tk.Label(parent, text="📁 DATASET & BENCHMARK EXPLORER", font=("Segoe UI", 10, "bold"), fg="#93c5fd", bg="#222428")
        lbl.pack(anchor="w", pady=(0, 4))

        # Dataset folder selector
        folder_frame = tk.Frame(parent, bg="#222428")
        folder_frame.pack(fill="x", pady=2)
        
        self.dataset_path_entry = tk.Entry(folder_frame, bg="#1e2023", fg="#ffffff", font=("Segoe UI", 8), insertbackground="white")
        self.dataset_path_entry.pack(side="left", fill="x", expand=True, padx=(0, 4))
        self.dataset_path_entry.insert(0, self.dataset_dir)
        
        browse_ds_btn = tk.Button(folder_frame, text="...", font=("Segoe UI", 8, "bold"), bg="#3b82f6", fg="white", relief="flat", padx=6, command=self.browse_dataset_dir)
        browse_ds_btn.pack(side="right")

        # Category Filter Tabs (All / Violence / NonViolence)
        filter_frame = tk.Frame(parent, bg="#222428")
        filter_frame.pack(fill="x", pady=4)
        
        self.dataset_filter = tk.StringVar(value="All")
        for text, val, color in [("All", "All", "#4b5563"), ("Violence", "Violence", "#dc2626"), ("Non-Violence", "NonViolence", "#16a34a")]:
            btn = tk.Radiobutton(
                filter_frame, text=text, value=val, variable=self.dataset_filter,
                indicatoron=False, font=("Segoe UI", 8, "bold"), bg="#2c2e33", fg="#d1d5db",
                selectcolor=color, activebackground=color, activeforeground="white",
                command=self.refresh_dataset_list, padx=6, pady=2
            )
            btn.pack(side="left", fill="x", expand=True, padx=1)

        # Search box
        search_frame = tk.Frame(parent, bg="#222428")
        search_frame.pack(fill="x", pady=(2, 4))
        tk.Label(search_frame, text="🔍", bg="#222428", fg="#9ca3af").pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.refresh_dataset_list())
        search_entry = tk.Entry(search_frame, textvariable=self.search_var, bg="#1e2023", fg="#ffffff", font=("Segoe UI", 9), insertbackground="white")
        search_entry.pack(side="left", fill="x", expand=True, padx=4)

        # Video Listbox with Scrollbar
        list_container = tk.Frame(parent, bg="#1e2023")
        list_container.pack(fill="both", expand=True, pady=4)
        
        scrollbar = tk.Scrollbar(list_container)
        scrollbar.pack(side="right", fill="y")
        
        self.video_listbox = tk.Listbox(
            list_container, bg="#1a1c1e", fg="#e5e7eb", font=("Consolas", 8),
            selectbackground="#2563eb", selectforeground="#ffffff",
            highlightthickness=0, yscrollcommand=scrollbar.set
        )
        self.video_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.video_listbox.yview)
        self.video_listbox.bind("<Double-Button-1>", lambda e: self.load_selected_dataset_video())
        
        self.dataset_count_lbl = tk.Label(parent, text="Videos found: 0", font=("Segoe UI", 8), fg="#9ca3af", bg="#222428")
        self.dataset_count_lbl.pack(anchor="w", pady=2)

        # Action Buttons
        btn_box = tk.Frame(parent, bg="#222428")
        btn_box.pack(fill="x", pady=2)
        
        load_vid_btn = tk.Button(btn_box, text="▶ Load & Evaluate Video", font=("Segoe UI", 9, "bold"), bg="#2563eb", fg="white", relief="flat", pady=4, command=self.load_selected_dataset_video)
        load_vid_btn.pack(fill="x", pady=2)
        
        browse_file_btn = tk.Button(btn_box, text="📂 Open Custom Video...", font=("Segoe UI", 8), bg="#374151", fg="white", relief="flat", pady=3, command=self.browse_custom_video)
        browse_file_btn.pack(fill="x", pady=2)

        webcam_btn = tk.Button(btn_box, text="📷 Live Camera Stream", font=("Segoe UI", 8), bg="#475569", fg="white", relief="flat", pady=3, command=self.start_webcam)
        webcam_btn.pack(fill="x", pady=2)

    def setup_player_panel(self, parent):
        # Top Live Alert Banner
        self.alert_banner = tk.Label(
            parent, text="READY — SELECT A VIDEO TO DETECT",
            font=("Segoe UI", 12, "bold"), bg="#1e2023", fg="#60a5fa", pady=6
        )
        self.alert_banner.pack(fill="x", pady=(0, 6))

        # Main Player Canvas & Side Analytics Area
        mid_split = tk.Frame(parent, bg="#222428")
        mid_split.pack(fill="both", expand=True)

        # Video Canvas Container
        self.canvas_frame = tk.Frame(mid_split, bg="#0d0e11", bd=1, relief="solid")
        self.canvas_frame.pack(side="left", fill="both", expand=True, padx=(0, 6))
        
        self.canvas = tk.Canvas(self.canvas_frame, bg="#0d0e11", cursor="crosshair", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", self.on_canvas_resize)
        
        # Interactive Mouse Events for Bounding Box Drawing
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)
        self.canvas.bind("<Button-3>", lambda e: self.clear_bounding_box()) # Right click clear

        # Right Side Analytics / Gauge Card
        analytics_card = tk.Frame(mid_split, bg="#1e2023", width=280, padx=10, pady=8)
        analytics_card.pack(side="right", fill="y")
        analytics_card.pack_propagate(False)
        self.setup_analytics_card(analytics_card)

        # Video Timeline Seeker Bar
        timeline_frame = tk.Frame(parent, bg="#222428")
        timeline_frame.pack(fill="x", pady=(6, 2))
        
        self.time_lbl = tk.Label(timeline_frame, text="00:00 / 00:00", font=("Consolas", 9), fg="#9ca3af", bg="#222428")
        self.time_lbl.pack(side="left", padx=4)
        
        self.seek_var = tk.DoubleVar(value=0)
        self.seek_scale = tk.Scale(
            timeline_frame, variable=self.seek_var, from_=0, to=100, orient="horizontal",
            showvalue=False, bg="#222428", fg="#3b82f6", activebackground="#60a5fa",
            troughcolor="#374151", highlightthickness=0, bd=0, command=self.on_seek
        )
        self.seek_scale.pack(side="left", fill="x", expand=True, padx=6)
        
        self.frame_num_lbl = tk.Label(timeline_frame, text="Frame: 0 / 0", font=("Consolas", 9), fg="#9ca3af", bg="#222428")
        self.frame_num_lbl.pack(side="right", padx=4)

        # Bottom Controls Bar
        controls_bar = tk.Frame(parent, bg="#222428", pady=4)
        controls_bar.pack(fill="x")
        self.setup_controls_bar(controls_bar)

        # Bottom Tabs (Detection Event Log & ROI Options)
        bottom_notebook = ttk.Notebook(parent)
        bottom_notebook.pack(fill="x", pady=(4, 0))
        
        benchmark_tab = tk.Frame(bottom_notebook, bg="#1e2023", padx=6, pady=4)
        log_tab = tk.Frame(bottom_notebook, bg="#1e2023", padx=6, pady=4)
        roi_tab = tk.Frame(bottom_notebook, bg="#1e2023", padx=6, pady=4)
        
        bottom_notebook.add(benchmark_tab, text="📊 Benchmark vs Realtime Comparison")
        bottom_notebook.add(log_tab, text="📋 Violence Alert Timeline Log")
        bottom_notebook.add(roi_tab, text="🎯 Bounding Box & ROI Settings")
        
        self.setup_benchmark_comparison_tab(benchmark_tab)
        self.setup_event_log_tab(log_tab)
        self.setup_roi_tab(roi_tab)

    def setup_analytics_card(self, parent):
        tk.Label(parent, text="📊 REALTIME METRICS", font=("Segoe UI", 10, "bold"), fg="#93c5fd", bg="#1e2023").pack(anchor="w", pady=(0, 4))

        # Real-time Sliding Window Violence Probability Bar
        tk.Label(parent, text="Live Sliding Window (Violence %)", font=("Segoe UI", 8, "bold"), fg="#f87171", bg="#1e2023").pack(anchor="w")
        self.v_prob_bar = ttk.Progressbar(parent, orient="horizontal", length=240, mode="determinate")
        self.v_prob_bar.pack(fill="x", pady=(1, 1))
        self.v_prob_text = tk.Label(parent, text="0.0%", font=("Segoe UI", 12, "bold"), fg="#ef4444", bg="#1e2023")
        self.v_prob_text.pack(anchor="e", pady=(0, 4))

        # Non-Violence Probability Bar
        tk.Label(parent, text="Live Safe / Normal %", font=("Segoe UI", 8, "bold"), fg="#34d399", bg="#1e2023").pack(anchor="w")
        self.nv_prob_bar = ttk.Progressbar(parent, orient="horizontal", length=240, mode="determinate")
        self.nv_prob_bar.pack(fill="x", pady=(1, 1))
        self.nv_prob_text = tk.Label(parent, text="100.0%", font=("Segoe UI", 11, "bold"), fg="#10b981", bg="#1e2023")
        self.nv_prob_text.pack(anchor="e", pady=(0, 6))

        # Whole-Video Full Evaluation Card
        eval_card = tk.LabelFrame(parent, text="⚡ Whole-Video Benchmark Eval", font=("Segoe UI", 8, "bold"), fg="#fcd34d", bg="#1a1c1e", padx=6, pady=4)
        eval_card.pack(fill="x", pady=(0, 6))
        
        self.whole_eval_score_lbl = tk.Label(eval_card, text="Whole Video: Not evaluated", font=("Segoe UI", 9, "bold"), fg="#e5e7eb", bg="#1a1c1e")
        self.whole_eval_score_lbl.pack(anchor="w")
        
        self.json_benchmark_lbl = tk.Label(eval_card, text="JSON Benchmark: N/A", font=("Consolas", 8), fg="#9ca3af", bg="#1a1c1e")
        self.json_benchmark_lbl.pack(anchor="w")

        run_whole_eval_btn = tk.Button(eval_card, text="⚡ Run Full Video Eval (16 Uniform Frames)", font=("Segoe UI", 8, "bold"), bg="#d97706", fg="white", relief="flat", pady=2, command=self.run_whole_video_eval)
        run_whole_eval_btn.pack(fill="x", pady=(4, 0))

        # Performance Stats Grid
        stats_frame = tk.Frame(parent, bg="#1e2023")
        stats_frame.pack(fill="x", pady=2)
        
        def add_stat_row(row, title, default_val):
            tk.Label(stats_frame, text=title, font=("Segoe UI", 8), fg="#9ca3af", bg="#1e2023").grid(row=row, column=0, sticky="w", pady=1)
            lbl = tk.Label(stats_frame, text=default_val, font=("Consolas", 9, "bold"), fg="#f3f4f6", bg="#1e2023")
            lbl.grid(row=row, column=1, sticky="e", pady=1)
            stats_frame.columnconfigure(0, weight=1)
            stats_frame.columnconfigure(1, weight=1)
            return lbl

        self.stat_latency = add_stat_row(0, "Sliding Latency:", "0.0 ms")
        self.stat_fps = add_stat_row(1, "Display FPS:", "0.0 FPS")
        self.stat_engine = add_stat_row(2, "ONNX Provider:", self.detector.provider if self.detector else "None")
        self.stat_bbox = add_stat_row(3, "ROI Box Status:", "Full Frame")
        self.stat_alerts = add_stat_row(4, "Total Alerts:", "0")

        # Snapshot & Export Buttons
        tk.Frame(parent, bg="#374151", height=1).pack(fill="x", pady=4)
        
        snap_btn = tk.Button(parent, text="📷 Save Snapshot", font=("Segoe UI", 8), bg="#374151", fg="white", relief="flat", pady=3, command=self.save_snapshot)
        snap_btn.pack(fill="x", pady=2)

        export_btn = tk.Button(parent, text="🎬 Export Annotated Video", font=("Segoe UI", 8, "bold"), bg="#059669", fg="white", relief="flat", pady=3, command=self.export_annotated_video)
        export_btn.pack(fill="x", pady=2)

    def setup_controls_bar(self, parent):
        # Play / Pause button
        self.play_btn = tk.Button(parent, text="▶ Play", font=("Segoe UI", 10, "bold"), bg="#2563eb", fg="white", relief="flat", width=9, command=self.toggle_play)
        self.play_btn.pack(side="left", padx=4)

        # Step Back / Step Forward
        step_back_btn = tk.Button(parent, text="⏮ -1 Frame", font=("Segoe UI", 8), bg="#374151", fg="white", relief="flat", command=lambda: self.step_frame(-1))
        step_back_btn.pack(side="left", padx=2)

        step_fwd_btn = tk.Button(parent, text="+1 Frame ⏭", font=("Segoe UI", 8), bg="#374151", fg="white", relief="flat", command=lambda: self.step_frame(1))
        step_fwd_btn.pack(side="left", padx=2)

        stop_btn = tk.Button(parent, text="⏹ Stop", font=("Segoe UI", 8), bg="#dc2626", fg="white", relief="flat", command=self.stop_video)
        stop_btn.pack(side="left", padx=4)

        # Loop Toggle
        self.loop_var = tk.BooleanVar(value=True)
        loop_chk = tk.Checkbutton(parent, text="🔁 Loop", variable=self.loop_var, font=("Segoe UI", 8), bg="#222428", fg="#d1d5db", selectcolor="#1e2023", activebackground="#222428")
        loop_chk.pack(side="left", padx=6)

        # Separator
        tk.Frame(parent, bg="#374151", width=1, height=22).pack(side="left", padx=6)

        # Threshold Slider
        tk.Label(parent, text="Alert Threshold:", font=("Segoe UI", 8, "bold"), fg="#9ca3af", bg="#222428").pack(side="left", padx=(4, 2))
        self.threshold_var = tk.DoubleVar(value=0.50)
        thresh_scale = tk.Scale(
            parent, variable=self.threshold_var, from_=0.10, to=0.95, resolution=0.05,
            orient="horizontal", showvalue=True, bg="#222428", fg="#f59e0b",
            activebackground="#fbbf24", troughcolor="#374151", highlightthickness=0, bd=0, length=100
        )
        thresh_scale.pack(side="left", padx=2)

        # Temporal Stride Selector
        tk.Label(parent, text="Stride:", font=("Segoe UI", 8, "bold"), fg="#9ca3af", bg="#222428").pack(side="left", padx=(6, 2))
        self.stride_var = tk.IntVar(value=4)
        stride_combo = ttk.Combobox(parent, textvariable=self.stride_var, values=[1, 2, 4, 8], width=3, state="readonly")
        stride_combo.pack(side="left", padx=2)
        stride_combo.bind("<<ComboboxSelected>>", lambda e: self.on_stride_changed())

        # Speed Selector
        tk.Label(parent, text="Speed:", font=("Segoe UI", 8, "bold"), fg="#9ca3af", bg="#222428").pack(side="left", padx=(6, 2))
        self.speed_var = tk.StringVar(value="1.0x")
        speed_combo = ttk.Combobox(parent, textvariable=self.speed_var, values=["0.25x", "0.5x", "1.0x", "1.5x", "2.0x"], width=5, state="readonly")
        speed_combo.pack(side="left", padx=2)
        speed_combo.bind("<<ComboboxSelected>>", self.on_speed_changed)

    def setup_benchmark_comparison_tab(self, parent):
        top_info = tk.Frame(parent, bg="#1e2023")
        top_info.pack(fill="x", pady=2)
        
        self.comp_gt_lbl = tk.Label(top_info, text="Ground Truth: None", font=("Segoe UI", 9, "bold"), fg="#93c5fd", bg="#1e2023")
        self.comp_gt_lbl.pack(side="left", padx=8)

        self.comp_json_lbl = tk.Label(top_info, text="full_evaluation_results.json: N/A", font=("Segoe UI", 9, "bold"), fg="#a78bfa", bg="#1e2023")
        self.comp_json_lbl.pack(side="left", padx=16)

        self.comp_uniform_lbl = tk.Label(top_info, text="ONNX Uniform 16-Frame: N/A", font=("Segoe UI", 9, "bold"), fg="#fbbf24", bg="#1e2023")
        self.comp_uniform_lbl.pack(side="left", padx=16)

        self.comp_sliding_lbl = tk.Label(top_info, text="Live Sliding Window: 0.0%", font=("Segoe UI", 9, "bold"), fg="#34d399", bg="#1e2023")
        self.comp_sliding_lbl.pack(side="right", padx=8)

        desc_lbl = tk.Label(parent, text="💡 Note: 'full_evaluation_results.json' used Whole-Video Uniform 16-Frame Sampling (linspace 0..N-1). During playback, the detector evaluates a Sliding Window in real-time. Use 'Run Full Video Eval' to see the exact whole-video benchmark output.", font=("Segoe UI", 8, "italic"), fg="#9ca3af", bg="#1e2023")
        desc_lbl.pack(anchor="w", padx=8, pady=2)

    def setup_event_log_tab(self, parent):
        scroll = tk.Scrollbar(parent)
        scroll.pack(side="right", fill="y")
        
        self.event_listbox = tk.Listbox(
            parent, height=4, bg="#18191c", fg="#e5e7eb", font=("Consolas", 9),
            selectbackground="#dc2626", selectforeground="#ffffff",
            highlightthickness=0, yscrollcommand=scroll.set
        )
        self.event_listbox.pack(side="left", fill="both", expand=True)
        scroll.config(command=self.event_listbox.yview)
        self.event_listbox.bind("<Double-Button-1>", self.on_event_double_click)

    def setup_roi_tab(self, parent):
        top_row = tk.Frame(parent, bg="#1e2023")
        top_row.pack(fill="x", pady=2)
        
        tk.Label(top_row, text="Drawing Mode:", font=("Segoe UI", 8, "bold"), fg="#93c5fd", bg="#1e2023").pack(side="left", padx=(0, 6))
        
        r1 = tk.Radiobutton(top_row, text="Detect Full Frame (Overlay BBox)", variable=self.roi_mode, value="full", font=("Segoe UI", 8), bg="#1e2023", fg="#d1d5db", selectcolor="#2563eb", activebackground="#1e2023")
        r1.pack(side="left", padx=4)

        r2 = tk.Radiobutton(top_row, text="Crop & Detect Inside Drawn BBox (ROI Only)", variable=self.roi_mode, value="roi", font=("Segoe UI", 8), bg="#1e2023", fg="#d1d5db", selectcolor="#2563eb", activebackground="#1e2023")
        r2.pack(side="left", padx=4)

        auto_chk = tk.Checkbutton(top_row, text="🤖 Auto Motion / Subject BBoxes", variable=self.auto_bbox_enabled, font=("Segoe UI", 8, "bold"), bg="#1e2023", fg="#38bdf8", selectcolor="#0284c7", activebackground="#1e2023")
        auto_chk.pack(side="left", padx=12)

        clear_btn = tk.Button(top_row, text="🧹 Clear Drawn BBox", font=("Segoe UI", 8), bg="#4b5563", fg="white", relief="flat", padx=8, command=self.clear_bounding_box)
        clear_btn.pack(side="right", padx=4)

        tip_lbl = tk.Label(parent, text="💡 Tip: Click and drag your mouse over any area on the video player to draw a custom bounding box ROI. Right-click canvas to clear.", font=("Segoe UI", 8, "italic"), fg="#9ca3af", bg="#1e2023")
        tip_lbl.pack(anchor="w", pady=(2, 0))

    # --------------------------------------------------------------------------
    # DATASET BROWSER METHODS
    # --------------------------------------------------------------------------
    def browse_dataset_dir(self):
        d = filedialog.askdirectory(title="Select Dataset Directory", initialdir=self.dataset_dir or PROJECT_ROOT)
        if d:
            self.dataset_dir = d
            self.dataset_path_entry.delete(0, tk.END)
            self.dataset_path_entry.insert(0, d)
            self.refresh_dataset_list()

    def refresh_dataset_list(self):
        self.video_listbox.delete(0, tk.END)
        path = self.dataset_path_entry.get().strip()
        if not path or not os.path.exists(path):
            self.dataset_count_lbl.config(text="Dataset directory not found.")
            return

        filter_mode = self.dataset_filter.get() # All / Violence / NonViolence
        search_query = self.search_var.get().lower().strip()

        video_extensions = (".mp4", ".avi", ".mkv", ".mov", ".flv", ".webm")
        matched_videos = []

        # Recursively search or scan top level / category folders
        for root_dir, _, files in os.walk(path):
            rel_folder = os.path.relpath(root_dir, path)
            for f in files:
                if f.lower().endswith(video_extensions):
                    full_p = os.path.join(root_dir, f)
                    is_violence = "violence" in rel_folder.lower() and "non" not in rel_folder.lower()
                    is_non_violence = "nonviolence" in rel_folder.lower() or "non_violence" in rel_folder.lower() or "non violence" in rel_folder.lower()
                    
                    if filter_mode == "Violence" and not is_violence:
                        continue
                    if filter_mode == "NonViolence" and not is_non_violence:
                        continue

                    if search_query and search_query not in f.lower() and search_query not in rel_folder.lower():
                        continue

                    # Lookup benchmark evaluation if exists
                    b_info = ""
                    if f in self.benchmark_records:
                        rec = self.benchmark_records[f]
                        v_pct = rec.get("prob_violence", 0.0) * 100.0
                        b_info = f" | Eval: {v_pct:.0f}% V"

                    cat_tag = "V" if is_violence else "NV" if is_non_violence else "?"
                    display_str = f"[{cat_tag}] {f}{b_info}"
                    matched_videos.append((display_str, full_p, f, is_violence))

        matched_videos.sort(key=lambda x: x[0])
        for disp_str, full_p, fname, is_v in matched_videos:
            self.video_listbox.insert(tk.END, disp_str)

        self.matched_videos = matched_videos
        self.dataset_count_lbl.config(text=f"Videos found: {len(matched_videos)} (Indexed with Benchmark JSON)")

    def load_selected_dataset_video(self):
        sel = self.video_listbox.curselection()
        if not sel or not hasattr(self, "matched_videos") or sel[0] >= len(self.matched_videos):
            return
        _, vid_path, fname, is_v = self.matched_videos[sel[0]]
        self.load_video(vid_path)

    def browse_custom_video(self):
        f = filedialog.askopenfilename(
            title="Open Video File",
            initialdir=self.dataset_dir or PROJECT_ROOT,
            filetypes=[("Video Files", "*.mp4 *.avi *.mkv *.mov *.webm"), ("All Files", "*.*")]
        )
        if f:
            self.load_video(f)

    def browse_model(self):
        f = filedialog.askopenfilename(
            title="Select ONNX Model",
            initialdir=os.path.dirname(self.model_path),
            filetypes=[("ONNX Models", "*.onnx"), ("All Files", "*.*")]
        )
        if f:
            if self.load_model_engine(f):
                self.model_info_lbl.config(text=f"Model: {os.path.basename(f)}")
                if self.stat_engine:
                    self.stat_engine.config(text=self.detector.provider)

    # --------------------------------------------------------------------------
    # VIDEO PLAYBACK & CAPTURE
    # --------------------------------------------------------------------------
    def load_video(self, video_path):
        self.stop_video()
        if not os.path.exists(video_path):
            messagebox.showerror("File Error", f"Video file not found: {video_path}")
            return

        self.cap = cv2.VideoCapture(video_path)
        if not self.cap.isOpened():
            messagebox.showerror("Codec Error", f"Failed to open video file: {video_path}")
            return

        self.video_path = video_path
        self.is_webcam = False
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30.0
        if self.fps <= 0 or self.fps > 120:
            self.fps = 30.0
            
        self.current_frame_idx = 0
        self.frame_ring.clear()
        self.event_listbox.delete(0, tk.END)
        self.history_events.clear()
        self.stat_alerts.config(text="0")
        self.prev_gray_frame = None
        self._init_motion_detector()
        
        self.seek_scale.config(to=max(1, self.total_frames - 1))
        self.seek_var.set(0)
        
        # Check Ground Truth & Benchmark Report record
        bname = os.path.basename(video_path)
        gt_text = "Violence" if ("violence" in video_path.lower() and "non" not in video_path.lower()) else "NonViolence" if "non" in video_path.lower() else "Unknown"
        self.comp_gt_lbl.config(text=f"Ground Truth: {gt_text}")

        if bname in self.benchmark_records:
            rec = self.benchmark_records[bname]
            j_v = rec.get("prob_violence", 0.0) * 100.0
            j_nv = rec.get("prob_non_violence", 0.0) * 100.0
            self.json_benchmark_lbl.config(text=f"JSON Benchmark: {j_v:.1f}% Violence / {j_nv:.1f}% Safe")
            self.comp_json_lbl.config(text=f"Benchmark JSON: {j_v:.1f}% V ({rec.get('ground_truth_name', '')})")
        else:
            self.json_benchmark_lbl.config(text="JSON Benchmark: Not in benchmark file")
            self.comp_json_lbl.config(text="Benchmark JSON: N/A")

        # Automatically execute Whole-Video Uniform Evaluation in background
        self.run_whole_video_eval()

        # Read first frame and render
        self.step_frame(0)
        self.alert_banner.config(text=f"LOADED: {bname}", fg="#60a5fa", bg="#1e2023")
        self.toggle_play()

    def run_whole_video_eval(self):
        if not self.video_path or self.is_webcam or self.detector is None:
            return
        
        self.whole_eval_score_lbl.config(text="Whole Video: Evaluating 16 Uniform Frames...", fg="#fbbf24")
        threading.Thread(target=self._async_whole_video_worker, daemon=True).start()

    def _async_whole_video_worker(self):
        crop_roi = self.user_bbox if (self.roi_mode.get() == "roi" and self.user_bbox) else None
        p_nv, p_v, lat = self.detector.evaluate_video_uniform(self.video_path, num_frames=16, crop_roi=crop_roi)
        self.whole_video_prob_v = p_v
        self.whole_video_prob_nv = p_nv
        self.whole_video_latency = lat
        self.root.after(0, self._on_whole_video_complete)

    def _on_whole_video_complete(self):
        v_pct = self.whole_video_prob_v * 100.0
        nv_pct = self.whole_video_prob_nv * 100.0
        is_v = (self.whole_video_prob_v >= self.threshold_var.get())
        status = "VIOLENCE" if is_v else "SAFE / NORMAL"
        color = "#ef4444" if is_v else "#10b981"
        
        self.whole_eval_score_lbl.config(text=f"Whole Video: {status} ({v_pct:.1f}% V | {self.whole_video_latency:.0f}ms)", fg=color)
        self.comp_uniform_lbl.config(text=f"ONNX Uniform: {v_pct:.1f}% V ({status})", fg=color)

    def start_webcam(self):
        self.stop_video()
        self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_ANY)
        if not self.cap.isOpened():
            messagebox.showerror("Camera Error", "Could not open webcam device 0.")
            return

        self.video_path = "Webcam:0"
        self.is_webcam = True
        self.total_frames = 1
        self.fps = 30.0
        self.current_frame_idx = 0
        self.frame_ring.clear()
        self.seek_scale.config(to=1)
        self.alert_banner.config(text="LIVE WEBCAM STREAM ACTIVE", fg="#34d399", bg="#1e2023")
        self.is_playing = True
        self.play_btn.config(text="⏸ Pause", bg="#f59e0b")

    def toggle_play(self):
        if self.cap is None:
            return
        self.is_playing = not self.is_playing
        if self.is_playing:
            self.play_btn.config(text="⏸ Pause", bg="#f59e0b")
        else:
            self.play_btn.config(text="▶ Play", bg="#2563eb")

    def stop_video(self):
        self.is_playing = False
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        self.play_btn.config(text="▶ Play", bg="#2563eb")
        self.alert_banner.config(text="STOPPED / READY", fg="#9ca3af", bg="#1e2023")
        self.v_prob_bar["value"] = 0
        self.nv_prob_bar["value"] = 0
        self.v_prob_text.config(text="0.0%")
        self.nv_prob_text.config(text="0.0%")

    def step_frame(self, step=1):
        if self.cap is None or self.is_webcam:
            return
        self.is_playing = False
        self.play_btn.config(text="▶ Play", bg="#2563eb")
        target = max(0, min(self.total_frames - 1, self.current_frame_idx + step))
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, target)
        self.current_frame_idx = target
        self.seek_var.set(target)
        ret, frame = self.cap.read()
        if ret and frame is not None:
            self.process_and_render_frame(frame)

    def on_seek(self, val):
        if self.cap is None or self.is_webcam:
            return
        target = int(float(val))
        if abs(target - self.current_frame_idx) > 1:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, target)
            self.current_frame_idx = target
            ret, frame = self.cap.read()
            if ret and frame is not None:
                self.process_and_render_frame(frame)

    def on_speed_changed(self, event=None):
        txt = self.speed_var.get().replace("x", "")
        try:
            self.playback_speed = float(txt)
        except Exception:
            self.playback_speed = 1.0

    def on_stride_changed(self):
        self.frame_stride = self.stride_var.get()
        max_len = self.clip_length * self.frame_stride
        self.frame_ring = deque(list(self.frame_ring), maxlen=max_len)

    # --------------------------------------------------------------------------
    # INTERACTIVE BOUNDING BOX MOUSE EVENTS
    # --------------------------------------------------------------------------
    def on_mouse_down(self, event):
        self.is_drawing_bbox = True
        self.draw_start_pt = (event.x, event.y)
        self.draw_cur_pt = (event.x, event.y)

    def on_mouse_drag(self, event):
        if self.is_drawing_bbox:
            self.draw_cur_pt = (event.x, event.y)
            # Trigger immediate redraw of canvas
            if self.current_raw_frame is not None:
                self.render_frame_to_canvas(self.current_raw_frame)

    def on_mouse_up(self, event):
        if self.is_drawing_bbox and self.draw_start_pt:
            self.is_drawing_bbox = False
            x0, y0 = self.draw_start_pt
            x1, y1 = event.x, event.y
            
            # Map canvas coords to original video coords
            if self.current_raw_frame is not None:
                orig_h, orig_w = self.current_raw_frame.shape[:2]
                
                # Convert canvas (x, y) to image (fx, fy)
                fx0 = int(np.clip((x0 - self.disp_pad_x) / max(1e-4, self.disp_scale), 0, orig_w))
                fy0 = int(np.clip((y0 - self.disp_pad_y) / max(1e-4, self.disp_scale), 0, orig_h))
                fx1 = int(np.clip((x1 - self.disp_pad_x) / max(1e-4, self.disp_scale), 0, orig_w))
                fy1 = int(np.clip((y1 - self.disp_pad_y) / max(1e-4, self.disp_scale), 0, orig_h))
                
                min_x, max_x = min(fx0, fx1), max(fx0, fx1)
                min_y, max_y = min(fy0, fy1), max(fy0, fy1)
                
                if (max_x - min_x) > 20 and (max_y - min_y) > 20:
                    self.user_bbox = (min_x, min_y, max_x, max_y)
                    self.stat_bbox.config(text=f"[{max_x-min_x}x{max_y-min_y} ROI]")
                    if self.roi_mode.get() == "roi":
                        self.run_whole_video_eval()
                else:
                    self.user_bbox = None
                    self.stat_bbox.config(text="Full Frame")
                    
            self.draw_start_pt = None
            self.draw_cur_pt = None
            if self.current_raw_frame is not None:
                self.render_frame_to_canvas(self.current_raw_frame)

    def clear_bounding_box(self):
        self.user_bbox = None
        self.draw_start_pt = None
        self.draw_cur_pt = None
        self.stat_bbox.config(text="Full Frame")
        if self.current_raw_frame is not None:
            self.render_frame_to_canvas(self.current_raw_frame)

    def on_canvas_resize(self, event):
        self.disp_w = max(100, event.width)
        self.disp_h = max(100, event.height)
        if self.current_raw_frame is not None:
            self.render_frame_to_canvas(self.current_raw_frame)

    # --------------------------------------------------------------------------
    # CORE DETECTION & FRAME PROCESSING LOOP
    # --------------------------------------------------------------------------
    def gui_loop(self):
        t_loop_start = time.perf_counter()
        
        if self.is_playing and self.cap is not None and self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret or frame is None:
                if self.loop_var.get() and not self.is_webcam:
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    self.current_frame_idx = 0
                    ret, frame = self.cap.read()
                else:
                    self.is_playing = False
                    self.play_btn.config(text="▶ Play", bg="#2563eb")
                    
            if ret and frame is not None:
                self.current_frame_idx = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES)) if not self.is_webcam else self.current_frame_idx + 1
                self.seek_var.set(self.current_frame_idx)
                self.process_and_render_frame(frame)

        # Dynamic sleep timing for accurate FPS playback
        elapsed = (time.perf_counter() - t_loop_start) * 1000.0
        target_ms = max(5, int((1000.0 / max(1.0, self.fps * self.playback_speed)) - elapsed))
        self.root.after(target_ms, self.gui_loop)

    def process_and_render_frame(self, frame_bgr):
        self.current_raw_frame = frame_bgr
        orig_h, orig_w = frame_bgr.shape[:2]
        
        # 1. Automatic Motion / Activity Bounding Box Detection
        if self.auto_bbox_enabled.get() and (self.current_frame_idx % 4 == 0 or not self.auto_detected_boxes):
            try:
                scale_factor = 320.0 / max(orig_w, orig_h)
                small_w, small_h = int(orig_w * scale_factor), int(orig_h * scale_factor)
                small_frame = cv2.resize(frame_bgr, (small_w, small_h))
                gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
                gray = cv2.GaussianBlur(gray, (7, 7), 0)

                detected = []
                if self.bg_subtractor is not None:
                    fg_mask = self.bg_subtractor.apply(small_frame)
                    _, fg_thresh = cv2.threshold(fg_mask, 150, 255, cv2.THRESH_BINARY)
                    contours, _ = cv2.findContours(fg_thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    min_area = (small_w * small_h) * 0.02
                    for cnt in contours:
                        if cv2.contourArea(cnt) > min_area:
                            bx, by, bw, bh = cv2.boundingRect(cnt)
                            detected.append((
                                int(bx / scale_factor),
                                int(by / scale_factor),
                                int((bx + bw) / scale_factor),
                                int((by + bh) / scale_factor)
                            ))
                elif self.prev_gray_frame is not None:
                    diff = cv2.absdiff(self.prev_gray_frame, gray)
                    _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
                    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    min_area = (small_w * small_h) * 0.02
                    for cnt in contours:
                        if cv2.contourArea(cnt) > min_area:
                            bx, by, bw, bh = cv2.boundingRect(cnt)
                            detected.append((
                                int(bx / scale_factor),
                                int(by / scale_factor),
                                int((bx + bw) / scale_factor),
                                int((by + bh) / scale_factor)
                            ))
                self.prev_gray_frame = gray
                if detected:
                    self.auto_detected_boxes = detected[:4] # Keep top prominent boxes
            except Exception:
                pass

        # 2. Extract Preprocessed CHW Tensor (Full Frame or User ROI)
        crop_roi = self.user_bbox if (self.roi_mode.get() == "roi" and self.user_bbox) else None
        if self.detector is not None:
            chw = self.detector.preprocess_frame(frame_bgr, crop_roi=crop_roi)
            self.frame_ring.append(chw)

            # 3. Trigger Sliding Window ONNX Inference Asynchronously
            max_ring_len = self.clip_length * self.frame_stride
            if len(self.frame_ring) >= max_ring_len and (self.current_frame_idx % self.infer_step == 0):
                if not self.is_inferring:
                    ring_list = list(self.frame_ring)
                    strided_frames = [ring_list[i * self.frame_stride] for i in range(self.clip_length)]
                    
                    clip_tensor = np.stack(strided_frames, axis=1) # (3, 16, 224, 224)
                    clip_input = np.expand_dims(clip_tensor, axis=0).astype(np.float32)

                    cur_sec = self.current_frame_idx / max(1.0, self.fps)
                    self.is_inferring = True
                    threading.Thread(
                        target=self._async_infer_worker,
                        args=(clip_input, self.current_frame_idx, cur_sec),
                        daemon=True
                    ).start()

        # 4. Render to Canvas
        self.render_frame_to_canvas(frame_bgr)

    def _async_infer_worker(self, clip_input, frame_idx, current_sec):
        try:
            prob_nv, prob_v, lat_ms = self.detector.predict_clip(clip_input)
            self.root.after(0, lambda: self._on_infer_complete(prob_nv, prob_v, lat_ms, frame_idx, current_sec))
        except Exception as e:
            print(f"[Infer Error] {e}")
        finally:
            self.is_inferring = False

    def _on_infer_complete(self, prob_nv, prob_v, lat_ms, frame_idx, current_sec):
        self.last_prob_v = prob_v
        self.last_prob_nv = prob_nv
        self.last_latency_ms = lat_ms
        
        now = time.time()
        self.last_fps = 1.0 / max(1e-4, (now - self.last_infer_time))
        self.last_infer_time = now

        # Check Alert Threshold
        threshold = self.threshold_var.get()
        
        if prob_v >= threshold:
            # Log alert event
            time_str = f"{int(current_sec//60):02d}:{current_sec%60:04.1f}"
            alert_msg = f"🚨 [{time_str}] VIOLENCE ({prob_v*100:.1f}%) | Latency: {lat_ms:.1f}ms"
            
            if not self.history_events or (now - self.history_events[-1]["time"]) > 2.0:
                self.history_events.append({"time": now, "sec": current_sec, "text": alert_msg, "prob_v": prob_v})
                self.event_listbox.insert(0, alert_msg)
                self.stat_alerts.config(text=str(len(self.history_events)))

        # Update UI Gauges
        self.update_gauges(prob_v, prob_nv, lat_ms, threshold)

    def update_gauges(self, prob_v, prob_nv, latency_ms, threshold):
        v_pct = prob_v * 100.0
        nv_pct = prob_nv * 100.0
        self.v_prob_bar["value"] = v_pct
        self.nv_prob_bar["value"] = nv_pct
        self.v_prob_text.config(text=f"{v_pct:.1f}%")
        self.nv_prob_text.config(text=f"{nv_pct:.1f}%")
        
        self.stat_latency.config(text=f"{latency_ms:.1f} ms")
        self.stat_fps.config(text=f"{self.last_fps:.1f} FPS")
        self.comp_sliding_lbl.config(text=f"Live Sliding: {v_pct:.1f}% V")

        if prob_v >= threshold:
            self.alert_flash_count = (self.alert_flash_count + 1) % 2
            bg_color = "#dc2626" if self.alert_flash_count == 0 else "#991b1b"
            self.alert_banner.config(text=f"🚨 ALERT: VIOLENCE DETECTED ({v_pct:.1f}%)", fg="#ffffff", bg=bg_color)
        else:
            self.alert_banner.config(text=f"✅ SAFE / NORMAL ({nv_pct:.1f}%)", fg="#10b981", bg="#1e2023")

    def render_frame_to_canvas(self, frame_bgr):
        orig_h, orig_w = frame_bgr.shape[:2]
        canvas_w = max(100, self.disp_w)
        canvas_h = max(100, self.disp_h)
        
        # Calculate aspect ratio preserving scaling
        scale = min(canvas_w / max(1, orig_w), canvas_h / max(1, orig_h))
        scaled_w = max(1, int(orig_w * scale))
        scaled_h = max(1, int(orig_h * scale))
        
        pad_x = (canvas_w - scaled_w) // 2
        pad_y = (canvas_h - scaled_h) // 2
        
        self.disp_scale = scale
        self.disp_pad_x = pad_x
        self.disp_pad_y = pad_y

        # Draw overlays on copy of frame
        disp_frame = frame_bgr.copy()
        threshold = self.threshold_var.get()
        is_violence = (self.last_prob_v >= threshold)
        status_color = (0, 0, 235) if is_violence else (0, 200, 0) # BGR: Red / Green

        # Overlay Auto-detected BBoxes
        if self.auto_bbox_enabled.get() and self.auto_detected_boxes:
            for (bx1, by1, bx2, by2) in self.auto_detected_boxes:
                cv2.rectangle(disp_frame, (bx1, by1), (bx2, by2), status_color, 2)
                tag = "VIOLENCE" if is_violence else "ACTIVITY"
                cv2.putText(disp_frame, tag, (bx1, max(15, by1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, status_color, 1)

        # Overlay User Drawn BBox
        if self.user_bbox is not None:
            ux1, uy1, ux2, uy2 = self.user_bbox
            box_color = (0, 165, 255) if self.roi_mode.get() == "roi" else (255, 255, 0) # Orange / Cyan
            cv2.rectangle(disp_frame, (ux1, uy1), (ux2, uy2), box_color, 2)
            lbl = "ROI REGION" if self.roi_mode.get() == "roi" else "BOUNDING BOX"
            cv2.putText(disp_frame, lbl, (ux1, max(20, uy1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, box_color, 2)

        # Top-left HUD badge on video
        hud_text = f"{'VIOLENCE' if is_violence else 'NORMAL'}: {max(self.last_prob_v, self.last_prob_nv)*100:.1f}% ({self.last_latency_ms:.0f}ms)"
        cv2.putText(disp_frame, hud_text, (18, 36), cv2.FONT_HERSHEY_SIMPLEX, 0.85, status_color, 2)

        # Resize for display canvas
        resized = cv2.resize(disp_frame, (scaled_w, scaled_h), interpolation=cv2.INTER_AREA)
        rgb_disp = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb_disp)
        
        # Create full letterbox image with background padding
        letterbox = Image.new("RGB", (canvas_w, canvas_h), color="#0d0e11")
        letterbox.paste(pil_img, (pad_x, pad_y))

        # Live drawing rectangle preview
        if self.is_drawing_bbox and self.draw_start_pt and self.draw_cur_pt:
            draw = ImageDraw.Draw(letterbox)
            x0, y0 = self.draw_start_pt
            x1, y1 = self.draw_cur_pt
            draw.rectangle([min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)], outline="#38bdf8", width=2)

        photo = ImageTk.PhotoImage(image=letterbox)
        self.canvas.create_image(0, 0, image=photo, anchor="nw")
        self.canvas.image = photo # Keep reference

        # Update Time & Frame labels
        cur_sec = self.current_frame_idx / max(1.0, self.fps)
        tot_sec = self.total_frames / max(1.0, self.fps)
        cur_str = f"{int(cur_sec//60):02d}:{int(cur_sec%60):02d}"
        tot_str = f"{int(tot_sec//60):02d}:{int(tot_sec%60):02d}"
        self.time_lbl.config(text=f"{cur_str} / {tot_str}")
        self.frame_num_lbl.config(text=f"Frame: {self.current_frame_idx} / {self.total_frames}")

    def on_event_double_click(self, event):
        sel = self.event_listbox.curselection()
        if not sel or not self.history_events or sel[0] >= len(self.history_events):
            return
        idx = len(self.history_events) - 1 - sel[0]
        if 0 <= idx < len(self.history_events):
            target_sec = self.history_events[idx]["sec"]
            target_frame = int(target_sec * self.fps)
            self.step_frame(target_frame - self.current_frame_idx)

    # --------------------------------------------------------------------------
    # SNAPSHOT & EXPORT CAPABILITIES
    # --------------------------------------------------------------------------
    def save_snapshot(self):
        if self.current_raw_frame is None:
            messagebox.showwarning("Snapshot", "No video frame is currently loaded.")
            return
        
        save_p = filedialog.asksaveasfilename(
            title="Save Snapshot Image",
            defaultextension=".png",
            filetypes=[("PNG Image", "*.png"), ("JPEG Image", "*.jpg")]
        )
        if save_p:
            cv2.imwrite(save_p, self.current_raw_frame)
            messagebox.showinfo("Snapshot Saved", f"Saved current frame to:\n{save_p}")

    def export_annotated_video(self):
        if not self.video_path or self.is_webcam:
            messagebox.showwarning("Export", "Please load a video file to export.")
            return
        
        save_p = filedialog.asksaveasfilename(
            title="Export Annotated Video",
            defaultextension=".mp4",
            filetypes=[("MP4 Video", "*.mp4")]
        )
        if not save_p:
            return

        export_thread = threading.Thread(target=self._run_export_worker, args=(self.video_path, save_p), daemon=True)
        export_thread.start()

    def _run_export_worker(self, in_path, out_path):
        cap = cv2.VideoCapture(in_path)
        if not cap.isOpened():
            return
        
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        tot = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        writer = cv2.VideoWriter(out_path, fourcc, fps, (w, h))

        ring = deque(maxlen=self.clip_length * self.frame_stride)
        frame_idx = 0
        cur_prob_v = 0.0
        thresh = self.threshold_var.get()

        progress_win = tk.Toplevel(self.root)
        progress_win.title("Exporting Video...")
        progress_win.geometry("380x120")
        progress_win.configure(bg="#222428")
        tk.Label(progress_win, text="Exporting annotated video with ONNX detection...", font=("Segoe UI", 9, "bold"), fg="#ffffff", bg="#222428").pack(pady=8)
        pb = ttk.Progressbar(progress_win, length=320, mode="determinate")
        pb.pack(pady=6)

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret or frame is None:
                break
            frame_idx += 1
            
            chw = self.detector.preprocess_frame(frame)
            ring.append(chw)

            if len(ring) == (self.clip_length * self.frame_stride) and (frame_idx % self.infer_step == 0):
                r_list = list(ring)
                strided = [r_list[i * self.frame_stride] for i in range(self.clip_length)]
                clip = np.expand_dims(np.stack(strided, axis=1), axis=0).astype(np.float32)
                _, cur_prob_v, _ = self.detector.predict_clip(clip)

            is_v = (cur_prob_v >= thresh)
            col = (0, 0, 235) if is_v else (0, 200, 0)
            tag = f"{'VIOLENCE ALERT' if is_v else 'NORMAL'}: {cur_prob_v*100:.1f}%"
            cv2.putText(frame, tag, (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.1, col, 3)

            writer.write(frame)
            if frame_idx % 10 == 0:
                pb["value"] = (frame_idx / max(1, tot)) * 100
                progress_win.update()

        cap.release()
        writer.release()
        progress_win.destroy()
        messagebox.showinfo("Export Complete", f"Annotated video successfully exported to:\n{out_path}")

    def on_close(self):
        self.stop_video()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = ViolenceDetectorGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
