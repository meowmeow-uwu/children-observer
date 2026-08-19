# model_utils.py
import torch
import torch.nn as nn
from collections import OrderedDict
import pytorchvideo.models.hub as hub

def custome_X3D(num_classes=2):
    try:
        model = hub.x3d_m(pretrained=False)
    except Exception:
        model = torch.hub.load('facebookresearch/pytorchvideo', 'x3d_m', pretrained=False)
    input_size = model.blocks[-1].proj.in_features
    model.blocks[-1].proj = nn.Sequential(
        nn.Identity(),
        nn.Linear(in_features=input_size, out_features=num_classes)
    )
    return model

def load_model(model, model_path, device):
    state_dict = torch.load(model_path, map_location=device, weights_only=False)
    if isinstance(state_dict, dict) and 'model' in state_dict:
        state_dict = state_dict['model']
    
    new_state_dict = OrderedDict()
    for k, v in state_dict.items():
        key = k
        if key.startswith('module.'):
            key = key[len('module.'):]
        if key.startswith('backbone.'):
            key = key[len('backbone.'):]
        new_state_dict[key] = v
        
    model.load_state_dict(new_state_dict, strict=False)
    model.to(device)
    return model

