-- =====================================================================
-- CORRYU ETF 가격 데이터 마이그레이션
-- Supabase Dashboard → SQL Editor 에서 실행
-- =====================================================================

-- ── 1. etf_prices (OHLCV + adj_close 일봉 데이터) ──────────────────
create table if not exists etf_prices (
    ticker    text    not null,
    date      date    not null,
    open      real,
    high      real,
    low       real,
    close     real    not null,
    volume    bigint  not null default 0,
    adj_close real    not null,
    primary key (ticker, date)
);

-- 티커별 날짜 내림차순 조회 인덱스 (차트, 기술지표 계산용)
create index if not exists etf_prices_ticker_date_idx
    on etf_prices (ticker, date desc);

-- RLS: 공개 읽기만 허용, 쓰기는 service_role key 사용 스크립트만
alter table etf_prices enable row level security;

create policy "etf_prices_public_read"
    on etf_prices for select using (true);


-- ── 2. etf_prices_log (적재 진행 추적용) ───────────────────────────
-- 초기 bulk 적재 시 어떤 티커까지 완료됐는지 기록 → 중단 후 재개 가능
create table if not exists etf_prices_log (
    ticker      text        primary key,
    loaded_at   timestamptz not null default now(),
    row_count   int         not null default 0
);

alter table etf_prices_log enable row level security;

create policy "etf_prices_log_public_read"
    on etf_prices_log for select using (true);


-- ── 3. 확인 쿼리 ───────────────────────────────────────────────────
select tablename, rowsecurity
from pg_tables
where schemaname = 'public'
  and tablename in ('etf_prices', 'etf_prices_log');
