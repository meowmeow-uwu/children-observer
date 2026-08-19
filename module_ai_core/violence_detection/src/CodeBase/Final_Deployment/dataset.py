# dataset.py
import os
import numpy as np
from torch.utils.data import Dataset
import torch

class VideoDataset(Dataset):
    def __init__(self, root_dir, transform=None):
        self.root_dir = root_dir
        self.transform = transform
        self.classes = ['Violence', 'NonViolence']
        self.frame_paths = []
        self.labels = []

        for label, class_name in enumerate(self.classes):
            class_dir = os.path.join(root_dir, class_name)
            if not os.path.exists(class_dir):
                continue
            for frame_file in os.listdir(class_dir):
                frame_path = os.path.join(class_dir, frame_file)
                self.frame_paths.append(frame_path)
                self.labels.append(label)

    def __len__(self):
        return len(self.frame_paths)
    def __getitem__(self, idx):
        frames = np.load(self.frame_paths[idx], allow_pickle=True)  # (T, H, W, C)
        
        # convert to tensor and permute to (C, T, H, W)
        frames = torch.from_numpy(frames).permute(3, 0, 1, 2).float()  # C, T, H, W
        
        label = self.labels[idx]
        return frames, label
