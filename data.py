import streamlit as st
import akshare as ak
import pandas as pd
import time
import os
import json
from datetime import datetime, date, timedelta
from utils import clean_etf_symbol
import hashlib

# 缓存目录
CACHE_DIR = "data_cache"
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

ETF_LIST_CACHE = os.path.join(CACHE_DIR, "etf_list.csv")
ETF_LIST_CACHE_TTL = 30  # 天

def get_cache_file_path(symbol):
    """获取缓存文件路径"""
    return os.path.join(CACHE_DIR, f"{symbol}_data.csv")

def get_metadata_file_path():
    """获取元数据文件路径"""
    return os.path.join(CACHE_DIR, "metadata.json")

def load_metadata():
    """加载元数据"""
    metadata_file = get_metadata_file_path()
    if os.path.exists(metadata_file):
        try:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            st.warning(f"加载元数据失败: {e}")
    return {}

def save_metadata(metadata):
    """保存元数据"""
    try:
        # 确保缓存目录存在
        if not os.path.exists(CACHE_DIR):
            os.makedirs(CACHE_DIR)
            
        metadata_file = get_metadata_file_path()
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.warning(f"保存元数据失败: {e}")

def is_cache_valid(symbol):
    """检查缓存是否有效（当天数据）"""
    metadata = load_metadata()
    today = date.today().isoformat()
    # 确保symbol为字符串类型
    symbol_str = str(symbol)
    return metadata.get(symbol_str, {}).get('date') == today

def save_to_cache(symbol, df):
    """保存数据到缓存"""
    try:
        # 确保缓存目录存在
        if not os.path.exists(CACHE_DIR):
            os.makedirs(CACHE_DIR)
            
        cache_file = get_cache_file_path(symbol)
        df.to_csv(cache_file, encoding='utf-8')
        
        # 更新元数据
        metadata = load_metadata()
        # 确保symbol为字符串类型
        symbol_str = str(symbol)
        metadata[symbol_str] = {
            'date': date.today().isoformat(),
            'rows': len(df),
            'columns': list(df.columns)
        }
        save_metadata(metadata)
        
        st.success(f"{symbol}数据已缓存")
    except Exception as e:
        st.warning(f"缓存{symbol}数据失败: {e}")

def load_from_cache(symbol):
    """从缓存加载数据"""
    try:
        cache_file = get_cache_file_path(symbol)
        if os.path.exists(cache_file):
            # 确保日期索引正确解析
            df = pd.read_csv(cache_file, index_col=0)
            df.index = pd.to_datetime(df.index)
            return df
    except Exception as e:
        st.warning(f"加载{symbol}缓存失败: {e}")
    return None

# 获取所有ETF列表
@st.cache_data(ttl=24*3600)  # 缓存24小时，避免频繁请求
def get_etf_list(force_refresh=False):
    # 先查缓存，除非强制刷新
    if not force_refresh and os.path.exists(ETF_LIST_CACHE):
        mtime = datetime.fromtimestamp(os.path.getmtime(ETF_LIST_CACHE))
        if (datetime.now() - mtime).days < ETF_LIST_CACHE_TTL:
            try:
                df = pd.read_csv(ETF_LIST_CACHE)
                if not df.empty:
                    return df
            except Exception as e:
                st.warning(f"ETF列表缓存读取失败: {e}")
    # 缓存无效或不存在，或强制刷新，重新拉取
    try:
        etf_spot = ak.fund_etf_spot_ths()
        if not etf_spot.empty:
            etf_list = etf_spot[['基金代码', '基金名称']].rename(columns={'基金代码': 'symbol', '基金名称': 'name'})
            etf_list['symbol'] = etf_list['symbol'].apply(clean_etf_symbol)
            etf_list = etf_list.drop_duplicates(subset=['symbol'])
            etf_list.to_csv(ETF_LIST_CACHE, index=False)
            st.success("ETF列表缓存已刷新！")
            return etf_list
        else:
            st.warning("ak.fund_etf_spot_ths()返回空，尝试读取本地ETF列表缓存")
    except Exception as e:
        st.warning(f"获取ETF列表失败: {str(e)}，尝试读取本地ETF列表缓存")
    # 兜底：本地csv
    if os.path.exists(ETF_LIST_CACHE):
        try:
            df = pd.read_csv(ETF_LIST_CACHE)
            return df
        except Exception as e:
            st.error(f"本地ETF列表缓存读取失败: {e}")
    return pd.DataFrame(columns=['symbol', 'name'])

# 获取ETF历史数据（带重试机制+CSV缓存）
def fetch_etf_data_with_retry(symbol, start_date, end_date, etf_list, max_retries=3, delay=1):
    # 检查缓存是否有效
    if is_cache_valid(symbol):
        cached_data = load_from_cache(symbol)
        if cached_data is not None:
            # 筛选时间范围
            start_date = pd.to_datetime(start_date)
            end_date = pd.to_datetime(end_date)
            filtered_data = cached_data[(cached_data.index >= start_date) & (cached_data.index <= end_date)]
            if not filtered_data.empty:
                st.info(f"使用{symbol}缓存数据")
                # 返回符合组合回测格式的数据
                clean_symbol = clean_etf_symbol(symbol)
                row = etf_list[etf_list['symbol'] == symbol]
                if not row.empty:
                    etf_name = row['name'].values[0]
                else:
                    etf_name = symbol
                    st.warning(f"ETF代码 {symbol} 不在ETF列表中，已用代码作为名称")
                return filtered_data[['收盘']].rename(columns={'收盘': f"{clean_symbol}_{etf_name}"})
    
    # 缓存无效或不存在，从API获取完整数据
    st.info(f"从API获取{symbol}完整数据...")
    for attempt in range(max_retries):
        try:
            clean_symbol = clean_etf_symbol(symbol)
            row = etf_list[etf_list['symbol'] == symbol]
            if not row.empty:
                etf_name = row['name'].values[0]
            else:
                etf_name = symbol
                st.warning(f"ETF代码 {symbol} 不在ETF列表中，已用代码作为名称")
            st.write(f"📥 获取 {etf_name}({symbol}) 的完整历史数据...")
            
            # 获取完整数据（不指定日期范围）
            df = ak.fund_etf_hist_em(
                symbol=clean_symbol,
                period='daily',
                adjust='qfq'
            )
            
            if df.empty:
                st.warning(f"⚠️ {etf_name}({symbol}) 返回空数据")
                return pd.DataFrame()
            
            df['日期'] = pd.to_datetime(df['日期'])
            df.set_index('日期', inplace=True)
            
            # 保存完整数据到缓存
            save_to_cache(symbol, df)
            
            # 筛选请求的时间范围
            start_date = pd.to_datetime(start_date)
            end_date = pd.to_datetime(end_date)
            filtered_df = df[(df.index >= start_date) & (df.index <= end_date)]
            
            if filtered_df.empty:
                st.warning(f"⚠️ {etf_name}({symbol}) 在选定日期范围内无数据")
                return pd.DataFrame()
                
            date_range = f"{filtered_df.index.min().strftime('%Y-%m-%d')} ~ {filtered_df.index.max().strftime('%Y-%m-%d')}"
            days = len(filtered_df)
            st.write(f"📆 {etf_name}({symbol}) 数据区间：{date_range}，共 {days} 天")
            
            # 返回符合组合回测格式的数据
            return filtered_df[['收盘']].rename(columns={'收盘': f"{clean_symbol}_{etf_name}"})
            
        except Exception as e:
            if attempt < max_retries - 1:
                st.warning(f"⚠️ 获取 {symbol} 数据失败 (尝试 {attempt + 1}/{max_retries}), 将在 {delay}秒后重试...")
                time.sleep(delay)
                continue
            st.warning(f"⚠️ 无法获取 {symbol} 的数据: {str(e)}")
            # 尝试使用历史缓存数据
            cached_data = load_from_cache(symbol)
            if cached_data is not None:
                start_date = pd.to_datetime(start_date)
                end_date = pd.to_datetime(end_date)
                filtered_data = cached_data[(cached_data.index >= start_date) & (cached_data.index <= end_date)]
                if not filtered_data.empty:
                    st.warning(f"使用{symbol}历史缓存数据")
                    clean_symbol = clean_etf_symbol(symbol)
                    row = etf_list[etf_list['symbol'] == symbol]
                    if not row.empty:
                        etf_name = row['name'].values[0]
                    else:
                        etf_name = symbol
                        st.warning(f"ETF代码 {symbol} 不在ETF列表中，已用代码作为名称")
                    return filtered_data[['收盘']].rename(columns={'收盘': f"{clean_symbol}_{etf_name}"})
            return pd.DataFrame()

if st.button("让AI分析合适的投资策略"):
    st.info("已发送AI请求，正在等待AI返回结果...")
    try:
        csv_data = df.head(200).to_csv(index=False)
        prompt = f"以下是某些资产的历史日期和收盘价数据，请你作为专业投资顾问，分析适合的投资策略（如定投、轮动、趋势、均值回归等），并说明理由和注意事项：\n{csv_data}"
        with st.spinner("AI正在分析，请稍候..."):
            result = ai_chat(prompt, api_key=api_key)
        if not result or result.strip() == "":
            st.error("AI未返回结果，请检查API Key和网络，或稍后重试。")
        elif "AI调用失败" in result:
            st.error(result)
        else:
            st.markdown("#### AI策略建议：")
            st.write(result)
    except Exception as e:
        st.error(f"AI分析异常: {e}")