import json
import time
import logging
import asyncio
import re
from typing import Dict, Any, List, Optional

from core.database import db
from core.model_router import model_router, TaskClass
from core.workspace.broadcast import broadcast_workspace_state

logger = logging.getLogger("nexus.agent_swarm")

class AgentSwarmManager:
    """
    Manages the Multi-Agent Swarm Registry and sequential execution loop.
    Decomposes user requests, invokes specialized sub-agents, logs executions,
    and synthesizes results.
    """

    async def execute_swarm_task(self, goal: str, session_id: str = "default_session") -> Dict[str, Any]:
        logger.info(f"🤖 Starting swarm task: '{goal}' for session: {session_id}")
        
        # 1. Fetch available agents from SQLite
        all_agents = await db.get_agents()
        if not all_agents:
            logger.warning("⚠️ No agents found in registry. Running standard fallback chat.")
            fallback_res = await model_router.route_task(
                TaskClass.CHAT,
                system_prompt="You are parent_delegate, the orchestrator. Give a direct answer.",
                messages=[{"role": "user", "content": goal}]
            )
            return {"success": True, "result": fallback_res, "steps": []}

        # Ensure browser_agentic_task is available in the swarm registry
        if not any(a["id"] == "browser_agentic_task" for a in all_agents):
            all_agents.append({
                "id": "browser_agentic_task",
                "name": "Browser Agent",
                "description": "Multi-step browser automation agent. Navigates websites, clicks, types, and extracts page data.",
                "color": "#ff00ff",
                "status": "idle",
                "calls": 0,
                "runtime": "0.0s"
            })

        # Format agents for planning prompt
        agents_str = "\n".join([
            f"- {a['id']}: {a['description']} (status: {a['status']})"
            for a in all_agents if a['id'] != 'parent_delegate'
        ])

        # 2. Planning Phase via parent_delegate
        plan_prompt = f"""
You are the parent_delegate, the orchestrator of the Nexus Agent Swarm.
Your job is to break down the user's goal into a sequential plan of sub-tasks, assigning each sub-task to one of the available specialized agents.

Available Agents:
{agents_str}

User Goal:
"{goal}"

Your output must be a valid JSON array of step objects, containing only "agent_id" and "task" properties. E.g.:
[
  {{"agent_id": "query_memory", "task": "Search memory for user coding preferences"}},
  {{"agent_id": "browser_agentic_task", "task": "Open youtube, search for 'Zaalima', and click play"}},
  {{"agent_id": "web_search", "task": "Search DuckDuckGo for the latest Next.js 15 features"}}
]

Rules:
1. Choose only from the available agent_ids listed above. Do NOT invent new agent_ids.
2. The tasks should be clear, concise, and actionable by the sub-agents.
3. If a goal requires browser navigation, element interaction (clicking, form submission), or page state extraction on specific web applications (like Shopify dashboard or YouTube), you MUST output a step assigning 'browser_agentic_task' as the target sub-agent.
4. Output ONLY the raw JSON array. Do not include markdown code block formatting (like ```json) or explanations.
"""
        logger.info("📋 Planning steps via parent_delegate...")
        plan_res = await model_router.route_task(
            TaskClass.PLANNING,
            system_prompt="You are a precise JSON planning engine. Output only the JSON array.",
            messages=[{"role": "user", "content": plan_prompt}]
        )

        steps = self._parse_plan_json(plan_res)
        if not steps:
            logger.warning(f"⚠️ Failed to parse plan or plan empty. Raw response: {plan_res}")
            # Fallback to direct routing
            direct_res = await model_router.route_task(
                TaskClass.CHAT,
                system_prompt="You are parent_delegate. Synthesize a direct response to the user's goal.",
                messages=[{"role": "user", "content": goal}]
            )
            return {"success": True, "result": direct_res, "steps": []}

        logger.info(f"📋 Generated plan with {len(steps)} steps: {steps}")

        # 3. Execution Phase
        results_context = []
        executed_steps = []

        for idx, step in enumerate(steps):
            agent_id = step.get("agent_id")
            if not agent_id or not isinstance(agent_id, str):
                logger.warning(f"⚠️ Invalid agent_id in step: {step}")
                continue
            task_desc = step.get("task", "") or ""
            if not isinstance(task_desc, str):
                task_desc = str(task_desc)

            # Verify agent exists in registry
            agent_rec = next((a for a in all_agents if a["id"] == agent_id), None)
            if not agent_rec:
                logger.warning(f"⚠️ Planned agent '{agent_id}' not found in registry. Skipping.")
                continue

            logger.info(f"🚀 Running step {idx+1}/{len(steps)}: Agent={agent_id}, Task='{task_desc}'")

            # Update status to "active" and increment calls
            agent_rec["status"] = "active"
            agent_rec["calls"] += 1
            await db.update_agent(agent_id, agent_rec)

            # Broadcast status to UI
            await broadcast_workspace_state(
                active_capability=agent_id,
                status="running",
                current_task=task_desc
            )

            # Measure duration
            start_time = time.perf_counter()
            step_result = ""
            try:
                step_result = await self._dispatch_sub_agent(agent_id, task_desc, session_id)
            except Exception as e:
                logger.error(f"❌ Sub-agent '{agent_id}' execution failed: {e}", exc_info=True)
                step_result = f"Error: {str(e)}"
            
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            runtime_str = f"{elapsed_ms / 1000:.2f}s"

            # Log run details to database
            result_snippet = (step_result[:300] + "...") if len(step_result) > 300 else step_result
            await db.log_agent_run(agent_id, task_desc, result_snippet, elapsed_ms)

            # Set status back to "idle" and save runtime
            agent_rec["status"] = "idle"
            agent_rec["runtime"] = runtime_str
            await db.update_agent(agent_id, agent_rec)

            # Broadcast status update
            await broadcast_workspace_state(
                active_capability=agent_id,
                status="idle",
                execution_time=runtime_str,
                last_result=result_snippet
            )

            results_context.append(f"Step {idx+1} [Agent: {agent_id}]: {task_desc}\nResult: {step_result}")
            executed_steps.append({
                "agent_id": agent_id,
                "task": task_desc,
                "result": result_snippet,
                "duration_ms": elapsed_ms
            })

        # 4. Synthesis Phase via parent_delegate
        results_str = "\n\n".join(results_context)
        synthesis_prompt = f"""
You are parent_delegate, the orchestrator of the Nexus Agent Swarm.
You have executed a series of sub-agent tasks to address the user's goal.

User Goal: "{goal}"

Execution History and Results:
{"="*40}
{results_str}
{"="*40}

Please compile, summarize, and synthesize these findings into a final, user-friendly response.
"""
        logger.info("✍️ Synthesizing final response via parent_delegate...")
        final_answer = await model_router.route_task(
            TaskClass.CHAT,
            system_prompt="You are parent_delegate, a helpful synthesizing assistant.",
            messages=[{"role": "user", "content": synthesis_prompt}]
        )

        return {
            "success": True,
            "result": final_answer,
            "steps": executed_steps
        }

    async def _dispatch_sub_agent(self, agent_id: str, task: str, session_id: str) -> str:
        """Invokes the specific sub-agent handler asynchronously."""
        if agent_id == "browser_agentic_task":
            from core.browser_agent import browser_agent
            try:
                # BrowserAgent uses the isolated session_id profile internally
                res = await browser_agent.run_agentic_task(task, session_id=session_id)
                # run_agentic_task returns a dict {"success": bool, "result": str, ...}
                if isinstance(res, dict):
                    return str(res.get("result") or res.get("error") or res)
                return str(res)
            except Exception as e:
                logger.error(f"❌ Browser Agent failed on task '{task}': {e}", exc_info=True)
                return f"Browser Agent Error: {str(e)}"

        elif agent_id == "web_search":
            from tools.third_party_tools import search_web
            res = await search_web(task)
            return res.get("result") or f"Search failed: {res.get('error')}"

        elif agent_id == "query_memory":
            from core.lance_memory import get_memory
            mem = await get_memory()
            results = await mem.search_memory(task, limit=3)
            history = await db.get_session_history(session_id, limit=5)
            
            lines = ["Memory search results:"]
            for r in results:
                lines.append(f"- {r.get('text', '')} (meta: {r.get('metadata', '')})")
            lines.append("\nRecent conversation history:")
            for h in history:
                lines.append(f"- {h['role']}: {h['content']}")
            return "\n".join(lines)

        elif agent_id == "run_command":
            # Extract clean shell command
            extract_prompt = f"Extract only the exact Windows shell command to execute from this task description: '{task}'. Do not include quotes, comments, backticks, or explanations. E.g. for 'List files in project' return 'dir'."
            command = await model_router.route_task(
                TaskClass.FAST_ROUTING,
                system_prompt="You are a precise command extractor. Output only the raw shell command.",
                messages=[{"role": "user", "content": extract_prompt}]
            )
            command = command.strip().strip("`").strip()
            
            from core.guardrails import guardrails
            classification, reason = guardrails.scan_command(command)
            if classification == "BLOCKED":
                return f"Blocked: {reason}"
            elif classification == "RESTRICTED":
                authorized = await guardrails.request_authorization(session_id, command)
                if not authorized:
                    return "Unauthorized: User denied execution of command."

            try:
                proc = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30.0)
                res = stdout.decode().strip() or stderr.decode().strip() or "Success (No output)"
                return res[:2000]  # Cap length
            except Exception as e:
                return f"Error executing command: {str(e)}"

        elif agent_id == "rag_oracle":
            import core.rag_oracle as rag_oracle_module
            if rag_oracle_module.oracle_instance:
                res = await rag_oracle_module.oracle_instance.consult_oracle(task)
                return res.get("answer") or f"RAG consult failed: {res.get('error')}"
            return "Error: RAG Oracle not initialized."

        return f"Unknown agent ID: {agent_id}"

    def _parse_plan_json(self, plan_res: str) -> List[Dict[str, Any]]:
        """Extracts and parses the JSON plan array from LLM response."""
        match = re.search(r'\[\s*\{.*\}\s*\]', plan_res, re.DOTALL)
        text_to_parse = match.group(0) if match else plan_res
        try:
            return json.loads(text_to_parse)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse swarm plan JSON: {plan_res}")
            return []

swarm_manager = AgentSwarmManager()
