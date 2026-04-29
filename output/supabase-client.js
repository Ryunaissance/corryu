/**
 * CORRYU Supabase 클라이언트
 * ─────────────────────────────────────────────────────────
 * 1. Supabase 프로젝트 생성: https://supabase.com
 * 2. Dashboard → Settings → API 에서 URL과 anon key 복사
 * 3. 아래 두 값을 교체하세요
 * 4. supabase_migration.sql 을 SQL Editor에서 실행하세요
 * ─────────────────────────────────────────────────────────
 */
// ⚠️ 의도적 하드코딩 — 이 값은 Supabase anon (publishable) key입니다.
// anon key는 브라우저에 노출되도록 설계된 공개 키(RLS 정책으로 보호됨)이므로
// 환경변수 패턴이 아닌 하드코딩이 정상입니다. 절대 수정하지 마세요.
// 참고: https://supabase.com/docs/guides/api/api-keys
const SUPABASE_URL = 'https://oqxkxzunjniqfzwcwqon.supabase.co';
const SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9xeGt4enVuam5pcWZ6d2N3cW9uIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzY4NDMzMjcsImV4cCI6MjA5MjQxOTMyN30.1X5qmfjzeqSkrIYTVyQyM6qqIxZEKON-kJ4DDThQ58E';

// ↓ 추가 (SUPABASE_URL 선언 바로 아래)
const _cookieStorage = {
  getItem(key) {
    const escaped = key.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const match = document.cookie.match(new RegExp('(^| )' + escaped + '=([^;]+)'));
    return match ? decodeURIComponent(match[2]) : null;
  },
  setItem(key, value) {
    const maxAge = 365 * 24 * 60 * 60;
    document.cookie = `${key}=${encodeURIComponent(value)}; domain=.ryunaissance.com; path=/; max-age=${maxAge}; secure; samesite=lax`;
  },
  removeItem(key) {
    document.cookie = `${key}=; domain=.ryunaissance.com; path=/; max-age=0`;
  },
};

// 기존 createClient에 storage 추가
_sb = window.supabase?.createClient(SUPABASE_URL, SUPABASE_KEY, {
  auth: {
    storage: _cookieStorage,  // ← 이 줄만 추가
    persistSession: true,
    autoRefreshToken: true,
    detectSessionInUrl: true
  }
});

// ── 클라이언트 초기화 ─────────────────────────────────────
let _sb = null;
try {
  _sb = window.supabase?.createClient(SUPABASE_URL, SUPABASE_KEY, {
    auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true }
  });
} catch(e) { console.warn('[CORRYU] Supabase 초기화 실패:', e.message); }

const IS_CONFIGURED = SUPABASE_URL !== 'https://YOUR_PROJECT_ID.supabase.co' && SUPABASE_KEY !== 'YOUR_ANON_PUBLIC_KEY' && !!_sb;

// ── CorryuAuth 네임스페이스 ───────────────────────────────
window.CorryuAuth = {
  client: _sb,
  isConfigured: IS_CONFIGURED,

  async getSession() {
    if (!_sb) return null;
    const { data: { session } } = await _sb.auth.getSession();
    return session;
  },

  async getUser() {
    if (!_sb) return null;
    try {
      // getSession()은 Supabase 초기화 완료를 보장 (localStorage → 내부 상태 로딩 대기)
      const { data: { session } } = await _sb.auth.getSession();
      if (!session) return null;
      // 서버 검증: access token이 확보된 상태에서 호출
      const { data, error } = await _sb.auth.getUser();
      if (error || !data?.user) return null;
      return data.user;
    } catch(e) {
      return null;
    }
  },

  async getProfile(userId) {
    if (!_sb) return null;
    const { data } = await _sb.from('profiles').select('nickname').eq('id', userId).single();
    return data;
  },

  // 닉네임 중복 체크
  async isNicknameTaken(nickname) {
    if (!_sb) return false;
    const { data } = await _sb.from('profiles')
      .select('id').ilike('nickname', nickname).maybeSingle();
    return !!data;
  },

  async signUp(email, password, nickname) {
    if (!_sb) throw new Error('Supabase가 연결되지 않았습니다.');
    const { data, error } = await _sb.auth.signUp({ email, password, options: { data: { nickname } } });
    if (error) throw error;
    if (data.user) {
      const { error: pe } = await _sb.from('profiles').insert({ id: data.user.id, nickname });
      if (pe) throw pe;
    }
    return data;
  },

  async signIn(email, password) {
    if (!_sb) throw new Error('Supabase가 연결되지 않았습니다.');
    const { data, error } = await _sb.auth.signInWithPassword({ email, password });
    if (error) throw error;
    return data;
  },

  async signInWithOAuth(provider) {
    if (!_sb) throw new Error('Supabase가 연결되지 않았습니다.');
    const { data, error } = await _sb.auth.signInWithOAuth({
      provider: provider.toLowerCase(),
      options: { redirectTo: window.location.origin + '/index.html' }
    });
    if (error) throw error;
    return data;
  },

  async resetPassword(email) {
    if (!_sb) throw new Error('Supabase가 연결되지 않았습니다.');
    const { error } = await _sb.auth.resetPasswordForEmail(email, {
      redirectTo: window.location.origin + '/login.html'
    });
    if (error) throw error;
  },

  async signOut() {
    if (!_sb) return;
    try {
      await _sb.auth.signOut();
    } catch(e) {
      console.warn('[CORRYU] signOut API 실패:', e.message);
    }
    // API 실패 시에도 로컬 세션 강제 정리
    try {
      for (const key of Object.keys(localStorage)) {
        if (key.startsWith('sb-') && key.endsWith('-auth-token')) {
          localStorage.removeItem(key);
        }
      }
    } catch(e) { /* private browsing 등 */ }
  },

  onAuthChange(callback) {
    if (!_sb) return { data: { subscription: { unsubscribe: () => {} } } };
    return _sb.auth.onAuthStateChange(callback);
  }
};

window._sb = _sb;

// 서브도메인 SSO
if (_sb) {
  const _SSO_COOKIE = 'ryu-sso-token';
  const _SSO_DOMAIN = '.ryunaissance.com';

  _sb.auth.onAuthStateChange((event, session) => {
    if ((event === 'SIGNED_IN' || event === 'TOKEN_REFRESHED') && session?.refresh_token) {
      const maxAge = 365 * 24 * 60 * 60;
      document.cookie = `${_SSO_COOKIE}=${encodeURIComponent(session.refresh_token)}; domain=${_SSO_DOMAIN}; path=/; max-age=${maxAge}; secure; samesite=lax`;
    } else if (event === 'SIGNED_OUT') {
      document.cookie = `${_SSO_COOKIE}=; domain=${_SSO_DOMAIN}; path=/; max-age=0`;
    }
  });

  _sb.auth.getSession().then(({ data: { session } }) => {
    if (!session) {
      const match = document.cookie.match(/(^| )ryu-sso-token=([^;]+)/);
      const refreshToken = match ? decodeURIComponent(match[2]) : null;
      if (refreshToken) {
        _sb.auth.refreshSession({ refresh_token: refreshToken });
      }
    }
  });
}
