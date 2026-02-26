/**
 * Vercel Serverless Function — 사용자 오버라이드 GitHub 동기화 프록시
 * 클라이언트에 PAT 노출 없이 서버 측 GITHUB_PAT 환경변수 사용
 *
 * GET  /api/sync  → output/user_overrides.json 읽기
 * POST /api/sync  → output/user_overrides.json 쓰기 (body: { overrides, sha? })
 */
export default async function handler(req, res) {
  const pat = process.env.GITHUB_PAT;
  if (!pat) return res.status(500).json({ error: 'GITHUB_PAT env not configured' });

  const REPO   = 'Ryunaissance/corryu';
  const BRANCH = 'main';
  const PATH   = 'output/user_overrides.json';
  const apiUrl = `https://api.github.com/repos/${REPO}/contents/${PATH}`;
  const ghHeaders = {
    Authorization: `Bearer ${pat}`,
    Accept: 'application/vnd.github+json',
  };

  if (req.method === 'GET') {
    try {
      const r = await fetch(`${apiUrl}?ref=${BRANCH}`, {
        headers: ghHeaders,
        signal: AbortSignal.timeout(8000),
      });
      if (r.status === 404) return res.status(404).json({ error: 'not found' });
      if (!r.ok) return res.status(r.status).json({ error: `GitHub ${r.status}` });
      const d = await r.json();
      const content = JSON.parse(
        Buffer.from(d.content.replace(/\n/g, ''), 'base64').toString('utf8')
      );
      res.setHeader('Cache-Control', 'no-store');
      return res.json({ content, sha: d.sha });
    } catch (e) {
      return res.status(502).json({ error: e.message });
    }
  }

  if (req.method === 'POST') {
    try {
      const { overrides, sha } = req.body || {};
      if (!overrides) return res.status(400).json({ error: 'overrides required' });
      const ts = Date.now();
      const payload = Object.assign({ _meta: { ts } }, overrides);
      const encoded = Buffer.from(JSON.stringify(payload, null, 2)).toString('base64');
      const body = {
        message: 'sync: corryu user overrides',
        content: encoded,
        branch: BRANCH,
      };
      if (sha) body.sha = sha;
      const r = await fetch(apiUrl, {
        method: 'PUT',
        headers: { ...ghHeaders, 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        signal: AbortSignal.timeout(10000),
      });
      if (!r.ok) {
        const errBody = await r.json().catch(() => ({}));
        return res.status(r.status).json({ error: `GitHub ${r.status}`, detail: errBody.message });
      }
      const d = await r.json();
      return res.json({ sha: d.content && d.content.sha, ts });
    } catch (e) {
      return res.status(502).json({ error: e.message });
    }
  }

  return res.status(405).json({ error: 'Method not allowed' });
}
