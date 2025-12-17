# Rui Santos & Sara Santos - Random Nerd Tutorials
# Complete project details at https://RandomNerdTutorials.com/raspberry-pi-mjpeg-streaming-web-server-picamera2/

# Mostly copied from https://picamera.readthedocs.io/en/release-1.13/recipes2.html
# Run this script, then point a web browser at http:<this-ip-address>:7123
# Note: needs simplejpeg to be installed (pip3 install simplejpeg).

import io
import logging
import socket
import time
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime
from picamera2 import Picamera2
from picamera2.encoders import JpegEncoder
from picamera2.outputs import FileOutput
from picamera2.encoders import MJPEGEncoder
from picamera2.controls import Controls

#Configuration start
picture_path = '/home/birdmin/pictures'

#Configuration end

PAGE = """\
<html>
<head>
<title>picamera2 MJPEG streaming demo</title>
</head>
<body>
<h1>Picamera2 MJPEG Streaming Demo</h1>
<img src="stream.mjpg" width="800" height="600" />
</body>
</html>
"""

JSON_OK = """
{"success": true}
"""

class StreamingOutput(io.BufferedIOBase):
    def __init__(self):
        self.frame = None
        self.condition = threading.Condition()

    def write(self, buf):
        with self.condition:
            self.frame = buf
            self.condition.notify_all()


class StreamingHandler(BaseHTTPRequestHandler):

    def do_POST(self):
        if self.path == '/rest/v1/savepic':
            os.makedirs(picture_path, exist_ok=True)

            now = datetime.now()
            date_time = now.strftime("%Y-%m-%d_%H:%M:%S.%f")
            file_path = picture_path + "/" + date_time + "_image.jpg"
            picam2.capture_file(file_path)
            content = JSON_OK.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
        else:
            self.send_error(404)
            self.end_headers()

    def do_GET(self):
        if self.path == '/':
            self.send_response(301)
            self.send_header('Location', '/index.html')
            self.end_headers()
        elif self.path == '/index.html':
            content = PAGE.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
        elif self.path == '/stream.mjpg':
            self.send_response(200)
            self.send_header('Age', 0)
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
            self.end_headers()
            try:
                while True:
                    with output.condition:
                        output.condition.wait()
                        frame = output.frame
                    self.wfile.write(b'--FRAME\r\n')
                    self.send_header('Content-Type', 'image/jpeg')
                    self.send_header('Content-Length', len(frame))
                    self.end_headers()
                    self.wfile.write(frame)
                    self.wfile.write(b'\r\n')
            except Exception as e:
                logging.warning(
                    'Removed streaming client %s: %s',
                    self.client_address, str(e))
        else:
            self.send_error(404)
            self.end_headers()


class Thread(threading.Thread):
    def __init__(self, i):
        threading.Thread.__init__(self)
        self.i = i
        self.daemon = True
        self.start()
    def run(self):
        httpd = HTTPServer(addr, StreamingHandler, False)

        # Prevent the HTTP server from re-binding every handler.
        # https://stackoverflow.com/questions/46210672/
        httpd.socket = sock
        httpd.server_bind = self.server_close = lambda self: None

        httpd.serve_forever()


if __name__ == '__main__':
    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    
    try:
        # configure and enable the camera
        logger.info("Initializing camera...")
        tuning = Picamera2.load_tuning_file("ov5647_noir.json")
        picam2 = Picamera2(tuning=tuning)
        video_config = picam2.create_video_configuration(main={"size": (2592, 1944), "format": 'XRGB8888'}, lores={"size": (800, 600), "format": 'YUV420'}, encode="lores")
        ctrls = Controls(picam2)
        ctrls.AwbEnable = True
        encoder = MJPEGEncoder(10000000)
        picam2.configure(video_config)
        output = StreamingOutput()
        picam2.start_recording(encoder, FileOutput(output))
        picam2.set_controls(ctrls)
        logger.info("Camera initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize camera: {e}")
        exit(1)
    
    try:
        logger.info("Starting server on port 7123...")
        addr = ('', 7123)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(addr)
        sock.listen(5)
        logger.info("Server socket created and listening")

        [Thread(i) for i in range(6)]
        logger.info("Server threads started, server is ready")
        while True:
            time.sleep(10000)

    except Exception as e:
        logger.error(f"Server error: {e}")
    finally:
        logger.info("Shutting down...")
        if 'picam2' in locals():
            picam2.stop_recording()
        logger.info("Shutdown complete")

