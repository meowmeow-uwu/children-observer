"""
Tests cho module_ai_core - datasets, models.
"""

import numpy as np
import pytest

from module_ai_core.datasets.childsun_loader import ChildSUnDataset, CHILDSUN_CLASSES
from module_ai_core.datasets.violence_loader import ViolenceDataset, VIOLENCE_CLASSES
from module_ai_core.datasets.augmentation import get_train_transforms, get_val_transforms


class TestChildSUnDataset:
    def test_classes_defined(self):
        assert len(CHILDSUN_CLASSES) > 0
        assert "child" in CHILDSUN_CLASSES
        assert "knife" in CHILDSUN_CLASSES

    def test_init_missing_dir(self):
        """Should not crash when dataset dir doesn't exist."""
        ds = ChildSUnDataset(root_dir="/nonexistent/path")
        assert len(ds) == 0

    def test_get_class_name(self):
        ds = ChildSUnDataset(root_dir="/nonexistent/path")
        assert ds.get_class_name(0) == "child"
        assert ds.get_class_name(999).startswith("unknown")


class TestViolenceDataset:
    def test_classes_defined(self):
        assert len(VIOLENCE_CLASSES) > 0
        assert "normal" in VIOLENCE_CLASSES
        assert "slap" in VIOLENCE_CLASSES

    def test_init_missing_dir(self):
        ds = ViolenceDataset(root_dir="/nonexistent/path")
        assert len(ds) == 0


class TestAugmentation:
    def test_train_transforms_created(self):
        transforms = get_train_transforms(640)
        assert transforms is not None

    def test_val_transforms_created(self):
        transforms = get_val_transforms(640)
        assert transforms is not None
