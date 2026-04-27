# Start with GetStream: Voice-First AI Assistant

> Opinionated starter guide for wiring your **voice + text AI assistant UI** to GetStream (Chat + Video/Audio) using the **free Build tier** and **OpenAI Realtime voice**.
>
> Assumes: modern web frontend (React/Next/etc.), Node.js backend, and that you already have basic UI shells for text and voice.

---

## 0. What GetStream Actually Gives You

GetStream is *not* an LLM provider.
It gives you **real‑time infrastructure** that your AI assistant can sit on top of:

- **Chat Messaging** – channels, users, messages, reactions, rich UI components, moderation, etc.[web:8][web:25]
- **Video & Audio** – WebRTC‑based audio rooms, video calls, livestreams, and full React/React Native/iOS/Android SDKs.[web:2][web:12]
- **Edge Network** – low‑latency global infrastructure used by 1B+ end users and 2K+ apps.[web:10][web:9]
- **AI Voice & Agent Integrations** – built‑in integration with **OpenAI Realtime** for voice agents and higher‑level “Vision Agents” libraries.[web:16][web:33][web:32]

Your stack will look roughly like this:

- Browser UI → Stream Video SDK (audio room) → Stream edge → OpenAI Realtime (voice agent)
- Browser UI → Stream Chat SDK → your Node backend → LLM(s) + tools → Stream Chat (AI messages)

---

## 1. Free Plan – What You Can Get Away With

### 1.1 Chat Build Tier

For prototyping and early beta, the **Chat “Build” plan** is enough:[web:15]

- **1,000 Monthly Active Users (MAU)**.
- **100 concurrent WebSocket connections**.
- Access to *all* chat features; community support; no credit card.

Plenty for a dev project or a small early‑adopter group.
If you push past that, you move to paid Start/Elevate plans – but don’t waste time optimizing for that now.

### 1.2 Video & Audio Build Tier

For voice, you use **Stream Video & Audio** (backed by WebRTC).[web:2][web:6]

- Build tier gives **~333,000 participant minutes free** plus **$100 free usage per month** on Video & Audio.[web:10]
- Pricing beyond that is **usage‑based** (per 1,000 participant minutes), so you only pay when you start getting real traffic.[web:10]

For a single voice‑assistant per user (audio only), that’s a *lot* of free experimentation.

---

## 2. Architecture for Your Voice‑First Assistant

### 2.1 Voice Flow (Primary Priority)

1. User hits **“Talk”** in your UI.
2. Frontend calls your backend for **call credentials** (Stream API key, user token, call ID, type).
3. Backend:
   - Uses `@stream-io/node-sdk` to create a **video/audio call** (usually `callType = "audio_room"` or `"default"`).[web:2][web:28]
   - Connects an **OpenAI Realtime agent** to that call via `video.connectOpenAi`.[web:16][web:33][web:39]
4. Frontend joins the call using the **React Video SDK**; user audio goes via Stream → OpenAI Realtime → back to the call.
5. The assistant speaks in real time using OpenAI’s voice; you can also capture transcripts and push them into Stream Chat as messages.

This gives you low‑latency voice with robust WebRTC behavior (NAT traversal, bad networks, etc.) without you hand‑rolling signaling.[web:2][web:12]

### 2.2 Text Chat Flow (Second Priority)

1. Your text UI uses **Stream Chat React** or plain JS SDK to connect a user.
2. You create a dedicated **channel** (e.g., type `messaging`) for each user or conversation.[web:8][web:25]
3. When the user sends a message, your backend:
   - Receives it via webhook or a custom endpoint.
   - Calls OpenAI/Anthropic/whatever with the full channel history.
   - Sends the AI response back as a **message authored by an “agent user”**.
4. You can synchronize voice transcripts into chat so both modes share the same context.

Stream provides full sample code for AI assistants with Chat + AI.[web:25][web:37]

---

## 3. Create Your Stream Account & App

1. Go to **https://getstream.io** and sign up (GitHub/Google works).[web:13]
2. From the dashboard, create a **new app** and enable:
   - **Chat** (for text messaging).
   - **Video & Audio** (for voice).
3. Note your **API Key** and **API Secret** – you’ll need both on the backend.[web:2]
4. Switch the app to a **development environment** (no region lock headaches yet).

For now, don’t over‑optimize: keep a single app that handles both voice and text.

---

## 4. Backend Setup (Python)

You’ll run a Python backend (modular monolith) to:

- Generate **user tokens** for Chat and Video.
- Create calls and orchestrate AI agents.
- Connect AI agents to calls (e.g., via Stream Video Python SDK).
- Act as the glue between Stream and your tool-calling stack.

### 4.1 Install Dependencies

In your backend project:

```bash
pip install stream-python
```

### 4.2 Initialize Stream Client

Initialize the Stream clients in `src/backend/services/stream_client.py`.

```python
import os
from stream_chat import StreamChat
from getstream import Stream

# Load from config/settings.py
STREAM_API_KEY = os.environ.get("STREAM_API_KEY")
STREAM_API_SECRET = os.environ.get("STREAM_API_SECRET")

# Chat Client
chat_client = StreamChat(api_key=STREAM_API_KEY, api_secret=STREAM_API_SECRET)

# Video/Voice Client
video_client = Stream(api_key=STREAM_API_KEY, api_secret=STREAM_API_SECRET)

def generate_user_token(user_id: str) -> str:
    """Generate a JWT for the frontend to authenticate with Stream."""
    return chat_client.create_token(user_id)
```
  };
}
```

- `upsertUsers` ensures the user exists in the Video/Chat system.[web:2]
- `generateUserToken` creates a signed JWT valid for a period (default ~1 hour).[web:2]

Expose this via REST:

```ts
// GET /api/stream/credentials?userId=xyz
// → returns { apiKey, userId, token }
```

### 4.3 Create a Call and Connect the Voice Agent

To attach a voice agent, you:

1. Create a **call** (type `default` or `audio_room`).
2. Connect OpenAI Realtime via `video.connectOpenAi`.

Backend pseudo‑code, inspired by Stream’s AI voice assistant tutorial:[web:16][web:33][web:39]

```ts
import crypto from 'crypto';
import { RealtimeClient } from '@openai/realtime-api-beta';

export async function createVoiceCall() {
  const callId = crypto.randomUUID();
  const call = streamClient.video.call('audio_room', callId);

  // Create the call server-side so the agent and user can join
  await call.getOrCreate({ data: { created_by_id: 'system' } });

  // Connect OpenAI Realtime to the call via Stream helper
  const realtimeClient = await streamClient.video.connectOpenAi({
    call,
    openAiApiKey: process.env.OPENAI_API_KEY!,
    agentUserId: 'voice-agent',
    model: 'gpt-4o-realtime-preview',
  });

  realtimeClient.updateSession({
    instructions:
      'You are a helpful, concise assistant. Speak clearly and keep answers short.',
    voice: 'alloy',
  });

  // Optional: log transcripts
  realtimeClient.on('realtime.event', ({ event }) => {
    if (event.type === 'response.audio_transcript.done') {
      console.log('Transcript:', event.transcript);
    }
  });

  // Generate user credentials so the frontend can join
  const { apiKey, userId, token } = await getUserCredentials('human-user');

  return {
    apiKey,
    token,
    userId,
    callId,
    callType: 'audio_room',
  };
}
```

Then expose this as an endpoint:

```ts
// POST /api/voice/session
// → returns { apiKey, token, userId, callId, callType }
```

You can also mirror Stream’s tutorial pattern and create a `/connect` endpoint used by the frontend to attach the agent separately.[web:16][web:40]

---

## 5. Frontend: Join the Voice Call (React)

### 5.1 Install the React Video SDK

In your frontend project:

```bash
yarn add @stream-io/video-react-sdk
```

The React SDK gives you:

- A **StreamVideoClient** abstraction.
- Ready‑made components for call layouts, controls, and audio rooms.
- Hooks to get call state, audio levels, etc.[web:12][web:22][web:28]

### 5.2 Create a "Join Voice" Flow

On your “Talk to Toby” button click:

1. Call `POST /api/voice/session` to get credentials.
2. Initialize `StreamVideoClient` with the API key, user and token.
3. Create a call instance and join.

Pseudo‑code (React/TypeScript):

```tsx
import {
  StreamVideo,
  StreamCall,
  StreamVideoClient,
  useCallStateHooks,
} from '@stream-io/video-react-sdk';
import '@stream-io/video-react-sdk/dist/css/styles.css';

function VoiceAssistant() {
  const [client, setClient] = useState<StreamVideoClient | null>(null);
  const [call, setCall] = useState<any>(null);

  const startVoice = async () => {
    const res = await fetch('/api/voice/session', { method: 'POST' });
    const { apiKey, token, userId, callId, callType } = await res.json();

    const user = { id: userId, name: 'You' };
    const c = new StreamVideoClient({ apiKey, user, token });

    const call = c.call(callType, callId);
    await call.join({ create: false });

    setClient(c);
    setCall(call);
  };

  if (!client || !call) {
    return <button onClick={startVoice}>Start voice with Toby</button>;
  }

  return (
    <StreamVideo client={client}>
      <StreamCall call={call}>
        {/* Use built-in layout or customize */}
        <MinimalAudioUI />
      </StreamCall>
    </StreamVideo>
  );
}
```

Once the user joins, the agent attached server‑side will auto‑join and start handling audio via OpenAI Realtime.[web:16][web:33]

If you want a super minimal audio UI:

- Hide the video tiles.
- Only show mute/unmute and “end call” buttons.
- Optionally display **waveform / speaking indicator** using `useCallStateHooks().useCallStats` or audio‑level hooks.[web:12]

---

## 6. Wiring Text Chat with AI Agents

### 6.1 Choose Chat SDK

For a web UI like the screenshot you shared, **Stream Chat React** is the most productive option:[web:8][web:25]

```bash
npm install stream-chat stream-chat-react
```

High-level setup:

```tsx
import { Chat, Channel, Window } from 'stream-chat-react';
import { StreamChat } from 'stream-chat';

const client = StreamChat.getInstance(import.meta.env.VITE_STREAM_API_KEY);

await client.connectUser(
  { id: userId },
  userToken
);

const channel = client.channel('messaging', 'toby-private', {
  members: [userId, 'toby-agent'],
});
await channel.watch();

function TextChat() {
  return (
    <Chat client={client}>
      <Channel channel={channel}>
        <Window>
          {/* MessageList, MessageInput etc. */}
        </Window>
      </Channel>
    </Chat>
  );
}
```

How you get `userToken`:

- Same pattern as Video: use your backend’s `getUserCredentials` endpoint.

### 6.2 Create an "Agent User" in Chat

On the backend (Node with `stream-chat` server SDK or using the Node video/client SDK), create a user for the AI:

- `id = 'toby-agent'`.
- `role = 'admin'` or a custom role.
- Optional `name` + `image` (avatar).

You can either upsert this via Chat’s server SDK or re‑use `upsertUsers` from the `StreamClient` if you use the unified SDK where Chat + Video share the same user base.[web:2][web:37]

### 6.3 Handling Messages and Generating AI Replies

Pattern that Stream’s official AI assistant samples use:[web:25][web:37][web:31]

1. User sends a message in a channel.
2. Backend receives a webhook (`message.new`) **or** you expose `/api/chat/ai` and call it directly from the frontend.
3. Backend:
   - Fetches last N messages of the channel.
   - Calls your LLM (OpenAI, Anthropic, etc.) with the full conversation.
   - Optionally adds tools like web search, DB lookups, function calling.
4. Backend sends message **as the agent user**:

```ts
await channel.sendMessage({
  text: aiReply,
  user_id: 'toby-agent',
});
```

5. Chat UI renders it like a normal message but visually styled as “Assistant”.

Because you’re already using Stream Video for voice, you can also sync voice transcripts into the channel using `channel.sendMessage` whenever you receive `response.audio_transcript.done` events from OpenAI Realtime (see 4.3).

---

## 7. Using `agent-skills` to Bootstrap Agents Faster

Stream’s homepage and recent blog posts reference **Agent Skills** with the CLI command:

```bash
npx skills add GetStream/agent-skills
```

This uses the open **`skills` CLI** (think `npm` but for AI agent configurations/tools), maintained by Vercel and others.[web:18][web:24][web:27][web:30]

### 7.1 What the `GetStream/agent-skills` Repo Gives You

Recent GetStream posts and the **Vision Agents** project show that this skill set includes:[web:32][web:35][web:43][web:42]

- Ready‑made **agents wired to Stream’s edge network** (`getstream.Edge()` in Python).
- Preconfigured **STT (Deepgram / Whisper)**, **TTS (ElevenLabs, Cartesia Sonic 3, etc.)**, and **LLM** integrations.[web:32][web:35][web:43]
- Utilities to **join Stream video/audio calls** as an agent and respond with voice + vision.

You don’t *have* to use these, but they’re a huge shortcut if you want a flexible Python‑based agent process instead of hand‑coding everything in Node.

### 7.2 Installing Skills

From your project root:

```bash
# Install the skills CLI globally (if not already)
npm install -g skills

# Install Stream’s agent skill into the current project
npx skills add GetStream/agent-skills --skill stream
```

Notes:[web:18][web:24][web:27]

- `.skills.json` is like `package.json` for skills; `skills-lock.json` pins exact versions.[web:18]
- Skills install into `.agents/skills/` by default.[web:18]
- You can target specific **agents** (e.g. `claude-code`, `cursor`) with `--agent` if you’re wiring this into dev tools.[web:27]

Once installed, check the repo’s documentation (or the `vision_agents` GitHub README) for commands like:

```bash
uv run plugins/openai/voice_agent.py run
# or
uv run plugins/ollama/video_analysis_agent.py run
```

Those examples show how to:

- Create an `Agent(edge=getstream.Edge(), ...)`.
- Join a Stream call by type + ID.
- Use STT + TTS + LLMs + vision processors in one pipeline.[web:32][web:35][web:43]

For your app, you can:

- Keep Node as the HTTP backend.
- Spin up an **agent worker** (Python Vision Agent) that connects to Stream calls when requested.

---

## 8. Staying Inside the Free Plan (Practical Tips)

- **Use a single dev app** with Chat + Video enabled.
- Limit **parallel voice calls** to your own sessions + a handful of testers.
- Use **audio‑only** for the assistant; it’s cheaper and lighter than full video.[web:10]
- Clean up old channels & messages periodically if you approach storage limits on the free tier.[web:15]

If you start hitting MAU or participant‑minute ceilings, that’s a *good* problem – it means people are using your app.
At that point, upgrade plans and add monitoring.

---

## 9. Step‑By‑Step Checklist (TL;DR Implementation Plan)

1. **Create Stream app** with Chat + Video enabled; copy API key + secret.[web:2][web:10][web:15]
2. **Backend** (Node):
   - Install `@stream-io/node-sdk` and `@openai/realtime-api-beta`.
   - Implement `getUserCredentials(userId)`.
   - Implement `createVoiceCall()` that:
     - Creates `audio_room` / `default` call.
     - Connects OpenAI Realtime via `video.connectOpenAi`.
   - Expose `/api/stream/credentials` and `/api/voice/session`.
3. **Frontend – Voice**:
   - Install `@stream-io/video-react-sdk`.
   - On microphone button click, call `/api/voice/session`, initialize `StreamVideoClient`, join the call, and render minimal audio UI.
4. **Frontend – Text**:
   - Install `stream-chat` + `stream-chat-react`.
   - Connect user with token from backend.
   - Create/join channel with members `[userId, 'toby-agent']`.
5. **Backend – Text AI**:
   - Implement webhook or `/api/chat/ai` to call LLM using channel history.
   - Send AI replies as `user_id: 'toby-agent'`.
   - Optionally push voice transcripts into the same channel.
6. (Optional but powerful) **Install `GetStream/agent-skills`** and experiment with Vision Agents for more advanced voice/vision workflows.

Follow this order and you’ll have **voice working first**, text following right behind, all sitting on top of a scalable infra that won’t crumble the second real users show up.
