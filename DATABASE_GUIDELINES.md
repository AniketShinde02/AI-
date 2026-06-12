# Nexus 2.0 Database Guidelines (Firestore Free-Tier)

These rules are BINDING for AntiGravity to ensure the project stays within Firebase Free Tier limits and maintains production-grade performance.

## 1. Zero-Wastage Read/Write Policy
- **Batching**: Never perform multiple individual writes in a loop. Use `firestore.WriteBatch()` for operations > 2 documents.
- **Read Caching**: Use local session caching for user profiles to avoid fetching the same profile document multiple times per request.
- **Projection**: Only fetch necessary fields using `.select()` if the document is large.

## 2. Query Optimization (No Redundant Queries)
- **Indexing**: Always define single-field and composite indexes in code comments so the user knows what to enable in the console.
- **Ordering**: Limit `order_by` operations to the minimum required for voice context.
- **No Polling**: Use real-time listeners (`on_snapshot`) only when absolutely necessary for the UI. Otherwise, use one-time async gets.

## 3. Structural Integrity (No-SQL Patterns)
- **Denormalization**: Store small, frequently used data (like `username`) directly inside the `Memory` or `Task` document to avoid a second "Join" read.
- **Flat Collections**: Keep collections flat where possible to avoid deep sub-collection read overhead.

## 4. Connection Pooling
- **Singleton Client**: The `FirebaseDB` class must remain a singleton. Never re-initialize `firebase_admin` inside service methods.

## 5. Security & Costs
- **No Billing**: Avoid any logic that triggers auto-scaling or paid Firebase features.
- **TTL**: Implement a logical "Cleanup" field for memories so old context doesn't bloat the DB size.
