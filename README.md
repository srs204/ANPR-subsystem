# ANPR-subsystem
An automatic license plate recognition model for parking lots, deployed on edge through a Jetson Orin Nano.

# Purpose
When deployed, it gives the parking lot owner the ability to view the entry and exit of individual cars through an app, differentiated by their license plates and timestamps.
This can be particularly helpful in auditing, maintaining logs, analyzing patterns, adjusting price models and promotions, and automating ticketing and tolling for the parking lot owner.

# Usage
The model and all of its dependencies are tested on a Jetson Orin Nano running on Jetpack 6.2 SDK (Ubuntu 22.04).
The user is expected to configure a virtual environment and have all the libraries and dependencies installed in their host system as specified by the requirements.txt.

# Coordination
The model(s) run the inference in real-time and/or pre-recorded parking footage and pass the data to a MariaDB database instance running on a headless Raspberry Pi 3 server. The .env file is used to initialize the token and authorize the transfer between the Jetson and the Pi server. The storage and retrieval system, i.e., the database, is encrypted using AES, and the AES key is encrypted using RSA and multifactor authentication through OTP. A flask GUI app is also available, which can be used to connect to the server and view the database through any devices connected and authorized within the local network. 

# Model
local.py runs the inference on a local path, and camerainfr.py uses the Jetson's camera input port 0/1 to open a camera module and run the inference in real-time.
Both of the models use yolo11n.pt model developed by Ultralytics to identify the vehicle frame, on which the open source library openalpr is used to identify license plate numbers.
The models are trained to recognize the type of car (car/truck/motorcycle, etc) and the placement of license plates on a vehicle frame, and adjust to the Texas number plate format of "AAA-0000".
Multiple instances of the same license plate recognized within 30 seconds will result in only the one with the highest confidence being passed to the server as an "entry".
Any duplicate instance after the 30-second window will be marked as an "exit" from the parking lot for that particular vehicle.
An OpenCV imgui window is used to visualize the running inference for the user, and a "detected_vehicles_and_plates.mp4" and .csv file are generated in the /output directory to monitor after postprocessing.

# Libraries
This project’s inference pipeline is built on NVIDIA-optimized PyTorch and TorchVision (CUDA 11.8), which provide the deep-learning framework and model utilities necessary to load, run, and optimize the convolutional neural network on the Jetson Orin Nano’s GPU. On top of that, the Ultralytics YOLO11n package wraps a state-of-the-art object detection architecture, offering pre-trained weights, streamlined model classes, and convenient training/inference APIs. YOLO11n handles the core detection of vehicles and license plates by processing image tensors through the neural network, applying non-maximum suppression, and yielding bounding boxes, class labels, and confidence scores.

For real-time image acquisition, transformation, and result visualization, OpenCV captures frames from the camera feed, converts color spaces, applies geometric and morphological operations (e.g., resizing, thresholding), and draws annotated boxes and text overlays back onto the video stream. Behind the scenes, NumPy provides the high-performance array structures that both PyTorch tensors and OpenCV images interoperate with seamlessly—enabling pixel-level arithmetic, batch stacking, and coordinate transformations—while Pandas is leveraged to collect, aggregate, and export detection statistics (such as counts per frame or timestamps) into tabular formats suitable for logging or downstream analysis.

To keep configuration clean and adaptable across different deployment environments, python-dotenv reads environment variables (e.g., database credentials, model paths) from a .env file at startup, and pytz ensures that all timestamps—whether marking when a license plate was seen or when an entry was written to the database—are correctly localized to the desired time zone. When detections need to be persisted, MySQL-connector-python opens a secure connection to a MySQL database, executes parameterized INSERT or UPDATE statements, and commits records such as plate text, confidence scores, image snapshots, and event times. Finally, for specialized optical character recognition of license plates, OpenALPR provides a native C++-backed engine with Python bindings that crop the license plate region, preprocess it for contrast enhancement, and run plate–character segmentation and recognition to return the alphanumeric plate string.
