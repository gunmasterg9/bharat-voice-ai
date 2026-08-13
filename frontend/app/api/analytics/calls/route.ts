import { NextResponse } from 'next/server';
import { DatabaseSync } from 'node:sqlite';
import path from 'path';

export const revalidate = 0;

function getDb() {
  const dbPath = path.resolve(process.cwd(), '../backend/data/bharat_voice.db');
  return new DatabaseSync(dbPath);
}

export async function GET(req: Request) {
  try {
    const { searchParams } = new URL(req.url);
    const limit = Math.min(100, Math.max(1, parseInt(searchParams.get('limit') || '50', 10)));

    const db = getDb();
    const query = `
      SELECT
        call_id,
        user_id,
        channel,
        language,
        started_at,
        ended_at,
        duration_seconds,
        outcome,
        success_reason,
        failure_reason,
        tool_used,
        escalation_created
      FROM calls
      ORDER BY id DESC
      LIMIT ?;
    `;

    const stmt = db.prepare(query);
    const rows = stmt.all(limit);
    db.close();

    return NextResponse.json({
      success: true,
      calls: rows,
    });
  } catch (error) {
    console.error('[API ANALYTICS CALLS GET ERROR]', error);
    return NextResponse.json(
      {
        success: false,
        calls: [],
        error: String(error),
      },
      { status: 500 }
    );
  }
}
