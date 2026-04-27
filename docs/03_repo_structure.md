# 03 – Repository & Folder Structure Guide

This document defines the **monorepo structure** for the Nexus-style voice-first assistant. It follows current guidance for AI-heavy Python projects and monorepos: one repo, clear domains (frontend, backend, agents, docs), and consistent naming and boundaries.[web:329][web:318][web:326][web:327]

It also defines how to maintain a **CHANGELOG** following the "Keep a Changelog" format.[web:334][web:330]

---

## 1. Top-level layout

Use a **single monorepo**:

```text
nexus/
  backend/
  windows_agent/
  frontend/
  docs/
  scripts/
  .env.example
  CHANGELOG.md
  README.md
```

Reasoning:
- Monorepo keeps frontend, backend, and agent code in one place, which is easier for AI tools to navigate and keeps context in one repo.[web:329][web:333]
- Each major piece gets its own top-level directory.

---

## 2. Backend structure (Next.js API Routes)

Backend logic is co-located with the frontend in a Next.js App Router structure.

```text
frontend/
  src/
    app/
      api/             # Next.js REST endpoints
        chat/          # Text messaging endpoints
        stream/        # GetStream token & voice session orchestration
        suggestions/   # AI search suggestions
    lib/
      db/              # Drizzle ORM schemas & clients
      services/        # External integrations (Stream, LLMs)
    hooks/             # React Query hooks calling the API
```

Guidelines:
- `api/` = incoming HTTP surfaces and background promises.
- `lib/services/` = external dependencies (Stream, Groq, DB).
- `lib/db/` = data models and schemas only.

This aligns with a simpler, solo-dev friendly architecture where the frontend and backend live in the same repository. Background jobs (Celery/Redis) are deferred to Future / v2 if required.

---

## 3. Windows agent structure (Python)

A separate package focused on Windows automation.

```text
windows_agent/
  pyproject.toml / requirements.txt
  src/
    windows_agent/
      __init__.py
      server.py           # HTTP/WS server on localhost
      main.py             # entry point (if run as script/exe)
      handlers/
        __init__.py
        apps.py           # open_app, focus_app, close_app
        files.py          # create_folder, move, copy, delete (with policy)
        input.py          # type_text, key combos
      policy.py           # safety rules
      models.py           # request/response schemas
      utils.py            # shared helpers
  tests/
    test_apps.py
    test_files.py
    test_input.py

```

Guidelines:
- **Use `pywinauto`** only inside `handlers/` and `policy.py`.[web:52][web:331][web:335]
- `server.py` should be thin: parse request, call handler, format response.
- `policy.py` enforces safe vs sensitive actions.

---

## 4. Frontend structure (Next.js)

Next.js app for UI; Tauri can later wrap this.

```text
frontend/
  package.json
  pnpm-lock.yaml
  next.config.js
  src/
    app/ or pages/
      layout.tsx
      page.tsx
      api/           # optional Next route handlers (not core backend)
    components/
      VoiceButton.tsx
      ChatWindow.tsx
      TaskList.tsx
      SettingsPanel.tsx
    hooks/
      useVoiceSession.ts
      useTasks.ts
    lib/
      apiClient.ts   # fetch wrapper for backend REST
      config.ts
    styles/
      globals.css
  public/
    icons/
    manifest.json
```

Guidelines:
- **Use pnpm** as the package manager for the frontend.
- Keep business logic out of components; use hooks and `lib/` helpers.[web:333]
- All calls to backend go through `lib/apiClient.ts`.
- Voice-related UI logic goes through `useVoiceSession` hook.

---

## 5. Docs structure

Central place for all markdown docs we’ve been generating.

```text
docs/
  01_idea_problem.md
  02_prd_master.md
  03_repo_structure.md        # this file
  04_feature_specs.md
  05_db_schema_data_model.md
  06_api_contract.md
  07_architecture_doc.md
  ai_context.md
  /assets
    diagrams/                 # exported Excalidraw diagrams
```

Guidelines:
- Keep file names numbered and stable for easy reference in conversations.
- Store exported Excalidraw diagrams in `docs/assets/diagrams/`.

---

## 6. Scripts

General automation, not product code.

```text
scripts/
  dev_backend.sh
  dev_frontend.sh
  format_backend.sh
  format_frontend.sh
  run_tests.sh
```

Keep scripts small and focused.

---

## 7. CHANGELOG

### 7.1 Location and format

- File: `CHANGELOG.md` at repo root.
- Format: **Keep a Changelog 1.0.0** (Unreleased section, then versioned sections).[web:334][web:330]

Structure:

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- 

### Changed
- 

### Fixed
- 

## [0.1.0] - 2026-04-24

### Added
- Initial repo structure (backend, windows_agent, frontend, docs).
- Core docs: PRD, architecture, feature specs, schema, API, AI context.
```

Guidelines from changelog and API tooling docs:
- Maintain a human-readable changelog, not a dump of git commits.[web:334]
- Group changes by **Added**, **Changed**, **Fixed**, **Deprecated**, etc.[web:334][web:330]

### 7.2 Process for updates

- For each meaningful change, update `CHANGELOG.md` under `[Unreleased]`.
- On release, move relevant bullets into a new version section and set date.
- Keep sections short but specific.

---

## 8. Repo usage with AI tools

When using AI coding tools (Cursor, Perplexity, Claude, etc.):

- Always load:
  - `docs/02_prd_master.md`
  - `docs/07_architecture_doc.md`
  - `docs/04_feature_specs.md`
  - `docs/ai_context.md`
- Keep new code inside the existing structure (backend/core, backend/services, windows_agent/handlers, etc.).
- When adding new capabilities, update docs (PRD/architecture/specs) first, then add new files to the appropriate folder.

This structure follows advice from recent guides on multi-agent and AI project structure: keep agents, actions/tools, core logic, and HTTP interfaces separated, and document the structure clearly for humans and AI.[web:327][web:328][web:318][web:326]
