import { StreamClient } from '@stream-io/node-sdk';
import { NextResponse } from 'next/server';

/**
 * PRODUCTION-GRADE API: /api/stream/voice-session
 * Pattern: Single User + Multiple Specialized Agents
 * 
 * This API orchestrates "Multi-Agent" environments where one user can have
 * multiple AI specialized agents (e.g. Research Agent, Personal Assistant)
 * listening or speaking in the same voice space.
 */
export async function POST(request: Request) {
  const apiKey = process.env.NEXT_PUBLIC_STREAM_API_KEY;
  const apiSecret = process.env.STREAM_API_SECRET;

  if (!apiKey || !apiSecret) {
    return NextResponse.json({ error: 'Stream configuration missing' }, { status: 500 });
  }

  try {
    const { userId, agentType = 'general' } = await request.json();
    
    if (!userId) {
      return NextResponse.json({ error: 'userId is required' }, { status: 400 });
    }

    const serverClient = new StreamClient(apiKey, apiSecret);

    // 1. Session ID pattern: Allows multiple concurrent agent contexts if needed
    const sessionId = `nexus_session_${userId.split('_').pop()}`;
    const callType = 'default'; // 'default' bypasses backstage permissions for local testing

    // 2. Multi-Agent Setup: Ensure the primary user and the agent IDs are ready
    // We treat agents as "System Users" in the Stream environment
    const agentId = `agent_${agentType}_${userId.split('_').pop()}`;

    await serverClient.upsertUsers([
      { id: userId, role: 'admin', name: 'User' },
      { id: agentId, role: 'admin', name: `Nexus ${agentType} Agent` }
    ]);

    // 3. Persistent Call Room for the user
    // This allows the user to leave and re-join the same "office" space
    const call = serverClient.video.call(callType, sessionId);
    await call.getOrCreate({
      data: {
        created_by_id: userId,
        members: [
          { user_id: userId, role: 'admin' },
          { user_id: agentId, role: 'admin' }
        ],
        custom: {
          title: `Nexus Workspace: ${agentType}`,
          isMultiAgent: true,
          userId: userId,
        },
      },
    });

    // 4. Token generation for the primary user
    const token = serverClient.createToken(userId);

    // 5. Trigger the Python backend to start the Agent
    try {
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_WS_URL 
        ? process.env.NEXT_PUBLIC_BACKEND_WS_URL.replace('ws://', 'http://').replace('wss://', 'https://')
        : 'http://localhost:8000';
        
      console.log(`[Nexus API] Triggering Python Agent to join call: ${callType}:${sessionId}`);
      const agentRes = await fetch(`${backendUrl}/api/agent/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ call_id: sessionId, call_type: callType }),
      });
      
      if (!agentRes.ok) {
        console.warn('[Nexus API] Python Agent failed to start:', await agentRes.text());
      } else {
        console.log('[Nexus API] Python Agent start triggered successfully.');
      }
    } catch (e: any) {
      console.warn('[Nexus API] Could not reach Python Agent Backend:', e.message);
    }

    return NextResponse.json({
      apiKey,
      token,
      userId,
      agentId,
      callId: sessionId,
      callType,
      config: {
        maxDuration: 'unlimited',
        quality: 'ultra-low-latency'
      }
    });

  } catch (error: any) {
    console.error('Nexus Architecture Error:', error);
    return NextResponse.json({ 
      error: 'Architecture failure', 
      details: error.message 
    }, { status: 500 });
  }
}
