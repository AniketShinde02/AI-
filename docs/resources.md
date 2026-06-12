
# free-coding-models Integration Guide for Nexus 2.0

## Overview
[vava-nessa/free-coding-models](https://github.com/vava-nessa/free-coding-models) is an NPM CLI that benchmarks and routes to 158+ **free coding LLMs** from 23 providers. Live TUI for model discovery, proxy support.

**Stars**: 4.2K | **Forks**: 1.2K | **Active**: Weekly benchmarks (2026).

## Why Nexus 2.0
- **Latency**: <200ms models for <800ms TTFA
- **Cost**: $0 coding during dev/monetization
- **Routing**: Dynamic model selection per task type

## Installation
```bash
npm install -g free-coding-models
free-coding-models  # Launch TUI
```

## Top Models for Nexus (Coding Category)
| Model | Provider | Latency | HumanEval | Use Case |
|-------|----------|---------|-----------|----------|
| DeepSeek-Coder-V2-Lite | Together | 120ms | 78.5% | Agent scripts |
| Qwen2.5-Coder-7B | Groq | 85ms | 75.2% | Intent class |
| Devstral-Small | Mistral | 150ms | 72.1% | Debug/research |

## FastAPI Router Integration
```python
import subprocess
import json

async def get_best_model(prompt: str):
    result = subprocess.run([
        'free-coding-models', 'benchmark',
        '--prompt', prompt,
        '--top', '3', '--json'
    ], capture_output=True, text=True)
    return json.loads(result.stdout)[0]

# Usage in Nexus
model = await get_best_model('Classify Nexus browser task')
```

## Provider Setup (Free Tiers)
1. **Groq**: [console.groq.com](https://console.groq.com/keys) → Qwen/Llama3.3
2. **Together**: [together.ai](https://api.together.xyz/settings/api-keys) → DeepSeek
3. **Ollama**: [ollama.com](https://ollama.com/library/codellama) → Local

## Nexus Task Routing
```yaml
intent_classification: Qwen2.5-Groq (85ms)
browser_planning: DeepSeek-V2 (120ms)
code_generation: Devstral (150ms)
research: Llama3.3-70B (200ms)
```

## CLI Commands
```bash
# Benchmark Nexus prompt
free-coding-models benchmark --prompt 'Nexus task intent' --top 5

# TUI discovery
free-coding-models

# Proxy single call
free-coding-models proxy --model qwen2.5-coder --prompt 'FastAPI task'
```

## Dev Workflow
```
1. Benchmark 5 Nexus prompts → Pick top-3
2. Update llm_router.py with results
3. Antigravity: "Use free-coding-models top model for this"
4. Monitor latency dashboard
```

## Production Fallback
```python
async def nexus_llm(prompt: str, plan: str):
    if plan == 'free':
        model = await get_free_model(prompt)
        return free_proxy(model, prompt)
    return paid_openrouter(prompt)
```

## Cost Savings
| Users | Paid Cost | Free Cost |
|-------|-----------|-----------|
| 100 | $50/mo | $0 |
| 1K | $500/mo | $50 (Power tier) |

## Monitoring
- **Atlas Metrics**: Model latency p95
- **CLI Updates**: `npm update -g free-coding-models`

## Links
- Repo: [GitHub](https://github.com/vava-nessa/free-coding-models)
- NPM: [npmjs.com/package/free-coding-models](https://www.npmjs.com/package/free-coding-models)
- Providers: [Groq](https://groq.com), [Together](https://together.ai), [Ollama](https://ollama.com)
- Nexus Prompts Repo: Create `./prompts/nexus_benchmarks.json`

## Risks
- Rate limits → Multi-provider
- Hallucinations → HumanEval >75%
