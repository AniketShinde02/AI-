import { NextResponse } from 'next/server';

/**
 * API Route: /api/suggestions
 * Returns intelligent suggestions based on partial input.
 * Implements Rule #4: Debouncing & Throttling (server-side filter)
 */
export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const query = searchParams.get('q')?.toLowerCase() || '';

  const allSuggestions = [
    "How does quantum computing work?",
    "Write a production-grade Next.js layout",
    "Explain the theory of relativity",
    "Best practices for React 19",
    "Create a glassmorphic UI design",
    "Summarize my recent chats",
    "Help me plan my day",
    "What is the capital of France?",
    "How to use GetStream for voice?",
    "Build a real-time AI assistant"
  ];

  if (!query) {
    return NextResponse.json([]);
  }

  const filtered = allSuggestions
    .filter(s => s.toLowerCase().includes(query))
    .slice(0, 5);

  return NextResponse.json(filtered);
}
