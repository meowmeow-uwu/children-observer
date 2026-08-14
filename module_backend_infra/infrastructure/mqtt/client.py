import json
import asyncio
import aiomqtt
from loguru import logger
from core.config import settings

class MQTTManager:
    def __init__(self):
        self.client: aiomqtt.Client | None = None
        self.broker_host = settings.MQTT_BROKER_HOST
        self.broker_port = settings.MQTT_BROKER_PORT
        self.username = settings.MQTT_USERNAME
        self.password = settings.MQTT_PASSWORD

    async def publish(self, topic: str, payload: dict | str | bytes, retain: bool = False):
        """Hàm dùng chung để bắn tín hiệu xuống Edge (Ví dụ: Cập nhật ROI)"""
        if not self.client:
            logger.error("MQTT Client chưa sẵn sàng.")
            return
            
        try:
            if isinstance(payload, dict):
                payload = json.dumps(payload)
            await self.client.publish(topic, payload=payload, retain=retain)
            logger.info(f"[MQTT PUB] Topic: {topic}")
        except Exception as e:
            logger.error(f"[MQTT PUB ERROR] {str(e)}")

    async def connect_and_listen(self, router_callback):
        """Vòng lặp kết nối và lắng nghe dữ liệu từ Edge AI"""
        reconnect_interval = 3
        while True:
            try:
                # Cấu hình Client
                async with aiomqtt.Client(
                    hostname=self.broker_host,
                    port=self.broker_port,
                    username=self.username,
                    password=self.password
                ) as client:
                    self.client = client
                    logger.success(f" Đã kết nối MQTT Broker tại {self.broker_host}:{self.broker_port}")
                    
                    # 1. Subscribe các topic từ Raspberry Pi
                    # Sử dụng wildcard (+) để lắng nghe toàn bộ thiết bị
                    await client.subscribe("devices/+/alerts")
                    await client.subscribe("devices/+/snapshots")
                    await client.subscribe("devices/+/webrtc/answer")

                    # 2. Vòng lặp nhận tin nhắn
                    async for message in client.messages:
                        # Giao việc xử lý tin nhắn cho Router
                        await router_callback(message)

            except aiomqtt.MqttError as error:
                self.client = None
                logger.warning(f" Mất kết nối MQTT. Thử lại sau {reconnect_interval}s... Lỗi: {error}")
                await asyncio.sleep(reconnect_interval)

# Khởi tạo Singleton
mqtt_manager = MQTTManager()