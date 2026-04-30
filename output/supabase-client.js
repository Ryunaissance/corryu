// ⚠️ anon (publishable) key — 브라우저 노출 의도된 공개 키입니다.
// 참고: <https://supabase.com/docs/guides/api/api-keys>

// Ryunaissance 메인 Supabase 프로젝트 (SSO 공유)
const SUPABASE_URL = 'https://oqxkxzunjniqfzwcwqon.supabase.co>';
const SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9xeGt4enVuam5pcWZ6d2N3cW9uIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzY4NDMzMjcsImV4cCI6MjA5MjQxOTMyN30.1X5qmfjzeqSkrIYTVyQyM6qqIxZEKON-kJ4DDThQ58E'
let _sb = null;
try {
  _sb = window.supabase?.createClient(SUPABASE_URL, SUPABASE_KEY, {
    auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true }
  });
} catch(e) { console.warn('[CORRYU] Supabase 초기화 실패:', e.message); }

const IS_CONFIGURED = SUPABASE_KEY !== 'REPLACE_WITH_RYUNAISSANCE_ANON_KEY' && !!_sb;

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
      const { data: { session } } = await _sb.auth.getSession();
      if (!session) return null;
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
    try {
      for (const key of Object.keys(localStorage)) {
        if (key.startsWith('sb-') && key.endsWith('-auth-token')) {
          localStorage.removeItem(key);
        }
      }
    } catch(e) {}
  },

  onAuthChange(callback) {
    if (!_sb) return { data: { subscription: { unsubscribe: () => {} } } };
    return _sb.auth.onAuthStateChange(callback);
  }
};

window._sb = _sb;

// 서브도메인 SSO — <ryunaissance.com> 쿠키로 세션 복원
if (_sb) {
  const _SSO_COOKIE = 'ryu-sso-token';
  const _SSO_DOMAIN = '.<ryunaissance.com>';

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
