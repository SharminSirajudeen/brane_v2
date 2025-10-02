"""
Memory Consolidation System - Prevents Knowledge Degradation

This system uses the connected LLM to periodically:
1. Compress episodic memories (L2)
2. Update semantic knowledge graph (L3)
3. Refine procedural workflows (L4)
4. Detect and resolve contradictions
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class MemoryConsolidator:
    """
    Consolidates neuron memory to prevent degradation.
    Runs periodically based on interaction count or time.
    """

    def __init__(
        self,
        neuron,
        consolidation_threshold: int = 100,  # Consolidate every N interactions
        max_l2_size: int = 50  # Max episodic memories before compression
    ):
        self.neuron = neuron
        self.consolidation_threshold = consolidation_threshold
        self.max_l2_size = max_l2_size
        self.last_consolidation = datetime.utcnow()
        self.interactions_since_consolidation = 0

    def should_consolidate(self) -> bool:
        """Check if consolidation is needed"""
        # Consolidate if:
        # 1. Hit interaction threshold
        # 2. L2 memory is too large
        # 3. Been more than 24 hours
        time_since = datetime.utcnow() - self.last_consolidation

        return (
            self.interactions_since_consolidation >= self.consolidation_threshold
            or len(self.neuron.memory.episodic_memory) > self.max_l2_size
            or time_since > timedelta(hours=24)
        )

    async def consolidate(self) -> Dict[str, Any]:
        """
        Run full memory consolidation.
        Returns stats about what was consolidated.
        """
        logger.info(f"Starting memory consolidation for neuron {self.neuron.id}")

        stats = {
            "l1_before": len(self.neuron.memory.working_memory),
            "l2_before": len(self.neuron.memory.episodic_memory),
            "l3_before": len(self.neuron.memory.semantic_memory),
            "l4_before": len(self.neuron.memory.procedural_memory),
            "timestamp": datetime.utcnow().isoformat()
        }

        try:
            # Step 1: Compress L1 → L2 (Working → Episodic)
            await self._compress_working_memory()

            # Step 2: Consolidate L2 (Remove duplicates, summarize)
            await self._consolidate_episodic_memory()

            # Step 3: Extract L3 (Build semantic knowledge graph)
            await self._extract_semantic_knowledge()

            # Step 4: Learn L4 (Detect procedural patterns)
            await self._learn_procedures()

            # Step 5: Detect contradictions
            await self._resolve_contradictions()

            stats.update({
                "l1_after": len(self.neuron.memory.working_memory),
                "l2_after": len(self.neuron.memory.episodic_memory),
                "l3_after": len(self.neuron.memory.semantic_memory),
                "l4_after": len(self.neuron.memory.procedural_memory),
                "success": True
            })

            self.last_consolidation = datetime.utcnow()
            self.interactions_since_consolidation = 0

            logger.info(f"Consolidation complete: {stats}")
            return stats

        except Exception as e:
            logger.error(f"Consolidation failed: {e}", exc_info=True)
            stats["success"] = False
            stats["error"] = str(e)
            return stats

    async def _compress_working_memory(self):
        """Compress L1 working memory into L2 episodic summaries"""
        if len(self.neuron.memory.working_memory) < 5:
            return  # Not enough to compress

        # Get recent interactions
        recent = self.neuron.memory.working_memory[-10:]

        # Ask LLM to summarize
        prompt = f"""
You are maintaining long-term memory for an AI assistant.

Summarize the following 10 recent interactions into a concise episodic memory:
- Focus on key facts, user preferences, and important context
- Remove redundant information
- Keep specific details that might be referenced later

Interactions:
{self._format_interactions(recent)}

Provide a 2-3 sentence summary.
"""

        summary = await self._ask_llm(prompt)

        # Add to episodic memory
        self.neuron.memory.episodic_memory.append({
            "summary": summary,
            "timestamp": datetime.utcnow().isoformat(),
            "interaction_count": len(recent)
        })

        # Clear compressed working memory (keep last 5 for continuity)
        self.neuron.memory.working_memory = self.neuron.memory.working_memory[-5:]

    async def _consolidate_episodic_memory(self):
        """Consolidate L2 episodic memory (remove duplicates, merge related)"""
        if len(self.neuron.memory.episodic_memory) <= 10:
            return

        # Get all episodic memories
        episodes = self.neuron.memory.episodic_memory

        prompt = f"""
You are maintaining episodic memory for an AI assistant.

Review these {len(episodes)} memory summaries and:
1. Remove duplicate information
2. Merge related episodes
3. Flag outdated facts
4. Consolidate into max 20 entries

Episodic Memories:
{self._format_episodes(episodes)}

Return a JSON array of consolidated memories:
[
  {{"summary": "...", "importance": 1-10}},
  ...
]
"""

        consolidated_json = await self._ask_llm(prompt)

        # Parse and update (with error handling)
        try:
            import json
            consolidated = json.loads(consolidated_json)
            self.neuron.memory.episodic_memory = consolidated[:20]  # Keep top 20
        except Exception as e:
            logger.error(f"Failed to parse consolidated memories: {e}")

    async def _extract_semantic_knowledge(self):
        """Extract L3 semantic knowledge (entities, concepts, facts)"""
        # Get recent episodic memories
        recent_episodes = self.neuron.memory.episodic_memory[-10:]

        prompt = f"""
Extract key knowledge from these memory summaries.

Format as a knowledge graph with entities and relationships:
{{
  "entities": {{"entity_name": "description"}},
  "facts": ["fact 1", "fact 2"],
  "preferences": {{"category": "preference"}}
}}

Memories:
{self._format_episodes(recent_episodes)}
"""

        knowledge_json = await self._ask_llm(prompt)

        try:
            import json
            knowledge = json.loads(knowledge_json)

            # Merge with existing semantic memory
            if "entities" in knowledge:
                self.neuron.memory.semantic_memory.setdefault("entities", {})
                self.neuron.memory.semantic_memory["entities"].update(knowledge["entities"])

            if "facts" in knowledge:
                self.neuron.memory.semantic_memory.setdefault("facts", [])
                self.neuron.memory.semantic_memory["facts"].extend(knowledge["facts"])

            if "preferences" in knowledge:
                self.neuron.memory.semantic_memory.setdefault("preferences", {})
                self.neuron.memory.semantic_memory["preferences"].update(knowledge["preferences"])

        except Exception as e:
            logger.error(f"Failed to extract semantic knowledge: {e}")

    async def _learn_procedures(self):
        """Learn L4 procedural workflows (detect patterns)"""
        if len(self.neuron.memory.working_memory) < 10:
            return

        recent = self.neuron.memory.working_memory[-20:]

        prompt = f"""
Analyze these interactions to detect procedural patterns.

Look for:
- Common workflows (e.g., "User always asks X then Y")
- Problem-solving sequences
- Preferred interaction styles

Interactions:
{self._format_interactions(recent)}

Return workflows as JSON:
{{
  "workflows": [
    {{"name": "...", "steps": ["step1", "step2"], "frequency": "high/medium/low"}}
  ]
}}
"""

        workflows_json = await self._ask_llm(prompt)

        try:
            import json
            workflows = json.loads(workflows_json)

            self.neuron.memory.procedural_memory.setdefault("workflows", [])
            self.neuron.memory.procedural_memory["workflows"].extend(workflows.get("workflows", []))

        except Exception as e:
            logger.error(f"Failed to learn procedures: {e}")

    async def _resolve_contradictions(self):
        """Detect and resolve contradicting facts in memory"""
        facts = self.neuron.memory.semantic_memory.get("facts", [])

        if len(facts) < 5:
            return

        prompt = f"""
Review these facts for contradictions or outdated information:

{chr(10).join(f"- {fact}" for fact in facts)}

Identify:
1. Contradictions (fact A vs fact B)
2. Outdated facts (based on recency)
3. Validated facts (no issues)

Return JSON:
{{
  "contradictions": [
    {{"fact1": "...", "fact2": "...", "resolution": "..."}}
  ],
  "validated_facts": ["fact1", "fact2"],
  "outdated_facts": ["old_fact1"]
}}
"""

        resolution_json = await self._ask_llm(prompt)

        try:
            import json
            resolution = json.loads(resolution_json)

            # Keep only validated facts + resolutions
            validated = resolution.get("validated_facts", [])
            resolutions = [r["resolution"] for r in resolution.get("contradictions", [])]

            self.neuron.memory.semantic_memory["facts"] = validated + resolutions

        except Exception as e:
            logger.error(f"Failed to resolve contradictions: {e}")

    # Helper methods

    async def _ask_llm(self, prompt: str) -> str:
        """Use the neuron's LLM to process memory"""
        if not self.neuron.llm_broker:
            raise ValueError("LLM broker not initialized")

        response = ""
        async for chunk in self.neuron.llm_broker.stream(
            prompt=prompt,
            tools=[],
            max_tokens=2000
        ):
            response += chunk

        return response.strip()

    def _format_interactions(self, interactions: List[Dict]) -> str:
        """Format interactions for LLM prompt"""
        formatted = []
        for i, interaction in enumerate(interactions, 1):
            formatted.append(
                f"{i}. User: {interaction.get('user', 'N/A')}\n"
                f"   Assistant: {interaction.get('assistant', 'N/A')}"
            )
        return "\n".join(formatted)

    def _format_episodes(self, episodes: List[Dict]) -> str:
        """Format episodic memories for LLM prompt"""
        formatted = []
        for i, episode in enumerate(episodes, 1):
            summary = episode.get("summary", episode) if isinstance(episode, dict) else episode
            formatted.append(f"{i}. {summary}")
        return "\n".join(formatted)

    def record_interaction(self):
        """Call this after each chat interaction"""
        self.interactions_since_consolidation += 1
