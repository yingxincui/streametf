import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import akshare as ak
from datetime import datetime, timedelta
import os
import json

# 动量策略页面

# 默认ETF池
DEFAULT_ETF_POOL = {
    '510300': '300ETF',
    '159915': '创业板',
    '513050': '中概互联网ETF',
    '159941': '纳指ETF',
    '518880': '黄金ETF',
    '511090':'30年国债'
}

# 缓存目录
CACHE_DIR = "etf_cache"
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

def get_cache_file_path(symbol):
    """获取缓存文件路径"""
    return os.path.join(CACHE_DIR, f"{symbol}_data.csv")

def get_cache_meta_file_path():
    """获取缓存元数据文件路径"""
    return os.path.join(CACHE_DIR, "cache_meta.json")

def load_cache_meta():
    """加载缓存元数据"""
    meta_file = get_cache_meta_file_path()
    if os.path.exists(meta_file):
        try:
            with open(meta_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_cache_meta(meta_data):
    """保存缓存元数据"""
    meta_file = get_cache_meta_file_path()
    try:
        with open(meta_file, 'w', encoding='utf-8') as f:
            json.dump(meta_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        small_log(f"保存缓存元数据失败: {e}")

def is_cache_valid(symbol):
    """检查缓存是否有效（同一天的数据）"""
    today = datetime.now().strftime('%Y-%m-%d')
    meta_data = load_cache_meta()
    
    # 确保symbol为字符串类型
    symbol_str = str(symbol)
    if symbol_str in meta_data:
        last_update = meta_data[symbol_str].get('last_update', '')
        return last_update == today
    return False

def save_to_cache(symbol, df):
    """保存数据到缓存"""
    try:
        cache_file = get_cache_file_path(symbol)
        df.to_csv(cache_file, encoding='utf-8')
        
        # 更新元数据
        meta_data = load_cache_meta()
        # 确保symbol为字符串类型
        symbol_str = str(symbol)
        meta_data[symbol_str] = {
            'last_update': datetime.now().strftime('%Y-%m-%d'),
            'data_length': len(df),
            'latest_date': df.index[-1].strftime('%Y-%m-%d') if len(df) > 0 else ''
        }
        save_cache_meta(meta_data)
        
    except Exception as e:
        small_log(f"保存{symbol}缓存失败: {e}")

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
        small_log(f"加载{symbol}缓存失败: {e}")
    return None

# 获取ETF数据的函数
def fetch_etf_data(symbol="510300"):
    # 检查缓存是否有效
    if is_cache_valid(symbol):
        cached_data = load_from_cache(symbol)
        if cached_data is not None:
            small_log(f"使用{symbol}缓存数据")
            return cached_data
    
    # 缓存无效或不存在，从API获取数据
    small_log(f"从API获取{symbol}数据...")
    try:
        # 使用 akshare 的 fund_etf_hist_em 接口获取 ETF 数据
        df = ak.fund_etf_hist_em(symbol=symbol, period="daily", adjust='qfq')
        # 转换日期格式
        df['日期'] = pd.to_datetime(df['日期'])  # 假设日期列名为 '日期'
        df.set_index('日期', inplace=True)
        # 重命名列以符合标准格式
        df.rename(columns={
            '开盘': 'Open',
            '最高': 'High',
            '最低': 'Low',
            '收盘': 'Close',
            '成交量': 'Volume'
        }, inplace=True)
        
        # 确保索引是datetime类型
        df.index = pd.to_datetime(df.index)
        
        # 保存到缓存
        save_to_cache(symbol, df)
        return df
        
    except Exception as e:
        small_log(f"获取{symbol}数据失败: {e}")
        # 尝试使用缓存数据（即使不是今天的）
        cached_data = load_from_cache(symbol)
        if cached_data is not None:
            small_log(f"使用{symbol}历史缓存数据")
            return cached_data
        return pd.DataFrame()

# 计算动量和均线
def calculate_momentum_and_ma(df, momentum_period=20, ma_period=28):
    # 计算动量：当前收盘价与20天前收盘价的百分比变化
    df['Momentum'] = df['Close'] / df['Close'].shift(momentum_period) - 1
    # 计算28天均线
    df['MA'] = df['Close'].rolling(window=ma_period).mean()
    return df

# 筛选符合条件的ETF
def select_etfs(etf_list, etf_names, momentum_period=20, ma_period=28):
    etf_data = {}
    for symbol in etf_list:
        try:
            df = fetch_etf_data(symbol)
            if df.empty:
                small_log(f"{symbol} 数据为空，已跳过")
                continue
            df = calculate_momentum_and_ma(df, momentum_period, ma_period)
            etf_data[symbol] = df
        except Exception as e:
            small_log(f"处理{symbol}数据失败: {e}")
            continue
    
    if not etf_data:
        small_log("无法获取任何ETF数据")
        return [], []
    
    # 获取最新的数据
    latest_data = {symbol: df.iloc[-1] for symbol, df in etf_data.items()}
    
    # 收集所有ETF的动量和是否大于均线的信息
    all_etfs = []
    for symbol, data in latest_data.items():
        above_ma = data['Close'] > data['MA']
        all_etfs.append((symbol, etf_names[symbol], data['Close'], data['MA'], data['Momentum'], above_ma))
    
    # 按动量排序
    all_etfs.sort(key=lambda x: x[4], reverse=True)
    
    # 选择动量排名前两位且收盘价大于均线的ETF
    selected_etfs = [(etf[0], etf[1], etf[2], etf[3], etf[4]) for etf in all_etfs if etf[5]][:2]
    return selected_etfs, all_etfs

# 回测函数
def backtest_strategy(etf_list, etf_names, start_date, end_date, momentum_period=20, ma_period=28, max_positions=2):
    """回测动量策略"""
    # 转换日期类型
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)
    
    # 获取所有ETF的历史数据
    etf_data = {}
    for symbol in etf_list:
        try:
            df = fetch_etf_data(symbol)
            if df.empty:
                continue
            # 筛选时间范围
            df = df[(df.index >= start_date) & (df.index <= end_date)]
            if len(df) < max(momentum_period, ma_period) + 10:  # 确保有足够的数据
                continue
            df = calculate_momentum_and_ma(df, momentum_period, ma_period)
            etf_data[symbol] = df
        except Exception as e:
            small_log(f"处理{symbol}数据失败: {e}")
            continue
    
    if len(etf_data) < 2:
        small_log("可用ETF数量不足2只，无法回测")
        return None, None, None
    
    # 获取所有ETF的共同日期
    common_dates = None
    for symbol, df in etf_data.items():
        if common_dates is None:
            common_dates = set(df.index)
        else:
            common_dates = common_dates.intersection(set(df.index))
    
    if len(common_dates) < 30:
        small_log("共同交易日不足30天，无法回测")
        return None, None, None
    
    common_dates = sorted(list(common_dates))
    
    # 回测逻辑
    # 初始化投资组合净值，从第一个有效交易日开始
    start_index = max(momentum_period, ma_period)
    portfolio_values = [1.0]  # 初始净值1.0
    holdings_history = []  # 持仓历史
    trade_history = []  # 交易历史
    
    current_holdings = set()  # 当前持仓
    
    for i, date in enumerate(common_dates):
        if i < start_index:
            # 前N天数据不足，跳过
            continue
        
        # 计算当日动量排名
        momentums = {}
        candidates = []
        
        for symbol, df in etf_data.items():
            if date in df.index:
                row = df.loc[date]
                if not pd.isna(row['Close']) and not pd.isna(row['MA']) and not pd.isna(row['Momentum']):
                    if row['Close'] > row['MA']:
                        candidates.append(symbol)
                        momentums[symbol] = row['Momentum']
        
        # 按动量排序，取前N名
        if candidates:
            sorted_candidates = sorted(candidates, key=lambda x: momentums[x], reverse=True)
            top_candidates = sorted_candidates[:max_positions]
            
            # 检查是否需要调仓
            to_sell = current_holdings - set(top_candidates)
            to_buy = set(top_candidates) - current_holdings
            
            # 记录交易
            for etf in to_sell:
                trade_history.append({
                    '日期': date.strftime('%Y-%m-%d'),
                    'ETF代码': etf,
                    'ETF名称': etf_names[etf],
                    '操作': '卖出',
                    '价格': etf_data[etf].loc[date, 'Close']
                })
            
            for etf in to_buy:
                trade_history.append({
                    '日期': date.strftime('%Y-%m-%d'),
                    'ETF代码': etf,
                    'ETF名称': etf_names[etf],
                    '操作': '买入',
                    '价格': etf_data[etf].loc[date, 'Close']
                })
            
            # 更新持仓
            current_holdings = set(top_candidates)
        else:
            # 没有符合条件的ETF，清仓
            for etf in current_holdings:
                trade_history.append({
                    '日期': date.strftime('%Y-%m-%d'),
                    'ETF代码': etf,
                    'ETF名称': etf_names[etf],
                    '操作': '卖出',
                    '价格': etf_data[etf].loc[date, 'Close']
                })
            current_holdings = set()
        
        # 记录持仓
        holdings_history.append({
            '日期': date.strftime('%Y-%m-%d'),
            '持仓ETF': list(current_holdings),
            '持仓数量': len(current_holdings)
        })
        
        # 计算当日收益
        if i > 0 and current_holdings:
            # 计算持仓ETF的平均收益
            daily_returns = []
            for etf in current_holdings:
                if i > 0:
                    prev_date = common_dates[i-1]
                    if prev_date in etf_data[etf].index and date in etf_data[etf].index:
                        prev_price = etf_data[etf].loc[prev_date, 'Close']
                        curr_price = etf_data[etf].loc[date, 'Close']
                        if prev_price > 0:
                            daily_return = (curr_price / prev_price - 1)
                            daily_returns.append(daily_return)
            
            if daily_returns:
                # 计算平均收益
                avg_daily_return = sum(daily_returns) / len(daily_returns)
                portfolio_values.append(portfolio_values[-1] * (1 + avg_daily_return))
            else:
                portfolio_values.append(portfolio_values[-1])
        else:
            portfolio_values.append(portfolio_values[-1])
    
    # 计算回测指标
    if len(portfolio_values) > 1:
        # 确保首末净值与日期一一对应
        start_value = portfolio_values[0]
        end_value = portfolio_values[-1]
        total_return = (end_value / start_value - 1) * 100
        # 使用正确的起始日期计算天数
        start_date_index = max(momentum_period, ma_period)
        days = (common_dates[-1] - common_dates[start_date_index]).days
        annual_return = calculate_annual_return(start_value, end_value, days)
        max_drawdown = calculate_max_drawdown(portfolio_values)
        sharpe_ratio = calculate_sharpe_ratio(portfolio_values)
    else:
        total_return = 0
        annual_return = 0
        max_drawdown = 0
        sharpe_ratio = 0
    
    return {
        'portfolio_values': portfolio_values,
        'dates': [d.strftime('%Y-%m-%d') for d in common_dates[max(momentum_period, ma_period):]],
        'total_return': total_return,  # 总收益率=首末净值之比-1
        'annual_return': annual_return,
        'max_drawdown': max_drawdown,
        'sharpe_ratio': sharpe_ratio,
        'trade_count': len(trade_history)
    }, trade_history, holdings_history

def calculate_annual_return(start_value, end_value, days):
    """计算年化收益率"""
    if days <= 0 or start_value <= 0:
        return 0
    years = days / 365.25
    # 使用更稳定的年化收益率计算方法
    if years > 0:
        return ((end_value / start_value) ** (1 / years) - 1) * 100
    else:
        return 0

def calculate_max_drawdown(values):
    """计算最大回撤"""
    if len(values) < 2:
        return 0
    
    max_dd = 0
    peak = values[0]
    
    for value in values:
        if value > peak:
            peak = value
        dd = (peak - value) / peak * 100
        if dd > max_dd:
            max_dd = dd
    
    return max_dd

def calculate_sharpe_ratio(values):
    """计算夏普比率"""
    if len(values) < 2:
        return 0
    
    returns = []
    for i in range(1, len(values)):
        if values[i-1] > 0:
            returns.append((values[i] / values[i-1] - 1) * 100)
    
    if not returns:
        return 0
    
    mean_return = np.mean(returns)
    std_return = np.std(returns)
    
    if std_return == 0:
        return 0
    
    # 假设无风险利率为3%
    risk_free_rate = 3
    sharpe = (mean_return - risk_free_rate) / std_return * np.sqrt(252)
    
    return sharpe

def small_log(msg):
    st.markdown(f"<div style='font-size:12px; color:#888;'>{msg}</div>", unsafe_allow_html=True)

# 修改页面标题
st.title("🔄 大类资产轮动")

st.markdown("""
> 本工具基于动量与均线策略，自动推荐大类资产（ETF）轮动持仓。
> 
> - **动量筛选**：优先选择近期涨幅靠前的资产
> - **均线过滤**：仅持有价格高于均线的资产
> - **等权分配**：持仓资产等权重分配，便于实盘跟踪
""")
st.markdown("---")

# 设置页面配置
st.set_page_config(
    page_title="大类资产轮动",
    page_icon="🔄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 显示缓存信息
st.sidebar.subheader("缓存信息")
meta_data = load_cache_meta()
if meta_data:
    st.sidebar.write("**已缓存的ETF：**")
    for symbol, info in meta_data.items():
        st.sidebar.write(f"- {symbol}: {info.get('last_update', 'N/A')}")
    
    # 清除缓存按钮
    if st.sidebar.button("清除所有缓存"):
        try:
            for file in os.listdir(CACHE_DIR):
                file_path = os.path.join(CACHE_DIR, file)
                if os.path.isfile(file_path):
                    os.remove(file_path)
            st.sidebar.success("缓存已清除")
            st.rerun()
        except Exception as e:
            st.sidebar.error(f"清除缓存失败: {e}")
else:
    small_log("暂无缓存数据")

# ETF池选择
etf_list = list(DEFAULT_ETF_POOL.keys())
all_etfs = DEFAULT_ETF_POOL

# 修复default类型和内容
raw_default = list(DEFAULT_ETF_POOL.keys())
if etf_list and raw_default:
    default = [type(etf_list[0])(x) for x in raw_default]
    default = [x for x in default if x in etf_list]
else:
    default = []

st.markdown("**选择指数池（可多选，默认6只）：**")
selected_etfs = st.multiselect(
    "ETF池",
    options=list(all_etfs.keys()),
    default=default,
    format_func=lambda x: f"{x} - {all_etfs.get(x, x)}"
)

# 策略参数
col1, col2, col3 = st.columns(3)
with col1:
    momentum_period = st.number_input("动量周期", min_value=5, max_value=60, value=20)
with col2:
    ma_period = st.number_input("均线周期", min_value=5, max_value=60, value=28)
with col3:
    max_positions = st.number_input("最大持仓数量", min_value=1, max_value=5, value=2)

# 自动计算逻辑
def auto_calculate_momentum():
    """自动计算动量策略结果"""
    if len(selected_etfs) < 2:
        st.warning("请至少选择2只ETF")
        return None, None
    
    with st.spinner("正在获取ETF数据并计算持仓..."):
        try:
            selected_etfs_result, all_etfs_result = select_etfs(selected_etfs, all_etfs, momentum_period, ma_period)
            return selected_etfs_result, all_etfs_result
        except Exception as e:
            st.error(f"计算失败: {e}")
            import traceback
            st.markdown("<div style='font-size:12px; color:#888;'>" + traceback.format_exc().replace('\n', '<br>') + "</div>", unsafe_allow_html=True)
            return None, None

# 检查是否需要重新计算
current_params = {
    'selected_etfs': selected_etfs,
    'momentum_period': momentum_period,
    'ma_period': ma_period,
    'max_positions': max_positions
}

# 如果参数发生变化或没有缓存结果，则重新计算
if ('momentum_params' not in st.session_state or 
    st.session_state.momentum_params != current_params or
    'momentum_results' not in st.session_state):
    
    st.session_state.momentum_params = current_params
    selected_etfs_result, all_etfs_result = auto_calculate_momentum()
    st.session_state.momentum_results = {
        'selected_etfs_result': selected_etfs_result,
        'all_etfs_result': all_etfs_result
    }
else:
    # 使用缓存的结果
    selected_etfs_result = st.session_state.momentum_results['selected_etfs_result']
    all_etfs_result = st.session_state.momentum_results['all_etfs_result']

# 显示结果
if selected_etfs_result is not None and all_etfs_result is not None:
    st.markdown("---")
    st.subheader("✅ 推荐持仓")
    if selected_etfs_result:
        holdings_data = []
        for symbol, name, close, ma, momentum in selected_etfs_result:
            holdings_data.append({
                'ETF代码': symbol,
                'ETF名称': name,
                '当前价格(元)': f"{close:.2f}",
                f'{ma_period}日均线': f"{ma:.2f}",
                '价格-均线': f"{close - ma:.2f}",
                f'{momentum_period}日动量': f"{momentum*100:.2f}%",
                '持仓权重': f"{100/len(selected_etfs_result):.1f}%"
            })
        holdings_df = pd.DataFrame(holdings_data)
        st.dataframe(holdings_df.style.background_gradient(cmap="Greens"), use_container_width=True)
        st.success(f"推荐持有 {len(selected_etfs_result)} 只ETF，等权重分配")
    else:
        st.warning("暂无符合条件的ETF，建议空仓")
    
    st.markdown("---")
    st.subheader("📊 所有ETF动量排名")
    all_etfs_data = []
    for symbol, name, close, ma, momentum, above_ma in all_etfs_result:
        all_etfs_data.append({
            'ETF代码': symbol,
            'ETF名称': name,
            '当前价格(元)': f"{close:.2f}",
            f'{ma_period}日均线': f"{ma:.2f}",
            '价格-均线': f"{close - ma:.2f}",
            f'{momentum_period}日动量': f"{momentum*100:.2f}%",
            '站上均线': '✅' if above_ma else '❌',
            '推荐': '⭐' if (symbol, name, close, ma, momentum) in selected_etfs_result else ''
        })
    all_etfs_df = pd.DataFrame(all_etfs_data)
    all_etfs_df = all_etfs_df.sort_values(f'{momentum_period}日动量', ascending=False, key=lambda x: pd.to_numeric(x.str.rstrip('%'), errors='coerce'))
    st.dataframe(all_etfs_df.style.background_gradient(cmap="Blues"), use_container_width=True)
    st.info("动量排名仅供参考，建议结合自身风险偏好决策。")
    
    st.markdown("---")
    st.markdown("""
    **策略说明：**
    - 仅持有价格高于均线的资产，避免下跌趋势踩雷
    - 动量周期、均线周期、最大持仓数量均可自定义
    - 推荐持仓为等权分配，便于实盘跟踪
    - 本工具不构成投资建议，投资需谨慎
    """)

# 添加手动刷新按钮
if st.button("🔄 手动刷新数据"):
    # 清除缓存结果，强制重新计算
    if 'momentum_results' in st.session_state:
        del st.session_state.momentum_results
    if 'momentum_params' in st.session_state:
        del st.session_state.momentum_params
    st.rerun()