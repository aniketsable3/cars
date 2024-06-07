from flask import Flask, render_template, Response
import numpy as np
from ultralytics import YOLO
import cv2
import cvzone
import math
from sort import Sort

app = Flask(__name__)

# Initialize video capture
cap = cv2.VideoCapture("video/cars.mp4")  # For Video

# Load YOLO model
model = YOLO("yolov8l.pt")

# Class names for YOLO
classNames = ["person", "bicycle", "car", "motorbike", "aeroplane", "bus", "train", "truck", "boat",
              "traffic light", "fire hydrant", "stop sign", "parking meter", "bench", "bird", "cat",
              "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra", "giraffe", "backpack", "umbrella",
              "handbag", "tie", "suitcase", "frisbee", "skis", "snowboard", "sports ball", "kite", "baseball bat",
              "baseball glove", "skateboard", "surfboard", "tennis racket", "bottle", "wine glass", "cup",
              "fork", "knife", "spoon", "bowl", "banana", "apple", "sandwich", "orange", "broccoli",
              "carrot", "hot dog", "pizza", "donut", "cake", "chair", "sofa", "pottedplant", "bed",
              "diningtable", "toilet", "tvmonitor", "laptop", "mouse", "remote", "keyboard", "cell phone",
              "microwave", "oven", "toaster", "sink", "refrigerator", "book", "clock", "vase", "scissors",
              "teddy bear", "hair drier", "toothbrush"]

# Load mask
mask = cv2.imread("Images/mask.png")
if mask is None:
    print("Error: Mask image not found")
    exit()

# Tracking
tracker = Sort(max_age=20, min_hits=3, iou_threshold=0.3)

# Detection limits
limits = [400, 297, 673, 297]
totalCount = []
id_class_map = {}

def generate_frames():
    while True:
        success, img = cap.read()
        if not success:
            break

        mask_resized = cv2.resize(mask, (img.shape[1], img.shape[0]))
        imgRegion = cv2.bitwise_and(img, mask_resized)

        imgGraphics = cv2.imread("Images/graphics.png", cv2.IMREAD_UNCHANGED)
        if imgGraphics is not None:
            img = cvzone.overlayPNG(img, imgGraphics, (0, 0))

        results = model(imgRegion, stream=True)

        detections = np.empty((0, 6))  # Change the initial array to have 6 columns

        for r in results:
            boxes = r.boxes
            for box in boxes:
                # Bounding Box
                x1, y1, x2, y2 = box.xyxy[0]
                x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                w, h = x2 - x1, y2 - y1

                # Confidence
                conf = math.ceil((box.conf[0] * 100)) / 100
                # Class Name
                cls = int(box.cls[0])
                currentClass = classNames[cls]

                if (currentClass == "car" or currentClass == "truck" or currentClass == "bus" or currentClass == "motorbike") and conf > 0.3:
                    currentArray = np.array([x1, y1, x2, y2, conf, cls])  # Add cls to the array
                    detections = np.vstack((detections, currentArray))

        resultsTracker = tracker.update(detections[:, :5])  # Only pass the first 5 columns to the tracker

        cv2.line(img, (limits[0], limits[1]), (limits[2], limits[3]), (0, 0, 255), 5)
        for result in resultsTracker:
            x1, y1, x2, y2, id = result
            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
            w, h = x2 - x1, y2 - y1

            if id not in id_class_map:
                matching_detections = detections[(detections[:, 0] == x1) & (detections[:, 1] == y1) &
                                                 (detections[:, 2] == x2) & (detections[:, 3] == y2)]
                if len(matching_detections) > 0:
                    cls = matching_detections[0, 5]
                    currentClass = classNames[int(cls)]
                    id_class_map[id] = currentClass
            else:
                currentClass = id_class_map[id]

            if currentClass in ["car", "truck", "bus", "motorbike"]:
                cvzone.cornerRect(img, (x1, y1, w, h), l=9, rt=2, colorR=(255, 0, 255))
                cvzone.putTextRect(img, f' {currentClass}', (max(0, x1), max(35, y1)), scale=2, thickness=3, offset=10)

            cx, cy = x1 + w // 2, y1 + h // 2
            cv2.circle(img, (cx, cy), 5, (255, 0, 255), cv2.FILLED)

            if limits[0] < cx < limits[2] and limits[1] - 15 < cy < limits[1] + 15:
                if totalCount.count(id) == 0:
                    totalCount.append(id)
                    cv2.line(img, (limits[0], limits[1]), (limits[2], limits[3]), (0, 255, 0), 5)

        cv2.putText(img, str(len(totalCount)), (255, 100), cv2.FONT_HERSHEY_PLAIN, 5, (50, 50, 255), 8)

        ret, buffer = cv2.imencode('.jpg', img)
        img = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + img + b'\r\n')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == "__main__":
    app.run(debug=True)

cap.release()
cv2.destroyAllWindows()
