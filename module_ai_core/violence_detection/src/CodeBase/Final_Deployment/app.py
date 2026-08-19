import os
import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import cv2
import torch
import numpy as np
from torchvision import transforms
from PIL import Image, ImageTk, ImageDraw, ImageFont
from collections import deque
from model_utils import load_model, custome_X3D

# Initialize device
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Load model and weights
num_classes = 2
class_names = ["Non Violence", "Violence"]
model = custome_X3D(num_classes)
model_path = os.path.join(os.path.dirname(__file__), "model.pth")
model = load_model(model, model_path, device)
model.eval()

# Global state
cap = None
is_running = False
frame_ring = deque()
history = []
clip_length = 16

# Preprocessing transforms
transform = transforms.Compose([
    transforms.ToTensor(),
    transforms.Resize((224, 224)),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

# Setup Tkinter UI
window = tk.Tk()
window.title("Violence Detection System - Realtime GUI Video Player")
window.geometry("850x760")
window.resizable(False, False)
window.configure(bg="#f5f5f5")

# Visual header
header_label = tk.Label(window, text="REALTIME VIOLENCE DETECTION GUI PLAYER", font=("Helvetica", 16, "bold"), fg="#1a237e", bg="#f5f5f5")
header_label.pack(pady=10)

# Container for Video Display (Fixed 640x360 pixels)
canvas_container = tk.Frame(window, width=640, height=360, bg="#1e1e1e")
canvas_container.pack_propagate(False)
canvas_container.pack(pady=5)

frame_label = tk.Label(canvas_container, bg="#1e1e1e")
frame_label.pack(fill="both", expand=True)

def create_placeholder(text="Click 'Select Video File' or 'Start Webcam' to begin"):
    img = Image.new("RGB", (640, 360), color="#1e1e1e")
    draw = ImageDraw.Draw(img)
    # Draw simple centered instruction
    draw.text((120, 170), text, fill="#ffffff")
    return ImageTk.PhotoImage(img)

placeholder_img = create_placeholder()
frame_label.config(image=placeholder_img)

# Status & Confidence Bar
status_frame = tk.Frame(window, bg="#f5f5f5")
status_frame.pack(pady=8)

prediction_label = tk.Label(status_frame, text="Status: Ready | Please select a video file or webcam source", font=("Helvetica", 12, "bold"), fg="#333333", bg="#f5f5f5")
prediction_label.pack()

confidence_bar = ttk.Progressbar(status_frame, orient="horizontal", length=640, mode="determinate")
confidence_bar.pack(pady=5)

# Config & Control Frame
control_frame = tk.Frame(window, bg="#f5f5f5")
control_frame.pack(pady=8)

stride_var = tk.IntVar(value=4)

def update_frame():
    global cap, is_running, frame_ring
    if not is_running or cap is None or not cap.isOpened():
        return

    ret, frame = cap.read()
    if not ret or frame is None:
        # Loop video file if reached end
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        ret, frame = cap.read()
        if not ret or frame is None:
            stop_video()
            return

    current_frame_idx = int(cap.get(cv2.CAP_PROP_POS_FRAMES))
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 30.0
    current_sec = current_frame_idx / fps

    frame_stride = stride_var.get()
    max_ring_len = clip_length * frame_stride
    
    if frame_ring.maxlen != max_ring_len:
        frame_ring = deque(list(frame_ring), maxlen=max_ring_len)

    # Process frame for model
    frame_resized = cv2.resize(frame, (224, 224))
    frame_rgb = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)
    tensor_frame = transform(frame_rgb)
    frame_ring.append(tensor_frame)

    # Run model inference when ring buffer has enough strided frames
    if len(frame_ring) >= max_ring_len and (current_frame_idx % 4 == 0):
        ring_list = list(frame_ring)
        strided_frames = [ring_list[i * frame_stride] for i in range(clip_length)]
        input_tensor = torch.stack(strided_frames).permute(1, 0, 2, 3).unsqueeze(0).to(device)

        with torch.no_grad():
            probabilities = model(input_tensor).squeeze() # [2]: 0=NonViolence, 1=Violence
            conf_non_violence = float(probabilities[0]) * 100
            conf_violence = float(probabilities[1]) * 100
            predicted_idx = 1 if conf_violence >= 50.0 else 0
            label = class_names[predicted_idx]

        confidence_bar["value"] = conf_violence

        if predicted_idx == 1:
            status_text = f"🚨 ALERT: VIOLENCE DETECTED ({conf_violence:.1f}%)"
            prediction_label.config(text=status_text, fg="#d32f2f")
            log_entry = f"[{current_sec:05.1f}s] ALERT: Violence Detected ({conf_violence:.1f}%)"
        else:
            status_text = f"✅ SAFE / NORMAL ({conf_non_violence:.1f}%)"
            prediction_label.config(text=status_text, fg="#388e3c")
            log_entry = f"[{current_sec:05.1f}s] SAFE: NonViolence ({conf_non_violence:.1f}%)"

        if len(history) == 0 or history[0] != log_entry:
            history.insert(0, log_entry)
            if len(history) > 20:
                history.pop()
            history_listbox.delete(0, tk.END)
            for item in history:
                history_listbox.insert(tk.END, item)

        # Draw overlay on display frame
        cv_color = (0, 0, 255) if predicted_idx == 1 else (0, 255, 0)
        cv2.putText(frame, f"{label}: {max(conf_violence, conf_non_violence):.1f}%", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, cv_color, 2)

    # Render frame image to GUI
    disp_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    disp_pil = Image.fromarray(disp_rgb).resize((640, 360))
    photo = ImageTk.PhotoImage(image=disp_pil)
    frame_label.config(image=photo)
    frame_label.image = photo

    window.after(30, update_frame)

def open_file():
    global cap, is_running, frame_ring
    file_path = filedialog.askopenfilename(
        title="Select Video File for Detection",
        initialdir=r"c:\Users\DamPhuQuy\Develop\children-observer\module_ai_core\violence_detection\archive\Real Life Violence Dataset",
        filetypes=[("Video Files", "*.mp4 *.avi *.mkv *.mov"), ("All Files", "*.*")]
    )
    if file_path:
        stop_video()
        cap = cv2.VideoCapture(file_path)
        if not cap.isOpened():
            messagebox.showerror("Video Error", f"Cannot open video file: {file_path}")
            return
        is_running = True
        frame_stride = stride_var.get()
        frame_ring = deque(maxlen=clip_length * frame_stride)
        history.clear()
        history_listbox.delete(0, tk.END)
        prediction_label.config(text=f"Playing Video: {os.path.basename(file_path)}", fg="#1565c0")
        update_frame()

def start_webcam():
    global cap, is_running, frame_ring
    stop_video()
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        messagebox.showerror("Camera Error", "Cannot access webcam device 0.")
        return
    is_running = True
    frame_stride = stride_var.get()
    frame_ring = deque(maxlen=clip_length * frame_stride)
    history.clear()
    history_listbox.delete(0, tk.END)
    prediction_label.config(text="Live Stream: Webcam Device 0", fg="#1565c0")
    update_frame()

def stop_video():
    global cap, is_running
    is_running = False
    if cap is not None:
        cap.release()
        cap = None
    prediction_label.config(text="Status: Stopped | Select Camera or Video File to Start", fg="#333333")
    confidence_bar["value"] = 0
    frame_label.config(image=placeholder_img)

# UI Controls Layout
file_button = tk.Button(control_frame, text="📁 Select Video File", font=("Helvetica", 11, "bold"), bg="#2e7d32", fg="white", padx=12, command=open_file)
file_button.pack(side="left", padx=10)

webcam_button = tk.Button(control_frame, text="🎥 Start Webcam", font=("Helvetica", 11, "bold"), bg="#1565c0", fg="white", padx=12, command=start_webcam)
webcam_button.pack(side="left", padx=10)

stop_button = tk.Button(control_frame, text="⏹ Stop", font=("Helvetica", 11, "bold"), bg="#c62828", fg="white", padx=12, command=stop_video)
stop_button.pack(side="left", padx=10)

stride_label = tk.Label(control_frame, text="Frame Stride:", font=("Helvetica", 10, "bold"), bg="#f5f5f5")
stride_label.pack(side="left", padx=(15, 2))

stride_spinbox = ttk.Spinbox(control_frame, from_=1, to=16, width=3, textvariable=stride_var, font=("Helvetica", 10))
stride_spinbox.pack(side="left", padx=5)

# Detection history log
history_label = tk.Label(window, text="Realtime Detection Timeline Log", font=("Helvetica", 11, "bold"), bg="#f5f5f5")
history_label.pack(pady=3)

history_listbox = tk.Listbox(window, height=6, width=80, font=("Consolas", 10))
history_listbox.pack(pady=5)

footer_label = tk.Label(window, text="Children Observer AI Core - PyTorch X3D Realtime Violence Detector", font=("Helvetica", 8), fg="#666666", bg="#f5f5f5")
footer_label.pack(side="bottom", fill="x", pady=5)

window.protocol("WM_DELETE_WINDOW", lambda: (stop_video(), window.destroy()))

if __name__ == "__main__":
    window.mainloop()
