import { StreamChat } from 'stream-chat';
import { NextResponse } from 'next/server';
import OpenAI from 'openai';
import { db } from '@/lib/db';
import { messages } from '@/lib/db/schema';

/**
 * PRODUCTION-GRADE API: /api/chat
 * Handles: Long-term Persistence + High-Speed Inference
 */
export async function POST(request: Request) {
  const apiKey = process.env.NEXT_PUBLIC_STREAM_API_KEY;
  const apiSecret = process.env.STREAM_API_SECRET;
  const groqApiKey = process.env.GROQ_API_KEY;

  if (!apiKey || !apiSecret) {
    return NextResponse.json({ error: 'Config missing' }, { status: 500 });
  }

  try {
    const { content, userId, metadata = {} } = await request.json();
    
    if (!content || !userId) {
      return NextResponse.json({ error: 'Missing payload' }, { status: 400 });
    }

    // 1. Parallel Task: Save User Message to DB
    const dbTask = db.insert(messages).values({
      role: 'user',
      content: content,
      metadata: { ...metadata, userId } as any // Cast to any to bypass strict JSON schema types
    });

    // 2. High-Speed Inference (Groq/SambaNova)
    const aiClient = new OpenAI({
      apiKey: groqApiKey || process.env.SAMBANOVA_API_KEY || process.env.GEMINI_API_KEY,
      baseURL: groqApiKey ? 'https://api.groq.com/openai/v1' : undefined,
    });

    const completion = await aiClient.chat.completions.create({
      messages: [
        { role: 'system', content: 'You are Nexus, a high-performance OS-level AI assistant.' },
        { role: 'user', content: content }
      ],
      model: process.env.LLM_MODEL || 'llama-3.3-70b-versatile',
      temperature: 0.7,
      max_tokens: 1024,
    });

    const aiReply = completion.choices[0].message.content || "I'm processing that...";

    // 3. Save AI Reply to DB
    await Promise.all([
      dbTask,
      db.insert(messages).values({
        role: 'assistant',
        content: aiReply,
        metadata: { model: completion.model, userId } as any
      })
    ]);

    return NextResponse.json({ 
      id: `ai_${Date.now()}`,
      role: 'assistant',
      content: aiReply,
      timestamp: Date.now()
    });

  } catch (error: any) {
    console.error('Nexus Logic Error:', error);
    return NextResponse.json({ error: 'Processing failed' }, { status: 500 });
  }
}
