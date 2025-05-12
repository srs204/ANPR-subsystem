import cv2
import numpy as np
from ultralytics import YOLO
import pandas as pd
import os
import logging
from pathlib import Path
import time
from datetime import datetime, timedelta
import pytz
import mysql.connector
from openalpr import Alpr
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('vehicle_and_plate_detection.log')
    ]
)

# MariaDB connection config
DB_CONFIG = {
    'user': os.getenv('DB_USER', 'jetson'),
    'password': os.getenv('DB_PASSWORD', 'yourpassword'),
    'host': os.getenv('DB_HOST', 'localhost'),
    'database': os.getenv('DB_NAME', 'parking_system'),
    'port': int(os.getenv('DB_PORT', 3306)),
}

class VehicleAndPlateDetector:
    def __init__(self):
        # Initialize YOLO model for vehicle detection
        self.vehicle_model = YOLO('yolo11n.pt')

        # Initialize OpenALPR
        self.alpr = Alpr("us", "/etc/openalpr/openalpr.conf", "/usr/local/share/openalpr/runtime_data")
        if not self.alpr.is_loaded():
            logging.error("Error loading OpenALPR")
            raise RuntimeError("OpenALPR failed to load")

        # Vehicle classes in COCO dataset
        self.vehicle_classes = [2, 3, 5, 7]
        self.vehicle_names = {2: 'car', 3: 'motorcycle', 5: 'bus', 7: 'truck'}

        # Performance parameters
        self.target_width = 1280
        self.frame_skip = 1
        self.min_plate_confidence = 0.7
        self.duplicate_window = 30  # Seconds to consider as duplicate plate

        # Timezone setup
        self.cdt_timezone = pytz.timezone('America/Chicago')

        # Plate tracking
        self.plate_tracker = {}

    def get_current_cdt_datetime(self):
        now_utc = datetime.now(pytz.utc)
        now_cdt = now_utc.astimezone(self.cdt_timezone)
        return now_cdt.strftime('%Y-%m-%d'), now_cdt.strftime('%H:%M:%S')

    def is_optimal_for_plate_detection(self, bbox, frame_shape):
        _, _, width, height = bbox
        frame_height, frame_width = frame_shape[:2]
        relative_size = (width * height) / (frame_width * frame_height)
        return relative_size > 0.03

    def insert_detection_to_db(self, detection):
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor()
            # Ensure vehicle type exists
            cursor.execute("SELECT id FROM vehicle_type WHERE name=%s", (detection['vehicle_type'],))
            result = cursor.fetchone()
            if result:
                vehicle_type_id = result[0]
            else:
                cursor.execute("INSERT INTO vehicle_type (name) VALUES (%s)", (detection['vehicle_type'],))
                conn.commit()
                vehicle_type_id = cursor.lastrowid
            # Insert parking entry
            cursor.execute(
                "INSERT INTO parking_entry (license_plate, timestamp, is_entry, vehicle_type_id, confidence) VALUES (%s, %s, %s, %s, %s)",
                (
                    detection['license_plate'],
                    f"{detection['date']} {detection['time']}",
                    True,  # or your logic for entry/exit
                    vehicle_type_id,
                    detection['text_confidence']
                )
            )
            conn.commit()
            cursor.close()
            conn.close()
            logging.info(f"Inserted detection into DB: {detection}")
        except Exception as e:
            logging.error(f"Error inserting detection into DB: {e}")

    def process_frame(self, frame, frame_number, fps):
        vehicle_results = self.vehicle_model(frame, classes=self.vehicle_classes, conf=0.5)
        vis_frame = frame.copy()
        timestamp = frame_number / fps
        vehicle_counts = {name: 0 for name in self.vehicle_names.values()}

        for result in vehicle_results:
            boxes = result.boxes
            for box in boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                confidence = float(box.conf[0])
                class_id = int(box.cls[0])
                vehicle_name = self.vehicle_names.get(class_id, 'unknown')
                vehicle_counts[vehicle_name] += 1

                cv2.rectangle(vis_frame, (x1, y1), (x2, y2), (0, 255, 0), 1)
                cv2.putText(vis_frame, f'{vehicle_name}: {confidence:.2f}', (x1, y1-10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

                if self.is_optimal_for_plate_detection((x1, y1, x2-x1, y2-y1), frame.shape):
                    try:
                        vehicle_region = frame[y1:y2, x1:x2]
                        ret, jpeg_bytes = cv2.imencode('.jpg', vehicle_region)
                        if not ret:
                            continue
                        results = self.alpr.recognize_array(jpeg_bytes.tobytes())
                        for plate in results['results']:
                            plate_text = plate['plate']
                            text_confidence = plate['confidence'] / 100.0
                            if (text_confidence >= self.min_plate_confidence and
                                4 <= len(plate_text) <= 8 and
                                any(c.isalpha() for c in plate_text) and
                                any(c.isdigit() for c in plate_text)):
                                # Draw plate polygon/rectangle
                                coords = plate['coordinates']
                                if len(coords) == 4:
                                    pts = np.array([[x1 + c['x'], y1 + c['y']] for c in coords], np.int32)
                                    pts = pts.reshape((-1, 1, 2))
                                    cv2.polylines(vis_frame, [pts], isClosed=True, color=(0, 0, 255), thickness=2)
                                    # Put plate text above the box
                                    min_y = min([y1 + c['y'] for c in coords])
                                    min_x = min([x1 + c['x'] for c in coords])
                                    cv2.putText(vis_frame, f'{plate_text}', (min_x, min_y - 10),
                                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                                current_date, current_time = self.get_current_cdt_datetime()
                                detection = {
                                    'date': current_date,
                                    'time': current_time,
                                    'license_plate': plate_text,
                                    'text_confidence': round(text_confidence, 2),
                                    'vehicle_type': vehicle_name,
                                    'vehicle_confidence': round(confidence, 2),
                                    'frame_number': frame_number,
                                    'timestamp': round(timestamp, 2)
                                }
                                self.insert_detection_to_db(detection)
                                logging.info(f"Detected plate: {plate_text} (confidence: {text_confidence:.2f})")
                    except Exception as e:
                        logging.warning(f"Plate detection error: {str(e)}")
                        continue

        return vis_frame

    def run(self, video_path=0):
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logging.error(f"Failed to open video/camera: {video_path}")
            return

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        frame_count = 0
        logging.info(f"Starting video/camera processing.")

        try:
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                # Flip the frame horizontally and vertically
                frame = cv2.flip(frame, -1)

                if frame_count % self.frame_skip == 0:
                    processed_frame = self.process_frame(frame, frame_count, fps)
                    cv2.imshow('Vehicle and License Plate Detection', processed_frame)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break

                frame_count += 1
        except Exception as e:
            logging.error(f"Processing error: {str(e)}")
        finally:
            cap.release()
            cv2.destroyAllWindows()
            logging.info(f"Processing completed. Processed {frame_count} frames")

    def __del__(self):
        if hasattr(self, 'alpr') and self.alpr:
            self.alpr.unload()

if __name__ == "__main__":
    detector = VehicleAndPlateDetector()
    detector.run(0)  # Use 0 for webcam, or provide video file path