from flask import Flask, render_template, jsonify, request
import mysql.connector
from datetime import datetime

app = Flask(__name__)

def get_db_connection():
    return mysql.connector.connect(
        host="10.60.35.183",
        user="jetson",
        password="Amelie_2001",
        database="parking_system",
        port=3306
    )

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/parking-data')
def get_parking_data():
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Base query
        query = "SELECT * FROM parking_entry"
        params = []
        
        # Add date filters if provided
        if start_date and end_date:
            query += " WHERE timestamp BETWEEN %s AND %s"
            params.extend([start_date, end_date])
        elif start_date:
            query += " WHERE timestamp >= %s"
            params.append(start_date)
        elif end_date:
            query += " WHERE timestamp <= %s"
            params.append(end_date)
            
        query += " ORDER BY timestamp DESC"
        
        cursor.execute(query, params)
        entries = cursor.fetchall()
        
        # Convert datetime objects to strings for JSON serialization
        for entry in entries:
            if isinstance(entry['timestamp'], datetime):
                entry['timestamp'] = entry['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'status': 'success',
            'data': entries
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 