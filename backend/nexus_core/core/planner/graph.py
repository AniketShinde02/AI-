from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class RetryPolicy(BaseModel):
    """Defines how a node should automatically retry upon failure."""
    max_attempts: int = Field(default=3, description="Maximum number of attempts (1 initial + retries).")
    backoff_factor: float = Field(default=1.5, description="Multiplier for backoff delay between retries.")

class ExecutionNode(BaseModel):
    """
    A deterministic execution step in the Orchestrator DAG.
    Every node guarantees execution boundaries with verification and recovery paths.
    """
    id: str = Field(..., description="Unique identifier for this node in the graph.")
    tool_id: str = Field(..., description="The underlying tool capability to dispatch, e.g., 'browser_agentic_task', 'pc_open_app'.")
    target: str = Field(default="", description="The target or prompt for the tool.")
    params: Dict[str, Any] = Field(default_factory=dict, description="Additional context or parameters.")
    
    # DAG Topology
    dependencies: List[str] = Field(default_factory=list, description="IDs of nodes that must successfully complete before this node can run.")
    
    # State Constraints
    preconditions: List[str] = Field(default_factory=list, description="English descriptions of state required before execution.")
    verification_rule: str = Field(default="", description="English description of the expected state after successful execution.")
    
    # Resilience
    retry_policy: RetryPolicy = Field(default_factory=RetryPolicy)
    recovery_node: Optional[str] = Field(default=None, description="Node ID to jump to if all retries are exhausted.")

class TaskGraph(BaseModel):
    """
    The full Orchestrator DAG representing a multi-step user goal.
    """
    graph_id: str = Field(..., description="Unique identifier for the entire execution graph.")
    goal: str = Field(..., description="The user's original raw goal.")
    nodes: List[ExecutionNode] = Field(default_factory=list, description="All execution nodes.")

    def get_node(self, node_id: str) -> Optional[ExecutionNode]:
        for n in self.nodes:
            if n.id == node_id:
                return n
        return None

    def get_roots(self) -> List[ExecutionNode]:
        """Returns nodes with no dependencies (entry points)."""
        return [n for n in self.nodes if not n.dependencies]
