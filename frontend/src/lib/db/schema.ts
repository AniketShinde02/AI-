import { pgTable, text, timestamp, uuid, jsonb } from "drizzle-orm/pg-core";

/**
 * Messages Table
 * Stores chat history for persistence across sessions.
 */
export const messages = pgTable("messages", {
  id: uuid("id").defaultRandom().primaryKey(),
  role: text("role", { enum: ["user", "assistant", "system"] }).notNull(),
  content: text("content").notNull(),
  metadata: jsonb("metadata").$type<{
    model?: string;
    tokens?: number;
    intent?: string;
  }>(),
  createdAt: timestamp("created_at").defaultNow().notNull(),
});

/**
 * Voice Sessions Table
 * Tracks voice call duration and quality.
 */
export const voiceSessions = pgTable("voice_sessions", {
  id: uuid("id").defaultRandom().primaryKey(),
  userId: text("user_id").notNull(),
  callId: text("call_id").notNull(),
  duration: text("duration"),
  startedAt: timestamp("started_at").defaultNow().notNull(),
  endedAt: timestamp("ended_at"),
});
