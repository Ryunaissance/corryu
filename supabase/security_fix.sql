-- =====================================================================
-- CORRYU 보안 이슈 수정 마이그레이션
-- Supabase Dashboard → SQL Editor 에서 실행하세요
--
-- 수정 항목:
--   1. Security Definer View     → security_invoker = on 으로 변경
--   2. RLS Disabled (etf_dividend) → RLS 활성화 + 공개 읽기 정책
--   3. Function Search Path Mutable → SET search_path = '' 고정
--
-- ※ Warning "Leaked Password Protection" 은 SQL로 수정 불가
--    Supabase Dashboard → Authentication → Settings →
--    "Enable HaveIBeenPwned (HIBP) integration" 을 수동으로 활성화하세요.
-- =====================================================================


-- ── 1. Security Definer View 수정 ─────────────────────────────────
-- 문제: ticker_likes 집계 뷰들이 뷰 소유자(superuser) 권한으로 실행되어
--       RLS 정책을 우회하고 모든 행에 접근 가능.
-- 수정: security_invoker = on → 호출한 사용자의 권한으로 실행.
--       ticker_likes 테이블에 "tl_public_read" 정책이 있으므로
--       anon/authenticated 모두 정상 조회 유지.

create or replace view public.ticker_likes_total
  with (security_invoker = on) as
  select ticker, count(*)::int as total_likes
  from public.ticker_likes
  group by ticker;

create or replace view public.ticker_likes_monthly
  with (security_invoker = on) as
  select ticker, count(*)::int as monthly_likes
  from public.ticker_likes
  where created_at >= date_trunc('month', now() at time zone 'UTC')
  group by ticker;

create or replace view public.ticker_likes_weekly
  with (security_invoker = on) as
  select ticker, count(*)::int as weekly_likes
  from public.ticker_likes
  where created_at >= date_trunc('week', now() at time zone 'UTC')
  group by ticker;


-- ── 2. etf_dividend 테이블 RLS 활성화 ────────────────────────────
-- 문제: etf_dividend 테이블에 RLS가 비활성화 상태.
--       anon 사용자가 테이블 전체를 무제한 조회/수정 가능.
-- 수정: RLS 활성화 + 읽기 전용 공개 정책 추가.
--       배당 데이터는 공개 정보이므로 select는 모두 허용,
--       write는 service_role 전용으로 제한.

alter table public.etf_dividend enable row level security;

-- 공개 읽기 허용 (배당 데이터는 공개 정보)
create policy "etf_dividend_public_read"
  on public.etf_dividend
  for select
  using (true);

-- ※ INSERT/UPDATE/DELETE 정책 미추가 = service_role 만 가능
--   (anon/authenticated 는 기본 차단)


-- ── 3. sync_vote_counts 함수 search_path 고정 ─────────────────────
-- 문제: search_path가 가변적이면 악의적 스키마 객체 삽입으로
--       함수 실행 흐름 조작 가능 (search path injection).
-- 수정: SET search_path = '' 로 완전 고정하고
--       함수 내 테이블 참조를 schema-qualified(public.) 로 변경.

create or replace function public.sync_vote_counts()
returns trigger
language plpgsql
security definer
set search_path = ''       -- ← 핵심 수정: 빈 search_path로 인젝션 차단
as $$
declare
  _cid uuid := coalesce(NEW.comment_id, OLD.comment_id);
begin
  update public.comments          -- schema-qualified
  set
    likes    = (
      select count(*)
      from public.comment_votes   -- schema-qualified
      where comment_id = _cid
        and vote_type = 'like'
    ),
    dislikes = (
      select count(*)
      from public.comment_votes   -- schema-qualified
      where comment_id = _cid
        and vote_type = 'dislike'
    )
  where id = _cid;
  return null;
end;
$$;


-- ── 4. 수정 결과 확인 쿼리 ────────────────────────────────────────

-- View security_invoker 확인
select viewname, definition
from pg_views
where schemaname = 'public'
  and viewname like 'ticker_likes%';

-- RLS 활성화 확인
select tablename, rowsecurity
from pg_tables
where schemaname = 'public'
  and tablename in ('etf_dividend', 'ticker_likes', 'comments', 'comment_votes', 'profiles', 'portfolios');

-- 함수 search_path 확인
select proname, proconfig
from pg_proc
join pg_namespace on pg_proc.pronamespace = pg_namespace.oid
where nspname = 'public'
  and proname = 'sync_vote_counts';
