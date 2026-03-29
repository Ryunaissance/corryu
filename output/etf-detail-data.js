// ── etf-detail-data.js ───────────────────────────────────────────────────────
// 정적 보조 데이터: 수수료·발행사·구성종목·섹터명
// 의존성 없음. 가장 먼저 로드됨.
// ─────────────────────────────────────────────────────────────────────────────

// ── 보조 데이터 (수수료·발행사·구성종목 등 etf_data.json에 없는 정보) ─────────
const SUPP = {
  'SPY':  { issuer:'State Street Global Advisors', bench:'S&P 500',           structure:'UIT', div:'분기 배당', numH:503,
            desc:'S&P 500 지수를 추종하는 세계 최초·최대 규모의 ETF. 미국 대형주 500개를 시가총액 가중 방식으로 보유합니다.',
            holdings:[['AAPL','Apple Inc.',7.32],['MSFT','Microsoft Corp.',6.81],['NVDA','NVIDIA Corp.',5.94],['AMZN','Amazon.com Inc.',3.78],['META','Meta Platforms',2.65],['GOOGL','Alphabet Class A',2.10],['GOOG','Alphabet Class C',1.82],['BRK.B','Berkshire Hathaway B',1.63],['LLY','Eli Lilly & Co.',1.52],['JPM','JPMorgan Chase',1.47]],
            perf:{'1M':2.3,'3M':5.1,'YTD':8.7,'1Y':22.4,'3Y_ann':12.1,'5Y_ann':14.7} },
  'QQQ':  { issuer:'Invesco',                       bench:'Nasdaq-100',         structure:'Open-End',  div:'분기 배당', numH:101,
            desc:'Nasdaq-100 지수를 추종하며 기술·성장주 중심으로 구성된 ETF. FAANG 및 대형 기술주 비중이 높습니다.',
            holdings:[['AAPL','Apple Inc.',9.15],['MSFT','Microsoft Corp.',8.44],['NVDA','NVIDIA Corp.',7.92],['AMZN','Amazon.com Inc.',5.02],['META','Meta Platforms',4.81],['GOOGL','Alphabet Class A',2.72],['GOOG','Alphabet Class C',2.58],['TSLA','Tesla Inc.',2.35],['AVGO','Broadcom Inc.',2.21],['COST','Costco Wholesale',1.86]],
            perf:{'1M':3.1,'3M':7.8,'YTD':12.3,'1Y':28.5,'3Y_ann':15.4,'5Y_ann':19.2} },
  'IVV':  { issuer:'BlackRock (iShares)',           bench:'S&P 500',             structure:'Open-End',  div:'분기 배당', numH:503,
            desc:'iShares Core S&P 500 ETF. 0.03%의 최저 수수료로 S&P 500 지수를 추종합니다.',
            holdings:[['AAPL','Apple Inc.',7.32],['MSFT','Microsoft Corp.',6.81],['NVDA','NVIDIA Corp.',5.94],['AMZN','Amazon.com Inc.',3.78],['META','Meta Platforms',2.65],['GOOGL','Alphabet Class A',2.10],['GOOG','Alphabet Class C',1.82],['BRK.B','Berkshire Hathaway B',1.63],['LLY','Eli Lilly & Co.',1.52],['JPM','JPMorgan Chase',1.47]],
            perf:{'1M':2.3,'3M':5.1,'YTD':8.7,'1Y':22.4,'3Y_ann':12.1,'5Y_ann':14.7} },
  'VOO':  { issuer:'Vanguard',                      bench:'S&P 500',             structure:'Open-End',  div:'분기 배당', numH:503,
            desc:'Vanguard S&P 500 ETF. 업계 최저 수준의 수수료로 S&P 500 지수를 추종합니다.',
            holdings:[['AAPL','Apple Inc.',7.31],['MSFT','Microsoft Corp.',6.80],['NVDA','NVIDIA Corp.',5.93],['AMZN','Amazon.com Inc.',3.77],['META','Meta Platforms',2.64],['GOOGL','Alphabet Class A',2.09],['GOOG','Alphabet Class C',1.81],['BRK.B','Berkshire Hathaway B',1.62],['LLY','Eli Lilly & Co.',1.51],['JPM','JPMorgan Chase',1.46]],
            perf:{'1M':2.3,'3M':5.1,'YTD':8.7,'1Y':22.3,'3Y_ann':12.0,'5Y_ann':14.6} },
  'VTI':  { issuer:'Vanguard',                      bench:'CRSP US Total Market',structure:'Open-End',  div:'분기 배당', numH:3615,
            desc:'미국 전체 주식 시장(대형·중형·소형주 포함)에 한 번에 투자하는 Total Market ETF.',
            holdings:[['AAPL','Apple Inc.',6.42],['MSFT','Microsoft Corp.',5.96],['NVDA','NVIDIA Corp.',5.21],['AMZN','Amazon.com Inc.',3.31],['META','Meta Platforms',2.32],['GOOGL','Alphabet Class A',1.84],['BRK.B','Berkshire Hathaway B',1.64],['GOOG','Alphabet Class C',1.59],['LLY','Eli Lilly & Co.',1.33],['JPM','JPMorgan Chase',1.28]],
            perf:{'1M':2.1,'3M':4.8,'YTD':8.2,'1Y':21.8,'3Y_ann':11.7,'5Y_ann':14.3} },
  'GLD':  { issuer:'State Street Global Advisors', bench:'LBMA Gold Price',      structure:'Grantor Trust', div:'무배당', numH:1,
            desc:'실물 금 가격을 추종하는 세계 최대 금 ETF. 주당 약 1/10 트로이온스의 금을 보유합니다.',
            holdings:[['GOLD','Physical Gold (0.1 oz/share)',100.0]],
            perf:{'1M':1.8,'3M':9.2,'YTD':11.4,'1Y':18.7,'3Y_ann':8.3,'5Y_ann':11.2} },
  'TLT':  { issuer:'BlackRock (iShares)',           bench:'ICE US Treasury 20+Y', structure:'Open-End', div:'월 배당', numH:26,
            desc:'만기 20년 이상 미국 장기 국채를 추종하는 ETF. 금리 하락 시 수익, 금리 상승 시 손실이 두드러집니다.',
            holdings:[['UST1','US Treasury 4.500% 2054',15.2],['UST2','US Treasury 4.125% 2054',9.8],['UST3','US Treasury 3.875% 2053',8.7],['UST4','US Treasury 4.250% 2052',7.3],['UST5','US Treasury 3.000% 2048',6.1],['UST6','US Treasury 2.250% 2052',5.4],['UST7','US Treasury 3.625% 2053',5.2],['UST8','US Treasury 1.875% 2051',4.8],['UST9','US Treasury 2.375% 2049',4.3],['UST10','US Treasury 2.875% 2049',3.9]],
            perf:{'1M':-1.2,'3M':-3.4,'YTD':-4.1,'1Y':-8.3,'3Y_ann':-12.4,'5Y_ann':-6.8} },
  'XLK':  { issuer:'State Street Global Advisors', bench:'S&P Technology Select Sector', structure:'Open-End', div:'분기 배당', numH:67,
            desc:'S&P 500 내 기술 섹터 기업을 모두 담은 ETF. 소프트웨어·하드웨어·반도체 기업을 포함합니다.',
            holdings:[['MSFT','Microsoft Corp.',22.81],['AAPL','Apple Inc.',20.05],['NVDA','NVIDIA Corp.',17.42],['AVGO','Broadcom Inc.',4.62],['ORCL','Oracle Corp.',3.18],['CSCO','Cisco Systems',3.05],['ADBE','Adobe Inc.',2.34],['CRM','Salesforce Inc.',2.21],['ACN','Accenture PLC',2.14],['AMD','Advanced Micro Devices',1.97]],
            perf:{'1M':4.2,'3M':9.8,'YTD':15.4,'1Y':34.2,'3Y_ann':18.6,'5Y_ann':22.8} },
  'XLF':  { issuer:'State Street Global Advisors', bench:'S&P Financials Select Sector', structure:'Open-End', div:'분기 배당', numH:72,
            desc:'S&P 500 내 금융 섹터(은행·보험·투자은행·카드)를 추종하는 ETF.',
            holdings:[['BRK.B','Berkshire Hathaway B',13.24],['JPM','JPMorgan Chase',12.81],['V','Visa Inc.',8.34],['MA','Mastercard Inc.',7.12],['BAC','Bank of America',4.62],['WFC','Wells Fargo',4.21],['GS','Goldman Sachs',3.84],['MS','Morgan Stanley',3.41],['SPGI','S&P Global Inc.',2.95],['BLK','BlackRock Inc.',2.78]],
            perf:{'1M':1.8,'3M':4.2,'YTD':7.1,'1Y':18.4,'3Y_ann':10.2,'5Y_ann':12.1} },
  'XLV':  { issuer:'State Street Global Advisors', bench:'S&P Healthcare Select Sector', structure:'Open-End', div:'분기 배당', numH:63,
            desc:'S&P 500 내 헬스케어 섹터(제약·바이오·의료기기·보험)를 추종하는 ETF.',
            holdings:[['LLY','Eli Lilly & Co.',12.84],['UNH','UnitedHealth Group',11.42],['JNJ','Johnson & Johnson',8.35],['ABBV','AbbVie Inc.',7.23],['MRK','Merck & Co.',6.84],['TMO','Thermo Fisher',4.21],['DHR','Danaher Corp.',3.82],['ABT','Abbott Laboratories',3.41],['PFE','Pfizer Inc.',3.12],['AMGN','Amgen Inc.',2.94]],
            perf:{'1M':0.8,'3M':2.4,'YTD':4.1,'1Y':10.2,'3Y_ann':8.4,'5Y_ann':10.8} },
  'XLE':  { issuer:'State Street Global Advisors', bench:'S&P Energy Select Sector', structure:'Open-End', div:'분기 배당', numH:22,
            desc:'S&P 500 내 에너지 섹터(정유·가스·정제·서비스)를 추종하는 ETF.',
            holdings:[['XOM','Exxon Mobil Corp.',23.74],['CVX','Chevron Corp.',18.32],['COP','ConocoPhillips',6.84],['EOG','EOG Resources',5.21],['MPC','Marathon Petroleum',4.87],['SLB','SLB (Schlumberger)',4.62],['PSX','Phillips 66',4.38],['VLO','Valero Energy',3.95],['OXY','Occidental Petroleum',3.42],['KMI','Kinder Morgan',2.87]],
            perf:{'1M':-1.4,'3M':-2.8,'YTD':-3.2,'1Y':4.2,'3Y_ann':22.4,'5Y_ann':16.8} },
  'IWM':  { issuer:'BlackRock (iShares)',           bench:'Russell 2000',        structure:'Open-End', div:'분기 배당', numH:2000,
            desc:'미국 소형주 약 2,000개로 구성된 Russell 2000 지수를 추종합니다. 미국 내수 경기에 민감합니다.',
            holdings:[['SMCI','Super Micro Computer',0.52],['MTSI','MACOM Technology',0.41],['VIRT','Virtu Financial',0.38],['SPSC','SPS Commerce',0.36],['MGNI','Magnite Inc.',0.34],['AEIS','Advanced Energy Ind.',0.33],['TMDX','TransMedics Group',0.32],['SKYW','SkyWest Inc.',0.31],['CTRE','CareTrust REIT',0.30],['HALO','Halozyme Therapeutics',0.29]],
            perf:{'1M':1.2,'3M':3.4,'YTD':5.8,'1Y':14.2,'3Y_ann':6.4,'5Y_ann':9.1} },
  'VEA':  { issuer:'Vanguard',                      bench:'FTSE Dev. All Cap ex US', structure:'Open-End', div:'반기 배당', numH:3900,
            desc:'미국·캐나다를 제외한 선진국 주식(유럽·일본·호주 등)에 투자하는 ETF.',
            holdings:[['NESN','Nestlé S.A.',1.82],['ASML','ASML Holding',1.74],['NOVN','Novartis AG',1.41],['RHHBY','Roche Holding',1.38],['SAP','SAP SE',1.35],['TM','Toyota Motor',1.31],['RDSA','Shell plc',1.24],['AZN','AstraZeneca',1.22],['SIE','Siemens AG',1.18],['HSBC','HSBC Holdings',1.14]],
            perf:{'1M':1.8,'3M':4.1,'YTD':6.3,'1Y':10.4,'3Y_ann':5.2,'5Y_ann':7.8} },
  'VWO':  { issuer:'Vanguard',                      bench:'FTSE Emerging Markets', structure:'Open-End', div:'반기 배당', numH:5600,
            desc:'중국·인도·브라질·한국 등 신흥국 주식 시장에 투자하는 ETF.',
            holdings:[['TSM','Taiwan Semiconductor',5.84],['BABA','Alibaba Group',3.42],['TCS','Tata Consultancy',2.18],['RELI','Reliance Industries',2.04],['PDD','PDD Holdings',1.94],['SMSN','Samsung Electronics',1.87],['JD','JD.com Inc.',1.52],['BIDU','Baidu Inc.',1.41],['INFY','Infosys Ltd.',1.32],['MBT','Mobile TeleSystems',1.24]],
            perf:{'1M':1.4,'3M':3.8,'YTD':5.2,'1Y':8.4,'3Y_ann':2.1,'5Y_ann':4.8} },
  'VNQ':  { issuer:'Vanguard',                      bench:'MSCI US IMI Real Estate 25/50', structure:'Open-End', div:'분기 배당', numH:163,
            desc:'미국 부동산 투자신탁(REITs)과 부동산 관련 기업에 투자하는 ETF.',
            holdings:[['PLD','Prologis Inc.',5.91],['AMT','American Tower',4.83],['EQIX','Equinix Inc.',4.12],['WELL','Welltower Inc.',3.47],['SPG','Simon Property Group',3.22],['DLR','Digital Realty',2.98],['PSA','Public Storage',2.76],['O','Realty Income Corp.',2.65],['CCI','Crown Castle',2.41],['WY','Weyerhaeuser',2.14]],
            perf:{'1M':1.4,'3M':3.8,'YTD':4.2,'1Y':12.3,'3Y_ann':2.8,'5Y_ann':7.4} },
  'HYG':  { issuer:'BlackRock (iShares)',           bench:'iBoxx USD Liquid HY', structure:'Open-End', div:'월 배당', numH:1195,
            desc:'미국 투기등급(하이일드) 회사채를 추종하는 ETF. 높은 배당 수익률과 신용 리스크가 특징.',
            holdings:[['HY01','T-Mobile USA 3.875% 2030',0.58],['HY02','Telecom Italia 5.303% 2034',0.45],['HY03','Carnival Corp. 6.000% 2029',0.43],['HY04','Ford Motor 4.750% 2043',0.41],['HY05','CCO Holdings 4.500% 2032',0.38],['HY06','Netflix Inc. 4.875% 2030',0.36],['HY07','Centene Corp. 4.625% 2029',0.35],['HY08','Bausch Health 5.250% 2030',0.33],['HY09','DISH DBS 5.875% 2024',0.32],['HY10','Pitney Bowes 6.350% 2037',0.31]],
            perf:{'1M':0.8,'3M':2.1,'YTD':1.9,'1Y':8.7,'3Y_ann':4.2,'5Y_ann':4.8} },
  'BND':  { issuer:'Vanguard',                      bench:'Bloomberg US Aggregate', structure:'Open-End', div:'월 배당', numH:10418,
            desc:'미국 투자등급 채권 전체(국채·회사채·MBS)를 추종하는 종합 채권 ETF.',
            holdings:[['UST','US Treasury Notes/Bonds',44.21],['GNMA','GNMA (정부 모기지)',20.14],['FNMA','Fannie Mae MBS',15.38],['CORP','Investment Grade Corp',12.41],['FHLMC','Freddie Mac MBS',5.83],['ABS','Asset-Backed Securities',2.03]],
            perf:{'1M':0.4,'3M':1.2,'YTD':0.8,'1Y':2.3,'3Y_ann':-1.8,'5Y_ann':0.4} },
  'GBTC': { issuer:'Grayscale Investments',         bench:'Bitcoin Price',        structure:'Spot BTC ETF', div:'무배당', numH:1,
            desc:'미국 SEC 승인 현물 비트코인 ETF. 비트코인을 직접 보유하며, BTC 가격을 1:1로 추종합니다.',
            holdings:[['BTC','Bitcoin (BTC)',100.0]],
            perf:{'1M':12.4,'3M':38.7,'YTD':45.2,'1Y':124.3,'3Y_ann':28.4,'5Y_ann':48.7} },
  'SQQQ': { issuer:'ProShares',                     bench:'Nasdaq-100 × −3',      structure:'Open-End', div:'분기 배당', numH:0,
            desc:'Nasdaq-100 지수의 일일 수익률 ×−3배를 추종하는 인버스 레버리지 ETF. 단기 하락 베팅·헤징 목적.',
            holdings:[],
            perf:{'1M':-8.9,'3M':-21.4,'YTD':-34.2,'1Y':-67.4,'3Y_ann':-42.8,'5Y_ann':-51.3} },
  'PEY':  { issuer:'Invesco',                       bench:'NASDAQ US Dividend Achievers 50', structure:'Open-End', div:'월 배당', numH:50,
            desc:'미국 고배당 우량주 50개를 선별해 배당 성장 실적에 따라 투자하는 ETF. 월 배당이 특징.',
            holdings:[['ALT','Altria Group Inc.',2.42],['T','AT&T Inc.',2.35],['LEG','Leggett & Platt',2.31],['UVV','Universal Corp.',2.28],['HEP','Holly Energy Partners',2.24],['BKH','Black Hills Corp.',2.21],['ESS','Essex Property Trust',2.18],['OHI','Omega Healthcare',2.15],['LAMR','Lamar Advertising',2.12],['NNN','National Retail Prop.',2.09]],
            perf:{'1M':0.8,'3M':2.4,'YTD':3.2,'1Y':8.4,'3Y_ann':4.2,'5Y_ann':7.8} },
  'UYR':  { issuer:'ProShares',                     bench:'Dow Jones US Real Estate × 2', structure:'Open-End', div:'분기 배당', numH:30,
            desc:'미국 부동산(REITs) 지수의 일일 수익률 ×2배를 추종하는 레버리지 ETF.',
            holdings:[['PLD','Prologis (레버리지)',5.91],['AMT','American Tower (레버리지)',4.83],['EQIX','Equinix (레버리지)',4.12]],
            perf:{'1M':2.8,'3M':7.6,'YTD':8.4,'1Y':22.1,'3Y_ann':3.2,'5Y_ann':9.8} },
  'IWF':  { issuer:'BlackRock (iShares)',           bench:'Russell 1000 Growth',  structure:'Open-End', div:'분기 배당', numH:415,
            desc:'Russell 1000 성장주 지수를 추종하는 ETF. 기술·헬스케어·소비재 대형 성장주 중심.',
            holdings:[['NVDA','NVIDIA Corp.',12.34],['AAPL','Apple Inc.',12.21],['MSFT','Microsoft Corp.',11.84],['AMZN','Amazon.com',6.42],['META','Meta Platforms',5.81],['GOOGL','Alphabet Class A',4.12],['TSLA','Tesla Inc.',3.84],['AVGO','Broadcom Inc.',3.21],['GOOG','Alphabet Class C',2.95],['LLY','Eli Lilly',2.84]],
            perf:{'1M':3.4,'3M':8.2,'YTD':13.1,'1Y':32.4,'3Y_ann':16.8,'5Y_ann':20.4} },
};

// ── ETF 이름 첫 단어(브랜드)로 발행사 추론 ─────────────────
// ETF 명명 규칙: 맨 처음 단어 = 발행사 브랜드
const _ISSUER_PREFIX = {
  // ── 대형 (100개+) ────────────────────────────────────
  'iShares':        'BlackRock (iShares)',
  'Ishares':        'BlackRock (iShares)',
  'Invesco':        'Invesco',
  'SPDR':           'State Street Global Advisors',
  'Vanguard':       'Vanguard',
  'WisdomTree':     'WisdomTree',
  'Wisdomtree':     'WisdomTree',
  'ProShares':      'ProShares',
  'Proshares':      'ProShares',
  'First':          'First Trust',       // "First Trust ..."
  'FT':             'First Trust',       // "FT Cboe Vest ..."
  'Global':         'Global X (Mirae Asset)', // "Global X ..."
  'VanEck':         'VanEck',
  'Vaneck':         'VanEck',
  'Fidelity':       'Fidelity Investments',
  'JPMorgan':       'JPMorgan Asset Management',
  'Jpmorgan':       'JPMorgan Asset Management',
  'Direxion':       'Direxion',
  'Schwab':         'Charles Schwab',
  // ── 중형 (20~99개) ───────────────────────────────────
  'Avantis':        'Avantis Investors',
  'Dimensional':    'Dimensional Fund Advisors',
  'Goldman':        'Goldman Sachs Asset Management',
  'Franklin':       'Franklin Templeton',
  'Xtrackers':      'DWS (Xtrackers)',
  'Nuveen':         'Nuveen',
  'ALPS':           'ALPS Advisors',
  'AdvisorShares':  'AdvisorShares',
  'Roundhill':      'Roundhill Investments',
  'Daily':          'Roundhill Investments',   // "Daily 2X ..." (Roundhill)
  'YieldMax':       'YieldMax',
  'Yieldmax':       'YieldMax',
  'MicroSectors':    'REX Shares (MicroSectors)',
  'MicroSectors\u2122':  'REX Shares (MicroSectors)', // MicroSectors™
  'MicroSectorsTM':  'REX Shares (MicroSectors)',
  'Microsectors':    'REX Shares (MicroSectors)',
  'U.S.':            'US Global Investors',            // "U.S. Global Jets ETF" 등
  'ALPS/CoreCommodity': 'ALPS Advisors',               // "ALPS/CoreCommodity Natural Resources"
  'Pacer':          'Pacer Financial',
  'The':            'State Street Global Advisors', // "The ... Select Sector SPDR"
  'Amplify':        'Amplify ETFs',
  'NEOS':           'NEOS Investment Management',
  'Neos':           'NEOS Investment Management',
  // ── 소형 (10~19개) ───────────────────────────────────
  'Tema':           'Tema ETFs',
  'VictoryShares':  'VictoryShares',
  'Victoryshares':  'VictoryShares',
  'Themes':         'Themes ETFs',
  'KraneShares':    'KraneShares',
  'ARK':            'ARK Investment Management',
  'PIMCO':          'PIMCO',
  'T.':             'T. Rowe Price',             // "T. Rowe Price ..."
  'Innovator':      'Innovator Capital Management',
  'Macquarie':      'Macquarie Asset Management',
  'abrdn':          'abrdn',
  'Sprott':         'Sprott Asset Management',
  'Volatility':     'Volatility Shares',
  'Teucrium':       'Teucrium Trading',
  'American':       'American Century Investments',
  'Strive':         'Strive Asset Management',
  'Harbor':         'Harbor Capital Advisors',
  'GraniteShares':  'GraniteShares',
  'Putnam':         'Franklin Templeton',
  'Janus':          'Janus Henderson',
  'Grayscale':      'Grayscale Investments',
  'Bitwise':        'Bitwise Asset Management',
  'Defiance':       'Defiance ETFs',
  'CoinShares':     'CoinShares',
  // ── 소수 (1~9개) ─────────────────────────────────────
  'Robo':           'ROBO Global',
  'BNY':            'BNY Mellon',
  'Zacks':          'Zacks Investment Management',
  'RiverFront':     'RiverFront Investment Group',
  'VistaShares':    'VistaShares',
  'Eaton':          'Eaton Vance',
  '2x':             'Volatility Shares',
  '-1x':            'Volatility Shares',
  'One':            'Volatility Shares',        // "One+One S&P 500 and Bitcoin ETF"
  'Davis':          'Davis Advisors',
  'ClearBridge':    'ClearBridge Investments',
  'Tortoise':       'Tortoise Capital',
  'USCF':           'USCF Investments',
  'Alerian':        'SS&C (Alerian)',
  'United':         'United States Commodity Funds',
  'State':          'State Street Global Advisors',
  'Principal':      'Principal Global Investors',
  'US':             'US Global Investors',
  'Transatlantic':  'Transatlantic Capital',
  'Point':          'Point Bridge Capital',
  'Barclays':       'Barclays',
  'Procure':        'Procure Asset Management',
  "Barron's":       'ALPS Advisors',
  'Cambria':        'Cambria Investment Management',
  'Western':        'Franklin Templeton',
  'UBS':            'UBS',
  'Select':         'State Street Global Advisors',
  'Listed':         'Teucrium',               // "Listed Funds Trust / Teucrium"
  'Solana':         'REX Shares',
  '21Shares':       '21Shares',
  '21shares':       '21Shares',
  'Fortuna':        'Fortuna Funds',
};
function inferIssuer(name) {
  if (!name) return '';
  const w = name.trim().split(/\s+/);
  // "T. Rowe Price" — 첫 단어가 "T."이면 두 번째 단어로 보완
  if (w[0] === 'T.' && w[1] === 'Rowe') return 'T. Rowe Price';
  // "Goldman Sachs" — 발행사로 표기
  if (w[0] === 'Goldman' && w[1] === 'Sachs') return 'Goldman Sachs Asset Management';
  // "BNY Mellon" — 발행사로 표기
  if (w[0] === 'BNY' && w[1] === 'Mellon') return 'BNY Mellon';
  return _ISSUER_PREFIX[w[0]] || '';
}

// 섹터 ID → 이름 매핑 (간소화)
const SECTOR_NAMES = {
  S01:'📈 US 대형주',S02:'💻 테크놀로지',S03:'🏥 헬스케어',S04:'🏦 금융',S05:'🛍️ 경기소비재',
  S06:'🛒 필수소비재',S07:'🏭 산업재',S08:'⚡ 유틸리티',S09:'📡 커뮤니케이션',S10:'⛏️ 소재',
  S11:'🌍 국제선진국',S12:'🌏 신흥국',S13:'📊 중소형주',S14:'🏛️ 투자등급채권',S15:'💵 단기채/현금성',
  S16:'⚠️ 하이일드',S17:'📈 TIPS/인플레이션',S18:'✨ 금/귀금속',S19:'🛢️ 에너지/원자재',
  S20:'🏘️ 부동산/REITs',S21:'₿ 가상자산',S22:'📉 인버스/숏',S24:'🧩 테마/특수목적'
};
