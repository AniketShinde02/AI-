"""
output_contract.py — Backward Compatibility Shim
================================================
DO NOT add logic here. All behavior lives in core/planner/contract.py.
"""
from core.planner.contract import scrub_output, scrub_and_log

__all__ = ["scrub_output", "scrub_and_log"]
