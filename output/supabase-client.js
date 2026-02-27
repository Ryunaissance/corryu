/**
 * CORRYU Supabase 클라이언트
 * ─────────────────────────────────────────────────────────
 * 1. Supabase 프로젝트 생성: https://supabase.com
 * 2. Dashboard → Settings → API 에서 URL과 anon key 복사
 * 3. 아래 두 값을 교체하세요
 * 4. supabase_migration.sql 을 SQL Editor에서 실행하세요
 * ─────────────────────────────────────────────────────────
 */
const SUPABASE_URL = 'https://YOUR_PROJECT_ID.supabase.co';
const SUPABASE_KEY = 'YOUR_ANON_PUBLIC_KEY';

// ── 클라이언트 초기화 ─────────────────────────────────────
let _sb = null;
try {
  _sb = window.supabase?.createClient(SUPABASE_URL, SUPABASE_KEY, {
    auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true }
  });
} catch(e) { console.warn('[CORRYU] Supabase 초기화 실패:', e.message); }

const IS_CONFIGURED = SUPABASE_URL !== 'https://YOUR_PROJECT_ID.supabase.co' && !!_sb;

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
    const s = await this.getSession();
    return s?.user ?? null;
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
      options: { redirectTo: window.location.origin + '/index' }
    });
    if (error) throw error;
    return data;
  },

  async resetPassword(email) {
    if (!_sb) throw new Error('Supabase가 연결되지 않았습니다.');
    const { error } = await _sb.auth.resetPasswordForEmail(email, {
      redirectTo: window.location.origin + '/login'
    });
    if (error) throw error;
  },

  async signOut() {
    if (!_sb) return;
    await _sb.auth.signOut();
  },

  onAuthChange(callback) {
    if (!_sb) return { data: { subscription: { unsubscribe: () => {} } } };
    return _sb.auth.onAuthStateChange(callback);
  }
};

window._sb = _sb;
