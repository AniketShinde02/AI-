import logging
from typing import Optional

import re
from pydantic import ValidationError
from core.model_router import model_router, TaskClass
from core.planner.graph import TaskGraph

logger = logging.getLogger("nexus.planner.compiler")

class PlannerCompiler:
    """
    Translates raw user goals into a deterministic Orchestrator TaskGraph (DAG).
    Uses Mistral-Large or Groq via model_router to generate strict JSON.
    """

    async def compile_goal(self, goal: str, session_id: str) -> Optional[TaskGraph]:
        logger.info(f"🧠 [PlannerCompiler] Compiling goal into DAG: '{goal}'")
        
        # 1. Provide available tools/capabilities to feed the LLM dynamically
        from core.database import db
        all_agents = await db.get_agents()
        capabilities = [
            "- pc_open_app (target: app name)",
            "- pc_type_text (target: text to type)",
            "- pc_press_shortcut (target: shortcut like 'enter', 'ctrl+c')",
            "- pc_close_app (target: app name)",
            "- pc_click (target: visual element to click)",
            "- browser_agentic_task (target: full natural language browser intent)",
            "- run_task_card (target: card ID)"
        ]
        
        if all_agents:
            capabilities.extend([f"- {a['id']} (target: {a['description']})" for a in all_agents if a['id'] != 'parent_delegate'])
            
        caps_str = "\n".join(capabilities)
        
        system_prompt = f"""
You are the Nexus V1.5 Orchestrator Task Planner.
Your job is to compile a raw user goal into a strict JSON Directed Acyclic Graph (DAG) representing an execution plan.

Available Tools:
{caps_str}

Rules:
1. You MUST output a SINGLE valid JSON object matching the TaskGraph schema.
2. Nodes represent execution steps. Each node must have a unique `id`, `tool_id`, `target`, and `dependencies`.
3. If a node must wait for another node to finish, add the previous node's `id` to the `dependencies` array.
4. `verification_rule` is an English string explaining what state proves the node succeeded.
5. `recovery_node` (optional) is the ID of the node to jump back to if this node fails completely.
6. Do NOT invent `tool_id`s outside of the Available Tools list.
7. Use 'browser_agentic_task' for ANY web interaction, providing the full browser intent as the `target`.
8. Do NOT use markdown code blocks (e.g., ```json). Output raw JSON.

Schema:
{{
  "graph_id": "string (unique)",
  "goal": "string (original user goal)",
  "nodes": [
    {{
      "id": "string",
      "tool_id": "string",
      "target": "string",
      "dependencies": ["string"],
      "preconditions": ["string"],
      "verification_rule": "string",
      "retry_policy": {{"max_attempts": 3, "backoff_factor": 1.5}},
      "recovery_node": null
    }}
  ]
}}
"""
        
        response = ""
        try:
            # Mistral-Large or top-tier model for robust JSON planning
            response = await model_router.route_task(
                task_class=TaskClass.PLANNING,
                system_prompt=system_prompt,
                messages=[{"role": "user", "content": f"Compile this goal: {goal}"}]
            )
            
            # Clean possible markdown
            if "```" in response:
                match = re.search(r'```(?:json)?\s*(\{.*\})\s*```', response, re.DOTALL)
                if match:
                    response = match.group(1)
            
            # Pydantic native validation
            graph = TaskGraph.model_validate_json(response.strip())
            
            logger.info(f"✅ [PlannerCompiler] Successfully compiled DAG with {len(graph.nodes)} nodes.")
            return graph
            
        except ValidationError as e:
            logger.error(f"❌ [PlannerCompiler] Pydantic schema validation failed: {e}\nRaw Response: {response}")
            return None
        except Exception as e:
            logger.error(f"❌ [PlannerCompiler] Compilation failed: {e}", exc_info=True)
            return None

planner_compiler = PlannerCompiler()
