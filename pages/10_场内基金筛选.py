import streamlit as st
import pandas as pd
import akshare as ak

st.title("场内基金筛选（东方财富网）")

st.markdown("""
本页可筛选场内交易基金，默认条件：成立超5年，年化收益率（成立来）大于10%。数据来源：东方财富网。
""")

@st.cache_data(ttl=3600)
def get_exchange_fund():
    return ak.fund_exchange_rank_em()

df = get_exchange_fund()

# 筛选条件
min_years = st.number_input("最短成立年限(年)", min_value=0, max_value=30, value=5)
min_cagr = st.number_input("最低年化收益率(%)", min_value=0.0, max_value=100.0, value=10.0, step=0.1)

df = df.copy()
df['成立来'] = pd.to_numeric(df['成立来'], errors='coerce')
df['成立日期'] = pd.to_datetime(df['成立日期'], errors='coerce')
df['成立年限'] = (pd.to_datetime('today') - df['成立日期']).dt.days / 365.25
# 用成立来总收益和成立年限算年化收益率（CAGR）
def calc_cagr(total_return, years):
    try:
        if pd.isna(total_return) or pd.isna(years) or years <= 0:
            return None
        total_return = total_return / 100
        if total_return <= -1:
            return None
        cagr = (1 + total_return) ** (1/years) - 1
        return cagr * 100
    except:
        return None
df['成立来年化(%)'] = df.apply(lambda row: calc_cagr(row['成立来'], row['成立年限']), axis=1)

filtered = df[(df['成立年限'] >= min_years) & (df['成立来年化(%)'] >= min_cagr) & (~df['成立来年化(%)'].isna())]

st.info(f"共筛选出 {len(filtered)} 只场内基金，满足：成立超{min_years}年，年化收益率大于{min_cagr}%")

cols_to_show = ['基金代码','基金简称','类型','成立年限','成立来','成立来年化(%)','单位净值','累计净值','近1年','近3年','手续费']
cols_exist = [col for col in cols_to_show if col in filtered.columns]
st.dataframe(filtered[cols_exist]
    .sort_values('成立来年化(%)', ascending=False)
    .style.format({'成立年限': '{:.1f}','成立来': '{:.2f}%','成立来年化(%)': '{:.2f}%','单位净值': '{:.3f}','累计净值': '{:.3f}','近1年': '{:.2f}%','近3年': '{:.2f}%'}),
    use_container_width=True) 