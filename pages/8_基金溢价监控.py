import streamlit as st
import pandas as pd
import numpy as np
import akshare as ak

st.title("基金溢价监控（QDII/LOF/ETF）")

st.markdown("""
本页用于监控QDII、LOF、ETF等基金的T-1日溢价率，数据来源：集思录。可自定义溢价率阈值，LOF优先展示。
""")

def fetch_qdii_data():
    try:
        qdii_data = ak.qdii_e_index_jsl()
        return qdii_data
    except Exception as e:
        st.error(f"获取数据失败: {e}")
        return None

def clean_data(data):
    if data is None:
        return None
    data = data.replace('-', np.nan)
    data['现价'] = pd.to_numeric(data['现价'], errors='coerce')
    # 处理溢价率字段 - 移除百分号并转为数值
    if 'T-1溢价率' in data.columns:
        data['T-1溢价率'] = data['T-1溢价率'].str.replace('%', '').astype(float)
    # 处理涨幅字段 - 移除百分号并转为数值
    if '涨幅' in data.columns:
        data['涨幅'] = data['涨幅'].str.replace('%', '').astype(float)
    # 处理指数涨幅字段 - 移除百分号并转为数值
    if 'T-1指数涨幅' in data.columns:
        data['T-1指数涨幅'] = data['T-1指数涨幅'].str.replace('%', '').astype(float)
    return data

def filter_and_monitor_premium_rate(data, threshold=1):
    if data is None:
        return None
    high_premium_funds = data[data['T-1溢价率'] > threshold]
    lof_funds = high_premium_funds[high_premium_funds['名称'].str.contains("LOF")]
    etf_funds = high_premium_funds[~high_premium_funds['名称'].str.contains("LOF")]
    result = pd.concat([lof_funds, etf_funds], ignore_index=True)
    return result

threshold = st.number_input("溢价率阈值(%)", min_value=0.0, max_value=10.0, value=1.0, step=0.1)

# 默认渲染数据
with st.spinner("正在获取QDII/LOF/ETF溢价数据..."):
    raw_data = fetch_qdii_data()
    data = clean_data(raw_data)
    result = filter_and_monitor_premium_rate(data, threshold)
    if result is None or result.empty:
        st.info("暂无溢价率高于阈值的基金。")
    else:
        # 显示主要字段
        display_columns = ['代码', '名称', '现价', '涨幅', 'T-1溢价率', 'T-1估值', '净值日期', '基金公司']
        available_columns = [col for col in display_columns if col in result.columns]
        st.dataframe(result[available_columns].sort_values('T-1溢价率', ascending=False), use_container_width=True)

# 添加刷新按钮
if st.button("刷新监控数据"):
    st.rerun() 