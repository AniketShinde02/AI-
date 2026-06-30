"""
agent_swarm.py — Backward Compatibility Shim
============================================
DO NOT add logic here. All behavior lives in core/orchestrator/swarm.py.
"""
from core.orchestrator.swarm import swarm_manager, AgentSwarmManager

__all__ = ["swarm_manager", "AgentSwarmManager"]
