import streamlit as st
import pandas as pd
import numpy as np
import akshare as ak
import datetime
from ai_utils import ai_chat, get_api_key, set_api_key

st.set_page_config(page_title="ETF排行榜", page_icon="🏆", layout="wide")
st.title("🏆 ETF排行榜")

st.markdown("本页展示场内交易基金近一月涨幅排名前50和后50的品种，数据来源：东方财富网，供快速筛选强弱势基金参考。")

def get_today_str():
    return datetime.date.today().strftime('%Y-%m-%d')

@st.cache_data
def get_etf_rank_data(today_str):
    return ak.fund_exchange_rank_em()

today_str = get_today_str()

# --- AI Key输入与保存 ---
# （已移除API Key输入区）

with st.spinner("正在获取场内基金排行数据..."):
    try:
        df = get_etf_rank_data(today_str)
        st.write(f"数据获取成功，共{len(df)}条记录")
        # 确保近1月字段存在且为数值型
        if '近1月' in df.columns:
            df['近1月'] = pd.to_numeric(df['近1月'], errors='coerce')
            df = df.dropna(subset=['近1月'])
            # 按近1月涨幅排序
            df_sorted = df.sort_values('近1月', ascending=False).reset_index(drop=True)
            # 显示主要字段
            display_columns = ['基金代码', '基金简称', '类型', '单位净值', '近1月', '近3月', '近1年', '成立日期']
            available_columns = [col for col in display_columns if col in df_sorted.columns]
            st.subheader("近一月涨幅前50名基金")
            st.dataframe(
                df_sorted.head(50)[available_columns].style.format({
                    '单位净值': '{:.4f}',
                    '近1月': '{:.2f}%',
                    '近3月': '{:.2f}%',
                    '近1年': '{:.2f}%'
                }), 
                use_container_width=True
            )
            st.subheader("近一月涨幅后50名基金")
            st.dataframe(
                df_sorted.tail(50).sort_values('近1月')[available_columns].style.format({
                    '单位净值': '{:.4f}',
                    '近1月': '{:.2f}%',
                    '近3月': '{:.2f}%',
                    '近1年': '{:.2f}%'
                }), 
                use_container_width=True
            )
            # 显示统计信息
            st.subheader("统计信息")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("平均涨幅", f"{df_sorted['近1月'].mean():.2f}%")
            with col2:
                st.metric("最高涨幅", f"{df_sorted['近1月'].max():.2f}%")
            with col3:
                st.metric("最低涨幅", f"{df_sorted['近1月'].min():.2f}%")
            # --- AI智能分析按钮 ---
            st.markdown("---")
            api_key = get_api_key()
            if st.button("让AI分析涨幅排行有什么规律"):
                if not api_key:
                    st.warning("未检测到API Key，请前往【API密钥配置】页面设置，否则无法使用AI分析功能。")
                else:
                    prompt = "请分析以下ETF近一月涨幅排行前20的数据，指出行业、风格、主题等特征和投资机会，简明总结规律：\n" + df_sorted.head(20).to_csv(index=False)
                    with st.spinner("AI正在分析，请稍候..."):
                        result = ai_chat(prompt, api_key=api_key)
                    st.markdown("#### AI分析结果：")
                    st.write(result)
        else:
            st.error("数据中未找到'近1月'字段")
            st.write("可用字段：", df.columns.tolist())
    except Exception as e:
        st.error(f"获取数据失败: {e}")
        st.write("请检查网络连接或稍后重试") 