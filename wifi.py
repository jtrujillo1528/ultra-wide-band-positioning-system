from machine import Pin
import network
import json
import time
import ubinascii
from umqtt.simple import MQTTClient
import uasyncio as asyncio

class AnchorNode:
    def __init__(self, ssid, password, mqtt_broker, mqtt_port=1883, threshold=5):
        """Initialize anchor node with network and MQTT broker details"""
        self.ssid = ssid
        self.password = password
        self.mqtt_broker = mqtt_broker
        self.mqtt_port = mqtt_port
        self.wlan = network.WLAN(network.STA_IF)
        self.connected = False
        self.proximity_threshold = threshold
        
        # Get MAC address and format it as the anchor ID
        self.wlan.active(True)
        mac = self.wlan.config('mac')
        self.anchor_id = ubinascii.hexlify(mac).decode('utf-8')
        print(f"Anchor ID (MAC): {self.anchor_id}")
        
        # Initialize MQTT client
        client_id = f"anchor_{self.anchor_id}"
        self.mqtt_client = MQTTClient(client_id, mqtt_broker, mqtt_port)
        self.mqtt_client.set_callback(self._on_message)
        
    async def connect_wifi(self):
        """Establish WiFi connection with error handling and retry"""
        print(f"Connecting to WiFi network: {self.ssid}")
        
        if not self.wlan.active():
            self.wlan.active(True)
            mac = self.wlan.config('mac')
            self.anchor_id = ubinascii.hexlify(mac).decode('utf-8')
            
        self.wlan.connect(self.ssid, self.password)
        
        # Wait for connection with timeout
        max_wait = 10
        while max_wait > 0:
            if self.wlan.status() < 0 or self.wlan.status() >= 3:
                break
            max_wait -= 1
            print("Waiting for connection...")
            await asyncio.sleep(1)
            
        if self.wlan.status() != 3:
            raise RuntimeError('WiFi connection failed')
        else:
            print('Connected')
            status = self.wlan.ifconfig()
            print(f'IP Address: {status[0]}')
            print(f'Anchor ID (MAC): {self.anchor_id}')
            self.connected = True
            
    async def connect_mqtt(self):
        """Connect to MQTT broker with error handling"""
        try:
            self.mqtt_client.connect()
            print(f"Connected to MQTT broker at {self.mqtt_broker}")
            
            # Subscribe to configuration topics
            self.mqtt_client.subscribe(f"config/anchor/{self.anchor_id}")
            self.mqtt_client.subscribe("config/anchor/all")
            
        except Exception as e:
            print(f"MQTT connection failed: {e}")
            raise
            
    def _on_message(self, topic, msg):
        """Handle incoming MQTT messages"""
        try:
            topic = topic.decode('utf-8')
            payload = json.loads(msg.decode('utf-8'))
            
            if topic.startswith('config/anchor/'):
                if 'proximity_threshold' in payload:
                    self.proximity_threshold = float(payload['proximity_threshold'])
                    print(f"Updated proximity threshold to {self.proximity_threshold}m")
                    
        except Exception as e:
            print(f"Error processing message: {e}")
            
    async def send_ranging_data(self, tag_id, distance):
        """Send ranging data via MQTT when tag is within threshold"""
        if distance <= self.proximity_threshold:
            try:
                data = {
                    "anchor_id": self.anchor_id,
                    "tag_id": tag_id,
                    "distance": distance,
                    "timestamp": time.time()
                }
                
                message = json.dumps(data)
                self.mqtt_client.publish(f"ranging/data/{self.anchor_id}", message)
                
                # Also send a heartbeat/status message
                status = {
                    "status": "active",
                    "timestamp": time.time()
                }
                self.mqtt_client.publish(f"ranging/status/{self.anchor_id}", json.dumps(status))
                
            except Exception as e:
                print(f"Error sending data: {e}")
                # Attempt to reconnect if connection lost
                if not self.wlan.isconnected():
                    self.connected = False
                    await self.connect_wifi()
                    await self.connect_mqtt()
    
    async def check_messages(self):
        """Check for pending MQTT messages"""
        try:
            self.mqtt_client.check_msg()
        except Exception as e:
            print(f"Error checking messages: {e}")
            
    async def heartbeat(self):
        """Periodic heartbeat to maintain active status"""
        while True:
            try:
                status = {
                    "status": "active",
                    "timestamp": time.time()
                }
                self.mqtt_client.publish(f"ranging/status/{self.anchor_id}", json.dumps(status))
                await asyncio.sleep(30)  # Send heartbeat every 30 seconds
            except Exception as e:
                print(f"Heartbeat error: {e}")
                await asyncio.sleep(5)  # Wait before retry
                
    async def reconnection_monitor(self):
        """Monitor and handle connection status"""
        while True:
            if not self.wlan.isconnected():
                print("Connection lost, attempting to reconnect...")
                self.connected = False
                try:
                    await self.connect_wifi()
                    await self.connect_mqtt()
                except Exception as e:
                    print(f"Reconnection failed: {e}")
            await asyncio.sleep(5)  # Check every 5 seconds

async def main():
    # Example usage
    WIFI_SSID = "xxxx"
    WIFI_PASSWORD = "xxxxx"
    MQTT_BROKER = "test.mosquitto.org"  # Public test broker (replace with your broker)
    MQTT_PORT = 1883
    
    try:
        anchor = AnchorNode(WIFI_SSID, WIFI_PASSWORD, MQTT_BROKER, MQTT_PORT, threshold=5)
        await anchor.connect_wifi()
        await anchor.connect_mqtt()
        print("Anchor node ready for ranging")
        
        # Create tasks for background operations
        asyncio.create_task(anchor.heartbeat())
        asyncio.create_task(anchor.reconnection_monitor())
        
        # Example ranging data (to be replaced with actual DWM1000 ranging code)
        await anchor.send_ranging_data(0x1234, 2)
        
        # Main loop
        while True:
            await anchor.check_messages()
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        print("Stopping anchor node...")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())