/**
 * Vercel Serverless Function — Yahoo Finance 서버사이드 프록시
 * 브라우저 CORS 문제를 우회: /api/yf?ticker=SMH
 *
 * Node.js 18+ 내장 fetch 사용 (Vercel 기본 환경)
 */
export default async function handler(req, res) {
  const { ticker, range = '5y', interval = '1mo' } = req.query;

  if (!ticker || typeof ticker !== 'string' || !/^[A-Z0-9.\-]{1,20}$/i.test(ticker)) {
    return res.status(400).json({ error: 'ticker required (e.g. ?ticker=SMH)' });
  }

  const url =
    `https://query2.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(ticker.toUpperCase())}` +
    `?range=${range}&interval=${interval}&includeAdjustedClose=true`;

  try {
    const yfRes = await fetch(url, {
      headers: {
        'User-Agent':
          'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ' +
          '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9',
      },
      signal: AbortSignal.timeout(8000),
    });

    if (!yfRes.ok) {
      return res.status(yfRes.status).json({ error: `Yahoo Finance ${yfRes.status}` });
    }

    const data = await yfRes.json();
    // 1시간 캐시 (CDN edge에서 처리, 함수 호출 횟수 절약)
    res.setHeader('Cache-Control', 's-maxage=3600, stale-while-revalidate=300');
    return res.json(data);
  } catch (e) {
    return res.status(502).json({ error: e.message });
  }
}
