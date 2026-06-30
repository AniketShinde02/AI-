# Nexus Vision Skills Library

This document defines the official Vision automation skills supported by Nexus.

## 1. Analyze Screen (`vision_analyze_screen`)
- **Required Capabilities**: `vision_analyze_screen`
- **Preconditions**: Primary monitor must be readable.
- **Verification**: Verifies that the LLM successfully parses the base64 screenshot payload.
- **Recovery**: None.
- **Example Prompt**: "What am I looking at?", "Analyze my screen for errors"

## 2. OCR Extraction
- **Required Capabilities**: `vision_analyze_screen`
- **Preconditions**: Text is visible on screen.
- **Verification**: Returns extracted text.
- **Recovery**: None.
- **Example Prompt**: "Extract the text from this image"
