# 📡 tRPC API Documentation
*Last Updated: 29/6/2026, 9:13:49 pm*

Automated documentation for Nexus tRPC endpoints.

### `getSuggestions`
**Description**: Fetch search suggestions
**Input**:
- `q: z.string().min(2)`
**Type**: `QUERY`

### `chat`
**Description**: Execute a text-based AI chat completion
**Input**:
- `content: z.string()`
- `userId: z.string().optional()`
- `model: z.string().optional()`
**Type**: `MUTATION`

### `getVoiceSession`
**Description**: Initialize a real-time voice call session
**Input**:
- `userId: z.string()`
- `agentType: z.string().default('general')`
- `model: z.string().optional()`
- `persona: z.string().default('female')`
**Type**: `MUTATION`
