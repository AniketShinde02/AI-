"""
orchestrator/__init__.py
========================
Nexus Orchestrator Domain — Public API
"""
from core.orchestrator.registry_def import CAPABILITY_DEFINITIONS, CapabilityDef, _make_app_schema
from core.orchestrator.capabilities import registry, CapabilityRegistry
from core.orchestrator.swarm import swarm_manager, AgentSwarmManager

__all__ = [
    "CAPABILITY_DEFINITIONS",
    "CapabilityDef",
    "_make_app_schema",
    "registry",
    "CapabilityRegistry",
    "swarm_manager",
    "AgentSwarmManager"
]
