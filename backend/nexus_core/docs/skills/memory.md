# Nexus Memory Skills Library

This document defines the official Memory automation skills supported by Nexus.
These skills interact with the user's vector storage (Lance Memory) and Scrapper OS.

## 1. Create Task (`create_task`)
- **Required Capabilities**: `create_task`
- **Preconditions**: Memory engine must be initialized.
- **Verification**: Checks DB insertion success.
- **Recovery**: Reports DB constraint errors.
- **Example Prompt**: "Remind me to buy milk", "Add a high priority task for Friday"

## 2. Create Note (`create_note`)
- **Required Capabilities**: `create_note`
- **Preconditions**: Memory engine must be initialized.
- **Verification**: Checks DB insertion success.
- **Recovery**: Reports DB constraint errors.
- **Example Prompt**: "Save a note about my meeting", "Remember this API key"

## 3. Scrapper OS Tasks (`check_scrapper_health`, `list_available_scrapers`, `run_scrapper_task`)
- **Required Capabilities**: `check_scrapper_health`, `list_available_scrapers`, `run_scrapper_task`
- **Preconditions**: Scrapper OS backend must be running.
- **Verification**: Verifies HTTP response codes and JSON payload from Scrapper API.
- **Recovery**: None.
- **Example Prompt**: "Check scrapper health", "List all bots", "Run the Reddit scraper"
