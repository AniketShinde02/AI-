import asyncio
import logging
from typing import Dict, Any

from core.planner.graph import TaskGraph, ExecutionNode
from core.workspace import workspace_manager
from core.executors.desktop_executor import DesktopExecutor
from core.executors.browser_executor import BrowserExecutor
from core.executors.vision_executor import VisionExecutor
from core.executors.memory_executor import MemoryExecutor
from core.executors.research_executor import ResearchExecutor
from core.executors.verification_executor import VerificationExecutor
from core.executors.recovery_executor import RecoveryExecutor

# Global Executor Registry
EXECUTOR_REGISTRY = {}

def get_executor(capability: str):
    if not EXECUTOR_REGISTRY:
        # Lazy initialization
        executors = [
            DesktopExecutor(), BrowserExecutor(), VisionExecutor(),
            MemoryExecutor(), ResearchExecutor(), VerificationExecutor(),
            RecoveryExecutor()
        ]
        for ex in executors:
            for cap in ex.get_capabilities():
                EXECUTOR_REGISTRY[cap] = ex
    return EXECUTOR_REGISTRY.get(capability)

logger = logging.getLogger("nexus.planner.executor")


class ExecutionEngine:
    """
    Traverses and executes a TaskGraph deterministically.
    Handles dependency resolution, hook dispatch, global timeouts, and node recovery.
    """

    def __init__(self, session_id: str):
        self.session_id = session_id

    async def execute_graph(self, graph: TaskGraph) -> Dict[str, Any]:
        logger.info(f"🚀 [Orchestrator] Starting Graph '{graph.graph_id}' for goal: {graph.goal}")
        
        node_states = {n.id: "PENDING" for n in graph.nodes}
        node_attempts = {n.id: 0 for n in graph.nodes}
        results_history = []
        
        while True:
            # Check if all nodes are SUCCESS or RECOVERED
            if all(state in ["SUCCESS", "RECOVERED"] for state in node_states.values()):
                break
                
            # Find nodes that are PENDING and have all dependencies marked SUCCESS or RECOVERED
            ready_nodes = [
                n for n in graph.nodes
                if node_states[n.id] == "PENDING" and all(node_states.get(dep) in ["SUCCESS", "RECOVERED"] for dep in n.dependencies)
            ]
            
            if not ready_nodes:
                # If no nodes are ready, check if any are FAILED or RUNNING
                if any(state == "RUNNING" for state in node_states.values()):
                    await asyncio.sleep(0.1)
                    continue
                if any(state == "FAILED" for state in node_states.values()):
                    logger.error("❌ [Orchestrator] Graph execution blocked due to failed dependencies.")
                    return {"success": False, "reason": "Dependency failure", "history": results_history}
                
                logger.error("❌ [Orchestrator] Graph cycle detected or unresolvable dependencies!")
                return {"success": False, "reason": "Graph cycle", "history": results_history}
            
            current_node = ready_nodes[0]
            node_states[current_node.id] = "RUNNING"
            node_attempts[current_node.id] += 1

            # Update WorkspaceManager — DAG state is now visible to all consumers
            workspace_manager.update_dag_node(
                graph_id=graph.graph_id,
                node_id=current_node.id,
                retries=node_attempts[current_node.id] - 1,
            )
            workspace_manager.update_execution(status="running", active_capability=current_node.tool_id)

            logger.info(f"▶️ [Orchestrator] Executing Node '{current_node.id}' (Attempt {node_attempts[current_node.id]})")
            
            try:
                res = await asyncio.wait_for(self._dispatch_node(current_node), timeout=120.0)
            except asyncio.TimeoutError:
                logger.error(f"❌ [Orchestrator] Node '{current_node.id}' TIMED OUT after 120s.")
                res = {"success": False, "verified": False, "error": "Execution Timeout", "result": ""}
            
            results_history.append({"node_id": current_node.id, "attempt": node_attempts[current_node.id], "result": res})
            
            if res.get("success"):
                logger.info(f"✅ [Orchestrator] Node '{current_node.id}' succeeded.")
                node_states[current_node.id] = "SUCCESS"
            else:
                if node_attempts[current_node.id] < current_node.retry_policy.max_attempts:
                    logger.warning(f"⚠️ [Orchestrator] Node '{current_node.id}' failed. Retrying (Attempt {node_attempts[current_node.id]}/{current_node.retry_policy.max_attempts}).")
                    node_states[current_node.id] = "PENDING"
                    await asyncio.sleep(current_node.retry_policy.backoff_factor ** node_attempts[current_node.id])
                else:
                    logger.warning(f"⚠️ [Orchestrator] Node '{current_node.id}' exhausted retries. Checking recovery path.")
                    node_states[current_node.id] = "FAILED"
                    
                    if current_node.recovery_node and current_node.recovery_node in node_states:
                        logger.info(f"♻️ [Orchestrator] Activating recovery node: '{current_node.recovery_node}'")
                        
                        # We mark the current node as RECOVERED so downstream dependencies can execute.
                        # BUT we must inject the recovery node into the dependencies of ALL downstream nodes.
                        node_states[current_node.id] = "RECOVERED"
                        
                        for n in graph.nodes:
                            if current_node.id in n.dependencies and current_node.recovery_node not in n.dependencies:
                                n.dependencies.append(current_node.recovery_node)
                    else:
                        logger.error(f"❌ [Orchestrator] No recovery path for '{current_node.id}'. Aborting graph.")
                        return {"success": False, "reason": f"Node {current_node.id} failed completely", "history": results_history}

        logger.info(f"🏁 [Orchestrator] Graph '{graph.graph_id}' completed successfully.")
        workspace_manager.update_dag_node(graph_id=None, node_id=None)
        workspace_manager.update_execution(status="completed")
        return {"success": True, "history": results_history}

    async def _dispatch_node(self, node: ExecutionNode) -> Dict[str, Any]:
        """Routes a node's tool_id to the correct Domain Executor."""
        tool = node.tool_id
        target = node.target
        params = node.params.copy()
        params["session_id"] = self.session_id
        params["target"] = target
        
        executor = get_executor(tool)
        if not executor:
            logger.warning(f"Unknown tool_id '{tool}' in graph. Failing node.")
            return {"success": False, "error": f"Unknown tool_id: {tool}", "verified": False}
            
        try:
            # PC capabilities receive visual verification fallback by default
            is_desktop = isinstance(executor, DesktopExecutor)
            return await executor.run(
                capability=tool, 
                params=params, 
                max_retries=node.retry_policy.max_attempts,
                visual_verification=is_desktop
            )
        except Exception as e:
            logger.error(f"Executor dispatch crashed for '{node.id}': {e}", exc_info=True)
            return {"success": False, "error": str(e), "verified": False}
