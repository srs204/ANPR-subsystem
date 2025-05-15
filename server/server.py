from flask import Flask, request, jsonify
from flask_socketio import SocketIO
from app import db, create_app
from app.models import ParkingEntry, VehicleType, ParkingOccupancy
from datetime import datetime
import logging
import os
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('pi_server.log')
    ]
)

# Load environment variables
load_dotenv()

# Initialize Flask app
app = create_app()
socketio = SocketIO(app, cors_allowed_origins="*")

# Cache for vehicle types
vehicle_type_cache = {}

def get_vehicle_type(type_name):
    """Get or create vehicle type from database"""
    # Only cache the id, not the object
    if type_name not in vehicle_type_cache:
        vehicle_type = VehicleType.query.filter_by(name=type_name).first()
        if not vehicle_type:
            vehicle_type = VehicleType(name=type_name)
            db.session.add(vehicle_type)
            db.session.commit()
        vehicle_type_cache[type_name] = vehicle_type.id
    # Always return a session-bound object
    return VehicleType.query.get(vehicle_type_cache[type_name])

def update_parking_occupancy(is_entry):
    """Update parking occupancy count"""
    occupancy = ParkingOccupancy.query.order_by(ParkingOccupancy.last_updated.desc()).first()
    if not occupancy:
        # Initialize with default values if no record exists
        occupancy = ParkingOccupancy(total_spaces=100, occupied_spaces=0)
        db.session.add(occupancy)
    
    # Update occupied spaces
    if is_entry:
        occupancy.occupied_spaces += 1
    else:
        occupancy.occupied_spaces = max(0, occupancy.occupied_spaces - 1)
    
    occupancy.last_updated = datetime.utcnow()
    db.session.commit()
    
    return occupancy

@app.route('/api/detection', methods=['POST'])
def api_detection():
    try:
        detection = request.get_json()
        if not detection:
            return jsonify({'error': 'No data received'}), 400

        # Extract fields from detection
        license_plate = detection.get('license_plate')
        vehicle_type_name = detection.get('vehicle_type')
        text_confidence = detection.get('text_confidence')
        vehicle_confidence = detection.get('vehicle_confidence')
        frame_number = detection.get('frame_number')
        timestamp = detection.get('timestamp')
        date = detection.get('date')
        time_str = detection.get('time')

        # Find or create vehicle type
        vehicle_type = get_vehicle_type(vehicle_type_name)

        # Compose datetime from date and time
        dt = datetime.strptime(f"{date} {time_str}", "%Y-%m-%d %H:%M:%S")

        # Create parking entry (assume entry for now)
        entry = ParkingEntry(
            license_plate=license_plate,
            timestamp=dt,
            is_entry=True,  # or add logic to determine entry/exit
            vehicle_type_id=vehicle_type.id,
            confidence=text_confidence  # or combine with vehicle_confidence if you want
        )
        db.session.add(entry)
        db.session.commit()

        return jsonify({'status': 'success'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@socketio.on('connect')
def handle_connect():
    logging.info('Jetson connected')

@socketio.on('disconnect')
def handle_disconnect():
    logging.info('Jetson disconnected')

@socketio.on('license_plate_detection')
def handle_detection(data):
    """Handle license plate detection events from Jetson"""
    try:
        detections = data.get('detections', [])
        fps = data.get('fps', 0)
        
        for detection in detections:
            # Skip if we can't determine entry/exit
            if detection.get('is_entry') is None:
                continue
            
            # Get vehicle type
            vehicle_type = get_vehicle_type(detection['vehicle_type'])
            
            # Create parking entry
            entry = ParkingEntry(
                license_plate=detection['license_plate'],
                timestamp=datetime.fromisoformat(detection['timestamp']),
                is_entry=detection['is_entry'],
                vehicle_type_id=vehicle_type.id,
                confidence=detection['confidence']
            )
            
            db.session.add(entry)
            
            # Update occupancy
            occupancy = update_parking_occupancy(detection['is_entry'])
            
            logging.info(
                f"Processed {'entry' if detection['is_entry'] else 'exit'}: "
                f"Plate: {detection['license_plate']}, "
                f"Type: {detection['vehicle_type']}, "
                f"Confidence: {detection['confidence']:.2f}, "
                f"Occupancy: {occupancy.occupied_spaces}/{occupancy.total_spaces}"
            )
        
        db.session.commit()
        
    except Exception as e:
        logging.error(f"Error processing detection: {str(e)}")
        db.session.rollback()

@socketio.on('detector_status')
def handle_status(data):
    """Handle status updates from Jetson"""
    fps = data.get('fps', 0)
    running = data.get('running', False)
    logging.info(f"Jetson status - FPS: {fps}, Running: {running}")

if __name__ == '__main__':
    # Get port from environment variable or use default
    port = int(os.getenv('PI_PORT', 5000))
    
    # Run the server
    socketio.run(app, host='0.0.0.0', port=port, debug=False) 