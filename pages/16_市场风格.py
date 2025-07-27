import streamlit as st
import akshare as ak
import pandas as pd
import os

# 设置页面配置
st.set_page_config(page_title="市场风格分析", page_icon="📊", layout="wide")

# 页面标题
st.title("📊 市场风格分析")
st.markdown("""
本页面通过计算创业板指数、中证红利指数、沪深300指数和中证1000指数在近20日、60日和250日的涨幅，
来判断短期、中期和长期的市场风格（成长/价值、大盘/小盘）。
""")

# 定义指数代码
chuangye_index = "sz399006"  # 创业板指数
zhongzheng_dividend_index = "sh000922"  # 中证红利指数
hushen300_index = "sh000300"  # 沪深300指数
zhongzheng1000_index = "sh000852"  # 中证1000指数

# 获取当前日期
end_date = pd.Timestamp.today().strftime("%Y%m%d")
# 定义20天、60天和250天前的日期
start_date_20 = (pd.Timestamp(end_date) - pd.Timedelta(days=20)).strftime("%Y%m%d")
start_date_60 = (pd.Timestamp(end_date) - pd.Timedelta(days=60)).strftime("%Y%m%d")
start_date_250 = (pd.Timestamp(end_date) - pd.Timedelta(days=250)).strftime("%Y%m%d")

@st.cache_data
def get_index_data(symbol, start_date, end_date):
    try:
        df = ak.stock_zh_index_daily_em(symbol=symbol, start_date=start_date, end_date=end_date)
        return df
    except Exception as e:
        st.error(f"获取指数数据失败: {e}")
        return pd.DataFrame()

# 获取指数数据
chuangye_df = get_index_data(chuangye_index, start_date_250, end_date)
zhongzheng_dividend_df = get_index_data(zhongzheng_dividend_index, start_date_250, end_date)
hushen300_df = get_index_data(hushen300_index, start_date_250, end_date)
zhongzheng1000_df = get_index_data(zhongzheng1000_index, start_date_250, end_date)

# 检查数据是否为空
if chuangye_df.empty or zhongzheng_dividend_df.empty or hushen300_df.empty or zhongzheng1000_df.empty:
    st.error("未能获取到指数数据，请检查网络连接或稍后重试。")
else:
    # 确保数据按日期排序
    chuangye_df['date'] = pd.to_datetime(chuangye_df['date'])
    zhongzheng_dividend_df['date'] = pd.to_datetime(zhongzheng_dividend_df['date'])
    hushen300_df['date'] = pd.to_datetime(hushen300_df['date'])
    zhongzheng1000_df['date'] = pd.to_datetime(zhongzheng1000_df['date'])
    
    chuangye_df = chuangye_df.sort_values('date').reset_index(drop=True)
    zhongzheng_dividend_df = zhongzheng_dividend_df.sort_values('date').reset_index(drop=True)
    hushen300_df = hushen300_df.sort_values('date').reset_index(drop=True)
    zhongzheng1000_df = zhongzheng1000_df.sort_values('date').reset_index(drop=True)
    
    # 计算近20日、60日和250日涨幅
    # 短期 (20日)
    if len(chuangye_df) >= 21 and len(zhongzheng_dividend_df) >= 21 and len(hushen300_df) >= 21 and len(zhongzheng1000_df) >= 21:
        chuangye_return_20 = (chuangye_df['close'].iloc[-1] - chuangye_df['close'].iloc[-21]) / chuangye_df['close'].iloc[-21]
        zhongzheng_dividend_return_20 = (zhongzheng_dividend_df['close'].iloc[-1] - zhongzheng_dividend_df['close'].iloc[-21]) / zhongzheng_dividend_df['close'].iloc[-21]
        hushen300_return_20 = (hushen300_df['close'].iloc[-1] - hushen300_df['close'].iloc[-21]) / hushen300_df['close'].iloc[-21]
        zhongzheng1000_return_20 = (zhongzheng1000_df['close'].iloc[-1] - zhongzheng1000_df['close'].iloc[-21]) / zhongzheng1000_df['close'].iloc[-21]
    else:
        st.error("数据不足，无法计算20日涨幅。")
        chuangye_return_20 = zhongzheng_dividend_return_20 = hushen300_return_20 = zhongzheng1000_return_20 = 0
    
    # 中期 (60日)
    if len(chuangye_df) >= 61 and len(zhongzheng_dividend_df) >= 61 and len(hushen300_df) >= 61 and len(zhongzheng1000_df) >= 61:
        chuangye_return_60 = (chuangye_df['close'].iloc[-1] - chuangye_df['close'].iloc[-61]) / chuangye_df['close'].iloc[-61]
        zhongzheng_dividend_return_60 = (zhongzheng_dividend_df['close'].iloc[-1] - zhongzheng_dividend_df['close'].iloc[-61]) / zhongzheng_dividend_df['close'].iloc[-61]
        hushen300_return_60 = (hushen300_df['close'].iloc[-1] - hushen300_df['close'].iloc[-61]) / hushen300_df['close'].iloc[-61]
        zhongzheng1000_return_60 = (zhongzheng1000_df['close'].iloc[-1] - zhongzheng1000_df['close'].iloc[-61]) / zhongzheng1000_df['close'].iloc[-61]
    else:
        st.error("数据不足，无法计算60日涨幅。")
        chuangye_return_60 = zhongzheng_dividend_return_60 = hushen300_return_60 = zhongzheng1000_return_60 = 0
    
    # 长期 (250日)
    if len(chuangye_df) >= 250 and len(zhongzheng_dividend_df) >= 250 and len(hushen300_df) >= 250 and len(zhongzheng1000_df) >= 250:
        chuangye_return_250 = (chuangye_df['close'].iloc[-1] - chuangye_df['close'].iloc[-250]) / chuangye_df['close'].iloc[-250]
        zhongzheng_dividend_return_250 = (zhongzheng_dividend_df['close'].iloc[-1] - zhongzheng_dividend_df['close'].iloc[-250]) / zhongzheng_dividend_df['close'].iloc[-250]
        hushen300_return_250 = (hushen300_df['close'].iloc[-1] - hushen300_df['close'].iloc[-250]) / hushen300_df['close'].iloc[-250]
        zhongzheng1000_return_250 = (zhongzheng1000_df['close'].iloc[-1] - zhongzheng1000_df['close'].iloc[-250]) / zhongzheng1000_df['close'].iloc[-250]
    else:
        st.error("数据不足，无法计算250日涨幅。")
        chuangye_return_250 = zhongzheng_dividend_return_250 = hushen300_return_250 = zhongzheng1000_return_250 = 0
    
    # 判断短期市场风格
    if chuangye_return_20 > zhongzheng_dividend_return_20:
        short_term_style = "短期成长风格"
    else:
        short_term_style = "短期价值风格"
    
    if hushen300_return_20 > zhongzheng1000_return_20:
        short_term_size_style = "短期大盘风格"
    else:
        short_term_size_style = "短期小盘风格"
    
    # 判断中期市场风格
    if chuangye_return_60 > zhongzheng_dividend_return_60:
        medium_term_style = "中期成长风格"
    else:
        medium_term_style = "中期价值风格"
    
    if hushen300_return_60 > zhongzheng1000_return_60:
        medium_term_size_style = "中期大盘风格"
    else:
        medium_term_size_style = "中期小盘风格"
    
    # 判断长期市场风格
    if chuangye_return_250 > zhongzheng_dividend_return_250:
        long_term_style = "长期成长风格"
    else:
        long_term_style = "长期价值风格"
    
    if hushen300_return_250 > zhongzheng1000_return_250:
        long_term_size_style = "长期大盘风格"
    else:
        long_term_size_style = "长期小盘风格"
    
    # 显示结果
    st.subheader("📈 短期市场风格判断（近20日）")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("创业板指数涨幅", f"{chuangye_return_20:.2%}")
        st.metric("中证红利指数涨幅", f"{zhongzheng_dividend_return_20:.2%}")
    with col2:
        st.metric("沪深300指数涨幅", f"{hushen300_return_20:.2%}")
        st.metric("中证1000指数涨幅", f"{zhongzheng1000_return_20:.2%}")
    
    st.success(f"**{short_term_style}**")
    st.success(f"**{short_term_size_style}**")
    
    st.subheader("📈 中期市场风格判断（近60日）")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("创业板指数涨幅", f"{chuangye_return_60:.2%}")
        st.metric("中证红利指数涨幅", f"{zhongzheng_dividend_return_60:.2%}")
    with col2:
        st.metric("沪深300指数涨幅", f"{hushen300_return_60:.2%}")
        st.metric("中证1000指数涨幅", f"{zhongzheng1000_return_60:.2%}")
    
    st.success(f"**{medium_term_style}**")
    st.success(f"**{medium_term_size_style}**")
    
    st.subheader("📈 长期市场风格判断（近250日）")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("创业板指数涨幅", f"{chuangye_return_250:.2%}")
        st.metric("中证红利指数涨幅", f"{zhongzheng_dividend_return_250:.2%}")
    with col2:
        st.metric("沪深300指数涨幅", f"{hushen300_return_250:.2%}")
        st.metric("中证1000指数涨幅", f"{zhongzheng1000_return_250:.2%}")
    
    st.success(f"**{long_term_style}**")
    st.success(f"**{long_term_size_style}**")
    
    # 准备邮件内容
    email_content = f"日期: {end_date}\n\n"
    email_content += "短期市场风格判断：\n"
    email_content += f"创业板指数近20日涨幅: {chuangye_return_20:.2%}\n"
    email_content += f"中证红利指数近20日涨幅: {zhongzheng_dividend_return_20:.2%}\n"
    email_content += f"沪深300指数近20日涨幅: {hushen300_return_20:.2%}\n"
    email_content += f"中证1000指数近20日涨幅: {zhongzheng1000_return_20:.2%}\n"
    email_content += f"短期市场风格: {short_term_style}\n"
    email_content += f"短期市场风格: {short_term_size_style}\n\n"
    
    email_content += "中期市场风格判断：\n"
    email_content += f"创业板指数近60日涨幅: {chuangye_return_60:.2%}\n"
    email_content += f"中证红利指数近60日涨幅: {zhongzheng_dividend_return_60:.2%}\n"
    email_content += f"沪深300指数近60日涨幅: {hushen300_return_60:.2%}\n"
    email_content += f"中证1000指数近60日涨幅: {zhongzheng1000_return_60:.2%}\n"
    email_content += f"中期市场风格: {medium_term_style}\n"
    email_content += f"中期市场风格: {medium_term_size_style}\n\n"
    
    email_content += "长期市场风格判断：\n"
    email_content += f"创业板指数近250日涨幅: {chuangye_return_250:.2%}\n"
    email_content += f"中证红利指数近250日涨幅: {zhongzheng_dividend_return_250:.2%}\n"
    email_content += f"沪深300指数近250日涨幅: {hushen300_return_250:.2%}\n"
    email_content += f"中证1000指数近250日涨幅: {zhongzheng1000_return_250:.2%}\n"
    email_content += f"长期市场风格: {long_term_style}\n"
    email_content += f"长期市场风格: {long_term_size_style}\n"
    
    # 提供邮件内容下载
    st.download_button(
        label="📥 下载市场风格分析结果",
        data=email_content,
        file_name=f"市场风格分析_{end_date}.txt",
        mime="text/plain"
    )