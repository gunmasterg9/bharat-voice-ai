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
    const status = searchParams.get('status');

    const db = getDb();
    let query = `
      SELECT id, reference_id, user_id, name, language, reason, summary, what_was_checked, urgency, preferred_follow_up, status, created_at, updated_at
      FROM escalations
    `;
    const params: (string | number)[] = [];

    if (status && status !== 'ALL') {
      query += ` WHERE status = ?`;
      params.push(status.toUpperCase());
    }

    query += ` ORDER BY created_at DESC LIMIT 100`;

    const stmt = db.prepare(query);
    const rows = stmt.all(...params);
    db.close();

    return NextResponse.json({ success: true, escalations: rows });
  } catch (error) {
    console.error('[API ESCALATIONS GET ERROR]', error);
    return NextResponse.json({ success: false, error: String(error) }, { status: 500 });
  }
}

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const {
      user_id = 'default_user',
      reason = 'Human help requested',
      summary = 'User requested human assistance.',
      what_was_checked = 'Agent triage',
      urgency = 'LOW',
      preferred_follow_up = 'phone',
      name,
      language,
      user_permission = false,
    } = body;

    if (!user_permission) {
      return NextResponse.json(
        { success: false, error: 'permission_denied', message: 'User permission is required.' },
        { status: 400 }
      );
    }

    const db = getDb();
    const dateStr = new Date().toISOString().slice(0, 10).replace(/-/g, '');

    // Duplicate check
    const dupStmt = db.prepare(
      `SELECT reference_id FROM escalations WHERE user_id = ? AND status = 'OPEN' AND reason = ? LIMIT 1`
    );
    const dup = dupStmt.get(user_id, reason) as { reference_id: string } | undefined;
    if (dup) {
      db.close();
      return NextResponse.json({
        success: true,
        reference_id: dup.reference_id,
        status: 'OPEN',
        is_duplicate: true,
      });
    }

    // Sequence ID
    const countStmt = db.prepare(
      `SELECT COUNT(*) as cnt FROM escalations WHERE reference_id LIKE ?`
    );
    const countRes = countStmt.get(`ESC-${dateStr}-%`) as { cnt: number } | undefined;
    const seq = (countRes?.cnt || 0) + 1;
    const refId = `ESC-${dateStr}-${String(seq).padStart(4, '0')}`;

    const now = new Date().toISOString();
    const insertStmt = db.prepare(`
      INSERT INTO escalations
      (reference_id, user_id, name, language, reason, summary, what_was_checked, urgency, preferred_follow_up, status, created_at, updated_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'OPEN', ?, ?)
    `);

    insertStmt.run(
      refId,
      user_id,
      name || null,
      language || null,
      reason,
      summary,
      what_was_checked,
      urgency.toUpperCase(),
      preferred_follow_up,
      now,
      now
    );

    db.close();

    return NextResponse.json({
      success: true,
      reference_id: refId,
      status: 'OPEN',
    });
  } catch (error) {
    console.error('[API ESCALATIONS POST ERROR]', error);
    return NextResponse.json({ success: false, error: String(error) }, { status: 500 });
  }
}
