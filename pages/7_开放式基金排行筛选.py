import streamlit as st
import pandas as pd
import akshare as ak

st.title("开放式基金排行筛选")

st.markdown("""
本页可按近3年年化收益率和成立时间等条件筛选开放式基金，数据来源：东方财富网。
默认筛选：成立超5年，近3年年化收益率大于10%。
""")

# 基金类型选择
symbol = st.selectbox("基金类型", ["全部", "股票型", "混合型", "债券型", "指数型", "QDII", "FOF"], index=0)

# 获取数据
@st.cache_data(ttl=3600)
def get_fund_rank(symbol):
    return ak.fund_open_fund_rank_em(symbol=symbol)

fund_df = get_fund_rank(symbol)

# 成立年限和年化收益率筛选
min_cagr = st.number_input("近3年最低年化收益率(%)", min_value=0.0, max_value=100.0, value=10.0, step=0.1)

# 处理成立时间
fund_df = fund_df.copy()
fund_df['成立来'] = pd.to_numeric(fund_df['成立来'], errors='coerce')
# 用近3年总收益算年化收益率（CAGR）
fund_df['近3年总收益'] = pd.to_numeric(fund_df['近3年'], errors='coerce')
def calc_cagr(total_return, years=3):
    try:
        if pd.isna(total_return):
            return None
        total_return = total_return / 100  # 转为增长倍数
        if total_return <= -1:
            return None
        cagr = (1 + total_return) ** (1/years) - 1
        return cagr * 100  # 百分比
    except:
        return None
fund_df['近3年年化'] = fund_df['近3年总收益'].apply(lambda x: calc_cagr(x, 3))

filtered = fund_df[(fund_df['近3年年化'] >= min_cagr) & (~fund_df['近3年年化'].isna())]

st.info(f"共筛选出 {len(filtered)} 只基金，满足：近3年年化收益率大于{min_cagr}%")

cols_to_show = ['基金代码','基金简称','近3年','近3年年化','单位净值','累计净值','近1年','成立来','近5年','手续费']
cols_exist = [col for col in cols_to_show if col in filtered.columns]
st.dataframe(filtered[cols_exist]
    .sort_values('近3年年化', ascending=False)
    .style.format({k: '{:.2f}%' for k in ['近3年','近3年年化','近1年','近5年','成立来'] if k in cols_exist} | {k: '{:.3f}' for k in ['单位净值','累计净值'] if k in cols_exist} | {'成立年限': '{:.1f}' if '成立年限' in cols_exist else ''}),
    use_container_width=True) 