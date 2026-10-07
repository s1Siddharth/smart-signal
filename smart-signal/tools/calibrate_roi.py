"""
tools/calibrate_roi.py — Interactive ROI calibration tool.

Usage:
    python tools/calibrate_roi.py [video_or_camera]

Click polygon points for each road (A, B, C, D). Press Enter to confirm each road.
Press 'r' to redo the current road. Press 'q' to quit and save.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2
import numpy as np

ROI_FILE = Path("roi.json")
ROADS = ["A", "B", "C", "D"]
COLORS = {
    "A": (0, 255, 0),
    "B": (0, 255, 255),
    "C": (255, 165, 0),
    "D": (255, 0, 255),
}


def main() -> None:
    source = sys.argv[1] if len(sys.argv) > 1 else "0"
    try:
        src = int(source)
    except ValueError:
        src = source

    cap = cv2.VideoCapture(src)
    if not cap.isOpened():
        print(f"Error: cannot open source: {source}")
        sys.exit(1)

    ok, first_frame = cap.read()
    if not ok:
        print("Error: cannot read first frame")
        sys.exit(1)
    cap.release()

    rois: dict[str, list[list[int]]] = {}

    for road in ROADS:
        frame = first_frame.copy()
        points: list[list[int]] = []

        print(f"\n=== Road {road} ===")
        print("Click polygon points. Press Enter to confirm, 'r' to redo, 'q' to quit.")

        def mouse_cb(event, x, y, flags, param):
            nonlocal frame, points
            if event == cv2.EVENT_LBUTTONDOWN:
                points.append([x, y])
                cv2.circle(frame, (x, y), 5, COLORS[road], -1)
                if len(points) > 1:
                    cv2.line(frame, tuple(points[-2]), tuple(points[-1]), COLORS[road], 2)

        cv2.namedWindow(f"Road {road}")
        cv2.setMouseCallback(f"Road {road}", mouse_cb)

        while True:
            # Draw all existing ROIs
            display = frame.copy()
            for r, pts in rois.items():
                poly = np.array(pts, dtype=np.int32)
                cv2.polylines(display, [poly], True, COLORS[r], 2)
                cx, cy = poly.mean(axis=0).astype(int)
                cv2.putText(display, f"Road {r}", (cx, cy), cv2.FONT_HERSHEY_SIMPLEX, 0.7, COLORS[r], 2)

            # Draw current points
            for pt in points:
                cv2.circle(display, tuple(pt), 5, COLORS[road], -1)
            if len(points) > 1:
                for i in range(1, len(points)):
                    cv2.line(display, tuple(points[i - 1]), tuple(points[i]), COLORS[road], 2)
            if len(points) > 2:
                cv2.line(display, tuple(points[-1]), tuple(points[0]), COLORS[road], 1)

            cv2.putText(display, f"Road {road}: click polygon points. Enter=confirm, r=redo, q=quit",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            cv2.imshow(f"Road {road}", display)

            key = cv2.waitKey(30) & 0xFF
            if key == 13 and len(points) >= 3:  # Enter
                rois[road] = points
                break
            elif key == ord("r"):
                points = []
                frame = first_frame.copy()
            elif key == ord("q"):
                print("Quitting.")
                cv2.destroyAllWindows()
                if rois:
                    ROI_FILE.write_text(json.dumps(rois, indent=2))
                    print(f"Saved {len(rois)} ROI(s) to {ROI_FILE}")
                return

        cv2.destroyAllWindows()

    ROI_FILE.write_text(json.dumps(rois, indent=2))
    print(f"\nAll ROIs saved to {ROI_FILE}")


if __name__ == "__main__":
    main()
