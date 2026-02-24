"""
월간 수익률 기반 상관행렬 생성 스크립트
- etf_close_data_cleaned.pkl 을 읽어 월말(ME) 가격으로 리샘플링
- 월간 수익률(pct_change) 계산
- 최소 12개월 이상 데이터가 있는 ETF만 포함 (결측치 많은 신생 ETF 제외)
- 상관행렬을 correlation_matrix_monthly.csv 로 저장
"""
import pandas as pd
import pickle

print("📊 월간 수익률 기반 상관행렬 생성 중...")

with open('data_processed/etf_close_data_cleaned.pkl', 'rb') as f:
    df_close = pickle.load(f)

print(f"  원본 일간 데이터: {df_close.shape[0]}일 × {df_close.shape[1]}종목")

# 월말 종가로 리샘플링
df_monthly = df_close.resample('ME').last()
print(f"  월간 리샘플 후: {df_monthly.shape[0]}개월 × {df_monthly.shape[1]}종목")

# 월간 수익률 계산
df_ret = df_monthly.pct_change(fill_method=None)

# 최소 36개월(3년) 이상 유효 수익률 데이터 있는 컬럼만 유지
min_months = 36
valid = df_ret.columns[df_ret.count() >= min_months]
df_ret = df_ret[valid]
print(f"  최소 {min_months}개월 필터링 후: {len(valid)}종목")

# 상관행렬 계산 (NaN 있는 부분은 pairwise 처리)
print("  상관행렬 계산 중... (시간 소요)")
corr_monthly = df_ret.corr(method='pearson', min_periods=24)

# 저장
out_path = 'correlation_matrix_monthly.csv'
corr_monthly.to_csv(out_path)
print(f"✅ 저장 완료: {out_path}  shape={corr_monthly.shape}")
