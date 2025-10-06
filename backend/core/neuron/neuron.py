"""
Neuron - AI Agent Core
Self-improving agent with 4-layer hierarchical memory
"""

import asyncio
import logging
import yaml
from typing import AsyncIterator, Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

from core.llm.broker import LLMBroker
from core.axon.axon import Axon
from core.synapse.synapse import Synapse
from core.neuron.memory_consolidator import MemoryConsolidator
from db.models import PrivacyTier

logger = logging.getLogger(__name__)


class NeuronState(str, Enum):
    """Neuron execution states"""
    IDLE = "idle"
    THINKING = "thinking"
    EXECUTING = "executing"
    ERROR = "error"


class HierarchicalMemory:
    """
    4-layer memory system for self-improvement.
    No fine-tuning required - learns from interactions.
    """

    def __init__(self):
        self.working_memory: List[Dict] = []  # L1: Recent context (last 10)
        self.episodic_memory: List[Dict] = []  # L2: Compressed summaries
        self.semantic_memory: Dict[str, Any] = {}  # L3: Knowledge graph
        self.procedural_memory: Dict[str, Any] = {}  # L4: Learned workflows

    def add_interaction(
        self,
        user_msg: str,
        assistant_msg: str,
        context: str,
        metadata: Optional[Dict] = None
    ):
        """Add new interaction and compact if needed"""
        interaction = {
            "user": user_msg,
            "assistant": assistant_msg,
            "context": context,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow().isoformat()
        }

        # L1: Working memory
        self.working_memory.append(interaction)

        # Compact if too large (keep only last 10)
        if len(self.working_memory) > 10:
            old_interactions = self.working_memory[:-10]
            summary = self._compress_interactions(old_interactions)
            self.episodic_memory.append(summary)
            self.working_memory = self.working_memory[-10:]

            logger.debug(f"Compacted {len(old_interactions)} interactions into episodic memory")

    def _compress_interactions(self, interactions: List[Dict]) -> Dict:
        """Compress multiple interactions into summary"""
        if not interactions:
            return {}

        # Extract key information
        topics = set()
        user_questions = []
        assistant_responses = []

        for i in interactions:
            user_questions.append(i["user"][:200])  # Truncate
            assistant_responses.append(i["assistant"][:200])

        return {
            "summary": f"Conversation covering: {', '.join(user_questions[:3])}...",
            "timestamp_range": (
                interactions[0]["timestamp"],
                interactions[-1]["timestamp"]
            ),
            "interaction_count": len(interactions),
            "created_at": datetime.utcnow().isoformat()
        }

    def get_context(self, max_items: int = 5) -> str:
        """Get recent context for LLM"""
        context_items = []

        # Add recent working memory
        for i in self.working_memory[-max_items:]:
            context_items.append(f"User: {i['user']}\nAssistant: {i['assistant']}")

        return "\n\n".join(context_items)


class Neuron:
    """
    AI Agent with self-improving memory.
    Model-agnostic via LLM Broker.
    """

    def __init__(self, neuron_id: str, config: Dict):
        """
        Initialize Neuron from configuration.

        Args:
            neuron_id: Unique identifier
            config: YAML configuration as dict
        """
        self.id = neuron_id
        self.config = config
        self.state = NeuronState.IDLE

        # Extract configuration
        self.metadata = config.get("metadata", {})
        self.name = self.metadata.get("name", "Unnamed Neuron")
        self.privacy_tier = PrivacyTier(config.get("privacy_tier", 0))

        # Components (initialized later)
        self.llm_broker: Optional[LLMBroker] = None
        self.axon: Optional[Axon] = None
        self.synapses: List[Synapse] = []
        self.memory = HierarchicalMemory()
        self.consolidator: Optional[MemoryConsolidator] = None

        logger.info(f"Neuron '{self.name}' created (ID: {self.id}, Tier: {self.privacy_tier})")

    async def initialize(self):
        """Initialize all components"""
        try:
            # 1. LLM Broker
            model_config = self.config.get("model", {})
            self.llm_broker = LLMBroker(model_config)
            await self.llm_broker.initialize()
            logger.info(f"Neuron '{self.name}': LLM Broker initialized")

            # 2. Axon (RAG)
            axon_config = self.config.get("axon", {})
            if axon_config.get("enabled"):
                self.axon = Axon(neuron_id=self.id, config=axon_config)
                await self.axon.load()
                logger.info(f"Neuron '{self.name}': Axon initialized")

            # 3. Synapses (Tools)
            tools_config = self.config.get("tools", [])
            for tool_config in tools_config:
                if tool_config.get("enabled"):
                    # TODO: Load synapse plugins dynamically
                    logger.debug(f"Synapse '{tool_config.get('id')}' registered")

            # 4. Memory Consolidator (anti-degradation)
            consolidation_config = self.config.get("consolidation", {})
            self.consolidator = MemoryConsolidator(
                neuron=self,
                consolidation_threshold=consolidation_config.get("threshold", 100),
                max_l2_size=consolidation_config.get("max_l2_size", 50)
            )
            logger.info(f"Neuron '{self.name}': Memory consolidator initialized")

            logger.info(f"Neuron '{self.name}' fully initialized")

        except Exception as e:
            self.state = NeuronState.ERROR
            logger.error(f"Neuron '{self.name}' initialization failed: {e}")
            raise

    async def chat(
        self,
        user_message: str,
        user_id: str,
        session_id: str
    ) -> AsyncIterator[str]:
        """
        Main chat interface with streaming responses.

        Args:
            user_message: User's message
            user_id: User ID for audit logging
            session_id: Chat session ID

        Yields:
            Streaming response chunks
        """
        self.state = NeuronState.THINKING
        full_response = ""

        try:
            # 1. Privacy tier check & PII/PHI redaction
            if self.privacy_tier == PrivacyTier.LOCAL:
                # TODO: Redact sensitive data using Presidio
                pass

            # 2. RAG augmentation
            context = ""
            if self.axon:
                relevant_docs = await self.axon.search(user_message, top_k=3)
                context = "\n\n".join([doc["text"] for doc in relevant_docs])
                logger.debug(f"RAG: Found {len(relevant_docs)} relevant documents")

            # 3. Build prompt with memory
            system_prompt = self.config.get("prompts", {}).get("system", "")
            memory_context = self.memory.get_context(max_items=3)

            full_prompt = self._build_prompt(
                system_prompt=system_prompt,
                memory_context=memory_context,
                rag_context=context,
                user_message=user_message
            )

            # 4. Tool definitions (LangChain + MCP)
            from api.tools import get_tools_for_llm
            langchain_tools = await get_tools_for_llm(self.config)

            # Convert LangChain tools to MCP format for LiteLLM
            tools = []
            for lc_tool in langchain_tools:
                tools.append({
                    "name": lc_tool.name,
                    "description": lc_tool.description,
                    "parameters": lc_tool.args if hasattr(lc_tool, 'args') else {}
                })

            # 5. LLM call (streaming)
            max_tokens = self.config.get("max_tokens", 2048)

            async for chunk in self.llm_broker.stream(
                prompt=full_prompt,
                tools=tools,
                max_tokens=max_tokens
            ):
                full_response += chunk
                yield chunk

            # 6. Update memory
            self.memory.add_interaction(
                user_msg=user_message,
                assistant_msg=full_response,
                context=context,
                metadata={
                    "session_id": session_id,
                    "model": self.llm_broker.model,
                    "privacy_tier": self.privacy_tier.value
                }
            )

            # 7. Check if consolidation needed (anti-degradation)
            if self.consolidator:
                self.consolidator.record_interaction()

                if self.consolidator.should_consolidate():
                    logger.info(f"Neuron '{self.name}': Triggering memory consolidation")
                    # Run consolidation in background (don't block response)
                    asyncio.create_task(self._run_consolidation())

            self.state = NeuronState.IDLE
            logger.info(f"Neuron '{self.name}': Chat completed")

        except Exception as e:
            self.state = NeuronState.ERROR
            logger.error(f"Neuron '{self.name}' chat error: {e}")
            yield f"\n\n[Error: {str(e)}]"

    async def _run_consolidation(self):
        """Run memory consolidation in background"""
        try:
            stats = await self.consolidator.consolidate()
            logger.info(f"Neuron '{self.name}': Consolidation stats: {stats}")
        except Exception as e:
            logger.error(f"Neuron '{self.name}': Consolidation failed: {e}")

    def _build_prompt(
        self,
        system_prompt: str,
        memory_context: str,
        rag_context: str,
        user_message: str
    ) -> str:
        """Build complete prompt with all context"""
        parts = []

        if system_prompt:
            parts.append(f"System: {system_prompt}")

        if memory_context:
            parts.append(f"Previous conversation:\n{memory_context}")

        if rag_context:
            parts.append(f"Relevant information:\n{rag_context}")

        parts.append(f"User: {user_message}")

        return "\n\n".join(parts)

    async def receive_message(self, message: Dict):
        """
        Handle inter-Neuron messages.
        Used by NeuronManager for multi-agent orchestration.
        """
        msg_type = message.get("type")

        if msg_type == "task_request":
            # Execute delegated task
            task = message.get("task")
            logger.info(f"Neuron '{self.name}': Received task '{task}'")

            # TODO: Execute task and return result
            result = {"status": "completed", "result": "Task completed"}

            return result

        elif msg_type == "status_check":
            return {
                "neuron_id": self.id,
                "name": self.name,
                "state": self.state.value,
                "privacy_tier": self.privacy_tier.value
            }

    def get_status(self) -> Dict:
        """Get current Neuron status"""
        return {
            "id": self.id,
            "name": self.name,
            "state": self.state.value,
            "privacy_tier": self.privacy_tier.value,
            "llm_initialized": self.llm_broker is not None,
            "axon_enabled": self.axon is not None,
            "synapses_count": len(self.synapses),
            "memory_size": len(self.memory.working_memory)
        }


def load_neuron_config(config_path: str) -> Dict:
    """
    Load Neuron configuration from YAML file.

    Args:
        config_path: Path to YAML config file

    Returns:
        Parsed configuration dict
    """
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # TODO: Validate against JSON Schema
    return config
