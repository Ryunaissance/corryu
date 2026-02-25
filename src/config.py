"""
CORRYU ETF Dashboard - 전역 설정 모듈
섹터 정의, 앵커 매핑, 분류 임계값, 레거시 규칙, 수동 오버라이드
"""
import os

# ── 경로 ─────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PROCESSED = os.path.join(BASE_DIR, 'data_processed')
DATA_SCRAPED = os.path.join(BASE_DIR, 'data_scraped')
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')
CORR_MONTHLY_CSV = os.path.join(BASE_DIR, 'correlation_matrix_monthly.csv')
CORR_DAILY_CSV = os.path.join(BASE_DIR, 'correlation_matrix.csv')

# ── 내 보유 종목 ──────────────────────────────────────
MY_PORTFOLIO = ['PEY', 'HYG', 'GBTC', 'GLD', 'VNQ', 'UYR', 'XLE']

# ── 분류 임계값 ──────────────────────────────────────
CORR_THRESHOLD = 0.55       # Pass 2 상관계수 최소 기준
PROTECT_EQUITIES = {        # 비주식 앵커에 끌려가면 안 되는 핵심 주식 ETF
    'VOO', 'IVV', 'SPY', 'VTI', 'VEA', 'IEFA', 'VWO', 'IEMG', 'VXUS',
    'VT', 'SCHB', 'ITOT', 'SCHX', 'VV', 'IWB', 'QQQ', 'IVW', 'VUG',
    'IWF', 'VTV', 'IWD', 'IWM', 'IJR', 'IJH', 'MDY', 'VB', 'VO',
    'IWR', 'IWO', 'IWN', 'VBR', 'VBK', 'XLK', 'XLV', 'XLF', 'XLY',
    'XLP', 'XLI', 'XLU', 'XLC', 'XLB', 'SMH', 'SOXX',
    # 주의: XLE는 S19(에너지) 앵커이므로 여기서 제외
}

# ── 자산군 정의 ──────────────────────────────────────
ASSET_CLASSES = {
    'EQUITY':      {'name': '주식',     'name_en': 'Equity',       'icon': '📈', 'order': 1},
    'FIXED_INCOME':{'name': '채권',     'name_en': 'Fixed Income', 'icon': '🛡️', 'order': 2},
    'REAL_ASSETS': {'name': '실물자산', 'name_en': 'Real Assets',  'icon': '🏗️', 'order': 3},
    'ALTERNATIVE': {'name': '대안',     'name_en': 'Alternatives', 'icon': '⚡', 'order': 4},
    'THEMATIC':    {'name': '테마',     'name_en': 'Thematic',     'icon': '🧩', 'order': 5},
}

# ── 섹터 정의 (24개) ─────────────────────────────────
SECTOR_DEFS = {
    # --- EQUITY (13개) ---
    'S01': {'name': 'US 대형주 종합',   'name_en': 'US Large Cap',           'anchor': 'VOO',  'asset_class': 'EQUITY',       'icon': '🇺🇸'},
    'S02': {'name': '테크놀로지',       'name_en': 'Technology',             'anchor': 'XLK',  'asset_class': 'EQUITY',       'icon': '💻'},
    'S03': {'name': '헬스케어',         'name_en': 'Healthcare',             'anchor': 'XLV',  'asset_class': 'EQUITY',       'icon': '🏥'},
    'S04': {'name': '금융',             'name_en': 'Financials',             'anchor': 'XLF',  'asset_class': 'EQUITY',       'icon': '🏦'},
    'S05': {'name': '경기소비재',       'name_en': 'Consumer Discretionary', 'anchor': 'XLY',  'asset_class': 'EQUITY',       'icon': '🛍️'},
    'S06': {'name': '필수소비재',       'name_en': 'Consumer Staples',       'anchor': 'XLP',  'asset_class': 'EQUITY',       'icon': '🛒'},
    'S07': {'name': '산업재',           'name_en': 'Industrials',            'anchor': 'XLI',  'asset_class': 'EQUITY',       'icon': '🏭'},
    'S08': {'name': '유틸리티',         'name_en': 'Utilities',              'anchor': 'XLU',  'asset_class': 'EQUITY',       'icon': '⚡'},
    'S09': {'name': '커뮤니케이션',     'name_en': 'Communication',          'anchor': 'XLC',  'asset_class': 'EQUITY',       'icon': '📡'},
    'S10': {'name': '소재',             'name_en': 'Materials',              'anchor': 'XLB',  'asset_class': 'EQUITY',       'icon': '⛏️'},
    'S11': {'name': '국제선진국',       'name_en': 'Intl Developed',         'anchor': 'VEA',  'asset_class': 'EQUITY',       'icon': '🌍'},
    'S12': {'name': '신흥국',           'name_en': 'Emerging Markets',       'anchor': 'VWO',  'asset_class': 'EQUITY',       'icon': '🌏'},
    'S13': {'name': '중소형주',         'name_en': 'Small/Mid Cap',          'anchor': 'IWM',  'asset_class': 'EQUITY',       'icon': '📊'},
    # --- FIXED INCOME (4개) ---
    'S14': {'name': '투자등급 채권',    'name_en': 'Investment Grade',       'anchor': 'BND',  'asset_class': 'FIXED_INCOME', 'icon': '🏛️'},
    'S15': {'name': '단기채/현금성',    'name_en': 'Short-Term/Cash',        'anchor': 'SHV',  'asset_class': 'FIXED_INCOME', 'icon': '💵'},
    'S16': {'name': '하이일드/신흥채',  'name_en': 'High Yield/EM Debt',     'anchor': 'HYG',  'asset_class': 'FIXED_INCOME', 'icon': '⚠️'},
    'S17': {'name': 'TIPS/인플레이션',  'name_en': 'TIPS/Inflation',         'anchor': 'SCHP', 'asset_class': 'FIXED_INCOME', 'icon': '📈'},
    # --- REAL ASSETS (3개) ---
    'S18': {'name': '금/귀금속',        'name_en': 'Gold/Precious Metals',   'anchor': 'GLD',  'asset_class': 'REAL_ASSETS',  'icon': '✨'},
    'S19': {'name': '에너지/원자재',    'name_en': 'Energy/Commodities',     'anchor': 'XLE',  'asset_class': 'REAL_ASSETS',  'icon': '🛢️'},
    'S20': {'name': '부동산/REITs',     'name_en': 'Real Estate/REITs',      'anchor': 'VNQ',  'asset_class': 'REAL_ASSETS',  'icon': '🏘️'},
    # --- ALTERNATIVE (2개) ---
    'S21': {'name': '가상자산',         'name_en': 'Crypto/Digital',         'anchor': 'GBTC', 'asset_class': 'ALTERNATIVE',  'icon': '₿'},
    'S22': {'name': '인버스/숏',        'name_en': 'Inverse/Short',          'anchor': 'SQQQ', 'asset_class': 'ALTERNATIVE',  'icon': '📉'},
    # S23 레버리지 롱 폐지: 레버리지 상품은 기초자산 섹터에 분류
    # --- THEMATIC (1개) ---
    'S24': {'name': '테마/특수목적',    'name_en': 'Thematic/Specialty',     'anchor': None,   'asset_class': 'THEMATIC',     'icon': '🧩'},
}

# 앵커 → 섹터 역방향 매핑
ANCHOR_TO_SECTOR = {v['anchor']: k for k, v in SECTOR_DEFS.items() if v['anchor']}

# ── 키워드 분류 규칙 (Pass 1) ────────────────────────

# 단기채 보호용 키워드 (인버스로 잘못 분류되지 않게)
SHORT_TERM_BOND_WORDS = [
    'short term', 'short-term', 'short duration', 'short-duration',
    'short maturity', '0-1 year', '1-3 year', 'ultra-short', 'ultra short',
    'floating rate', 'floating-rate', 'money market', 'treasury bill',
    'cash reserve',
]

KEYWORD_RULES = {
    # 인버스/숏 (S22) - 단기채 키워드가 포함되어 있으면 제외
    'S22': {
        'keywords': ['inverse', ' bear ', 'proshares short', 'proshares ultrashort',
                     '-1x ', '-2x ', '-3x ', 'direxion daily.*bear',
                     'short s&p', 'short dow', 'short nasdaq', 'short russell',
                     'short midcap', 'short smallcap', 'short ftse',
                     'short msci', 'short real estate', 'short high yield'],
        'ticker_patterns': ['SH', 'PSQ', 'DOG', 'RWM', 'SDS', 'QID', 'DXD', 'TWM',
                           'SPXU', 'SQQQ', 'SDOW', 'SRTY', 'SPXS', 'TZA', 'FAZ',
                           'ERY', 'LABD', 'YANG', 'DUST', 'JDST', 'DRIP', 'GDXD',
                           'WEBS', 'UVIX', 'VIXY', 'VXX', 'SVXY',
                           # ProShares UltraShort 시리즈 (비주식 기초자산 인버스)
                           'GLL', 'ZSL', 'EUO', 'BZQ', 'EWV', 'EPV', 'FXP',
                           'SSG', 'SCO', 'SDP', 'BIS', 'SRS', 'KOLD', 'RXD', 'SDD'],
        'exclude_if': SHORT_TERM_BOND_WORDS,
    },
    # S23 레버리지 롱 폐지: 키워드 룰 제거 → 상관계수로 기초자산 섹터에 자동 배정
    # 가상자산 (S21)
    'S21': {
        'keywords': ['bitcoin', 'crypto', 'ethereum', 'blockchain', 'digital asset',
                     'digital currency'],
        'ticker_patterns': ['GBTC', 'IBIT', 'FBTC', 'ARKB', 'BITB', 'HODL',
                           'BRRR', 'EZBC', 'BTCO', 'BTCW', 'DEFI', 'ETHE',
                           'ETHV', 'CETH', 'FETH', 'ETHW'],
    },
    # TIPS/인플레이션 (S17)
    'S17': {
        'keywords': ['tips', 'inflation protected', 'inflation-protected',
                     'treasury inflation', 'real return'],
        'ticker_patterns': ['SCHP', 'TIP', 'VTIP', 'STIP', 'LTPZ', 'SPIP',
                           'TIPX', 'PBTP', 'RINF'],
    },
    # 단기채/현금성 (S15)
    'S15': {
        'keywords': SHORT_TERM_BOND_WORDS,
        'ticker_patterns': ['SHV', 'BIL', 'SGOV', 'SHY', 'VGSH', 'SCHO',
                           'NEAR', 'MINT', 'JPST', 'GSY', 'GBIL', 'VBIL',
                           'USFR', 'TFLO', 'FLOT', 'FLRN', 'ISHUF'],
    },
    # 하이일드/신흥채 (S16)
    'S16': {
        'keywords': ['high yield', 'high-yield', 'junk bond', 'fallen angel',
                     'senior loan', 'leveraged loan', 'bank loan',
                     'emerging market bond', 'emerging market debt',
                     'emerging markets bond'],
        'ticker_patterns': ['HYG', 'JNK', 'USHY', 'HYLB', 'SHYG', 'HYDB',
                           'ANGL', 'BKLN', 'SRLN', 'EMB', 'VWOB', 'PCY',
                           'EMLC', 'EMHY'],
    },
    # 부동산/REITs (S20)
    'S20': {
        'keywords': ['reit', 'real estate', 'mortgage', 'home builder',
                     'homebuilder', 'housing'],
        'ticker_patterns': ['VNQ', 'SCHH', 'IYR', 'XLRE', 'USRT', 'VNQI',
                           'RWO', 'REET', 'FREL', 'BBRE', 'REZ', 'RWR',
                           'ICF', 'MORT', 'REM'],
    },
    # 금/귀금속 (S18)
    # exclude_if: 'goldman' → "Goldman Sachs" ETF명 오매칭 방지
    #             'golden dragon' → Invesco Golden Dragon China(PGJ) 오매칭 방지
    'S18': {
        'keywords': ['gold', 'silver', 'precious metal', 'platinum', 'palladium',
                     'gold miner', 'silver miner', 'mining'],
        'ticker_patterns': ['GLD', 'IAU', 'SLV', 'GDX', 'GDXJ', 'SIL', 'SILJ',
                           'GLDM', 'SGOL', 'PHYS', 'PSLV', 'RING', 'GOAU',
                           'AAAU', 'BAR', 'OUNZ', 'GLTR', 'PPLT', 'PALL',
                           'SIVR', 'SLVP', 'GDLM'],
        'exclude_if': ['goldman', 'golden dragon'],
    },
}

# ── 태그 규칙 (대시보드 표시용) ──────────────────────
# 태그 기능 비활성화
TAG_RULES = {}

# ── 레거시 임계값 ────────────────────────────────────
LEGACY_MIN_AUM = 100_000_000           # $100M
LEGACY_MIN_TRADING_DAYS = 750          # ~3년
LEGACY_TRACKING_ERROR_THRESHOLD = 0.50 # 앵커 대비 r
LEGACY_NEAR_DUPLICATE_CORR = 0.95      # 같은 섹터 내 중복 기준
LEGACY_NEAR_DUPLICATE_TOP_N = 20       # 중복 체크 대상 (섹터 내 AUM 상위 N개)

# ── 수동 레거시 오버라이드 (기존 LEGACY_TICKERS 이관) ─
MANUAL_LEGACY_OVERRIDES = {
    # -- 금/귀금속 섹터 (GLD 중복) --
    'IAU': 'GLD와 상관계수 매우 높음',
    'SLV': 'GLD와 상관계수 매우 높음',
    'GDLM': 'GLD와 상관계수 매우 높음',
    'GDX': 'GLD와 상관계수 매우 높음',
    'PHYS': 'GLD와 상관계수 매우 높음',
    'PSLV': 'GLD와 상관계수 매우 높음',
    'GDXJ': 'GLD와 상관계수 매우 높음',
    'SGOL': 'GLD와 상관계수 매우 높음',
    'SIVR': 'GLD와 상관계수 매우 높음',
    'SIL': 'GLD와 상관계수 매우 높음',
    'SILJ': 'GLD와 상관계수 매우 높음',
    'GLTR': 'GLD와 상관계수 매우 높음',
    'RING': 'GLD와 상관계수 매우 높음',
    'AAAU': 'GLD와 상관계수 매우 높음',
    'OUNZ': 'GLD와 상관계수 매우 높음',
    'BAR': 'GLD와 상관계수 매우 높음',
    'SLVP': 'GLD와 상관계수 매우 높음',
    'SGDM': 'GLD와 상관계수 매우 높음',
    'SGDJ': 'GLD와 상관계수 매우 높음',
    'GLDM': 'GLD와 상관계수 매우 높음',
    'IAUM': '상장기간 너무 짧음',
    'GDE': '상장기간 너무 짧음',
    'IGLD': '상장기간 너무 짧음',
    'FGDL': '상장기간 너무 짧음',
    'SLVR': 'GLD와 상관계수 매우 높음',
    'IAUI': 'GLD와 상관계수 매우 높음',
    'GDMN': '상장기간 너무 짧음',
    'AUMI': 'GLD와 상관계수 매우 높음',
    'AGMI': 'GLD와 상관계수 매우 높음',
    'GOAU': 'GLD와 상관계수 매우 높음',
    'GOEX': 'GLD와 상관계수 매우 높음',
    'GLDI': 'GLD와 상관계수 매우 높음',
    'SHNY': '상장기간 너무 짧음',
    'GDXU': 'GLD와 상관계수 매우 높음',
    'AGQ': 'GLD와 상관계수 매우 높음',
    'NUGT': 'GLD와 상관계수 매우 높음',
    'PPLT': '변동성에 비해 수익이 낮음',
    'PALL': '변동성에 비해 수익이 낮음',
    'PLTM': '변동성에 비해 수익이 낮음',
    # -- 부동산/REITs 섹터 (VNQ 중복) --
    'SCHH': 'VNQ와 상관계수 매우 높음',
    'XLRE': 'VNQ와 상관계수 매우 높음',
    'BBRE': 'VNQ와 상관계수 매우 높음',
    'REET': 'VNQ와 상관계수 매우 높음',
    'IYR': 'VNQ와 상관계수 매우 높음',
    'VNQI': 'VNQ와 상관계수 매우 높음',
    'USRT': 'VNQ와 상관계수 매우 높음',
    'FREL': 'VNQ와 상관계수 매우 높음',
    'RWO': 'VNQ와 상관계수 매우 높음',
    'HAUZ': 'VNQ와 상관계수 매우 높음',
    'REZ': 'VNQ와 상관계수 매우 높음',
    'JPRE': '상장기간 너무 짧음',
    'IYRI': '상장기간 너무 짧음',
    'REIT': '상장기간 너무 짧음',
    'MORT': 'VNQ와 상관계수 매우 높음',
    'SRVR': 'VNQ와 상관계수 매우 높음',
    'RWX': 'VNQ와 상관계수 매우 높음',
    'FRI': 'VNQ와 상관계수 매우 높음',
    'RSPR': 'VNQ와 상관계수 매우 높음',
    'IFGL': 'VNQ와 상관계수 매우 높음',
    'PSR': 'VNQ와 상관계수 매우 높음',
    'XTRE': 'VNQ와 상관계수 매우 높음',
    'FPRO': '상장기간 너무 짧음',
    'ERET': '상장기간 너무 짧음',
    'JRE': '상장기간 너무 짧음',
    'DESK': '상장기간 너무 짧음',
    'NURE': 'VNQ와 상관계수 매우 높음',
    'WTRE': 'VNQ와 상관계수 매우 높음',
    'RNTY': '상장기간 너무 짧음',
    'RDOG': 'VNQ와 상관계수 매우 높음',
    'RWR': 'VNQ와 상관계수 매우 높음',
    'ICF': 'VNQ와 상관계수 매우 높음',
    'SRET': 'VNQ와 상관계수 매우 높음',
    'URE': 'VNQ와 상관계수 매우 높음',
    'DRN': 'VNQ와 상관계수 매우 높음',
    'INDS': 'VNQ와 상관계수 매우 높음',
    'IDGT': 'VNQ와 상관계수 매우 높음',
    'DFGR': '상장기간 너무 짧음',
    'DFAR': '상장기간 너무 짧음',
    'AVRE': '상장기간 너무 짧음',
    # -- 에너지/원자재 섹터 S19 (XLE 중복) --
    'VDE':  'XLE와 상관계수 매우 높음',
    'FENY': 'XLE와 상관계수 매우 높음',
    'IYE':  'XLE와 상관계수 매우 높음',
    'RSPG': 'XLE와 상관계수 매우 높음',
    'IXC':  'XLE와 상관계수 매우 높음',
    'IEO':  'XLE와 상관계수 매우 높음',
    'FILL': 'XLE와 상관계수 매우 높음',
    'PXI':  'XLE와 상관계수 매우 높음',
    'FXN':  'XLE와 상관계수 매우 높음',
    'IEZ':  'XLE와 상관계수 매우 높음',
    'OIH':  'XLE와 상관계수 매우 높음',
    'XOP':  'XLE와 상관계수 매우 높음',
    'ENFR': 'XLE와 상관계수 매우 높음',
    'UMI':  'XLE와 상관계수 매우 높음',
    'MLPX': 'XLE와 상관계수 매우 높음',
    'MLPA': 'XLE와 상관계수 매우 높음',
    'AMLP': 'XLE와 상관계수 매우 높음',
}

# 자동 레거시에서 면제할 ETF (예: 앵커 ETF는 자동 면제)
LEGACY_EXEMPTIONS = set()
# 앵커 ETF 자동 면제
for s_def in SECTOR_DEFS.values():
    if s_def['anchor']:
        LEGACY_EXEMPTIONS.add(s_def['anchor'])
