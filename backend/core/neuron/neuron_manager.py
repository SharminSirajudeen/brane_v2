"""
NeuronManager - Multi-Agent Orchestration
Manages multiple Neuron instances with local and network messaging
"""

import asyncio
import logging
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
import os

from core.neuron.neuron import Neuron
from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class MessengerType(str, Enum):
    """Communication backend types"""
    IN_MEMORY = "in_memory"  # Fast local event bus
    FILE_SYSTEM = "filesystem"  # Shared filesystem (multi-machine)
    REDIS = "redis"  # Scalable network messaging


class NeuronManager:
    """
    Manages multiple Neuron instances and routes messages between them.

    Features:
    - In-memory event bus for local neurons (fast)
    - Filesystem messenger for multi-machine setups
    - Redis messenger for scalable deployments
    - Smart routing: local-first, then network
    - Lifecycle management (create, initialize, destroy)
    """

    def __init__(self, messenger_type: MessengerType = MessengerType.IN_MEMORY):
        """
        Initialize NeuronManager.

        Args:
            messenger_type: Communication backend to use
        """
        self.messenger_type = messenger_type

        # Active neurons (neuron_id -> Neuron instance)
        self.neurons: Dict[str, Neuron] = {}

        # Message queue for in-memory messaging
        self.message_queue: asyncio.Queue = asyncio.Queue()

        # Event subscriptions (neuron_id -> event_types)
        self.subscriptions: Dict[str, List[str]] = {}

        # Redis client (if using Redis messenger)
        self.redis_client: Optional[Any] = None

        # Filesystem messenger path
        self.fs_messenger_path = os.path.join(settings.STORAGE_PATH, "messages")

        logger.info(f"NeuronManager initialized (messenger: {messenger_type})")

    async def initialize(self):
        """Initialize messenger backend"""
        if self.messenger_type == MessengerType.REDIS:
            await self._init_redis()
        elif self.messenger_type == MessengerType.FILE_SYSTEM:
            await self._init_filesystem()
        elif self.messenger_type == MessengerType.IN_MEMORY:
            # Start message processor
            asyncio.create_task(self._process_messages())

        logger.info("NeuronManager messaging backend initialized")

    async def _init_redis(self):
        """Initialize Redis connection for distributed messaging"""
        try:
            import redis.asyncio as redis

            self.redis_client = await redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )

            # Test connection
            await self.redis_client.ping()

            logger.info("Redis messenger initialized")

        except Exception as e:
            logger.error(f"Redis initialization failed: {e}")
            logger.warning("Falling back to in-memory messenger")
            self.messenger_type = MessengerType.IN_MEMORY

    async def _init_filesystem(self):
        """Initialize filesystem-based messaging"""
        os.makedirs(self.fs_messenger_path, exist_ok=True)
        logger.info(f"Filesystem messenger initialized at {self.fs_messenger_path}")

    async def add_neuron(self, neuron_id: str, config: Dict) -> Neuron:
        """
        Add and initialize a new Neuron.

        Args:
            neuron_id: Unique identifier
            config: Neuron configuration

        Returns:
            Initialized Neuron instance
        """
        if neuron_id in self.neurons:
            logger.warning(f"Neuron {neuron_id} already exists, returning existing instance")
            return self.neurons[neuron_id]

        # Create Neuron
        neuron = Neuron(neuron_id=neuron_id, config=config)

        # Initialize
        await neuron.initialize()

        # Add to registry
        self.neurons[neuron_id] = neuron

        logger.info(f"Neuron {neuron_id} added to manager ({len(self.neurons)} total)")

        return neuron

    async def get_neuron(self, neuron_id: str) -> Optional[Neuron]:
        """
        Get Neuron instance by ID.

        Args:
            neuron_id: Neuron identifier

        Returns:
            Neuron instance or None if not found
        """
        return self.neurons.get(neuron_id)

    async def remove_neuron(self, neuron_id: str):
        """
        Remove and cleanup Neuron.

        Args:
            neuron_id: Neuron to remove
        """
        if neuron_id in self.neurons:
            # TODO: Cleanup resources (save state, close connections)
            del self.neurons[neuron_id]

            # Remove subscriptions
            if neuron_id in self.subscriptions:
                del self.subscriptions[neuron_id]

            logger.info(f"Neuron {neuron_id} removed from manager")

    async def send_message(
        self,
        from_neuron_id: str,
        to_neuron_id: str,
        message: Dict[str, Any]
    ):
        """
        Send message from one Neuron to another.

        Args:
            from_neuron_id: Sender Neuron ID
            to_neuron_id: Recipient Neuron ID
            message: Message payload
        """
        envelope = {
            "from": from_neuron_id,
            "to": to_neuron_id,
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        }

        # Route based on messenger type
        if self.messenger_type == MessengerType.IN_MEMORY:
            await self._send_local(envelope)
        elif self.messenger_type == MessengerType.REDIS:
            await self._send_redis(envelope)
        elif self.messenger_type == MessengerType.FILE_SYSTEM:
            await self._send_filesystem(envelope)

    async def _send_local(self, envelope: Dict):
        """Send message via in-memory queue (fast)"""
        await self.message_queue.put(envelope)
        logger.debug(f"Message queued: {envelope['from']} -> {envelope['to']}")

    async def _send_redis(self, envelope: Dict):
        """Send message via Redis pub/sub"""
        if not self.redis_client:
            logger.error("Redis client not initialized")
            return

        try:
            channel = f"neuron:{envelope['to']}"
            await self.redis_client.publish(
                channel,
                json.dumps(envelope)
            )
            logger.debug(f"Message sent via Redis: {envelope['from']} -> {envelope['to']}")

        except Exception as e:
            logger.error(f"Redis send failed: {e}")

    async def _send_filesystem(self, envelope: Dict):
        """Send message via shared filesystem"""
        try:
            # Create message file
            msg_filename = f"{envelope['to']}_{datetime.utcnow().timestamp()}.json"
            msg_path = os.path.join(self.fs_messenger_path, msg_filename)

            with open(msg_path, 'w') as f:
                json.dump(envelope, f)

            logger.debug(f"Message written to filesystem: {msg_filename}")

        except Exception as e:
            logger.error(f"Filesystem send failed: {e}")

    async def _process_messages(self):
        """Process messages from in-memory queue"""
        logger.info("Message processor started")

        while True:
            try:
                # Get message from queue
                envelope = await self.message_queue.get()

                to_neuron_id = envelope["to"]

                # Check if recipient is local
                if to_neuron_id in self.neurons:
                    neuron = self.neurons[to_neuron_id]

                    # Deliver message
                    try:
                        await neuron.receive_message(envelope["message"])
                        logger.debug(f"Message delivered to {to_neuron_id}")

                    except Exception as e:
                        logger.error(f"Message delivery failed for {to_neuron_id}: {e}")
                else:
                    logger.warning(f"Neuron {to_neuron_id} not found locally")

                self.message_queue.task_done()

            except Exception as e:
                logger.error(f"Message processing error: {e}")
                await asyncio.sleep(1)  # Backoff on error

    async def broadcast(self, from_neuron_id: str, event_type: str, data: Dict):
        """
        Broadcast event to all subscribed neurons.

        Args:
            from_neuron_id: Sender
            event_type: Event type (e.g., 'task_completed')
            data: Event data
        """
        message = {
            "type": event_type,
            "data": data
        }

        # Send to all subscribed neurons
        for neuron_id, subscribed_events in self.subscriptions.items():
            if event_type in subscribed_events:
                await self.send_message(from_neuron_id, neuron_id, message)

    async def subscribe(self, neuron_id: str, event_types: List[str]):
        """
        Subscribe neuron to event types.

        Args:
            neuron_id: Neuron to subscribe
            event_types: List of event types to subscribe to
        """
        if neuron_id not in self.subscriptions:
            self.subscriptions[neuron_id] = []

        for event_type in event_types:
            if event_type not in self.subscriptions[neuron_id]:
                self.subscriptions[neuron_id].append(event_type)

        logger.info(f"Neuron {neuron_id} subscribed to {event_types}")

    def get_all_neurons(self) -> List[Dict]:
        """
        Get status of all active neurons.

        Returns:
            List of neuron status dicts
        """
        return [
            neuron.get_status()
            for neuron in self.neurons.values()
        ]

    def get_stats(self) -> Dict:
        """Get manager statistics"""
        return {
            "total_neurons": len(self.neurons),
            "active_neurons": sum(1 for n in self.neurons.values() if n.state.value == "idle"),
            "messenger_type": self.messenger_type.value,
            "message_queue_size": self.message_queue.qsize() if self.messenger_type == MessengerType.IN_MEMORY else 0,
            "total_subscriptions": sum(len(events) for events in self.subscriptions.values())
        }


# Global manager instance (singleton)
_global_manager: Optional[NeuronManager] = None


async def get_neuron_manager() -> NeuronManager:
    """
    Get global NeuronManager instance.

    Returns:
        Singleton NeuronManager
    """
    global _global_manager

    if _global_manager is None:
        # Determine messenger type from settings
        messenger_type = MessengerType.IN_MEMORY

        # Use Redis if available in production
        if settings.ENVIRONMENT == "production" and settings.REDIS_URL:
            messenger_type = MessengerType.REDIS

        _global_manager = NeuronManager(messenger_type=messenger_type)
        await _global_manager.initialize()

    return _global_manager
