import { NextResponse } from 'next/server';
import { DatabaseSync } from 'node:sqlite';
import path from 'path';

export const revalidate = 0;

function getDb() {
  const dbPath = path.resolve(process.cwd(), '../backend/data/bharat_voice.db');
  return new DatabaseSync(dbPath);
}

export async function PATCH(req: Request, { params }: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await params;
    const body = await req.json();
    const { status } = body;

    const validStatuses = ['OPEN', 'IN_PROGRESS', 'RESOLVED'];
    const targetStatus = String(status || '').toUpperCase();

    if (!validStatuses.includes(targetStatus)) {
      return NextResponse.json(
        {
          success: false,
          error: 'invalid_status',
          message: `Status must be one of: ${validStatuses.join(', ')}`,
        },
        { status: 400 }
      );
    }

    const db = getDb();
    const now = new Date().toISOString();

    const updateStmt = db.prepare(
      `UPDATE escalations SET status = ?, updated_at = ? WHERE reference_id = ? OR id = ?`
    );
    const result = updateStmt.run(targetStatus, now, id, id);

    if (result.changes === 0) {
      db.close();
      return NextResponse.json(
        {
          success: false,
          error: 'not_found',
          message: `No escalation found with reference ID or ID: ${id}`,
        },
        { status: 404 }
      );
    }

    const selectStmt = db.prepare(`SELECT * FROM escalations WHERE reference_id = ? OR id = ?`);
    const updatedRecord = selectStmt.get(id, id);
    db.close();

    return NextResponse.json({
      success: true,
      escalation: updatedRecord,
    });
  } catch (error) {
    console.error('[API ESCALATION PATCH ERROR]', error);
    return NextResponse.json({ success: false, error: String(error) }, { status: 500 });
  }
}
