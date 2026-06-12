import { NextResponse } from 'next/server';

// Simple Groq-backed chat endpoint.
// This uses Groq API if GROQ_API_KEY is provided; otherwise returns a friendly fallback.
export async function POST(request: Request) {
  const groqApiKey = process.env.GROQ_API_KEY;
  const model = process.env.LLM_MODEL || 'llama-3.3-70b-versatile';

  try {
    const { content, userId } = await request.json();
    if (!content || !userId) {
      return NextResponse.json({ error: 'Missing payload' }, { status: 400 });
    }

    let aiReply = '';
    if (groqApiKey) {
      // Use the Groq/OpenAI-compatible Chat API
      const res = await fetch('https://api.groq.com/openai/v1/chat/completions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${groqApiKey}`,
        },
        body: JSON.stringify({
          messages: [
            { role: 'system', content: 'You are Nexus, a high-performance OS-level AI assistant.' },
            { role: 'user', content },
          ],
          model,
          temperature: 0.7,
          max_tokens: 1024,
        }),
      });
      const data = await res.json();
      aiReply = data?.choices?.[0]?.message?.content ?? 'Sorry, I cannot answer that yet.';
    } else {
      aiReply = `Groq API not configured. Echo: ${content}`;
    }

    return NextResponse.json({
      id: `groq_${Date.now()}`,
      role: 'assistant',
      content: aiReply,
      timestamp: Date.now(),
    });
  } catch (err) {
    console.error('Groq route error', err);
    return NextResponse.json({ error: 'Groq processing failed' }, { status: 500 });
  }
}
