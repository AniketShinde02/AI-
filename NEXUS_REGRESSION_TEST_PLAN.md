# Nexus Regression Test Plan

Before merging any architectural changes or new features into the `main` production branch, this suite must be executed to ensure stability.

## 1. Multilingual Voice Stability
| Test Case | Input | Expected Output | Actual Output | Pass/Fail | Notes |
|-----------|-------|-----------------|---------------|-----------|-------|
| English Audio | "Hello Nexus, what time is it?" | "The current time is..." | | | |
| Hindi Audio | "Namaste Nexus, kya samay hua hai?" | Correct Hindi or translated response. | | | |
| Marathi Audio | "Namaskar Nexus, kiti vajle?" | Correct Marathi response. | | | |
| Hinglish Audio | "Nexus, mera schedule kya hai today?" | Understands mixed syntax and replies contextually. | | | |

## 2. Speech Normalization & Filler Cleanup
| Test Case | Input | Expected Output | Actual Output | Pass/Fail | Notes |
|-----------|-------|-----------------|---------------|-----------|-------|
| Filler Words | "Uh, wait, actually open the browser." | "Open the browser." | | | |
| Self-Correction | "Remind me at 5, no wait, 6 PM." | "Remind me at 6 PM." | | | |

## 3. Automation Execution
| Test Case | Input | Expected Output | Actual Output | Pass/Fail | Notes |
|-----------|-------|-----------------|---------------|-----------|-------|
| Browser Task | "Navigate to Google and search for cats." | MCP Browser tool invoked, search executed, feedback returned. | | | |
| Desktop Task | "Open Notepad." | OS Daemon invoked, Notepad opens. | | | |
| Tool Dispatch | "Summarize this file." | File read tool invoked with correct path. | | | |

## 4. State & Infrastructure Stability
| Test Case | Input | Expected Output | Actual Output | Pass/Fail | Notes |
|-----------|-------|-----------------|---------------|-----------|-------|
| Memory Retrieval | "What is my favorite color?" (Previously stated as blue) | "Your favorite color is blue." | | | |
| WebSocket Recovery | Disconnect Wi-Fi for 3 seconds. | UI shows `Error` or `Reconnecting`. Audio resumes upon connection. | | | |
| Long Session | 15 continuous turns of conversation. | No memory leaks; latency remains < 1.5s. | | | |

*This file should be duplicated and filled out manually (or via automated scripts) prior to every major release.*
