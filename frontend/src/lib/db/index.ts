import { neon } from '@neondatabase/serverless';
import { drizzle } from 'drizzle-orm/neon-http';
import * as schema from './schema';

const sql = neon(process.env.DATABASE_URL!);

/**
 * Database Client
 * Singleton instance of the Drizzle client for Neon Postgres.
 */
export const db = drizzle(sql, { schema });
