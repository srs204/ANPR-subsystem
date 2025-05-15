from datetime import datetime
from . import db

class VehicleType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), nullable=False)  # car, motorcycle, bus, truck
    description = db.Column(db.String(100))

    def __repr__(self):
        return f'<VehicleType {self.name}>'

class ParkingEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    license_plate = db.Column(db.String(20), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    is_entry = db.Column(db.Boolean, nullable=False)  # True for entry, False for exit
    vehicle_type_id = db.Column(db.Integer, db.ForeignKey('vehicle_type.id'))
    vehicle_type = db.relationship('VehicleType')
    confidence = db.Column(db.Float)  # Detection confidence score

    def __repr__(self):
        return f'<ParkingEntry {self.license_plate} ({self.vehicle_type.name}) at {self.timestamp}>'

class ParkingOccupancy(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    total_spaces = db.Column(db.Integer, nullable=False)
    occupied_spaces = db.Column(db.Integer, nullable=False)
    last_updated = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    @property
    def percentage(self):
        return int((self.occupied_spaces / self.total_spaces) * 100)

    def __repr__(self):
        return f'<ParkingOccupancy {self.occupied_spaces}/{self.total_spaces}>' 