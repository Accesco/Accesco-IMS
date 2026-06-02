import json
import logging
from typing import Optional, Any
from aiokafka import AIOKafkaProducer
from app.core.config import settings

logger = logging.getLogger(__name__)

class KafkaProducerService:
    def __init__(self, bootstrap_servers: str):
        self.bootstrap_servers = bootstrap_servers
        self.producer: Optional[AIOKafkaProducer] = None

    async def start(self) -> None:
        """Starts the AIOKafkaProducer client."""
        if self.producer:
            return
        
        logger.info(f"Starting AIOKafkaProducer to {self.bootstrap_servers}")
        self.producer = AIOKafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            key_serializer=lambda k: str(k).encode("utf-8") if k else None
        )
        try:
            await self.producer.start()
            logger.info("AIOKafkaProducer started successfully")
        except Exception as e:
            logger.error(f"Failed to start AIOKafkaProducer: {e}")
            self.producer = None
            raise e

    async def stop(self) -> None:
        """Stops the AIOKafkaProducer client."""
        if self.producer:
            logger.info("Stopping AIOKafkaProducer")
            await self.producer.stop()
            self.producer = None
            logger.info("AIOKafkaProducer stopped")

    async def send_event(self, topic: str, key: Optional[Any], value: Any) -> None:
        """Publishes an event to the specified Kafka topic."""
        if not self.producer:
            logger.warning(f"AIOKafkaProducer not started. Trying to start dynamic client.")
            await self.start()
            
        if not self.producer:
            raise RuntimeError("Kafka producer service is not initialized")
            
        try:
            await self.producer.send_and_wait(topic, value=value, key=key)
            logger.info(f"Published event to topic '{topic}' with key '{key}'")
        except Exception as e:
            logger.error(f"Failed to publish event to topic '{topic}': {e}")
            raise e


kafka_producer = KafkaProducerService(settings.KAFKA_BOOTSTRAP_SERVERS)


# Dependency injection helper
async def get_kafka_producer() -> KafkaProducerService:
    return kafka_producer
