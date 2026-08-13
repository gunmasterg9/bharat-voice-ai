import { NextResponse } from 'next/server';
import { DatabaseSync } from 'node:sqlite';
import path from 'path';

export const revalidate = 0;

function getDb() {
  const dbPath = path.resolve(process.cwd(), '../backend/data/bharat_voice.db');
  return new DatabaseSync(dbPath);
}

export async function GET() {
  try {
    const db = getDb();
    const query = `
      SELECT
        COUNT(*) as total_calls,
        SUM(CASE WHEN outcome = 'SUCCESS' THEN 1 ELSE 0 END) as successful_calls,
        SUM(CASE WHEN outcome != 'SUCCESS' THEN 1 ELSE 0 END) as failed_calls
      FROM calls;
    `;

    const stmt = db.prepare(query);
    const result = stmt.get() as
      | {
          total_calls: number | null;
          successful_calls: number | null;
          failed_calls: number | null;
        }
      | undefined;
    db.close();

    const total = Number(result?.total_calls || 0);
    const success = Number(result?.successful_calls || 0);
    const failed = Number(result?.failed_calls || 0);

    return NextResponse.json({
      success: true,
      total_calls: total,
      successful_calls: success,
      failed_calls: failed,
    });
  } catch (error) {
    console.error('[API ANALYTICS SUMMARY GET ERROR]', error);
    return NextResponse.json(
      {
        success: false,
        total_calls: 0,
        successful_calls: 0,
        failed_calls: 0,
        error: String(error),
      },
      { status: 500 }
    );
  }
}
