# API Documentation (tRPC)

This project uses tRPC for type-safe, documented API endpoints. Following the **Awesome-tRPC** community patterns, all procedures are augmented with JSDoc and metadata.

## Endpoints

### `getSuggestions`
- **Type**: Query
- **Description**: Fetch search suggestions based on user input.
- **Input**: `{ q: string }`

### `chat`
- **Type**: Mutation
- **Description**: Execute a text-based AI chat completion using Groq.
- **Input**: `{ content: string, userId?: string, model?: string }`

### `getVoiceSession`
- **Type**: Mutation
- **Description**: Initialize a real-time voice call session with WebRTC tokens.
- **Input**: `{ userId: string, agentType?: string, model?: string }`

## Best Practices
- **Strict Validation**: All inputs are validated via Zod.
- **Error Handling**: Custom error messages are returned for missing API keys or backend failures.
- **Type Safety**: The `AppRouter` type is exported for full frontend/backend synchronization.
