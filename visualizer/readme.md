# Parking System Dashboard

A web-based dashboard for monitoring parking system entries and exits.

## Features

- Real-time display of parking entries and exits
- Auto-refresh every 30 seconds
- Manual refresh button
- Responsive design
- Clean and modern UI

## Setup

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. Run the Flask application:
```bash
python app.py
```

3. Open your web browser and navigate to:
```
http://localhost:5000
```

## Database Configuration

The application is configured to connect to a MariaDB database with the following settings:
- Host: 192.168.0.149 (change it to match rapi's IP)
- Port: 3306
- Database: parking_system
- User: jetson
- Password: Amelie_2001

## Project Structure

```
.
├── app.py              # Flask application
├── requirements.txt    # Python dependencies
├── static/
│   └── css/
│       └── style.css  # Stylesheet
└── templates/
    └── index.html     # Main page template
