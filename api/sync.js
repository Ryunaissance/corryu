/**
 * Vercel Serverless Function — 사용자 오버라이드 Blob 저장소
 * GitHub 커밋 대신 Vercel Blob에 직접 저장 → sha 충돌 없음
 *
 * GET  /api/sync  → 오버라이드 JSON 읽기
 * POST /api/sync  → 오버라이드 JSON 쓰기 (body: { overrides })
 *
 * 환경변수: BLOB_READ_WRITE_TOKEN (Vercel Blob Store)
 */
import { put, list } from '@vercel/blob';

const BLOB_PATH = 'corryu/user_overrides.json';

export default async function handler(req, res) {
  const token = process.env.BLOB_READ_WRITE_TOKEN;
  if (!token) return res.status(500).json({ error: 'BLOB_READ_WRITE_TOKEN not configured' });

  // ── GET: 읽기 ─────────────────────────────────────
  if (req.method === 'GET') {
    try {
      const { blobs } = await list({ prefix: BLOB_PATH, limit: 1, token });
      if (!blobs.length) return res.status(404).json({ error: 'not found' });
      const r = await fetch(blobs[0].downloadUrl, { signal: AbortSignal.timeout(5000) });
      if (!r.ok) return res.status(502).json({ error: `blob fetch ${r.status}` });
      const content = await r.json();
      res.setHeader('Cache-Control', 'no-store');
      return res.json({ content });
    } catch (e) {
      return res.status(502).json({ error: e.message });
    }
  }

  // ── POST: 쓰기 ────────────────────────────────────
  if (req.method === 'POST') {
    try {
      const { overrides } = req.body || {};
      if (!overrides) return res.status(400).json({ error: 'overrides required' });
      const ts = Date.now();
      const payload = { _meta: { ts }, ...overrides };
      await put(BLOB_PATH, JSON.stringify(payload), {
        access: 'public',
        addRandomSuffix: false,
        contentType: 'application/json',
        token,
      });
      return res.json({ ts });
    } catch (e) {
      return res.status(502).json({ error: e.message });
    }
  }

  return res.status(405).json({ error: 'Method not allowed' });
}
