"""Export the approved fall pose checkpoint to static Raspberry Pi ONNX variants."""

from __future__ import annotations

import argparse
import hashlib
import shutil
from pathlib import Path

from ultralytics import YOLO


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path("weights/fall_detection/best.pt"))
    parser.add_argument("--sizes", type=int, nargs="+", default=[640, 416])
    args = parser.parse_args()
    if not args.source.exists():
        raise FileNotFoundError(args.source)

    print(f"source={args.source} sha256={sha256(args.source)}")
    model = YOLO(str(args.source))
    for size in args.sizes:
        exported = Path(model.export(format="onnx", imgsz=size, batch=1, dynamic=False, simplify=True, opset=17))
        destination = args.source.with_name(f"best-{size}.onnx")
        shutil.move(str(exported), destination)
        print(f"onnx={destination} sha256={sha256(destination)}")


if __name__ == "__main__":
    main()
