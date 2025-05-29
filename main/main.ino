#include <WiFi.h>
#include "esp_camera.h"
#include "esp_timer.h"
#include "img_converters.h"
#include "Arduino.h"
#include "soc/soc.h"
#include "soc/rtc_cntl_reg.h"
#include "esp_http_server.h"
#include <WebServer.h>

// Replace with your network credentials
const char* ssid = "BASE_AP";                         // <== Replace with your network credentials
const char* password = "edmangoodlife123456";                  // <== Replace with your network credentials
const IPAddress local_IP(192, 168, 8, 200);
const IPAddress gateway(192, 168, 8, 1);
const IPAddress subnet(255, 255, 255, 0);

// Motor pins - FIXED: Using available GPIO pins that don't conflict with camera
#define IN1 14  // Changed from 12 (available GPIO)
#define IN2 15  // Changed from 13 (available GPIO) 
#define IN3 13  // Changed from 2 (available GPIO, was conflicting)
#define IN4 12  // Changed from 4 (available GPIO, was conflicting with camera Y2)

// Camera pin definitions for AI Thinker ESP32-CAM
#define PWDN_GPIO_NUM 32
#define RESET_GPIO_NUM -1
#define XCLK_GPIO_NUM 0
#define SIOD_GPIO_NUM 26
#define SIOC_GPIO_NUM 27
#define Y9_GPIO_NUM 35
#define Y8_GPIO_NUM 34
#define Y7_GPIO_NUM 39
#define Y6_GPIO_NUM 36
#define Y5_GPIO_NUM 21
#define Y4_GPIO_NUM 19
#define Y3_GPIO_NUM 18
#define Y2_GPIO_NUM 5   // This was conflicting with IN4 (GPIO 4)
#define VSYNC_GPIO_NUM 25
#define HREF_GPIO_NUM 23
#define PCLK_GPIO_NUM 22

WebServer server(80);
httpd_handle_t camera_httpd = NULL;

// Camera streaming handler
static esp_err_t stream_handler(httpd_req_t *req) {
  camera_fb_t * fb = NULL;
  esp_err_t res = ESP_OK;
  size_t _jpg_buf_len = 0;
  uint8_t * _jpg_buf = NULL;
  char * part_buf[128];
  static const char* _STREAM_CONTENT_TYPE = "multipart/x-mixed-replace;boundary=123456789000000000000987654321";
  static const char* _STREAM_BOUNDARY = "\r\n--123456789000000000000987654321\r\n";
  static const char* _STREAM_PART = "Content-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n";

  res = httpd_resp_set_type(req, _STREAM_CONTENT_TYPE);
  if(res != ESP_OK){
    return res;
  }

  // Send initial boundary
  res = httpd_resp_send_chunk(req, _STREAM_BOUNDARY, strlen(_STREAM_BOUNDARY));
  if(res != ESP_OK) return res;

  while(true){
    fb = esp_camera_fb_get();
    if (!fb) {
      Serial.println("Camera capture failed");
      res = ESP_FAIL;
      break;
    }

    if(fb->format != PIXFORMAT_JPEG){
      bool jpeg_converted = frame2jpg(fb, 80, &_jpg_buf, &_jpg_buf_len);
      esp_camera_fb_return(fb);
      fb = NULL;
      if(!jpeg_converted){
        Serial.println("JPEG compression failed");
        res = ESP_FAIL;
        break;
      }
    } else {
      _jpg_buf_len = fb->len;
      _jpg_buf = fb->buf;
    }

    if(res == ESP_OK){
      size_t hlen = snprintf((char *)part_buf, 128, _STREAM_PART, _jpg_buf_len);
      res = httpd_resp_send_chunk(req, (const char *)part_buf, hlen);
    }
    if(res == ESP_OK){
      res = httpd_resp_send_chunk(req, (const char *)_jpg_buf, _jpg_buf_len);
    }
    if(res == ESP_OK){
      res = httpd_resp_send_chunk(req, _STREAM_BOUNDARY, strlen(_STREAM_BOUNDARY));
    }
    
    if(fb){
      esp_camera_fb_return(fb);
      fb = NULL;
      _jpg_buf = NULL;
    } else if(_jpg_buf){
      free(_jpg_buf);
      _jpg_buf = NULL;
    }
    
    if(res != ESP_OK){
      Serial.println("Stream send failed");
      break;
    }
    
    // Small delay to prevent overwhelming
    delay(30);
  }
  return res;
}

void startCameraServer();

void setup() {
  WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0);  // disable brownout detector
  Serial.begin(115200);

  // Motor pin setup
  pinMode(IN1, OUTPUT);
  pinMode(IN2, OUTPUT);
  pinMode(IN3, OUTPUT);
  pinMode(IN4, OUTPUT);
  stopMotors();

  // Configure static IP
  if (!WiFi.config(local_IP, gateway, subnet)) {
    Serial.println("STA Failed to configure");
  }

  WiFi.begin(ssid, password);
  Serial.print("Connecting to Wi-Fi");

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nWiFi connected");
  Serial.println("Camera Stream Ready! Go to: http://" + WiFi.localIP().toString());

  // Camera configuration
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  
  // Optimize camera settings for better streaming
  if(psramFound()){
    config.frame_size = FRAMESIZE_VGA;
    config.jpeg_quality = 12;
    config.fb_count = 2;
  } else {
    config.frame_size = FRAMESIZE_QVGA;
    config.jpeg_quality = 12;
    config.fb_count = 1;
  }

  // Initialize camera
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed with error 0x%x", err);
    return;
  }
  
  // Get camera sensor and adjust settings
  sensor_t * s = esp_camera_sensor_get();
  if (s != NULL) {
    // Flip image vertically and horizontally if needed
    s->set_vflip(s, 1);        // Flip vertically
    s->set_hmirror(s, 1);      // Mirror horizontally
    
    // Adjust other settings for better streaming
    s->set_brightness(s, 0);   // -2 to 2
    s->set_contrast(s, 0);     // -2 to 2
    s->set_saturation(s, 0);   // -2 to 2
    s->set_special_effect(s, 0); // 0 to 6 (0-No Effect, 1-Negative, 2-Grayscale, 3-Red Tint, 4-Green Tint, 5-Blue Tint, 6-Sepia)
    s->set_whitebal(s, 1);     // 0 = disable , 1 = enable
    s->set_awb_gain(s, 1);     // 0 = disable , 1 = enable
    s->set_wb_mode(s, 0);      // 0 to 4 - if awb_gain enabled (0 - Auto, 1 - Sunny, 2 - Cloudy, 3 - Office, 4 - Home)
    s->set_exposure_ctrl(s, 1); // 0 = disable , 1 = enable
    s->set_aec2(s, 0);         // 0 = disable , 1 = enable
    s->set_ae_level(s, 0);     // -2 to 2
    s->set_aec_value(s, 300);  // 0 to 1200
    s->set_gain_ctrl(s, 1);    // 0 = disable , 1 = enable
    s->set_agc_gain(s, 0);     // 0 to 30
    s->set_gainceiling(s, (gainceiling_t)0); // 0 to 6
    s->set_bpc(s, 0);          // 0 = disable , 1 = enable
    s->set_wpc(s, 1);          // 0 = disable , 1 = enable
    s->set_raw_gma(s, 1);      // 0 = disable , 1 = enable
    s->set_lenc(s, 1);         // 0 = disable , 1 = enable
    s->set_hmirror(s, 0);      // 0 = disable , 1 = enable (overridden above)
    s->set_vflip(s, 0);        // 0 = disable , 1 = enable (overridden above)
    s->set_dcw(s, 1);          // 0 = disable , 1 = enable
    s->set_colorbar(s, 0);     // 0 = disable , 1 = enable
  }

  Serial.println("Camera initialized successfully");
  Serial.println("Motor pins assigned:");
  Serial.printf("  IN1 (Motor A+): GPIO %d\n", IN1);
  Serial.printf("  IN2 (Motor A-): GPIO %d\n", IN2);
  Serial.printf("  IN3 (Motor B+): GPIO %d\n", IN3);
  Serial.printf("  IN4 (Motor B-): GPIO %d\n", IN4);

  startCameraServer();
}

// Motor control functions
void stopMotors() {
  digitalWrite(IN1, LOW);
  digitalWrite(IN2, LOW);
  digitalWrite(IN3, LOW);
  digitalWrite(IN4, LOW);
}

void moveForward() {
  digitalWrite(IN1, HIGH);
  digitalWrite(IN2, LOW);
  digitalWrite(IN3, HIGH);
  digitalWrite(IN4, LOW);
}

void moveBackward() {
  digitalWrite(IN1, LOW);
  digitalWrite(IN2, HIGH);
  digitalWrite(IN3, LOW);
  digitalWrite(IN4, HIGH);
}

void turnLeft() {
  digitalWrite(IN1, LOW);
  digitalWrite(IN2, HIGH);
  digitalWrite(IN3, HIGH);
  digitalWrite(IN4, LOW);
}

void turnRight() {
  digitalWrite(IN1, HIGH);
  digitalWrite(IN2, LOW);
  digitalWrite(IN3, LOW);
  digitalWrite(IN4, HIGH);
}

void handleRoot() {
  String html = R"rawliteral(
    <!DOCTYPE html>
    <html>
    <head>
      <title>ESP32-CAM Robot</title>
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <style>
        body { 
          font-family: Arial, sans-serif; 
          text-align: center; 
          margin: 10px; 
          background-color: #1a1a1a;
          color: white;
        }
        
        .container {
          max-width: 600px;
          margin: 0 auto;
          padding: 20px;
        }
        
        h2 {
          color: #4CAF50;
          margin-bottom: 20px;
        }
        
        .video-container {
          position: relative;
          margin-bottom: 20px;
          border: 3px solid #4CAF50;
          border-radius: 10px;
          overflow: hidden;
          background-color: #000;
        }
        
        #stream {
          width: 100%;
          max-width: 480px;
          height: auto;
          display: block;
        }
        
        .controls {
          display: grid;
          grid-template-columns: 1fr 1fr 1fr;
          grid-template-rows: auto auto auto;
          gap: 10px;
          max-width: 300px;
          margin: 0 auto;
        }
        
        button {
          padding: 15px 20px;
          font-size: 16px;
          font-weight: bold;
          border: none;
          border-radius: 8px;
          background: linear-gradient(45deg, #4CAF50, #45a049);
          color: white;
          cursor: pointer;
          transition: all 0.3s;
          user-select: none;
          touch-action: manipulation;
        }
        
        button:hover {
          background: linear-gradient(45deg, #45a049, #4CAF50);
          transform: translateY(-2px);
          box-shadow: 0 4px 8px rgba(76, 175, 80, 0.3);
        }
        
        button:active {
          transform: translateY(0);
          box-shadow: 0 2px 4px rgba(76, 175, 80, 0.3);
        }
        
        .forward { grid-column: 2; grid-row: 1; }
        .left { grid-column: 1; grid-row: 2; }
        .stop { grid-column: 2; grid-row: 2; background: linear-gradient(45deg, #f44336, #da190b); }
        .stop:hover { background: linear-gradient(45deg, #da190b, #f44336); }
        .right { grid-column: 3; grid-row: 2; }
        .backward { grid-column: 2; grid-row: 3; }
        
        .status {
          margin-top: 20px;
          padding: 10px;
          background-color: #333;
          border-radius: 5px;
          font-weight: bold;
        }
        
        .stream-status {
          margin-top: 10px;
          font-size: 12px;
          color: #888;
        }
        
        .pin-info {
          margin-top: 20px;
          padding: 10px;
          background-color: #2a2a2a;
          border-radius: 5px;
          font-size: 12px;
          color: #ccc;
          text-align: left;
        }
        
        @media (max-width: 480px) {
          .container { padding: 10px; }
          button { padding: 12px 15px; font-size: 14px; }
          .controls { max-width: 250px; gap: 8px; }
          .pin-info { font-size: 10px; }
        }
      </style>
    </head>
    <body>
      <div class="container">
        <h2>🚗 ESP32-CAM Robot Car 📷</h2>
        
        <div class="video-container">
          <img id="stream" src="" alt="Camera Stream Loading...">
          <div class="stream-status" id="streamStatus">Connecting to camera...</div>
        </div>
        
        <div class="controls">
          <button class="forward" onmousedown="sendCommand('forward')" onmouseup="sendCommand('stop')" 
                  ontouchstart="sendCommand('forward')" ontouchend="sendCommand('stop')">
            ⬆️ Forward
          </button>
          
          <button class="left" onmousedown="sendCommand('left')" onmouseup="sendCommand('stop')"
                  ontouchstart="sendCommand('left')" ontouchend="sendCommand('stop')">
            ⬅️ Left
          </button>
          
          <button class="stop" onclick="sendCommand('stop')">
            🛑 Stop
          </button>
          
          <button class="right" onmousedown="sendCommand('right')" onmouseup="sendCommand('stop')"
                  ontouchstart="sendCommand('right')" ontouchend="sendCommand('stop')">
            ➡️ Right
          </button>
          
          <button class="backward" onmousedown="sendCommand('backward')" onmouseup="sendCommand('stop')"
                  ontouchstart="sendCommand('backward')" ontouchend="sendCommand('stop')">
            ⬇️ Backward
          </button>
        </div>
        
        <div class="status" id="status">Ready</div>
        
        <div class="pin-info">
          <strong>Motor Pin Assignments (Fixed):</strong><br>
          IN1 (Motor A+): GPIO 14<br>
          IN2 (Motor A-): GPIO 15<br>
          IN3 (Motor B+): GPIO 13<br>
          IN4 (Motor B-): GPIO 12
        </div>
      </div>
      
      <script>
        let isConnected = false;
        const streamImg = document.getElementById('stream');
        const statusDiv = document.getElementById('status');
        const streamStatusDiv = document.getElementById('streamStatus');
        
        // Initialize camera stream
        function initStream() {
          const streamUrl = window.location.protocol + '//' + window.location.hostname + ':81/stream';
          streamImg.src = streamUrl;
          
          streamImg.onload = function() {
            isConnected = true;
            streamStatusDiv.textContent = 'Camera connected ✓';
            streamStatusDiv.style.color = '#4CAF50';
          };
          
          streamImg.onerror = function() {
            isConnected = false;
            streamStatusDiv.textContent = 'Camera connection failed ✗';
            streamStatusDiv.style.color = '#f44336';
            // Retry connection
            setTimeout(initStream, 3000);
          };
        }
        
        // Send command to robot
        async function sendCommand(cmd) {
          try {
            const response = await fetch('/' + cmd);
            if (response.ok) {
              const text = await response.text();
              statusDiv.textContent = text;
              statusDiv.style.color = '#4CAF50';
            } else {
              statusDiv.textContent = 'Command failed';
              statusDiv.style.color = '#f44336';
            }
          } catch (error) {
            statusDiv.textContent = 'Connection error';
            statusDiv.style.color = '#f44336';
          }
        }
        
        // Prevent context menu on long press (mobile)
        document.addEventListener('contextmenu', function(e) {
          e.preventDefault();
        });
        
        // Initialize stream when page loads
        window.onload = function() {
          initStream();
        };
        
        // Handle visibility change to restart stream if needed
        document.addEventListener('visibilitychange', function() {
          if (!document.hidden && !isConnected) {
            initStream();
          }
        });
      </script>
    </body>
    </html>
  )rawliteral";
  server.send(200, "text/html", html);
}

void startCameraServer() {
  // Start camera streaming server
  httpd_config_t config = HTTPD_DEFAULT_CONFIG();
  config.server_port = 81;
  config.ctrl_port = 32769;
  
  httpd_uri_t stream_uri = {
    .uri       = "/stream",
    .method    = HTTP_GET,
    .handler   = stream_handler,
    .user_ctx  = NULL
  };
  
  if (httpd_start(&camera_httpd, &config) == ESP_OK) {
    httpd_register_uri_handler(camera_httpd, &stream_uri);
    Serial.println("Camera streaming server started on port 81");
    Serial.println("Stream URL: http://" + WiFi.localIP().toString() + ":81/stream");
  } else {
    Serial.println("Failed to start camera streaming server");
  }

  // Start control web server
  server.on("/", handleRoot);
  server.on("/forward", []() {
    moveForward();
    server.send(200, "text/plain", "Moving Forward");
  });
  server.on("/backward", []() {
    moveBackward();
    server.send(200, "text/plain", "Moving Backward");
  });
  server.on("/left", []() {
    turnLeft();
    server.send(200, "text/plain", "Turning Left");
  });
  server.on("/right", []() {
    turnRight();
    server.send(200, "text/plain", "Turning Right");
  });
  server.on("/stop", []() {
    stopMotors();
    server.send(200, "text/plain", "Stopped");
  });

  server.begin();
  Serial.println("Control server started on port 80");
}

void loop() {
  server.handleClient();
}