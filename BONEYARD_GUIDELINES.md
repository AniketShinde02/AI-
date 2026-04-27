# Boneyard-JS Development Guidelines

> [!IMPORTANT]
> **AntiGravity Standard**: ALL loading states and skeleton screens in this project MUST use `boneyard-js`. Manual skeleton components or hand-tuned placeholders are deprecated.

## Core Rules
1. **Always Wrap**: Any component that fetches data or has a loading state must be wrapped in `<Skeleton name="..." loading={isLoading}>`.
2. **Unique Names**: Every skeleton must have a unique `name` prop to avoid bone registry collisions.
3. **Use Fixtures**: For components that require auth or complex state, use the `fixture` prop to provide mock data for the build step.
4. **Regenerate Often**: After modifying layouts, run `npx boneyard-js build` (with the dev server running) to update the bones library.

## Workflow for New Components
1. **Implementation**:
   ```tsx
   import { Skeleton } from 'boneyard-js/react';
   
   // ...
   <Skeleton name="feature-card" loading={isLoading}>
     <FeatureCard data={data} />
   </Skeleton>
   ```
2. **Capture**:
   ```bash
   cd frontend
   npx boneyard-js build
   ```

## Configuration
Defaults are managed in `frontend/boneyard.config.json`. Global styles are injected via `frontend/src/bones/registry.ts`.
