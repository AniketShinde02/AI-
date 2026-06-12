# Codebase Scan Log - 2026-05-03 17:34:42

## System Components

### backend\src\backend\main.py
- class: VoiceSessionRequest
- function: startup_event
- function: health_check
- function: get_voice_session
- function: stream_voice_session
- function: _handle_voice_session
- route: get /health
- route: post /voice/session
- route: post /calls/{call_type}/{session_id}/sessions

### backend\src\backend\config\settings.py
- class: Settings
- function: GETSTREAM_API_KEY
- function: GETSTREAM_API_SECRET

### backend\src\backend\core\diagnostics.py
- function: check_environment

### backend\src\backend\core\firebase_db.py
- class: FirebaseDB
- function: get_db
- function: get_db

### backend\src\backend\services\memory.py
- class: MemoryService
- function: __init__
- function: db
- function: save_interaction
- function: get_recent_context
- function: save_task
- function: save_note

### backend\src\backend\services\profile.py
- class: ProfileService
- function: __init__
- function: get_profile
- function: upsert_profile

### backend\src\backend\services\task.py
- class: TaskService
- function: __init__
- function: create_task
- function: get_user_tasks
- function: batch_update_status

### backend\src\backend\voice\groq_llm.py
- class: GroqLLM
- function: __init__
- function: simple_response
- function: close

### backend\src\backend\voice\local_worker.py
- function: generate_speech
- function: health
- function: list_voices
- route: post /tts
- route: get /health
- route: get /voices

### backend\src\backend\voice\orchestrator.py
- class: NexusVoiceOrchestrator
- function: __init__
- function: create_agent
- function: _broadcast_logs_to_call
- function: join_call
- function: on_custom_event
- function: start_session

### backend\src\backend\voice\providers.py
- class: GroqSTT
- class: SpeechmaticsSTT
- class: SpeechmaticsTTS
- class: CartesiaTTS
- class: LocalKokoroTTS
- class: NullSTT
- class: LogBroadcaster
- function: __init__
- function: transcribe
- function: __init__
- function: transcribe
- function: msg_handler
- function: __init__
- function: generate
- function: __init__
- function: generate
- function: __init__
- function: generate
- function: transcribe
- function: __init__
- function: emit
- function: nexus_log

### backend\src\backend\voice\session.py
- class: VoiceSessionManager
- function: __init__
- function: create_session

### backend\src\backend\voice\tools\nexus_tools.py
- function: run_command
- function: open_application
- function: create_task
- function: create_note
- function: web_search

### backend\voice_agent\main.py
- function: greeter
- function: on_call_join
- function: on_event
- function: create_agent
- function: voice_session
- function: main
- route: post /voice/session

### backend\voice_agent\test_groq.py
- function: test

### backend\voice_agent\test_tts.py
- function: test

### backend\voice_agent\core\call_manager.py
- function: join_and_run_agent

### backend\voice_agent\core\concurrency.py
- function: get_semaphore
- function: acquire_call_slot
- function: release_call_slot

### backend\voice_agent\core\memory.py
- class: MemoryEngine
- function: __init__
- function: save_interaction
- function: get_recent_context
- function: update_profile
- function: get_user_profile
- function: save_task
- function: save_note

### backend\voice_agent\core\usage.py
- class: UsageMonitor
- function: __init__
- function: record_stt
- function: record_tts
- function: record_llm
- function: get_report
- function: calculate_cost

### backend\voice_agent\providers\llm.py
- class: GroqLLM
- function: __init__
- function: simple_response
- function: _convert_tools_to_provider_format
- function: _extract_tool_calls_from_response

### backend\voice_agent\providers\stt.py
- class: GroqSTT
- function: __init__
- function: process_audio
- function: _transcribe
- function: close

### backend\voice_agent\providers\tts.py
- class: KokoroTTS
- function: __init__
- function: stream_audio
- function: _generator
- function: stop_audio
- function: close

### backend\voice_agent\tools\memory_tools.py
- function: update_preferences

### backend\voice_agent\tools\system.py
- function: run_command
- function: open_application

### backend\voice_agent\tools\task_tools.py
- function: create_task
- function: create_note

### frontend\src\app\page.tsx
- interface: Task
- interface: Note

### frontend\src\components\ErrorBoundary.tsx
- interface: Props
- interface: State

### frontend\src\components\SystemLogs.tsx
- interface: SystemLogsProps

### frontend\src\contexts\NexusContext.tsx
- interface: Message
- interface: NexusContextType

### frontend\src\hooks\useHealthCheck.ts
- hook: useHealthCheck

### frontend\src\hooks\useNexusChat.ts
- hook: useNexusChat

### frontend\src\hooks\useNexusVoice.ts
- hook: useNexusVoice

### frontend\src\lib\features.ts
- hook: useFeature

### frontend\src\lib\logStore.ts
- interface: NexusLog

### frontend\src\lib\trpc\router.ts
- trpc: getSuggestions
- trpc: chat
- trpc: getVoiceSession

### them\generator.py
- function: scan_codebase
