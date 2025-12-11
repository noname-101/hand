"""
Rewritten Hand Gesture Control System

Changes made:
- Click distance threshold made configurable (settings + default variable)
- Controls can be mapped to gestures (selectable per control)
- "Add Gesture" dialog: record a custom gesture and bind it to a control
- Action mapping saved to `action_mappings.json` (gesture + enabled)

Notes:
- This file still requires the external dependencies: mediapipe, opencv-python, numpy, pyautogui, PySide6
"""

import sys
import time
import json
from pathlib import Path
import cv2
import numpy as np
import mediapipe as mp
import pyautogui
import os
import hashlib
import re
import random
import smtplib
import ssl

from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QComboBox, QCheckBox, QFrame, QGridLayout, QMessageBox, QDialog,
    QListWidget, QSpinBox, QTabWidget, QTextEdit, QLineEdit, QFormLayout,
    QInputDialog
)
from PySide6.QtGui import QImage, QPixmap, QPainter, QColor, QFont, QPalette
from PySide6.QtCore import QThread, Signal, Qt
import logging

# configure logging: avoid creating a persistent debug log file by default.
# Keep warnings/errors visible for troubleshooting but don't write verbose debug
# output to disk unless the user explicitly enables it.
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s %(levelname)s: %(message)s'
)

# Minimal modern dark stylesheet (can be tweaked). Uses subtle accents and rounded controls.
DARK_STYLE = """
QWidget { background: #121212; color: #E6E6E6; font-family: 'Segoe UI', 'Helvetica Neue', Arial; }
QLabel { color: #E6E6E6; }
QPushButton { background: #1E1E1E; color: #E6E6E6; border: 1px solid #2b2b2b; padding: 6px 10px; border-radius: 6px; }
QPushButton:hover { background: #2a2a2a; }
QPushButton:pressed { background: #151515; }
QLineEdit, QSpinBox, QComboBox, QTextEdit, QListWidget { background: #181818; border: 1px solid #2b2b2b; color: #E6E6E6; padding: 4px; }
QTabWidget::pane { border: 1px solid #2b2b2b; }
QTabBar::tab { background: #191919; color: #CFCFCF; padding: 8px 12px; border-top-left-radius:6px; border-top-right-radius:6px; }
QTabBar::tab:selected { background: #222; color: #FFFFFF; }
QCheckBox { color: #E6E6E6; }
QComboBox QAbstractItemView { background: #181818; selection-background-color: #2b6ea3; }
QScrollBar:vertical { background: #151515; width:12px; }
QScrollBar::handle:vertical { background: #2a2a2a; border-radius:6px; }
QMenuBar { background: transparent; }
QToolTip { background: #2b2b2b; color: #E6E6E6; border: 1px solid #3a3a3a; }
"""


def apply_dark_theme(app: QApplication):
    """Apply DARK_STYLE and a dark palette to the given QApplication."""
    try:
        app.setStyleSheet(DARK_STYLE)
        pal = QPalette()
        pal.setColor(QPalette.Window, QColor('#121212'))
        pal.setColor(QPalette.WindowText, QColor('#E6E6E6'))
        pal.setColor(QPalette.Base, QColor('#181818'))
        pal.setColor(QPalette.AlternateBase, QColor('#202020'))
        pal.setColor(QPalette.ToolTipBase, QColor('#E6E6E6'))
        pal.setColor(QPalette.ToolTipText, QColor('#E6E6E6'))
        pal.setColor(QPalette.Text, QColor('#E6E6E6'))
        pal.setColor(QPalette.Button, QColor('#1e1e1e'))
        pal.setColor(QPalette.ButtonText, QColor('#E6E6E6'))
        pal.setColor(QPalette.Highlight, QColor('#0A84FF'))
        pal.setColor(QPalette.HighlightedText, QColor('#FFFFFF'))
        app.setPalette(pal)
        try:
            app.setFont(QFont('Segoe UI', 10))
        except Exception:
            pass
    except Exception:
        logging.exception('apply_dark_theme failed')


def apply_light_theme(app: QApplication):
    """Apply a modern light stylesheet and palette for a clean, modern look.

    This keeps the UI visually consistent with the dark theme but uses a
    light background, subtle borders and a blue accent color.
    """
    # lightweight modern light stylesheet
    LIGHT_STYLE = """
QWidget { background: #F7F9FC; color: #1F2937; font-family: 'Segoe UI', 'Helvetica Neue', Arial; }
QLabel { color: #111827; }
QPushButton { background: #FFFFFF; color: #111827; border: 1px solid #E6E9EE; padding: 6px 10px; border-radius: 6px; }
QPushButton:hover { background: #F0F4FA; }
QPushButton:pressed { background: #E9F0FB; }
QLineEdit, QSpinBox, QComboBox, QTextEdit, QListWidget { background: #FFFFFF; border: 1px solid #E6E9EE; color: #111827; padding: 4px; }
QTabWidget::pane { border: 1px solid #E6E9EE; }
QTabBar::tab { background: #F3F6FA; color: #111827; padding: 8px 12px; border-top-left-radius:6px; border-top-right-radius:6px; }
QTabBar::tab:selected { background: #FFFFFF; color: #0B63D6; }
QCheckBox { color: #111827; }
QComboBox QAbstractItemView { background: #FFFFFF; selection-background-color: #D7E9FF; }
QScrollBar:vertical { background: #F3F6FA; width:12px; }
QScrollBar::handle:vertical { background: #E0E6ED; border-radius:6px; }
QToolTip { background: #FFFFFF; color: #111827; border: 1px solid #E6E9EE; }
"""
    try:
        app.setStyleSheet(LIGHT_STYLE)
        pal = QPalette()
        pal.setColor(QPalette.Window, QColor('#F7F9FC'))
        pal.setColor(QPalette.WindowText, QColor('#111827'))
        pal.setColor(QPalette.Base, QColor('#FFFFFF'))
        pal.setColor(QPalette.AlternateBase, QColor('#F3F6FA'))
        pal.setColor(QPalette.ToolTipBase, QColor('#FFFFFF'))
        pal.setColor(QPalette.ToolTipText, QColor('#111827'))
        pal.setColor(QPalette.Text, QColor('#111827'))
        pal.setColor(QPalette.Button, QColor('#FFFFFF'))
        pal.setColor(QPalette.ButtonText, QColor('#111827'))
        pal.setColor(QPalette.Highlight, QColor('#0B63D6'))
        pal.setColor(QPalette.HighlightedText, QColor('#FFFFFF'))
        app.setPalette(pal)
        try:
            app.setFont(QFont('Segoe UI', 10))
        except Exception:
            pass
    except Exception:
        logging.exception('apply_light_theme failed')


# -----------------------------
# Hand tracking helper
# -----------------------------
class HandDetector:
    def __init__(self, mode=False, maxHands=1, detectionCon=0.5, trackCon=0.5):
        self.mode = mode
        self.maxHands = maxHands
        self.detectionCon = detectionCon
        self.trackCon = trackCon
        self.tipIds = [4, 8, 12, 16, 20]

        self.mpHands = mp.solutions.hands
        self.hands = self.mpHands.Hands(
            static_image_mode=self.mode,
            max_num_hands=self.maxHands,
            min_detection_confidence=self.detectionCon,
            min_tracking_confidence=self.trackCon,
        )
        self.mpDraw = mp.solutions.drawing_utils
        self.lmList = []
        self.results = None

    def findHands(self, img, draw=True):
        imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        self.results = self.hands.process(imgRGB)

        if self.results.multi_hand_landmarks:
            for handLms in self.results.multi_hand_landmarks:
                if draw:
                    self.mpDraw.draw_landmarks(img, handLms, self.mpHands.HAND_CONNECTIONS)
        return img

    def findPosition(self, img, handNo=0, draw=False):
        xList, yList, bbox = [], [], []
        self.lmList = []

        if self.results and self.results.multi_hand_landmarks:
            myHand = self.results.multi_hand_landmarks[handNo]
            for id, lm in enumerate(myHand.landmark):
                h, w, _ = img.shape
                cx, cy = int(lm.x * w), int(lm.y * h)
                xList.append(cx)
                yList.append(cy)
                self.lmList.append([id, cx, cy])
                if draw:
                    cv2.circle(img, (cx, cy), 4, (255, 0, 255), cv2.FILLED)

            if xList and yList:
                bbox = (min(xList), min(yList), max(xList), max(yList))
                if draw:
                    cv2.rectangle(img, (bbox[0] - 20, bbox[1] - 20),
                                  (bbox[2] + 20, bbox[3] + 20), (0, 255, 0), 2)

        return self.lmList, bbox

    def fingersUp(self):
        if len(self.lmList) != 21:
            return [0, 0, 0, 0, 0]

        fingers = []
        # Thumb
        if self.lmList[self.tipIds[0]][1] > self.lmList[self.tipIds[0] - 1][1]:
            fingers.append(1)
        else:
            fingers.append(0)

        # Other fingers
        for id in range(1, 5):
            if self.lmList[self.tipIds[id]][2] < self.lmList[self.tipIds[id] - 2][2]:
                fingers.append(1)
            else:
                fingers.append(0)

        return fingers

    def findDistance(self, p1, p2, img=None, draw=False):
        if len(self.lmList) < max(p1, p2) + 1:
            return 9999, img, []

        x1, y1 = self.lmList[p1][1:]
        x2, y2 = self.lmList[p2][1:]
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

        if draw and img is not None:
            cv2.line(img, (x1, y1), (x2, y2), (0, 0, 255), 2)
            cv2.circle(img, (x1, y1), 6, (0, 0, 255), cv2.FILLED)
            cv2.circle(img, (x2, y2), 6, (0, 0, 255), cv2.FILLED)

        length = np.hypot(x2 - x1, y2 - y1)
        return length, img, [x1, y1, x2, y2, cx, cy]


# -----------------------------
# Gesture recognizer
# -----------------------------
class GestureRecognizer:
    def __init__(self):
        self.gesture_templates = {}
        self.load_custom_gestures()
        # matching threshold for custom gestures (lower is more permissive)
        self.match_threshold = 0.6

    def save_custom_gestures(self):
        gestures_file = Path('custom_gestures.json')
        try:
            with open(gestures_file, 'w') as f:
                # save normalized feature templates (coords, orientation, tip_dists)
                json.dump(self.gesture_templates, f, indent=2)
        except Exception as e:
            print('Error saving gestures:', e)

    def load_custom_gestures(self):
        gestures_file = Path('custom_gestures.json')
        if gestures_file.exists():
            try:
                with open(gestures_file, 'r') as f:
                    raw = json.load(f)
                # Convert legacy formats (raw landmark frames or plain normalized coords)
                templates = {}
                for name, frames in raw.items():
                    converted = []
                    for frm in frames:
                        try:
                            # Already stored as feature dict?
                            if isinstance(frm, dict) and 'coords' in frm:
                                converted.append(frm)
                                continue

                            # If frm is list of 21 [x,y] normalized coords -> compute orientation & tips
                            if isinstance(frm, list) and len(frm) == 21 and isinstance(frm[0], list) and len(frm[0]) == 2:
                                # compute orientation and tip dists from normalized coords
                                coords = frm
                                # orientation approx: vector from wrist (0) to middle_mcp (9)
                                try:
                                    wx, wy = coords[0]
                                    mx, my = coords[9]
                                    ang = float(np.degrees(np.arctan2(my - wy, mx - wx)))
                                except Exception:
                                    ang = 0.0
                                # tips distances from wrist
                                tips = []
                                for tid in [4, 8, 12, 16, 20]:
                                    tx, ty = coords[tid]
                                    d = float(np.hypot(tx - wx, ty - wy))
                                    tips.append(d)
                                converted.append({'coords': coords, 'orientation': ang, 'tip_dists': tips})
                                continue

                            # If frm is raw landmarks list of [id,x,y] -> convert to features
                            if isinstance(frm, list) and len(frm) >= 21 and isinstance(frm[0], list):
                                lm = [[int(p[0]), int(p[1]), int(p[2])] for p in frm]
                                coords = self._normalize_landmarks(lm)
                                if not coords:
                                    continue
                                wx, wy = coords[0]
                                mx, my = coords[9]
                                ang = float(np.degrees(np.arctan2(my - wy, mx - wx)))
                                tips = []
                                for tid in [4, 8, 12, 16, 20]:
                                    tx, ty = coords[tid]
                                    d = float(np.hypot(tx - wx, ty - wy))
                                    tips.append(d)
                                converted.append({'coords': coords, 'orientation': ang, 'tip_dists': tips})
                                continue

                        except Exception:
                            continue
                    if converted:
                        templates[name] = {'frames': converted, 'threshold': 0.6}
                self.gesture_templates = templates
            except Exception as e:
                print('Error loading gestures:', e)

    def _frame_to_features(self, lmList):
        """Convert an lmList (21 x [id,x,y]) to a feature dict:
        - coords: normalized list of [nx,ny]
        - orientation: angle degrees from wrist->middle_mcp
        - tip_dists: normalized distances tip->wrist for [thumb,index,middle,ring,pinky]
        """
        # Support either raw lmList ([[id,x,y],...]) or normalized coords ([[nx,ny],...])
        if not lmList or len(lmList) != 21:
            return None
        first = lmList[0]
        if isinstance(first, list) and len(first) == 2 and all(isinstance(v, (int, float)) for v in first):
            coords = lmList  # already normalized coords
        else:
            coords = self._normalize_landmarks(lmList)
        if not coords:
            return None
        try:
            wx, wy = coords[0]
            mx, my = coords[9]
            ang = float(np.degrees(np.arctan2(my - wy, mx - wx)))
        except Exception:
            ang = 0.0
        tips = []
        for tid in [4, 8, 12, 16, 20]:
            tx, ty = coords[tid]
            d = float(np.hypot(tx - wx, ty - wy))
            tips.append(d)
        # per-landmark vectors: to wrist and to previous landmark
        import math
        landmark_feats = []
        for i, (nx, ny) in enumerate(coords):
            dx_w = nx - wx
            dy_w = ny - wy
            dist_w = float(math.hypot(dx_w, dy_w))
            angle_w = float(math.atan2(dy_w, dx_w))

            if i == 0:
                dx_p = 0.0; dy_p = 0.0; dist_p = 0.0; angle_p = 0.0
            else:
                px, py = coords[i - 1]
                dx_p = nx - px
                dy_p = ny - py
                dist_p = float(math.hypot(dx_p, dy_p))
                angle_p = float(math.atan2(dy_p, dx_p))

            landmark_feats.append([float(nx), float(ny), float(dx_w), float(dy_w), float(dist_w), float(angle_w), float(dx_p), float(dy_p), float(dist_p), float(angle_p)])

        return {'coords': coords, 'orientation': ang, 'tip_dists': tips, 'landmark_feats': landmark_feats}

    def _get_fingers_state(self, lmList):
        if len(lmList) != 21:
            return [0, 0, 0, 0, 0]

        tipIds = [4, 8, 12, 16, 20]
        fingers = []

        # Thumb
        if lmList[tipIds[0]][1] > lmList[tipIds[0] - 1][1]:
            fingers.append(1)
        else:
            fingers.append(0)

        # Other fingers
        for id in range(1, 5):
            if lmList[tipIds[id]][2] < lmList[tipIds[id] - 2][2]:
                fingers.append(1)
            else:
                fingers.append(0)

        return fingers

    def _recognize_builtin(self, lmList):
        fingers = self._get_fingers_state(lmList)

        if sum(fingers) == 5:
            return 'scroll_up'
        if sum(fingers) == 0:
            return 'scroll_down'
        if fingers[1] == 1 and sum(fingers) == 1:
            return 'move'
        if fingers[1] == 1 and fingers[2] == 1 and sum(fingers) == 2:
            return 'left_click'
        if fingers[0] == 1 and fingers[1] == 1 and sum(fingers[1:]) == 1:
            return 'right_click'
        return 'none'

    def _normalize_landmarks(self, lmList):
        if not lmList:
            return []

        xs = [p[1] for p in lmList]
        ys = [p[2] for p in lmList]
        minx, maxx = min(xs), max(xs)
        miny, maxy = min(ys), max(ys)
        width = max(maxx - minx, 1)
        height = max(maxy - miny, 1)

        normalized = []
        for p in lmList:
            nx = (p[1] - minx) / width
            ny = (p[2] - miny) / height
            normalized.append([nx, ny])
        return normalized

    def _calculate_similarity(self, lm1, lm2):
        # Use Procrustes alignment for rotation/scale invariance before measuring distance
        # Support both plain coord lists and feature dicts
        # If inputs are feature dicts, combine Procrustes-aligned coord similarity,
        # orientation similarity, and tip-distance similarity.
        if isinstance(lm1, dict) and isinstance(lm2, dict):
            try:
                A = np.array(lm1['coords'])
                B = np.array(lm2['coords'])
                coord_sim = self._procrustes_similarity(A, B)

                a1 = float(lm1.get('orientation', 0.0))
                a2 = float(lm2.get('orientation', 0.0))
                ang_diff = min(abs(a1 - a2), 360 - abs(a1 - a2))
                ang_sim = max(0.0, 1.0 - (ang_diff / 90.0))

                # tip distances similarity (fallback)
                t1 = lm1.get('tip_dists', [])
                t2 = lm2.get('tip_dists', [])
                tip_sim = 0.0
                if t1 and t2 and len(t1) == len(t2):
                    diffs = [abs(x - y) for x, y in zip(t1, t2)]
                    avg_diff = float(sum(diffs) / len(diffs))
                    tip_sim = max(0.0, 1.0 - avg_diff)

                # per-landmark feature similarity if available
                feat_sim = 0.0
                if 'landmark_feats' in lm1 and 'landmark_feats' in lm2:
                    feat_sim = self._feature_similarity(lm1['landmark_feats'], lm2['landmark_feats'])

                # combine: give more weight to coordinate alignment and landmark features
                return 0.45 * coord_sim + 0.25 * feat_sim + 0.15 * ang_sim + 0.15 * tip_sim
            except Exception:
                return 0.0

        # Fallback: both are coord lists
        if not isinstance(lm1, list) or not isinstance(lm2, list):
            return 0.0
        if len(lm1) != len(lm2) or len(lm1) == 0:
            return 0.0
        total_distance = 0.0
        for p1, p2 in zip(lm1, lm2):
            dist = np.hypot(p1[0] - p2[0], p1[1] - p2[1])
            total_distance += dist
        avg_distance = total_distance / len(lm1)
        return max(0.0, 1.0 - avg_distance)

    def _procrustes_similarity(self, lm1, lm2):
        """Compute a similarity score between two normalized landmark sets using
        Procrustes alignment (translation, scaling, rotation). Returns similarity in [0,1]."""
        try:
            A = np.array(lm1, dtype=float)
            B = np.array(lm2, dtype=float)
            if A.shape != B.shape or A.shape[0] == 0:
                return 0.0

            # center
            A_c = A - A.mean(axis=0)
            B_c = B - B.mean(axis=0)

            # scale to unit norm
            normA = np.linalg.norm(A_c)
            normB = np.linalg.norm(B_c)
            if normA == 0 or normB == 0:
                return 0.0
            A_c /= normA
            B_c /= normB

            # optimal rotation via SVD
            U, _, Vt = np.linalg.svd(A_c.T @ B_c)
            R = U @ Vt
            A_rot = A_c @ R

            # compute mean pointwise distance
            dists = np.linalg.norm(A_rot - B_c, axis=1)
            avg = float(dists.mean())
            sim = max(0.0, 1.0 - avg)
            return sim
        except Exception:
            return 0.0

    def mean_template(self, templates):
        """Compute mean template from a list of normalized frames (Nx21x2)"""
        if not templates:
            return []
        try:
            arr = np.array(templates, dtype=float)
            mean = arr.mean(axis=0)
            return mean.tolist()
        except Exception:
            return []

    def _procrustes_similarity(self, A, B):
        """Compute similarity after Procrustes alignment of A->B.
        Returns value in [0,1] where 1 is identical.
        """
        try:
            A = np.array(A, dtype=np.float64)
            B = np.array(B, dtype=np.float64)
            if A.shape != B.shape or A.size == 0:
                return 0.0

            # center
            A_c = A - A.mean(axis=0)
            B_c = B - B.mean(axis=0)

            # scale to unit norm
            normA = np.linalg.norm(A_c)
            normB = np.linalg.norm(B_c)
            if normA == 0 or normB == 0:
                return 0.0
            A_n = A_c / normA
            B_n = B_c / normB

            # optimal rotation
            M = A_n.T.dot(B_n)
            U, _, Vt = np.linalg.svd(M)
            R = U.dot(Vt)
            A_rot = A_n.dot(R)

            # avg distance
            diffs = np.linalg.norm(A_rot - B_n, axis=1)
            avg = float(np.mean(diffs))
            sim = max(0.0, 1.0 - avg)
            return sim
        except Exception:
            return 0.0

    def _compare_with_templates(self, normalized_lm, templates):
        # normalized_lm may be coords (list of [x,y]) or a feature dict
        if not templates or not normalized_lm:
            return 0.0
        # ensure we have a feature dict for the current frame
        if isinstance(normalized_lm, list):
            curr_feat = self._frame_to_features(normalized_lm)
        else:
            curr_feat = normalized_lm

        max_similarity = 0.0
        for template in templates:
            # template may be a feature dict or pre-normalized coords
            sim = 0.0
            if isinstance(template, dict):
                sim = self._calculate_similarity(curr_feat, template)
            elif isinstance(template, list):
                # list of coords
                sim = self._calculate_similarity(curr_feat, template)
            max_similarity = max(max_similarity, sim)
        return max_similarity

    def _feature_similarity(self, featsA, featsB):
        """Compute similarity between two feature lists (21 x features).
        Returns value in [0,1]."""
        import math
        if not featsA or not featsB or len(featsA) != len(featsB):
            return 0.0
        total = 0.0
        n = len(featsA)
        for a, b in zip(featsA, featsB):
            # a and b are lists: [nx, ny, dx_w, dy_w, dist_w, angle_w, dx_p, dy_p, dist_p, angle_p]
            ax_pw, ay_pw = a[6], a[7]
            bx_pw, by_pw = b[6], b[7]
            na = math.hypot(ax_pw, ay_pw)
            nb = math.hypot(bx_pw, by_pw)
            cos_prev = 1.0 if na == 0 and nb == 0 else max(-1.0, min(1.0, (ax_pw * bx_pw + ay_pw * by_pw) / (na * nb + 1e-9)))
            sim_prev = (1.0 + cos_prev) / 2.0

            ax_w, ay_w = a[2], a[3]
            bx_w, by_w = b[2], b[3]
            naw = math.hypot(ax_w, ay_w)
            nbw = math.hypot(bx_w, by_w)
            cos_w = 1.0 if naw == 0 and nbw == 0 else max(-1.0, min(1.0, (ax_w * bx_w + ay_w * by_w) / (naw * nbw + 1e-9)))
            sim_w = (1.0 + cos_w) / 2.0

            # distance similarity (prev and wrist distances)
            dist_pa = a[8]
            dist_pb = b[8]
            dist_wa = a[4]
            dist_wb = b[4]
            sim_dist_prev = 1.0 - min(1.0, abs(dist_pa - dist_pb))
            sim_dist_w = 1.0 - min(1.0, abs(dist_wa - dist_wb))

            # combine
            sim = 0.45 * sim_prev + 0.45 * sim_w + 0.05 * sim_dist_prev + 0.05 * sim_dist_w
            total += sim
        return float(total / n)

    def recognize_gesture(self, lmList):
        if len(lmList) != 21:
            return 'none', 0.0

        builtin = self._recognize_builtin(lmList)
        if builtin != 'none':
            return builtin, 1.0

        normalized = self._normalize_landmarks(lmList)
        if not normalized:
            return 'none', 0.0

        # build current feature dict
        curr_feat = self._frame_to_features(normalized)
        if not curr_feat:
            return 'none', 0.0

        for name, templates in self.gesture_templates.items():
            # templates may be stored as {'frames': [...], 'threshold': x} or legacy list
            if isinstance(templates, dict) and 'frames' in templates:
                frames = templates.get('frames', [])
                threshold = float(templates.get('threshold', self.match_threshold))
            else:
                frames = templates
                threshold = self.match_threshold

            sim = self._compare_with_templates(curr_feat, frames)
            if sim >= threshold:
                return name, sim

        return 'none', 0.0


# -----------------------------
# Camera worker (captures frames & executes actions)
# -----------------------------
class CameraWorker(QThread):
    image_update = Signal(QImage)
    gesture_update = Signal(str)
    landmarks_update = Signal(list)

    def __init__(self, src=0):
        super().__init__()
        self.src = src
        self.running = False
        self.detector = HandDetector(maxHands=1)
        self.recognizer = GestureRecognizer()

        # camera + mapping
        self.wCam, self.hCam = 640, 480
        self.frameR = 100
        self.smoothening = 7
        self.plocX = 0
        self.plocY = 0
        self.clocX = 0
        self.clocY = 0

        # timing
        self.last_click_time = 0
        self.last_scroll_time = 0
        self.click_delay = 0.3
        self.scroll_delay = 0.05

        # threshold for finger-distance-based clicks (configurable)
        # interpreted as percentage of hand bounding-box diagonal (e.g. 8 = 8%)
        # Provide per-action defaults: left click more sensitive (10%), right click less (25%)
        self.click_distance_percentage = 8
        self.left_click_distance_percentage = 10
        self.right_click_distance_percentage = 50

        # attempt to load persisted settings (overrides defaults if present)
        try:
            self.load_settings()
        except Exception:
            pass

        # action mappings: {action: {enabled: bool, gesture: str}}
        self.enable_actions = True
        self.action_mappings = {}
        self.load_action_mappings()

    def stop(self, wait_ms: int = 2000):
        """Stop the camera worker loop and wait for the thread to finish.

        wait_ms: milliseconds to wait for the thread to exit (passed to QThread.wait).
        """
        try:
            # signal the run loop to stop
            self.running = False
            # if there's an event loop, request quit as well
            try:
                self.quit()
            except Exception:
                pass
            # wait for the thread to actually finish
            try:
                self.wait(wait_ms)
            except Exception:
                pass
        except Exception:
            logging.exception('Error while stopping CameraWorker')

    def load_action_mappings(self):
        try:
            with open('action_mappings.json', 'r') as f:
                self.action_mappings = json.load(f)
        except Exception:
            # defaults
            self.action_mappings = {
                'move': {'enabled': True, 'gesture': 'move'},
                'left_click': {'enabled': True, 'gesture': 'left_click'},
                'right_click': {'enabled': True, 'gesture': 'right_click'},
                'scroll_up': {'enabled': True, 'gesture': 'scroll_up'},
                'scroll_down': {'enabled': True, 'gesture': 'scroll_down'},
            }
    def load_settings(self):
        cfg = {}
        try:
            with open('settings.json', 'r') as f:
                cfg = json.load(f)
        except Exception:
            cfg = {}

        # backward-compatible keys
        try:
            if 'smoothening' in cfg:
                self.smoothening = int(cfg.get('smoothening', self.smoothening))
            if 'click_delay_ms' in cfg:
                self.click_delay = float(cfg.get('click_delay_ms', int(self.click_delay * 1000))) / 1000.0
            if 'click_distance_percentage' in cfg:
                self.click_distance_percentage = int(cfg.get('click_distance_percentage', self.click_distance_percentage))
            if 'left_click_distance_percentage' in cfg:
                self.left_click_distance_percentage = int(cfg.get('left_click_distance_percentage', self.left_click_distance_percentage))
            if 'right_click_distance_percentage' in cfg:
                self.right_click_distance_percentage = int(cfg.get('right_click_distance_percentage', self.right_click_distance_percentage))
            # theme
            if 'dark_mode' in cfg:
                try:
                    self.dark_mode = bool(cfg.get('dark_mode', False))
                except Exception:
                    self.dark_mode = False
            else:
                # default to True (dark) if not specified
                self.dark_mode = True
        except Exception:
            # fallback defaults
            self.dark_mode = True

    def save_settings(self):
        cfg = {
            'smoothening': int(self.smoothening),
            'click_delay_ms': int(self.click_delay * 1000),
            'click_distance_percentage': int(self.click_distance_percentage),
            'left_click_distance_percentage': int(self.left_click_distance_percentage),
            'right_click_distance_percentage': int(self.right_click_distance_percentage),
            'dark_mode': bool(getattr(self, 'dark_mode', True)),
        }
        try:
            with open('settings.json', 'w') as f:
                json.dump(cfg, f, indent=2)
        except Exception:
            logging.exception('Failed to save settings.json')

    def save_action_mappings(self):
        try:
            with open('action_mappings.json', 'w') as f:
                json.dump(self.action_mappings, f, indent=2)
        except Exception as e:
            print('Error saving mappings:', e)

    def run(self):
        cap = cv2.VideoCapture(self.src)
        if not cap.isOpened():
            for i in range(1, 4):
                cap = cv2.VideoCapture(i)
                if cap.isOpened():
                    break

        cap.set(3, self.wCam)
        cap.set(4, self.hCam)

        self.running = True
        while self.running:
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.02)
                continue

            frame = cv2.flip(frame, 1)
            frame = self.detector.findHands(frame)
            lmList, bbox = self.detector.findPosition(frame)

            gesture = 'none'
            if lmList:
                gesture, _ = self.recognizer.recognize_gesture(lmList)

            # overlay
            cv2.rectangle(frame, (self.frameR, self.frameR),
                          (self.wCam - self.frameR, self.hCam - self.frameR), (255, 0, 255), 2)
            cv2.putText(frame, f'Gesture: {gesture}', (20, 40), cv2.FONT_HERSHEY_PLAIN, 2, (0, 255, 0), 2)

            # emit UI
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_frame.shape
            qt_image = QImage(rgb_frame.data, w, h, ch * w, QImage.Format_RGB888)
            self.image_update.emit(qt_image)
            self.gesture_update.emit(gesture)
            self.landmarks_update.emit(lmList)

            if self.enable_actions and lmList:
                self._execute_action(gesture, lmList, frame, bbox)

            time.sleep(0.01)

        cap.release()

    def _execute_action(self, gesture, lmList, frame, bbox=None):
        now = time.time()
        screen_width, screen_height = pyautogui.size()

        # compute hand size reference (diagonal of bbox) for scale-invariant thresholds
        hand_diag = None
        if bbox and len(bbox) == 4:
            bw = bbox[2] - bbox[0]
            bh = bbox[3] - bbox[1]
            hand_diag = np.hypot(bw, bh)
        else:
            # fallback to frame size reference
            hand_diag = np.hypot(self.wCam, self.hCam)

        # actual threshold in pixels derived from percentage
        actual_threshold = max(6, int((self.click_distance_percentage / 100.0) * hand_diag))

        # Move: uses index tip (8) mapped to screen
        if 'move' in self.action_mappings and self.action_mappings['move']['enabled']:
            mapped_g = self.action_mappings['move'].get('gesture', 'move')
            if gesture == mapped_g and len(lmList) == 21:
                x1, y1 = lmList[8][1:]
                x3 = np.interp(x1, (self.frameR, self.wCam - self.frameR), (0, screen_width))
                y3 = np.interp(y1, (self.frameR, self.hCam - self.frameR), (0, screen_height))
                self.clocX = self.plocX + (x3 - self.plocX) / self.smoothening
                self.clocY = self.plocY + (y3 - self.plocY) / self.smoothening
                try:
                    pyautogui.moveTo(int(self.clocX), int(self.clocY))
                    self.plocX, self.plocY = self.clocX, self.clocY
                except Exception:
                    pass

        # Left click: check configured mapping
        if 'left_click' in self.action_mappings and self.action_mappings['left_click']['enabled']:
            mapped_g = self.action_mappings['left_click'].get('gesture', 'left_click')
            if gesture == mapped_g and now - self.last_click_time > self.click_delay:
                # use distance between index (8) and middle (12)
                length, _, pts = self.detector.findDistance(8, 12, frame, draw=False)
                # compute percentage of hand diagonal
                try:
                    hand_diag_val = float(hand_diag) if hand_diag and hand_diag > 0 else float(np.hypot(self.wCam, self.hCam))
                except Exception:
                    hand_diag_val = float(np.hypot(self.wCam, self.hCam))
                left_percent = (length / hand_diag_val) * 100.0
                logging.debug(f"Left click check: gesture={gesture}, mapped={mapped_g}, length={length:.2f}px, percent={left_percent:.2f}%, thr_pct={self.left_click_distance_percentage}%, cooldown={(now - self.last_click_time):.3f}s")
                # draw debug overlay for left click distance
                try:
                    cv2.putText(frame, f'Idx-Mid: {int(length)}px ({left_percent:.0f}%)', (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 255), 2)
                except Exception:
                    pass
                if left_percent <= float(self.left_click_distance_percentage):
                    try:
                        pyautogui.click()
                        logging.debug('LEFT CLICK executed')
                        print('LEFT CLICK')
                        # visual feedback on frame
                        if pts and len(pts) >= 6:
                            cx, cy = int(pts[4]), int(pts[5])
                            try:
                                cv2.circle(frame, (cx, cy), 10, (0, 255, 0), 3)
                            except Exception:
                                pass
                    except Exception as e:
                        logging.exception(f'Left click failed: {e}')
                    self.last_click_time = now
                else:
                    logging.debug('Left click condition not met (distance above threshold)')

        # Right click
        if 'right_click' in self.action_mappings and self.action_mappings['right_click']['enabled']:
            mapped_g = self.action_mappings['right_click'].get('gesture', 'right_click')
            if gesture == mapped_g and now - self.last_click_time > self.click_delay:
                # use distance between thumb (4) and index (8)
                length, _, pts = self.detector.findDistance(4, 8, frame, draw=False)
                try:
                    hand_diag_val = float(hand_diag) if hand_diag and hand_diag > 0 else float(np.hypot(self.wCam, self.hCam))
                except Exception:
                    hand_diag_val = float(np.hypot(self.wCam, self.hCam))
                right_percent = (length / hand_diag_val) * 100.0
                logging.debug(f"Right click check: gesture={gesture}, mapped={mapped_g}, length={length:.2f}px, percent={right_percent:.2f}%, thr_pct={self.right_click_distance_percentage}%, cooldown={(now - self.last_click_time):.3f}s")
                # draw debug overlay for right click distance
                try:
                    cv2.putText(frame, f'Thm-Idx: {int(length)}px ({right_percent:.0f}%)', (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 255), 2)
                except Exception:
                    pass
                if right_percent <= float(self.right_click_distance_percentage):
                    try:
                        pyautogui.rightClick()
                        logging.debug('RIGHT CLICK executed')
                        print('RIGHT CLICK')
                        if pts and len(pts) >= 6:
                            cx, cy = int(pts[4]), int(pts[5])
                            try:
                                cv2.circle(frame, (cx, cy), 10, (0, 255, 0), 3)
                            except Exception:
                                pass
                    except Exception as e:
                        logging.exception(f'Right click failed: {e}')
                    self.last_click_time = now
                else:
                    logging.debug('Right click condition not met (distance above threshold)')

        # Scroll up/down
        if 'scroll_up' in self.action_mappings and self.action_mappings['scroll_up']['enabled']:
            mapped_g = self.action_mappings['scroll_up'].get('gesture', 'scroll_up')
            if gesture == mapped_g and now - self.last_scroll_time > self.scroll_delay:
                try:
                    pyautogui.scroll(50)
                    print('SCROLL UP')
                except Exception:
                    pass
                self.last_scroll_time = now

        if 'scroll_down' in self.action_mappings and self.action_mappings['scroll_down']['enabled']:
            mapped_g = self.action_mappings['scroll_down'].get('gesture', 'scroll_down')
            if gesture == mapped_g and now - self.last_scroll_time > self.scroll_delay:
                try:
                    pyautogui.scroll(-50)
                    print('SCROLL DOWN')
                except Exception:
                    pass
                self.last_scroll_time = now


# -----------------------------
# Preview rendering helper
# -----------------------------
def render_template_pixmap(template_points, size=200):
    """Render normalized template points (list of [x,y]) into a QPixmap."""
    pix = QPixmap(size, size)
    pix.fill(QColor(40, 40, 40))
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(QColor(0, 180, 255))
    painter.setPen(QColor(200, 200, 200))
    for p in template_points:
        try:
            x = int(max(0, min(size - 1, p[0] * size)))
            y = int(max(0, min(size - 1, p[1] * size)))
            painter.drawEllipse(x - 4, y - 4, 8, 8)
        except Exception:
            continue
    painter.end()
    return pix


class PreviewConfirmDialog(QDialog):
    """Show preview of mean template and similarity warnings against existing gestures.
    Returns True if user accepts (Save), False if user wants to retake, None if cancelled."""
    def __init__(self, parent, pixmap, similarities):
        super().__init__(parent)
        self.setWindowTitle('Preview Recorded Gesture')
        self.setMinimumSize(420, 320)
        layout = QVBoxLayout()

        h = QHBoxLayout()
        self.preview = QLabel()
        self.preview.setPixmap(pixmap)
        self.preview.setFixedSize(200, 200)
        h.addWidget(self.preview)

        # similarity list
        sim_text = ''
        if similarities:
            sim_text = 'Similar gestures:\n'
            for name, sim in similarities:
                sim_text += f'  {name}: {sim:.2f}\n'
        else:
            sim_text = 'No similar gestures detected.'

        self.sim_label = QTextEdit()
        self.sim_label.setReadOnly(True)
        self.sim_label.setPlainText(sim_text)
        h.addWidget(self.sim_label)

        layout.addLayout(h)

        btn_layout = QHBoxLayout()
        self.retake_btn = QPushButton('Retake')
        self.save_btn = QPushButton('Save & Bind')
        self.cancel_btn = QPushButton('Cancel')
        btn_layout.addWidget(self.retake_btn)
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

        self.retake_btn.clicked.connect(self._on_retake)
        self.save_btn.clicked.connect(self._on_save)
        self.cancel_btn.clicked.connect(self._on_cancel)

        self.choice = None

    def _on_retake(self):
        self.choice = False
        self.done(0)

    def _on_save(self):
        self.choice = True
        self.accept()

    def _on_cancel(self):
        self.choice = None
        self.reject()


# -----------------------------
# Simple Login / Register dialog
# -----------------------------
class LoginDialog(QDialog):
    def __init__(self, parent=None, users_file='users.json'):
        super().__init__(parent)
        self.users_file = Path(users_file)
        self.setWindowTitle('Login')
        self.setMinimumSize(360, 160)

        layout = QVBoxLayout()
        form = QFormLayout()
        self.user_edit = QLineEdit()
        self.pass_edit = QLineEdit()
        self.pass_edit.setEchoMode(QLineEdit.Password)
        self.email_edit = QLineEdit()
        self.email_edit.setPlaceholderText('Required for registration')
        form.addRow('Username:', self.user_edit)
        form.addRow('Password:', self.pass_edit)
        form.addRow('Email (for registration):', self.email_edit)
        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        self.login_btn = QPushButton('Login')
        self.register_btn = QPushButton('Register')
        self.reset_btn = QPushButton('Forgot / Reset Password')
        self.cancel_btn = QPushButton('Cancel')
        btn_layout.addWidget(self.login_btn)
        btn_layout.addWidget(self.register_btn)
        btn_layout.addWidget(self.reset_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

        self.login_btn.clicked.connect(self.try_login)
        self.register_btn.clicked.connect(self.try_register)
        self.reset_btn.clicked.connect(self.try_reset_password)
        self.cancel_btn.clicked.connect(self.reject)

        # ensure users file exists
        if not self.users_file.exists():
            try:
                with open(self.users_file, 'w') as f:
                    json.dump({}, f)
            except Exception:
                pass

    def _hash(self, password: str) -> str:
        return hashlib.sha256(password.encode('utf-8')).hexdigest()

    def _save_users(self, users: dict):
        try:
            with open(self.users_file, 'w') as f:
                json.dump(users, f, indent=2)
        except Exception:
            pass

    def _generate_code(self, digits=6):
        start = 10 ** (digits - 1)
        return str(random.randint(start, 10**digits - 1))

    def _send_verification_code(self, to_email: str, code: str) -> (bool, str):
        """Try to send an email with the verification code.
        Looks for `email_config.json` or environment variables. Returns (sent, message).
        If sending is not configured or fails, returns (False, reason).
        """
        cfg_file = Path('email_config.json')
        cfg = {}
        if cfg_file.exists():
            try:
                with open(cfg_file, 'r') as f:
                    cfg = json.load(f)
            except Exception:
                cfg = {}

        # env overrides
        smtp_server = os.environ.get('SMTP_SERVER') or cfg.get('smtp_server')
        smtp_port = int(os.environ.get('SMTP_PORT') or cfg.get('smtp_port', 0) or 0)
        smtp_user = os.environ.get('SMTP_USER') or cfg.get('smtp_user')
        smtp_pass = os.environ.get('SMTP_PASS') or cfg.get('smtp_pass')
        use_tls = bool(os.environ.get('SMTP_TLS', cfg.get('smtp_tls', False)))

        if not smtp_server or not smtp_port or not smtp_user or not smtp_pass:
            return False, 'No SMTP configuration found; showing code locally for verification.'

        # compose simple message
        subject = 'Your verification code'
        body = f'Your verification code is: {code}'
        message = f'Subject: {subject}\n\n{body}'

        try:
            context = ssl.create_default_context()
            with smtplib.SMTP(smtp_server, smtp_port, timeout=10) as server:
                if use_tls:
                    server.starttls(context=context)
                server.login(smtp_user, smtp_pass)
                server.sendmail(smtp_user, to_email, message)
            return True, 'Sent'
        except Exception as e:
            return False, f'Failed to send email: {e}'

    def _prompt_verification(self, email: str, code: str) -> bool:
        """Prompt user to enter the verification code. Returns True if matched."""
        # For convenience, give the user up to 3 attempts
        attempts = 3
        for _ in range(attempts):
            txt, ok = QInputDialog.getText(self, 'Enter verification code', f'A verification code was sent to {email}. Enter it here:')
            if not ok:
                return False
            if txt.strip() == code:
                return True
            QMessageBox.warning(self, 'Incorrect', 'Verification code incorrect, try again')
        return False

    def try_login(self):
        user = self.user_edit.text().strip()
        pwd = self.pass_edit.text().strip()
        logging.debug(f"Login attempt for user='{user}'")
        if not user or not pwd:
            QMessageBox.warning(self, 'Error', 'Enter username and password')
            return
        try:
            with open(self.users_file, 'r') as f:
                users = json.load(f)
            logging.debug(f"Loaded users file '{self.users_file}' successfully; user count={len(users)}")
        except Exception:
            users = {}
            logging.exception(f"Failed to load users file '{self.users_file}'")
        if user not in users:
            logging.debug(f"User '{user}' not found in users.json")
            QMessageBox.warning(self, 'Login failed', 'User does not exist')
            return

        stored = users.get(user)
        # legacy format: stored is a hash string
        if isinstance(stored, str):
            logging.debug(f"Stored entry for '{user}' is legacy hash string")
            if stored == self._hash(pwd):
                logging.debug(f"Password match for legacy user '{user}'")
                self.accept()
                return
            else:
                logging.debug(f"Password mismatch for legacy user '{user}'; stored={stored[:12]}..., computed={self._hash(pwd)[:12]}...")
                # allow a quick debug reveal to help diagnose hash mismatches
                resp = QMessageBox.question(self, 'Login failed', 'Invalid username or password. Show debug info?', QMessageBox.Yes | QMessageBox.No)
                if resp == QMessageBox.Yes:
                    comp = self._hash(pwd)
                    QMessageBox.information(self, 'Debug', f'Stored hash: {stored[:8]}...\nComputed: {comp[:8]}...')
                return

        # new format: dict with password/email/verified
        if isinstance(stored, dict):
            logging.debug(f"Stored entry for '{user}' is dict; keys={list(stored.keys())}")
            if stored.get('password') != self._hash(pwd):
                logging.debug(f"Password mismatch for user '{user}'; stored='{str(stored.get('password'))[:12]}...', computed='{self._hash(pwd)[:12]}...'")
                resp = QMessageBox.question(self, 'Login failed', 'Invalid username or password. Show debug info?', QMessageBox.Yes | QMessageBox.No)
                if resp == QMessageBox.Yes:
                    comp = self._hash(pwd)
                    stored_pw = str(stored.get('password', ''))
                    QMessageBox.information(self, 'Debug', f'Stored hash: {stored_pw[:8]}...\nComputed: {comp[:8]}...')
                return

            # If password matches but the user is not verified, run verification flow.
            if not stored.get('verified', False):
                # attempt verification
                code = self._generate_code()
                sent, msg = self._send_verification_code(stored.get('email', ''), code)
                if not sent:
                    # show code locally for testing / fallback
                    QMessageBox.information(self, 'Verification', f"Could not send email ({msg}).\nUse this code for verification: {code}")
                else:
                    QMessageBox.information(self, 'Verification', 'Verification code sent to your email')

                ok = self._prompt_verification(stored.get('email', ''), code)
                if ok:
                    users[user]['verified'] = True
                    self._save_users(users)
                    logging.debug(f"User '{user}' verified via code and updated in users.json")
                    QMessageBox.information(self, 'Verified', 'Email verified — you can now login')
                    self.accept()
                    return
                else:
                    logging.debug(f"Verification failed for user '{user}' during login")
                    QMessageBox.warning(self, 'Verification failed', 'Could not verify email')
                    return

            # Password matched and user is verified: accept the dialog (successful login)
            logging.debug(f"User '{user}' provided correct password and is verified; logging in")
            self.accept()
            return

        QMessageBox.warning(self, 'Login failed', 'Invalid username or password')

    def try_register(self):
        user = self.user_edit.text().strip()
        pwd = self.pass_edit.text().strip()
        email = self.email_edit.text().strip()
        logging.debug(f"Register attempt for user='{user}', email='{email}'")
        if not user or not pwd or not email:
            QMessageBox.warning(self, 'Error', 'Enter username, password and email')
            return

        # basic email validation
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            QMessageBox.warning(self, 'Error', 'Enter a valid email address')
            return

        try:
            with open(self.users_file, 'r') as f:
                users = json.load(f)
            logging.debug(f"Loaded users file '{self.users_file}' for registration; user count={len(users)}")
        except Exception:
            users = {}
            logging.exception(f"Failed to load users file '{self.users_file}' during registration")
        if user in users:
            logging.debug(f"Attempt to register existing user '{user}'")
            QMessageBox.warning(self, 'Error', 'User already exists')
            return

        # generate code and attempt to send
        code = self._generate_code()
        sent, msg = self._send_verification_code(email, code)
        if not sent:
            # fallback: show the code locally so the user can complete verification in offline mode
            QMessageBox.information(self, 'Verification', f"Could not send email ({msg}).\nUse this code for verification: {code}")
        else:
            QMessageBox.information(self, 'Verification', 'Verification code sent to your email')

        ok = self._prompt_verification(email, code)
        if not ok:
            logging.debug(f"User '{user}' did not verify during registration")
            QMessageBox.warning(self, 'Error', 'Email verification failed or cancelled')
            return

        # save as dict: password hash, email, verified
        users[user] = {'password': self._hash(pwd), 'email': email, 'verified': True}
        try:
            self._save_users(users)
            logging.debug(f"Registered new user '{user}' saved to users.json")
            QMessageBox.information(self, 'Registered', f'User "{user}" registered and verified. You can now login.')
        except Exception as e:
            logging.exception(f"Failed to save new user '{user}'")
            QMessageBox.warning(self, 'Error', f'Could not save user: {e}')

    def try_reset_password(self):
        """Reset password flow: send code to stored email then allow setting a new password."""
        user = self.user_edit.text().strip()
        logging.debug(f"Password reset attempt for user='{user}'")
        if not user:
            QMessageBox.warning(self, 'Error', 'Enter your username to reset password')
            return
        try:
            with open(self.users_file, 'r') as f:
                users = json.load(f)
        except Exception:
            users = {}

        if user not in users:
            logging.debug(f"Reset requested for non-existent user '{user}'")
            QMessageBox.warning(self, 'Error', 'User does not exist')
            return

        stored = users.get(user)
        # ensure we have an email to send to (support legacy plain-hash entries without email)
        email = None
        if isinstance(stored, dict):
            email = stored.get('email')
        if not email:
            QMessageBox.warning(self, 'Error', 'No email on record for this user; cannot reset password')
            return

        code = self._generate_code()
        sent, msg = self._send_verification_code(email, code)
        logging.debug(f"Password reset code generated for user='{user}', email='{email}'; sent={sent}, msg={msg}")
        if not sent:
            QMessageBox.information(self, 'Verification', f"Could not send email ({msg}).\nUse this code for verification: {code}")
        else:
            QMessageBox.information(self, 'Verification', 'Verification code sent to your email')

        ok = self._prompt_verification(email, code)
        if not ok:
            logging.debug(f"Password reset verification failed or cancelled for user='{user}'")
            QMessageBox.warning(self, 'Error', 'Verification failed or cancelled')
            return

        # prompt for new password twice
        newpwd, ok1 = QInputDialog.getText(self, 'New password', 'Enter new password:', QLineEdit.Password)
        if not ok1 or not newpwd:
            QMessageBox.warning(self, 'Error', 'Password entry cancelled')
            return
        newpwd2, ok2 = QInputDialog.getText(self, 'Confirm password', 'Confirm new password:', QLineEdit.Password)
        if not ok2 or newpwd2 != newpwd:
            QMessageBox.warning(self, 'Error', 'Passwords do not match or confirmation cancelled')
            return

        # save new hash
        if isinstance(stored, dict):
            users[user]['password'] = self._hash(newpwd.strip())
            users[user]['verified'] = True
        else:
            # legacy stored as hash string -> migrate to dict with no email
            users[user] = {'password': self._hash(newpwd.strip()), 'email': email, 'verified': True}

        try:
            self._save_users(users)
            logging.debug(f"Password for user '{user}' updated and saved to users.json")
            QMessageBox.information(self, 'Reset', 'Password reset successful — you can now login')
        except Exception as e:
            logging.exception(f"Failed to save reset password for user '{user}'")
            QMessageBox.warning(self, 'Error', f'Could not save new password: {e}')


# -----------------------------
# AddGestureDialog: select control, name, record gesture and bind it
# -----------------------------
class AddGestureDialog(QDialog):
    def __init__(self, parent, controls):
        super().__init__(parent)
        self.setWindowTitle('Add Gesture and Bind to Control')
        self.setMinimumSize(400, 180)
        self.controls = controls

        layout = QVBoxLayout()

        form = QFormLayout()
        self.control_combo = QComboBox()
        for c in controls:
            self.control_combo.addItem(c)
        form.addRow('Bind to control:', self.control_combo)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText('Gesture name (e.g. two_fingers_close)')
        form.addRow('Gesture name:', self.name_edit)

        layout.addLayout(form)

        self.record_btn = QPushButton('Start Recording')
        self.record_btn.clicked.connect(self._on_start)
        layout.addWidget(self.record_btn)


        self.status = QLabel('Status: Ready')
        layout.addWidget(self.status)

        # preview area inside dialog
        self.preview_label = QLabel()
        self.preview_label.setFixedSize(200, 200)
        layout.addWidget(self.preview_label)

        self.setLayout(layout)

        self.recording = False
        self.frames = []
        self.frames_needed = 5

    def _on_start(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, 'Error', 'Enter a gesture name')
            return
        if self.recording:
            return
        self.recording = True
        self.frames = []
        self.record_btn.setEnabled(False)
        self.status.setText(f'Recording "{name}" - 0/{self.frames_needed}')
        # parent (MainWindow) will connect to camera landmarks and call add_frame

    def add_frame(self, lm):
        if not self.recording:
            return
        if not lm or len(lm) != 21:
            return
        self.frames.append(lm.copy())
        self.status.setText(f'Recording "{self.name_edit.text()}" - {len(self.frames)}/{self.frames_needed}')
        if len(self.frames) >= self.frames_needed:
            self.recording = False
            self.record_btn.setEnabled(True)
            # compute normalized frames and preview mean template
            parent = self.parent()
            norm_frames = []
            for f in self.frames:
                norm = parent.worker.recognizer._normalize_landmarks(f)
                if norm:
                    norm_frames.append(norm)

            if not norm_frames:
                QMessageBox.warning(self, 'Error', 'Recorded frames could not be normalized')
                return

            mean_template = parent.worker.recognizer.mean_template(norm_frames)
            pix = None
            try:
                pix = render_template_pixmap(mean_template, size=200)
                self.preview_label.setPixmap(pix)
            except Exception:
                pass

            # compare with existing templates
            similarities = []
            for name, templates in parent.worker.recognizer.gesture_templates.items():
                try:
                    existing_mean = parent.worker.recognizer.mean_template(templates)
                    sim = parent.worker.recognizer._procrustes_similarity(mean_template, existing_mean)
                    if sim > 0.5:  # report moderate similarities
                        similarities.append((name, sim))
                except Exception:
                    continue

            # show preview + similarity dialog; allow retake
            preview_dlg = PreviewConfirmDialog(self, pix if pix is not None else QPixmap(), similarities)
            res = preview_dlg.exec()
            choice = preview_dlg.choice
            if choice is True:
                # accept and let caller save normalized frames
                # replace raw frames with normalized frames in self.frames for caller convenience
                self.frames = norm_frames
                self.accept()
                return
            elif choice is False:
                # retake: clear frames and re-enable recording
                self.frames = []
                self.recording = True
                self.record_btn.setEnabled(False)
                self.status.setText(f'Recording "{self.name_edit.text()}" - 0/{self.frames_needed} (Retake)')
                self.preview_label.clear()
                return
            else:
                # canceled
                self.reject()
                return

    def get_result(self):
        return self.control_combo.currentText(), self.name_edit.text().strip(), self.frames


# -----------------------------
# Main GUI
# -----------------------------
class MainWindow(QWidget):
    def __init__(self, username=None):
        super().__init__()
        self.username = username or 'Guest'
        self.setWindowTitle(f'Hand Gesture Control - {self.username}')
        self.setMinimumSize(1200, 720)
        self.worker = CameraWorker()

        self._setup_ui()

        # connect signals
        self.worker.image_update.connect(self.update_image)
        self.worker.gesture_update.connect(self.update_gesture)

        # start camera
        self.worker.start()

    def _setup_ui(self):
        main_layout = QHBoxLayout()

        # Header area (user & status)
        header = QHBoxLayout()
        self.user_label = QLabel(f'User: {self.username}')
        self.user_label.setStyleSheet('font-weight: bold;')
        header.addWidget(self.user_label)
        header.addStretch()
        main_layout.addLayout(header)

        # Left: video
        self.video_label = QLabel()
        self.video_label.setFixedSize(640, 480)
        self.video_label.setStyleSheet('background: #111;')
        main_layout.addWidget(self.video_label)

        # Right: controls
        right = QVBoxLayout()
        self.gesture_label = QLabel('Current Gesture: none')
        right.addWidget(self.gesture_label)

        tabs = QTabWidget()
        tabs.addTab(self._create_control_tab(), 'Controls')
        tabs.addTab(self._create_settings_tab(), 'Settings')
        tabs.addTab(self._create_custom_tab(), 'Custom Gestures')

        right.addWidget(tabs)
        right.addStretch()
        main_layout.addLayout(right)

        self.setLayout(main_layout)

    def _create_control_tab(self):
        frame = QFrame()
        layout = QGridLayout()

        layout.addWidget(QLabel('<b>Gesture Controls (enable + select gesture)</b>'), 0, 0, 1, 3)

        # known control keys
        controls = [
            ('move', 'Move mouse'),
            ('left_click', 'Left Click'),
            ('right_click', 'Right Click'),
            ('scroll_up', 'Scroll Up'),
            ('scroll_down', 'Scroll Down'),
        ]

        self.control_widgets = {}
        builtin_options = ['move', 'left_click', 'right_click', 'scroll_up', 'scroll_down']

        # include custom gestures in the options
        custom_names = list(self.worker.recognizer.gesture_templates.keys())
        options = builtin_options + custom_names

        for i, (key, label) in enumerate(controls, 1):
            cb = QCheckBox(label)
            cb.setChecked(self.worker.action_mappings.get(key, {}).get('enabled', True))
            cb.stateChanged.connect(self._on_mapping_changed)
            layout.addWidget(cb, i, 0)

            combo = QComboBox()
            combo.addItems(options)
            # set current mapping if present
            cur_g = self.worker.action_mappings.get(key, {}).get('gesture')
            if cur_g and cur_g in options:
                combo.setCurrentText(cur_g)
            combo.currentTextChanged.connect(self._on_mapping_changed)
            layout.addWidget(combo, i, 1)

            self.control_widgets[key] = (cb, combo)

        # Add Gesture button
        add_btn = QPushButton('Add & Bind Gesture')
        add_btn.clicked.connect(self._on_add_gesture)
        layout.addWidget(add_btn, len(controls) + 2, 0, 1, 2)

        frame.setLayout(layout)
        return frame

    def _create_settings_tab(self):
        frame = QFrame()
        layout = QFormLayout()

        self.smoothing_spin = QSpinBox()
        self.smoothing_spin.setRange(1, 50)
        self.smoothing_spin.setValue(self.worker.smoothening)
        self.smoothing_spin.valueChanged.connect(lambda v: setattr(self.worker, 'smoothening', v))
        layout.addRow('Mouse smoothing:', self.smoothing_spin)

        self.click_delay_spin = QSpinBox()
        self.click_delay_spin.setRange(50, 2000)
        self.click_delay_spin.setValue(int(self.worker.click_delay * 1000))
        self.click_delay_spin.valueChanged.connect(lambda v: setattr(self.worker, 'click_delay', v / 1000.0))
        layout.addRow('Click delay (ms):', self.click_delay_spin)

        self.click_dist_spin = QSpinBox()
        self.click_dist_spin.setRange(1, 50)
        self.click_dist_spin.setValue(self.worker.click_distance_percentage)
        self.click_dist_spin.valueChanged.connect(lambda v: setattr(self.worker, 'click_distance_percentage', v))
        layout.addRow('Click distance threshold (% of hand size):', self.click_dist_spin)

        # per-action click thresholds
        self.left_click_dist_spin = QSpinBox()
        self.left_click_dist_spin.setRange(1, 50)
        self.left_click_dist_spin.setValue(self.worker.left_click_distance_percentage)
        self.left_click_dist_spin.valueChanged.connect(lambda v: setattr(self.worker, 'left_click_distance_percentage', v))
        layout.addRow('Left-click distance threshold (%):', self.left_click_dist_spin)

        self.right_click_dist_spin = QSpinBox()
        self.right_click_dist_spin.setRange(1, 50)
        self.right_click_dist_spin.setValue(self.worker.right_click_distance_percentage)
        self.right_click_dist_spin.valueChanged.connect(lambda v: setattr(self.worker, 'right_click_distance_percentage', v))
        layout.addRow('Right-click distance threshold (%):', self.right_click_dist_spin)

        # Dark mode toggle
        self.dark_mode_cb = QCheckBox('Dark mode')
        # ensure worker has attribute
        if not hasattr(self.worker, 'dark_mode'):
            self.worker.dark_mode = True
        self.dark_mode_cb.setChecked(bool(self.worker.dark_mode))
        def _on_dark_toggled(state):
            enabled = bool(state)
            self.worker.dark_mode = enabled
            app = QApplication.instance()
            if enabled:
                apply_dark_theme(app)
            else:
                apply_light_theme(app)
            try:
                self.worker.save_settings()
            except Exception:
                logging.exception('Failed to persist dark mode setting')

        self.dark_mode_cb.stateChanged.connect(_on_dark_toggled)
        layout.addRow(self.dark_mode_cb)

        self.enable_cb = QCheckBox('Enable actions')
        self.enable_cb.setChecked(self.worker.enable_actions)
        self.enable_cb.stateChanged.connect(lambda s: setattr(self.worker, 'enable_actions', bool(s)))
        layout.addRow(self.enable_cb)

        save_btn = QPushButton('Save Settings')
        save_btn.clicked.connect(self._save_settings)
        layout.addRow(save_btn)

        frame.setLayout(layout)
        return frame

    def _create_custom_tab(self):
        frame = QFrame()
        layout = QVBoxLayout()

        info = QTextEdit()
        info.setReadOnly(True)
        info.setPlainText('Record custom gestures and they will be available to bind to controls.')
        layout.addWidget(info)

        self.custom_list = QListWidget()
        layout.addWidget(QLabel('Saved custom gestures:'))
        layout.addWidget(self.custom_list)

        btn_layout = QHBoxLayout()
        refresh = QPushButton('Refresh')
        refresh.clicked.connect(self._refresh_custom_list)
        btn_layout.addWidget(refresh)

        delete = QPushButton('Delete Selected')
        delete.clicked.connect(self._delete_custom)
        btn_layout.addWidget(delete)

        layout.addLayout(btn_layout)

        frame.setLayout(layout)
        self._refresh_custom_list()
        return frame

    def _refresh_custom_list(self):
        self.custom_list.clear()
        for name in self.worker.recognizer.gesture_templates.keys():
            self.custom_list.addItem(name)

        # also refresh the combos in controls
        custom_names = list(self.worker.recognizer.gesture_templates.keys())
        for key, (cb, combo) in self.control_widgets.items():
            current = combo.currentText()
            builtins = ['move', 'left_click', 'right_click', 'scroll_up', 'scroll_down']
            combo.blockSignals(True)
            combo.clear()
            combo.addItems(builtins + custom_names)
            # QComboBox's model may not expose stringList(); check items directly
            items = [combo.itemText(i) for i in range(combo.count())]
            if current in items:
                combo.setCurrentText(current)
            combo.blockSignals(False)

    def _delete_custom(self):
        it = self.custom_list.currentItem()
        if not it:
            QMessageBox.warning(self, 'Error', 'Select a custom gesture to delete')
            return
        name = it.text()
        if name in self.worker.recognizer.gesture_templates:
            del self.worker.recognizer.gesture_templates[name]
            self.worker.recognizer.save_custom_gestures()
            QMessageBox.information(self, 'Deleted', f'Gesture "{name}" deleted')
            self._refresh_custom_list()

    def _on_mapping_changed(self):
        # update worker.action_mappings from widgets
        for key, (cb, combo) in self.control_widgets.items():
            enabled = cb.isChecked()
            gesture = combo.currentText()
            self.worker.action_mappings[key] = {'enabled': enabled, 'gesture': gesture}
        self.worker.save_action_mappings()

    def _on_add_gesture(self):
        controls = list(self.control_widgets.keys())
        dlg = AddGestureDialog(self, controls)

        # connect to worker landmarks to receive frames while dialog is open
        def _collect(lm):
            dlg.add_frame(lm)

        self.worker.landmarks_update.connect(_collect)
        result = dlg.exec()
        self.worker.landmarks_update.disconnect(_collect)

        if result == QDialog.Accepted:
            control_key, name, frames = dlg.get_result()
            if not name or not frames:
                QMessageBox.warning(self, 'Error', 'Recording failed or no name provided')
                return
            # normalize recorded frames (support both already-normalized and raw landmark frames)
            norm_frames = []
            for f in frames:
                try:
                    # detect normalized form: list of 21 [x,y] floats
                    if isinstance(f, list) and len(f) == 21 and isinstance(f[0], list) and len(f[0]) == 2:
                        # assume already normalized
                        norm_frames.append(f)
                    else:
                        norm = self.worker.recognizer._normalize_landmarks(f)
                        if norm:
                            norm_frames.append(norm)
                except Exception:
                    continue
            if not norm_frames:
                QMessageBox.warning(self, 'Error', 'Failed to normalize recorded gesture frames')
                return
            # convert normalized frames into feature dicts
            feature_frames = []
            for nf in norm_frames:
                try:
                    fdict = self.worker.recognizer._frame_to_features(nf)
                    if fdict:
                        feature_frames.append(fdict)
                except Exception:
                    continue
            if not feature_frames:
                QMessageBox.warning(self, 'Error', 'Failed to create feature frames for gesture')
                return

            # compute candidate mean and compare to existing gestures to pick a per-gesture threshold
            try:
                candidate_mean = self.worker.recognizer.mean_template([f['coords'] for f in feature_frames])
                candidate_feat = self.worker.recognizer._frame_to_features(candidate_mean)
            except Exception:
                candidate_feat = None

            closest_sim = 0.0
            if candidate_feat is not None:
                for other_name, other_val in self.worker.recognizer.gesture_templates.items():
                    # skip comparing to itself (shouldn't exist yet)
                    if other_name == name:
                        continue
                    # get frames list
                    if isinstance(other_val, dict) and 'frames' in other_val:
                        other_frames = other_val.get('frames', [])
                    else:
                        other_frames = other_val
                    # compute max similarity to this other gesture
                    max_sim = 0.0
                    for of in other_frames:
                        try:
                            sim = self.worker.recognizer._calculate_similarity(candidate_feat, of)
                            max_sim = max(max_sim, sim)
                        except Exception:
                            continue
                    closest_sim = max(closest_sim, max_sim)

            # set threshold between closest similarity and perfect match; clamp to reasonable bounds
            threshold = max(0.5, min(0.95, (closest_sim + 1.0) / 2.0))

            # store as new-format dict with frames and threshold
            self.worker.recognizer.gesture_templates[name] = {'frames': feature_frames, 'threshold': float(threshold)}
            self.worker.recognizer.save_custom_gestures()
            # bind to control
            self.worker.action_mappings[control_key] = {'enabled': True, 'gesture': name}
            self.worker.save_action_mappings()
            QMessageBox.information(self, 'Saved', f'Gesture "{name}" saved and bound to {control_key}')
            self._refresh_custom_list()
            # also refresh control combos to include new gesture
            self._on_mapping_changed()

    def update_image(self, qimage):
        self.video_label.setPixmap(QPixmap.fromImage(qimage))

    def update_gesture(self, gesture):
        self.gesture_label.setText(f'Current Gesture: {gesture}')

    def _save_settings(self):
        # persist to settings.json via worker
        try:
            self.worker.save_settings()
            QMessageBox.information(self, 'Saved', 'Settings saved')
        except Exception:
            QMessageBox.information(self, 'Saved', 'Settings updated (could not persist)')

    def closeEvent(self, event):
        self.worker.stop()
        event.accept()


def main():
    # Configure Qt high-DPI attributes and environment to avoid SetProcessDpiAwarenessContext warnings
    os.environ.setdefault('QT_ENABLE_HIGHDPI_SCALING', '1')
    os.environ.setdefault('QT_AUTO_SCREEN_SCALE_FACTOR', '1')
    # Set attributes before creating QApplication
    try:
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    except Exception:
        # ignore if attributes cannot be set
        pass

    app = QApplication(sys.argv)
    # apply theme from persisted settings (settings.json) so the login dialog
    # and entire UI respect the user's choice. Defaults to dark mode.
    try:
        dark_mode = True
        try:
            with open('settings.json', 'r') as f:
                cfg = json.load(f)
                dark_mode = bool(cfg.get('dark_mode', True))
        except Exception:
            # if the settings file doesn't exist or is invalid, default to dark
            dark_mode = True

        if dark_mode:
            apply_dark_theme(app)
        else:
            apply_light_theme(app)
    except Exception:
        logging.exception('Failed to apply persisted theme settings')
    # Show login first; if user cancels, offer to continue as Guest instead of exiting immediately
    login = LoginDialog()
    if login.exec() != QDialog.Accepted:
        # ask whether to continue as Guest (useful when running on systems where login is skipped)
        answer = QMessageBox.question(None, 'Login cancelled', 'Login cancelled. Continue as Guest?', QMessageBox.Yes | QMessageBox.No)
        if answer == QMessageBox.No:
            print('Login cancelled, exiting')
            return
        username = 'Guest'
    else:
        username = login.user_edit.text().strip()

    w = MainWindow(username=username)
    w.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()