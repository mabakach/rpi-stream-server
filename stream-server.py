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
camera_timeout_recovery = True  # Enable automatic camera recovery
camera_recovery_delay = 5  # Seconds to wait before reinitializing camera

#Configuration end

class CameraManager:
    def __init__(self):
        self.picam2 = None
        self.output = None
        self.encoder = None
        self.camera_lock = threading.Lock()
        self.is_camera_healthy = False
        self.logger = logging.getLogger(__name__)
        
    def initialize_camera(self):
        """Initialize camera with error handling"""
        with self.camera_lock:
            try:
                self.logger.info("Initializing camera...")
                
                # Clean up existing camera if any
                self.cleanup_camera()
                
                tuning = Picamera2.load_tuning_file("ov5647_noir.json")
                self.picam2 = Picamera2(tuning=tuning)
                video_config = self.picam2.create_video_configuration(
                    main={"size": (2592, 1944), "format": 'XRGB8888'}, 
                    lores={"size": (800, 600), "format": 'YUV420'}, 
                    encode="lores"
                )
                
                ctrls = Controls(self.picam2)
                ctrls.AwbEnable = True
                self.encoder = MJPEGEncoder(10000000)
                self.picam2.configure(video_config)
                self.output = StreamingOutput()
                self.picam2.start_recording(self.encoder, FileOutput(self.output))
                self.picam2.set_controls(ctrls)
                
                self.is_camera_healthy = True
                self.logger.info("Camera initialized successfully")
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to initialize camera: {e}")
                self.is_camera_healthy = False
                self.cleanup_camera()
                return False
    
    def cleanup_camera(self):
        """Clean up camera resources"""
        try:
            if self.picam2:
                self.picam2.stop_recording()
                self.picam2.close()
                self.picam2 = None
            self.output = None
            self.encoder = None
            self.logger.info("Camera resources cleaned up")
        except Exception as e:
            self.logger.warning(f"Error during camera cleanup: {e}")
    
    def reinitialize_camera(self):
        """Reinitialize camera after timeout/error"""
        self.logger.warning("Camera timeout detected, attempting recovery...")
        self.is_camera_healthy = False
        
        # Wait before reinitializing
        time.sleep(camera_recovery_delay)
        
        # Attempt reinitialization
        if self.initialize_camera():
            self.logger.info("Camera recovery successful")
            return True
        else:
            self.logger.error("Camera recovery failed")
            return False
    
    def capture_image(self, file_path):
        """Capture image with error handling"""
        with self.camera_lock:
            if not self.is_camera_healthy or not self.picam2:
                raise Exception("Camera not available")
            
            try:
                self.picam2.capture_file(file_path)
                return True
            except Exception as e:
                self.logger.error(f"Image capture failed: {e}")
                if "timeout" in str(e).lower() or "frontend" in str(e).lower():
                    if camera_timeout_recovery:
                        threading.Thread(target=self.reinitialize_camera, daemon=True).start()
                raise
    
    def get_frame(self):
        """Get current frame with timeout handling"""
        if not self.is_camera_healthy or not self.output:
            return None
            
        try:
            with self.output.condition:
                # Add timeout to detect camera issues
                if self.output.condition.wait(timeout=10):
                    return self.output.frame
                else:
                    self.logger.warning("Frame timeout - camera may have issues")
                    if camera_timeout_recovery:
                        threading.Thread(target=self.reinitialize_camera, daemon=True).start()
                    return None
        except Exception as e:
            self.logger.error(f"Error getting frame: {e}")
            return None

# Global camera manager instance
camera_manager = CameraManager()

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
            try:
                os.makedirs(picture_path, exist_ok=True)

                now = datetime.now()
                date_time = now.strftime("%Y-%m-%d_%H:%M:%S.%f")
                file_path = os.path.join(picture_path, f"{date_time}_image.jpg")
                
                camera_manager.capture_image(file_path)
                
                content = JSON_OK.encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', len(content))
                self.end_headers()
                self.wfile.write(content)
                logging.info(f"Image captured: {file_path}")
                
            except Exception as e:
                logging.error(f"Image capture failed: {e}")
                error_msg = '{"success": false, "error": "Camera not available"}'
                content = error_msg.encode('utf-8')
                self.send_response(503)
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
            if not camera_manager.is_camera_healthy:
                self.send_error(503, "Camera not available")
                self.end_headers()
                return
                
            self.send_response(200)
            self.send_header('Age', 0)
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
            self.end_headers()
            
            frames_sent = 0
            start_time = time.time()
            logging.info(f"New streaming client connected: {self.client_address}")
            
            try:
                while camera_manager.is_camera_healthy:
                    frame = camera_manager.get_frame()
                    
                    if frame is None:
                        logging.warning("No frame available, camera may be recovering")
                        time.sleep(0.1)
                        continue
                    
                    try:
                        self.wfile.write(b'--FRAME\r\n')
                        self.send_header('Content-Type', 'image/jpeg')
                        self.send_header('Content-Length', len(frame))
                        self.end_headers()
                        self.wfile.write(frame)
                        self.wfile.write(b'\r\n')
                        frames_sent += 1
                        
                        # Log stats periodically
                        if frames_sent % 1000 == 0:
                            elapsed = time.time() - start_time
                            fps = frames_sent / elapsed if elapsed > 0 else 0
                            logging.info(f"Client {self.client_address}: {frames_sent} frames, {fps:.1f} FPS")
                            
                    except (BrokenPipeError, ConnectionResetError):
                        break
                    except Exception as frame_error:
                        logging.error(f"Error sending frame: {frame_error}")
                        break
                        
            except Exception as e:
                logging.warning(
                    'Removed streaming client %s: %s',
                    self.client_address, str(e))
            finally:
                elapsed = time.time() - start_time
                logging.info(f"Client {self.client_address} disconnected after {frames_sent} frames in {elapsed:.1f}s")
        elif self.path == '/health':
            # Health check endpoint
            health_status = {
                "camera_healthy": camera_manager.is_camera_healthy,
                "timestamp": datetime.now().isoformat(),
                "status": "ok" if camera_manager.is_camera_healthy else "camera_error"
            }
            content = str(health_status).replace("'", '"').encode('utf-8')
            self.send_response(200 if camera_manager.is_camera_healthy else 503)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
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
    
    # Initialize camera
    if not camera_manager.initialize_camera():
        logger.error("Failed to initialize camera on startup")
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
        
        # Monitor camera health periodically
        last_health_check = time.time()
        
        while True:
            time.sleep(30)  # Check every 30 seconds instead of 10000
            
            # Periodic health check
            current_time = time.time()
            if current_time - last_health_check > 300:  # Every 5 minutes
                logger.info(f"Camera status: {'Healthy' if camera_manager.is_camera_healthy else 'Unhealthy'}")
                last_health_check = current_time

    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    except Exception as e:
        logger.error(f"Server error: {e}")
    finally:
        logger.info("Shutting down...")
        camera_manager.cleanup_camera()
        logger.info("Shutdown complete")

