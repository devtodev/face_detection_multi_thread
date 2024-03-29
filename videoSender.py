# USAGE
# python object_tracker.py --prototxt deploy.prototxt --model res10_300x300_ssd_iter_140000.caffemodel

# import the necessary packages
from pyimagesearch.centroidtracker import CentroidTracker
import threading
from imutils.video import VideoStream
import numpy as np
import argparse
import imutils
import time
import cv2
import sys
import socket
import time
from imutils.video import VideoStream

sys.path.insert(0, 'imagezmq/imagezmq')  # imagezmq.py is in ../imagezmq
import imagezmq

vs = VideoStream(src=0).start()
frame = vs.read()
frame = imutils.resize(frame, width=400)
(H, W) = frame.shape[:2]
detections = 0


def thread_video_capture(confidence):
    global vs
    global detections
    global frame
    # video sender initialization
    sender = imagezmq.ImageSender(connect_to='tcp://localhost:5555')
    node_name = socket.gethostname()  # send RPi hostname with each image
    time.sleep(2.0)  # allow camera sensor to warm up
    ct = CentroidTracker()
    print("[INFO] starting video stream...")
    # initialize the video stream and allow the camera sensor to warmup
    while True:
        frame = vs.read()
        frame = imutils.resize(frame, width=400)
        rects = []

        # loop over the detections
        if not isinstance(detections, int):
            for i in range(0, detections.shape[2]):
                # filter out weak detections by ensuring the predicted
                # probability is greater than a minimum threshold
                if detections[0, 0, i, 2] > confidence:
                    # compute the (x, y)-coordinates of the bounding box for
                    # the object, then update the bounding box rectangles list
                    box = detections[0, 0, i, 3:7] * np.array([W, H, W, H])
                    rects.append(box.astype("int"))

                    # draw a bounding box surrounding the object so we can
                    # visualize it
                    (startX, startY, endX, endY) = box.astype("int")
                    cv2.rectangle(frame, (startX, startY), (endX, endY), (0, 255, 0), 2)
        objects = ct.update(rects)
        # loop over the tracked objects
        for (objectID, centroid) in objects.items():
            # draw both the ID of the object and the centroid of the
            # object on the output frame
            text = "ID {}".format(objectID)
            cv2.putText(frame, text, (centroid[0] - 10, centroid[1] - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            cv2.circle(frame, (centroid[0], centroid[1]), 4, (0, 255, 0), -1)
            print("{} ({}, {})".format(text, centroid[0], centroid[1]))
        sender.send_image(node_name, frame)


def thread_video_analyze(prototxt, model, H, W):
    global detections
    global frame
    global detections
    # load our serialized model from disk
    print("[INFO] loading model...")
    net = cv2.dnn.readNetFromCaffe(prototxt, model)
    while True:
        time.sleep(0.5)  # allow camera sensor to warm up
        # construct a blob from the frame, pass it through the network,
        # obtain our output predictions, and initialize the list of
        # bounding box rectangles
        blob = cv2.dnn.blobFromImage(frame, 1.0, (W, H), (104.0, 177.0, 123.0))
        net.setInput(blob)
        detections = net.forward()


# construct the argument parse and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-p", "--prototxt", required=True,
                help="path to Caffe 'deploy' prototxt file")
ap.add_argument("-m", "--model", required=True,
                help="path to Caffe pre-trained model")
ap.add_argument("-c", "--confidence", type=float, default=0.5,
                help="minimum probability to filter weak detections")
arguments = vars(ap.parse_args())

analyze = threading.Thread(target=thread_video_analyze, args=(arguments["prototxt"], arguments["model"], H, W),
                           daemon=True)
analyze.start()

time.sleep(2.0)

capture = threading.Thread(target=thread_video_capture, args=(arguments["confidence"],), daemon=True)
capture.start()

while True:  # keep main thread running while the other two threads are non-daemon
    pass
# do a bit of cleanup
cv2.destroyAllWindows()
vs.stop()
