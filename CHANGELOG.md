# Changelog

All notable changes to this project will be documented in this file.

## [2026-06-19] — Shadow Army Agentic Strategy & Code Load Audit

### Author
- Antigravity AI
- Machine: JinWoo-PC (Local Developer Environment)

### Added
- Created comprehensive agentic browser and desktop strategy document in `C:/Users/JinWoo/.gemini/antigravity-ide/brain/4361a54f-fbaa-4440-8e5a-b112462127f6/browser_agentic_strategy.md`.
- Integrated **Solo Leveling "Shadow Monarch" & "Shadow Army" Tier System** mapping:
  - **Shadow Monarch (Jinwoo / User)**: Intent and high-risk safety gate approvals.
  - **Grand Marshal (Mistral Large)**: Macro plan orchestration (1 RPS throttle).
  - **Generals (Cerebras 120B)**: Micro-loop AXTree execution planner (1,000 RPM).
  - **Knights (Groq Llama 8B)**: Fast sub-second routing and JSON classification.
  - **Eyes (Gemini Flash)**: Multimodal screen verification and OCR.
  - **Infantry (Local System)**: Primitives, Playwright, RobotJS, and Local CLI scripts.
- Documented **Advanced Task Cards (Use Cards)** config schemas for Lead Generation & Outreach, Freelance Bidding, Social Media Posting, and Report Generation to prevent hardcoding.
- Outlined **Stealth Browser Architecture & Evasion Bottlenecks** (WebGL/Canvas spoofing, JA3/JA4 TLS profiles, Curve humanization, and High-DPI Coordinate scaling).

### Changed
- Analyzed and audited the code quality of `nexus_core/core/browser_agent.py` to identify current concurrent load limitations (currently single global instance bottleneck limits concurrency to exactly 1 active page).
- Revised fallback routing paths to leverage Cerebras 1,000 RPM capacity for high-density browser/PC command loops rather than stalling on Mistral 1 RPS limits.
