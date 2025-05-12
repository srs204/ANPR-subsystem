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
        self.alpr = Alpr("us",
                         "/etc/openalpr/openalpr.conf",
                         "/usr/local/share/openalpr/runtime_data")
        if not self.alpr.is_loaded():
            logging.error("Error loading OpenALPR")
            raise RuntimeError("OpenALPR failed to load")

        # Vehicle classes in COCO dataset
        self.vehicle_classes = [2, 3, 5, 7]
        self.vehicle_names = {2: 'car', 3: 'motorcycle', 5: 'bus', 7: 'truck'}

        # Initialize results storage (only plates now)
        self.plate_detections = []
        self.plate_tracker = {}  # To track plates and their first appearance time

        # Create output directory
        self.output_dir = Path('output')
        self.output_dir.mkdir(exist_ok=True, parents=True)

        # Performance parameters
        self.target_width = 1280
        self.frame_skip = 1
        self.min_plate_confidence = 0.7  # Minimum confidence for CSV registration
        self.duplicate_window = 30  # Seconds to consider as duplicate plate

        # Timezone setup
        self.cdt_timezone = pytz.timezone('America/Chicago')

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
                                len(plate_text) > 6 and  # Only plates with >6 characters
                                any(c.isalpha() for c in plate_text) and
                                any(c.isdigit() for c in plate_text)):
                                # Draw plate polygon
                                for coord in plate['coordinates']:
                                    x = x1 + coord['x']
                                    y = y1 + coord['y']
                                    cv2.circle(vis_frame, (x, y), 3, (0, 0, 255), -1)
                                cv2.putText(vis_frame, f'Plate: {plate_text}', (x1, y2+20),
                                          cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
                                current_date, current_time = self.get_current_cdt_datetime()
                                current_datetime = datetime.strptime(f"{current_date} {current_time}", "%Y-%m-%d %H:%M:%S")
                                if plate_text in self.plate_tracker:
                                    first_seen_time, best_confidence = self.plate_tracker[plate_text]
                                    time_diff = (current_datetime - first_seen_time).total_seconds()
                                    if time_diff <= self.duplicate_window:
                                        if text_confidence > best_confidence:
                                            self.plate_tracker[plate_text] = (first_seen_time, text_confidence)
                                            for detection in self.plate_detections:
                                                if detection['license_plate'] == plate_text:
                                                    detection.update({
                                                        'date': current_date,
                                                        'time': current_time,
                                                        'text_confidence': round(text_confidence, 2),
                                                        'vehicle_type': vehicle_name,
                                                        'vehicle_confidence': round(confidence, 2),
                                                        'frame_number': frame_number,
                                                        'timestamp': round(timestamp, 2)
                                                    })
                                                    break
                                        continue
                                    else:
                                        self.plate_tracker[plate_text] = (current_datetime, text_confidence)
                                else:
                                    self.plate_tracker[plate_text] = (current_datetime, text_confidence)
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
                                self.plate_detections.append(detection)
                                self.insert_detection_to_db(detection)
                                logging.info(f"Detected plate: {plate_text} (confidence: {text_confidence:.2f})")
                    except Exception as e:
                        logging.warning(f"Plate detection error: {str(e)}")
                        continue

        count_text = ", ".join([f"{k}: {v}" for k, v in vehicle_counts.items() if v > 0])
        if count_text:
            cv2.putText(vis_frame, count_text, (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 1)

        return vis_frame

    def process_video(self, video_path, output_video_path=None):
        if not os.path.exists(video_path):
            logging.error(f"Video file not found: {video_path}")
            return
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logging.error(f"Failed to open video: {video_path}")
            return
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        scale_factor = self.target_width / width
        if output_video_path:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out_width = self.target_width if scale_factor < 1 else width
            out_height = int(height * scale_factor) if scale_factor < 1 else height
            out = cv2.VideoWriter(output_video_path, fourcc, fps/self.frame_skip, (out_width, out_height))
        frame_count = 0
        processed_count = 0
        logging.info(f"Starting video processing. Total frames: {total_frames}")
        try:
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                if frame_count % 100 == 0:
                    time.sleep(0.05)
                if scale_factor < 1:
                    frame = cv2.resize(frame, (self.target_width, int(height * scale_factor)))
                if frame_count % self.frame_skip == 0:
                    processed_frame = self.process_frame(frame, frame_count, fps)
                    processed_count += 1
                    if output_video_path:
                        out.write(processed_frame)
                    cv2.imshow('Vehicle and License Plate Detection', processed_frame)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        logging.info("User requested to quit processing. Saving results...")
                        break
                frame_count += 1
                if frame_count % 30 == 0:
                    progress = (frame_count / total_frames) * 100
                    logging.info(f"Progress: {progress:.1f}% ({frame_count}/{total_frames} frames)")
                    if frame_count % 300 == 0:
                        self.save_results()
                        self.plate_detections.clear()
        except Exception as e:
            logging.error(f"Processing error: {str(e)}")
        finally:
            cap.release()
            if output_video_path:
                out.release()
            cv2.destroyAllWindows()
            self.save_results()
            logging.info(f"Processing completed. Processed {processed_count} of {frame_count} frames")

    def save_results(self):
        try:
            if self.plate_detections:
                high_confidence_plates = [plate for plate in self.plate_detections
                                        if (plate['text_confidence'] >= self.min_plate_confidence and
                                            len(plate['license_plate']) > 6)]  # Updated to match >6 characters
                if high_confidence_plates:
                    best_detections = {}
                    for plate in high_confidence_plates:
                        plate_text = plate['license_plate']
                        if plate_text not in best_detections or plate['text_confidence'] > best_detections[plate_text]['text_confidence']:
                            best_detections[plate_text] = plate
                    unique_plates = list(best_detections.values())
                    df_plates = pd.DataFrame(unique_plates)
                    column_order = [
                        'date',
                        'time',
                        'license_plate',
                        'text_confidence',
                        'vehicle_type',
                        'vehicle_confidence',
                        'frame_number',
                        'timestamp'
                    ]
                    df_plates = df_plates[column_order]
                    output_file = self.output_dir / 'plate_detections.csv'
                    df_plates.to_csv(output_file, index=False, mode='a', header=not output_file.exists())
                    logging.info(f"Saved {len(unique_plates)} unique high-confidence plate detections (>6 characters)")
                else:
                    logging.info("No plate detections met the confidence and length threshold")
        except Exception as e:
            logging.error(f"Error saving results: {str(e)}")

    def __del__(self):
        if hasattr(self, 'alpr') and self.alpr:
            self.alpr.unload()

def main():
    detector = VehicleAndPlateDetector()
    video_path = 'Martin.mp4'
    output_video_path = 'output/detected_vehicles_and_plates.mp4'
    logging.info(f"Starting video processing: {video_path}")
    detector.process_video(video_path, output_video_path)
    detector.save_results()
    logging.info("Processing completed successfully")

if __name__ == "__main__":
    if os.path.exists('vehicle_and_plate_detection.log'):
        os.remove('vehicle_and_plate_detection.log')
    main()
