"""
task_cards.py — Backward Compatibility Shim
===========================================
DO NOT add logic here. All behavior lives in core/workspace/ux_cards.py.
"""
from core.workspace.ux_cards import TaskCardEngine, task_card_engine

__all__ = ["TaskCardEngine", "task_card_engine"]
