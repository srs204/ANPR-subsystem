# ANPR-subsystem
An automatic license plate recognition model for parking lots, deployed on edge through a Jetson Orin Nano

# Purpose
When deployed, it gives the parking lot owner the ability to view the entry and exit of individual cars through an app, differentiated by their license plates and timestamps
This can be particularly helpful to audit, maintain logs, analyze patterns, adjust price models, promotions, and automate ticketing and tolling for the parking lot owner

# Model
local.py runs the inference on a local path, and camerainfr.py uses the Jetson's camera input port 0/1 to open a camera module and run the inference in real-time
Both of the models use yolo11n.pt model developed by Ultralytics to identify the vehicle frame, on which the open source library openalpr is used to identify license plate numbers
The models are trained to recognize the type of car (car/truck/motorcycle, etc) and the placement of license plates on a vehicle frame, and adjust to the Texas number plate format of "AAA-0000"
Multiple instances of the same license plate recognized within 30 seconds will result in only the one with the highest confidence being passed to the server as an "entry"
Any duplicate instance after the 30-second window will be marked as an "exit" from the parking lot for that particular vehicle
An OpenCV imgui window is used to visualize the running inference for the user, and a "detected_vehicles_and_plates.mp4" and .csv file are generated in the /output directory to monitor after postprocessing

