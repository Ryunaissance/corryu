-- =====================================================================
-- CORRYU 댓글 시스템 마이그레이션
-- Supabase Dashboard → SQL Editor 에서 순서대로 실행하세요
-- =====================================================================

-- ── 1. profiles (닉네임) ─────────────────────────────────────────────
create table if not exists profiles (
  id         uuid primary key references auth.users(id) on delete cascade,
  nickname   text not null,
  created_at timestamptz not null default now()
);

-- 닉네임 소문자 유니크 인덱스 (대소문자 구분 없이 중복 방지)
create unique index if not exists profiles_nickname_unique
  on profiles (lower(nickname));

alter table profiles enable row level security;

create policy "profiles_public_read"  on profiles for select using (true);
create policy "profiles_own_insert"   on profiles for insert to authenticated with check (auth.uid() = id);
create policy "profiles_own_update"   on profiles for update to authenticated using (auth.uid() = id);


-- ── 2. comments ──────────────────────────────────────────────────────
create table if not exists comments (
  id         uuid        primary key default gen_random_uuid(),
  ticker     text        not null,
  user_id    uuid        not null references auth.users(id) on delete cascade,
  nickname   text        not null,
  content    text        not null check (char_length(content) between 1 and 2000),
  parent_id  uuid        references comments(id) on delete cascade,
  depth      smallint    not null default 0 check (depth in (0, 1)),
  likes      int         not null default 0,
  dislikes   int         not null default 0,
  is_deleted boolean     not null default false,
  created_at timestamptz not null default now()
);

-- 티커 기준 최신순 조회 인덱스
create index if not exists comments_ticker_date_idx
  on comments (ticker, created_at desc) where not is_deleted;

-- 부모 댓글 기준 답글 조회 인덱스
create index if not exists comments_parent_idx
  on comments (parent_id, created_at asc) where not is_deleted;

alter table comments enable row level security;

create policy "comments_public_read"   on comments for select using (true);
create policy "comments_auth_insert"   on comments for insert to authenticated
  with check (auth.uid() = user_id and depth <= 1);
create policy "comments_own_update"    on comments for update to authenticated
  using (auth.uid() = user_id);   -- 소프트 삭제 (is_deleted = true) 용도


-- ── 3. comment_votes (중복 투표 방지) ───────────────────────────────
create table if not exists comment_votes (
  id         uuid        primary key default gen_random_uuid(),
  comment_id uuid        not null references comments(id) on delete cascade,
  user_id    uuid        not null references auth.users(id) on delete cascade,
  vote_type  text        not null check (vote_type in ('like', 'dislike')),
  created_at timestamptz not null default now(),
  unique (comment_id, user_id)
);

alter table comment_votes enable row level security;

create policy "votes_public_read"  on comment_votes for select using (true);
create policy "votes_auth_insert"  on comment_votes for insert to authenticated
  with check (auth.uid() = user_id);
create policy "votes_own_update"   on comment_votes for update to authenticated
  using (auth.uid() = user_id);
create policy "votes_own_delete"   on comment_votes for delete to authenticated
  using (auth.uid() = user_id);


-- ── 4. 좋아요/싫어요 자동 카운트 트리거 ─────────────────────────────
create or replace function sync_vote_counts()
returns trigger language plpgsql security definer as $$
declare
  _cid uuid := coalesce(NEW.comment_id, OLD.comment_id);
begin
  update comments
  set
    likes    = (select count(*) from comment_votes where comment_id = _cid and vote_type = 'like'),
    dislikes = (select count(*) from comment_votes where comment_id = _cid and vote_type = 'dislike')
  where id = _cid;
  return null;
end;
$$;

drop trigger if exists trg_vote_counts on comment_votes;
create trigger trg_vote_counts
  after insert or update or delete on comment_votes
  for each row execute function sync_vote_counts();


-- ── 5. 확인 쿼리 (실행 후 결과 확인) ──────────────────────────────
select tablename, rowsecurity
from pg_tables
where schemaname = 'public'
  and tablename in ('profiles', 'comments', 'comment_votes');


-- ── 6. ticker_likes (종목 좋아요) ────────────────────────────────
create table if not exists ticker_likes (
  id         uuid        primary key default gen_random_uuid(),
  ticker     text        not null,
  user_id    uuid        not null references auth.users(id) on delete cascade,
  created_at timestamptz not null default now(),
  unique (ticker, user_id)
);

create index if not exists ticker_likes_ticker_idx   on ticker_likes (ticker);
create index if not exists ticker_likes_created_idx  on ticker_likes (created_at desc);

alter table ticker_likes enable row level security;

create policy "tl_public_read"  on ticker_likes for select using (true);
create policy "tl_auth_insert"  on ticker_likes for insert to authenticated
  with check (auth.uid() = user_id);
create policy "tl_own_delete"   on ticker_likes for delete to authenticated
  using (auth.uid() = user_id);


-- ── 7. 인기 종목 집계 뷰 ─────────────────────────────────────────
-- 누적 총 좋아요
create or replace view ticker_likes_total as
  select ticker, count(*)::int as total_likes
  from ticker_likes
  group by ticker;

-- 이번달 좋아요 (월 첫 날 00:00 UTC 기준)
create or replace view ticker_likes_monthly as
  select ticker, count(*)::int as monthly_likes
  from ticker_likes
  where created_at >= date_trunc('month', now() at time zone 'UTC')
  group by ticker;

-- 이번주 좋아요 (월요일 00:00 UTC 기준)
create or replace view ticker_likes_weekly as
  select ticker, count(*)::int as weekly_likes
  from ticker_likes
  where created_at >= date_trunc('week', now() at time zone 'UTC')
  group by ticker;


-- ── 8. portfolios (포트폴리오 서버 저장) ─────────────────────────
create table if not exists portfolios (
  user_id    uuid        primary key references auth.users(id) on delete cascade,
  rows       jsonb       not null default '[]',
  updated_at timestamptz not null default now()
);

alter table portfolios enable row level security;

create policy "portfolios_own_read"   on portfolios for select to authenticated using (auth.uid() = user_id);
create policy "portfolios_own_insert" on portfolios for insert to authenticated with check (auth.uid() = user_id);
create policy "portfolios_own_update" on portfolios for update to authenticated using (auth.uid() = user_id);


-- ── 9. 확인 쿼리 ──────────────────────────────────────────────────
select tablename, rowsecurity
from pg_tables
where schemaname = 'public'
  and tablename in ('profiles', 'comments', 'comment_votes', 'ticker_likes', 'portfolios');
