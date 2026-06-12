This is the [assistant-ui](https://github.com/assistant-ui/assistant-ui) starter project.

## Getting Started

First, add your OpenAI API key to `.env.local` file:

```
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

Then, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.

## AI Context & Codebase Analysis

This project uses `code-review-graph` to maintain a high-signal context for AI agents. To sync the latest changes for the AI:

```powershell
./sync-context.ps1
```

This will:
1. Update the incremental knowledge graph.
2. Regenerate the AI-readable wiki in `.code-review-graph/wiki/`.
3. Clean up legacy context artifacts.
