# Nexus Browser Skills Library

This document defines the official Browser automation skills supported by Nexus.
These skills execute within the isolated `Playwright` environment managed by the `BrowserAgent`.

## 1. Navigation (`browser_open_url`)
- **Required Capabilities**: `browser_open_url`
- **Preconditions**: Valid URL.
- **Verification**: Verifies `current_url` in `BrowserMemory` post-navigation.
- **Recovery**: Retries if navigation times out.
- **Example Prompt**: "Go to github.com"

## 2. Extraction & Interaction (`browser_click`, `browser_type`, `browser_submit`, `browser_extract`)
- **Required Capabilities**: `browser_click`, `browser_type`, `browser_submit`, `browser_extract`
- **Preconditions**: Element exists in the DOM or Accessibility Tree snapshot.
- **Verification**: Checks if element state changes or navigation occurs.
- **Recovery**: Self-heals using fuzzy text matching or generic xpath fallbacks.
- **Example Prompt**: "Click the login button", "Type my username", "Extract the text from the article"

## 3. Search (`browser_search`)
- **Required Capabilities**: `browser_search`
- **Preconditions**: None.
- **Verification**: Verifies URL contains search engine query params.
- **Recovery**: None.
- **Example Prompt**: "Search Google for Python tutorials"

## 4. File Management (`browser_download`, `browser_upload`)
- **Required Capabilities**: `browser_download`, `browser_upload`
- **Preconditions**: Download link must be valid / Upload file path must exist.
- **Verification**: Confirms file exists on local disk after download / Confirms upload element accepts file.
- **Recovery**: Retries with larger timeout for downloads.
- **Example Prompt**: "Download the invoice", "Upload my resume"

## 5. Tab Management (`browser_tab_new`, `browser_tab_close`, `browser_tab_switch`, `browser_tab_list`)
- **Required Capabilities**: `browser_tab_new`, `browser_tab_close`, `browser_tab_switch`, `browser_tab_list`
- **Preconditions**: Target tab exists (for switch/close).
- **Verification**: Validates `total_tabs` and `current_tab_index` in `BrowserMemory`.
- **Recovery**: None.
- **Example Prompt**: "Open a new tab", "Switch to the first tab"

## 6. Autonomous Navigation (`browser_agentic_task`)
- **Required Capabilities**: `browser_agentic_task`
- **Preconditions**: Given a complex goal (e.g., "Find cheap flights").
- **Verification**: Loops Observe-Decide-Execute-Verify until goal achieved.
- **Recovery**: Internal LLM reflection and self-correction loop.
- **Example Prompt**: "Go to amazon and buy a laptop"
