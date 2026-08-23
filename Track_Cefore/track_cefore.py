#!/usr/bin/env python3

import subprocess
import cv2
import numpy as np
from ultralytics import YOLO

# ==========================================================
# Settings
# ==========================================================

CCNX_URI = "ccnx:/live/video"

WIDTH = 1242
HEIGHT = 376

YOLO_MODEL = "yolov8n.pt"

FRAME_SIZE = WIDTH * HEIGHT * 3

# ==========================================================
# Utility
# ==========================================================

def read_exact(pipe, size):
    buf = bytearray()

    while len(buf) < size:
        chunk = pipe.read(size - len(buf))

        if not chunk:
            return None

        buf.extend(chunk)

    return bytes(buf)

# ==========================================================
# YOLO
# ==========================================================

print("Loading YOLO model...")
model = YOLO(YOLO_MODEL)

# ==========================================================
# Start cefgetstream
# ==========================================================

print("Starting cefgetstream...")

cef_proc = subprocess.Popen(
    ["cefgetstream", CCNX_URI],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
)

# ==========================================================
# Start ffmpeg
# ==========================================================

print("Starting ffmpeg...")

ff_proc = subprocess.Popen(
    [
        "ffmpeg",
        "-loglevel", "info",
        "-fflags", "nobuffer",
        "-flags", "low_delay",
        "-i", "pipe:0",
        "-f", "rawvideo",
        "-pix_fmt", "bgr24",
        "pipe:1"
    ],
    stdin=cef_proc.stdout,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
)

# ==========================================================
# Main Loop
# ==========================================================

try:

    while True:

        raw = read_exact(ff_proc.stdout, FRAME_SIZE)

        if raw is None:

            print("\n=== ffmpeg stderr ===")

            err = ff_proc.stderr.read()

            try:
                print(err.decode())
            except:
                print(err)

            print("=====================\n")

            print("Stream ended.")
            break

        frame = np.frombuffer(
            raw,
            dtype=np.uint8
        ).reshape((HEIGHT, WIDTH, 3))

        results = model.track(
            frame,
            persist=True,
            tracker="bytetrack.yaml",
            verbose=False
        )

        annotated = results[0].plot()

        cv2.imshow(
            "Cefore YOLOv8 Tracking",
            annotated
        )

        key = cv2.waitKey(1)

        if key == 27:
            break

finally:

    print("Cleaning up...")

    cv2.destroyAllWindows()

    for p in [ff_proc, cef_proc]:

        if p is not None:

            try:
                p.terminate()
                p.wait(timeout=2)
            except:
                try:
                    p.kill()
                except:
                    pass

print("Done.")
