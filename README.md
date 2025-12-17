# Raspberry Pi Camera Stream Server

A robust MJPEG streaming server for Raspberry Pi cameras with automatic recovery capabilities and REST API for image capture.

## Features

- **Live MJPEG Streaming** - Real-time camera feed accessible via web browser
- **Image Capture API** - REST endpoint for capturing still images
- **Automatic Recovery** - Handles camera timeouts and hardware failures
- **Multi-threaded Server** - Supports multiple concurrent clients
- **Health Monitoring** - Built-in health check endpoint
- **Systemd Integration** - Runs as a system service with auto-restart

## Hardware Requirements

- Raspberry Pi (tested on Rapsberry Pi Nano 2)
- OV5647 Camera Module (NoIR version supported)
- Properly connected camera ribbon cable

## Software Requirements

- Python 3.7+
- picamera2
- Required Python packages (see Installation)

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/mabakach/rpi-stream-server.git
   cd rpi-stream-server
   ```

2. **Install dependencies:**
   ```bash
   # Update system
   sudo apt update && sudo apt upgrade -y
   
   # Install required packages
   sudo apt install python3-picamera2 python3-libcamera python3-kms++
   
   # Optional: Install simplejpeg for better performance
   pip3 install simplejpeg
   ```

3. **Configure camera:**
   ```bash
   # Enable camera interface
   sudo raspi-config
   # Navigate to: Interface Options > Camera > Enable
   
   # Reboot to apply changes
   sudo reboot
   ```

4. **Setup service (optional):**
   ```bash
   # Copy service file
   sudo cp stream-server.service /etc/systemd/system/
   
   # Update paths in service file if needed
   sudo nano /etc/systemd/system/stream-server.service
   
   # Enable and start service
   sudo systemctl enable stream-server.service
   sudo systemctl start stream-server.service
   ```

## Configuration

Edit the configuration section in `stream-server.py`:

```python
#Configuration start
picture_path = '/home/birdmin/pictures'        # Directory for captured images
camera_timeout_recovery = True                 # Enable automatic camera recovery
camera_recovery_delay = 5                      # Seconds to wait before recovery
#Configuration end
```

## Usage

### Manual Start

```bash
python3 stream-server.py
```

### As System Service

```bash
# Start service
sudo systemctl start stream-server.service

# Check status
sudo systemctl status stream-server.service

# View logs
sudo journalctl -u stream-server.service -f
```

### Access the Stream

1. **Web Interface:** `http://<raspberry-pi-ip>:7123/`
2. **Direct Stream:** `http://<raspberry-pi-ip>:7123/stream.mjpg`
3. **Health Check:** `http://<raspberry-pi-ip>:7123/health`

## API Endpoints

| Method | Endpoint | Description | Response |
|--------|----------|-------------|----------|
| GET | `/` | Redirects to main page | 301 Redirect |
| GET | `/index.html` | Web interface with embedded stream | HTML Page |
| GET | `/stream.mjpg` | MJPEG video stream | Video Stream |
| GET | `/health` | Camera health status | JSON Status |
| POST | `/rest/v1/savepic` | Capture and save image | JSON Response |

### API Examples

**Capture Image:**
```bash
curl -X POST http://192.168.1.100:7123/rest/v1/savepic
```

**Check Health:**
```bash
curl http://192.168.1.100:7123/health
```

**Response Examples:**

*Successful Image Capture:*
```json
{"success": true}
```

*Health Check (Healthy):*
```json
{
  "camera_healthy": true,
  "timestamp": "2025-12-17T21:30:00.123456",
  "status": "ok"
}
```

*Health Check (Camera Error):*
```json
{
  "camera_healthy": false,
  "timestamp": "2025-12-17T21:30:00.123456",
  "status": "camera_error"
}
```

## Camera Recovery

The server includes automatic recovery for camera timeout issues:

### When Recovery Triggers
- Camera frontend timeout errors
- Frame retrieval timeouts (>10 seconds)
- Hardware connection issues

### Recovery Process
1. Detect camera timeout/error
2. Mark camera as unhealthy
3. Clean up camera resources
4. Wait for recovery delay (5 seconds)
5. Reinitialize camera hardware
6. Resume streaming automatically

### Monitoring Recovery
```bash
# Watch logs for recovery events
sudo journalctl -u stream-server.service -f | grep -i "recovery\|timeout\|camera"
```

## Logging

### View Logs

**Systemd Journal:**
```bash
# Recent logs
sudo journalctl -u stream-server.service

# Follow logs in real-time
sudo journalctl -u stream-server.service -f

# Today's logs only
sudo journalctl -u stream-server.service --since today
```

**Application Log File:**
```bash
# View log file (if configured)
tail -f /home/birdmin/stream-server/stream-server.log
```

### Log Levels
- **INFO** - Normal operation, client connections, camera initialization
- **WARNING** - Client disconnections, camera recovery attempts
- **ERROR** - Camera failures, server errors

## Troubleshooting

### Common Issues

**1. Camera Not Detected**
```bash
# Check camera connection
libcamera-hello --list-cameras

# Verify camera interface is enabled
sudo raspi-config
```

**2. Permission Denied**
```bash
# Add user to video group
sudo usermod -a -G video $USER
# Logout and login again
```

**3. Port Already in Use**
```bash
# Check what's using port 7123
sudo lsof -i :7123

# Kill existing process if needed
sudo pkill -f stream-server.py
```

**4. Camera Timeout Errors**
- Check camera ribbon cable connection
- Try a different camera cable
- Verify camera is properly seated in connector
- Check for hardware damage

**5. High CPU Usage**
- Reduce video resolution in configuration
- Lower MJPEG bitrate
- Limit number of concurrent clients

### Service Issues

**Service Won't Start:**
```bash
# Check service status
sudo systemctl status stream-server.service

# View detailed logs
sudo journalctl -u stream-server.service -n 50
```

**Camera Recovery Not Working:**
```bash
# Check configuration
grep -A 5 "Configuration start" stream-server.py

# Verify camera_timeout_recovery is True
```

## Performance Tuning

### Camera Settings
- **High Quality:** 2592×1944 main, 800×600 stream
- **Balanced:** 1920×1080 main, 640×480 stream  
- **Low Bandwidth:** 1280×720 main, 480×360 stream

### Server Configuration
- **Default:** 6 worker threads, 10Mbps bitrate
- **High Load:** Increase worker threads
- **Low Bandwidth:** Reduce bitrate and resolution

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly on Raspberry Pi hardware
5. Submit a pull request

## License

This project is based on tutorials from Random Nerd Tutorials and picamera documentation. See original sources:
- [Random Nerd Tutorials](https://RandomNerdTutorials.com/raspberry-pi-mjpeg-streaming-web-server-picamera2/)
- [Picamera2 Documentation](https://picamera.readthedocs.io/)

## Support

For issues and questions:
1. Check the troubleshooting section above
2. Review the logs for error messages
3. Open an issue on GitHub with:
   - Raspberry Pi model and OS version
   - Camera module type
   - Complete error logs
   - Steps to reproduce the issue