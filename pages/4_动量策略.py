import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import akshare as ak
from datetime import datetime, timedelta
import os
import json

# 动量策略页面

# 控制是否显示缓存日志
SHOW_CACHE_LOGS = False

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
    # 如果是缓存相关的日志且设置为不显示，则跳过
    if not SHOW_CACHE_LOGS and ("缓存" in msg or "使用" in msg and "数据" in msg):
        return
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
        
        # 添加所有ETF动量排名表格
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
        
        # 添加横向柱状图：动量对比
        st.markdown("---")
        st.subheader("📊 动量对比柱状图")
        
        # 准备柱状图数据
        bar_data = []
        for symbol, name, close, ma, momentum, above_ma in all_etfs_result:
            bar_data.append({
                'ETF代码': symbol,
                'ETF名称': name,
                '动量值': momentum * 100,  # 转换为百分比
                '站上均线': above_ma
            })
        
        bar_df = pd.DataFrame(bar_data)
        bar_df = bar_df.sort_values('动量值', ascending=True)  # 升序排列，便于横向显示
        
        # 创建横向柱状图
        fig_bar = go.Figure()
        
        for _, row in bar_df.iterrows():
            # 根据动量值选择颜色：红色表示正动量，绿色表示负动量
            if row['动量值'] > 0:
                color = '#d32f2f'  # 红色表示正动量
            elif row['动量值'] < 0:
                color = '#388e3c'  # 绿色表示负动量
            else:
                color = '#666666'  # 灰色表示零动量
            
            fig_bar.add_trace(go.Bar(
                y=[f"{row['ETF代码']} - {row['ETF名称']}"],
                x=[row['动量值']],
                orientation='h',
                marker_color=color,
                name=f"{row['ETF代码']} - {row['ETF名称']}",
                hovertemplate='<b>%{y}</b><br>' +
                            '动量值: %{x:.2f}%<br>' +
                            '状态: ' + ('✅ 站上均线' if row['站上均线'] else '❌ 未站上均线') + '<br>' +
                            '<extra></extra>'
            ))
        
        # 设置图表样式
        fig_bar.update_layout(
            title_text='ETF动量对比',
            title_x=0.5,
            font_size=12,
            showlegend=False,
            xaxis_title='动量值 (%)',
            yaxis_title='ETF',
            height=400,
            xaxis_tickformat=",.2f",
            hovermode='closest'
        )
        
        # 添加零线
        fig_bar.add_vline(x=0, line_width=1, line_dash="dash", line_color="#666666", opacity=0.7)
        
        # 显示柱状图
        st.plotly_chart(fig_bar, use_container_width=True)
        
        # 添加柱状图说明
        st.info("""
        **柱状图说明：**
        - 红色柱：正动量（价格上涨趋势）
        - 绿色柱：负动量（价格下跌趋势）
        - 灰色柱：零动量（价格无变化）
        - 柱长表示动量值大小
        - 零线左侧为负动量，右侧为正动量
        - 状态列显示是否站上均线（✅站上，❌未站上）
        """)
        
        # 添加趋势图：展示近一年标的本身的走势
        st.markdown("---")
        st.subheader("📈 近一年走势趋势图")
        
        # 计算近一年的累计涨跌幅
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)
        
        # 创建趋势图
        fig = go.Figure()
        
        # 定义颜色方案 - 使用确定存在的颜色
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', 
                 '#e377c2', '#7f7f7f', '#bcbd22', '#17becf', '#a6cee3', '#fb9a99',
                 '#fdbf6f', '#cab2d6', '#ffff99', '#b15928', '#fccde5', '#d9d9d9']
        
        # 收集所有数据用于计算y轴范围
        all_cumulative_returns = []
        
        # 收集所有ETF的累计收益数据用于计算等权配置
        etf_returns_data = {}
        
        for i, (symbol, name, _, _, _, _) in enumerate(all_etfs_result):
            try:
                # 获取历史数据
                df = fetch_etf_data(symbol)
                if not df.empty:
                    # 筛选近一年数据
                    df_filtered = df[(df.index >= start_date) & (df.index <= end_date)]
                    if not df_filtered.empty:
                        # 计算累计涨跌幅（以年初为基准）
                        first_price = df_filtered.iloc[0]['Close']
                        cumulative_returns = (df_filtered['Close'] / first_price - 1) * 100
                        all_cumulative_returns.extend(cumulative_returns.tolist())
                        
                        # 存储数据用于计算等权配置
                        etf_returns_data[symbol] = {
                            'dates': df_filtered.index,
                            'returns': cumulative_returns,
                            'name': f"{symbol} - {name}"
                        }
                        
                        # 绘制趋势线，使用循环颜色
                        color = colors[i % len(colors)]
                        fig.add_trace(go.Scatter(
                            x=df_filtered.index, 
                            y=cumulative_returns,
                            mode='lines+markers', 
                            name=f"{symbol} - {name}", 
                            line=dict(color=color, width=2), 
                            marker=dict(size=3),
                            hovertemplate='<b>%{fullData.name}</b><br>' +
                                        '时间: %{x}<br>' +
                                        '累计涨跌幅: %{y:.2f}%<br>' +
                                        '<extra></extra>'
                        ))
                        
            except Exception as e:
                st.warning(f"获取 {symbol} 趋势数据失败: {e}")
                continue
        
        # 计算并绘制等权配置收益曲线
        if len(etf_returns_data) > 1:
            try:
                # 找到所有ETF的共同日期
                common_dates = None
                for symbol, data in etf_returns_data.items():
                    if common_dates is None:
                        common_dates = set(data['dates'])
                    else:
                        common_dates = common_dates.intersection(set(data['dates']))
                
                if common_dates and len(common_dates) > 10:
                    common_dates = sorted(list(common_dates))
                    
                    # 计算等权配置的累计收益
                    equal_weight_returns = []
                    for date in common_dates:
                        daily_return = 0
                        valid_returns = 0
                        for symbol, data in etf_returns_data.items():
                            if date in data['dates']:
                                # 找到该日期对应的收益率
                                date_idx = data['dates'].get_loc(date)
                                if date_idx > 0:  # 不是第一个数据点
                                    prev_date_idx = date_idx - 1
                                    prev_date = data['dates'][prev_date_idx]
                                    if prev_date in data['dates']:
                                        prev_return = data['returns'].iloc[prev_date_idx]
                                        curr_return = data['returns'].iloc[date_idx]
                                        # 计算日收益率
                                        daily_return += (curr_return - prev_return) / 100  # 转换为小数
                                        valid_returns += 1
                        
                        if valid_returns > 0:
                            # 计算等权平均日收益率
                            avg_daily_return = daily_return / valid_returns
                            if len(equal_weight_returns) == 0:
                                equal_weight_returns.append(0)  # 起始点为0%
                            else:
                                # 累加日收益率
                                equal_weight_returns.append(equal_weight_returns[-1] + avg_daily_return * 100)
                        else:
                            if len(equal_weight_returns) > 0:
                                equal_weight_returns.append(equal_weight_returns[-1])
                            else:
                                equal_weight_returns.append(0)
                    
                    # 绘制等权配置曲线
                    fig.add_trace(go.Scatter(
                        x=common_dates,
                        y=equal_weight_returns,
                        mode='lines+markers',
                        name='🏆 等权配置',
                        line=dict(color='#FF6B6B', width=3, dash='dash'),
                        marker=dict(size=4),
                        hovertemplate='<b>🏆 等权配置</b><br>' +
                                    '时间: %{x}<br>' +
                                    '累计涨跌幅: %{y:.2f}%<br>' +
                                    '<extra></extra>'
                    ))
                    
                    # 将等权配置数据也加入y轴范围计算
                    all_cumulative_returns.extend(equal_weight_returns)
                    
            except Exception as e:
                st.warning(f"计算等权配置收益失败: {e}")
        
        # 添加零线作为参考
        fig.add_hline(y=0, line_width=1, line_dash="dash", line_color="#666666", opacity=0.7)
        
        # 设置图表样式
        fig.update_layout(
            title_text='近一年累计涨跌幅趋势',
            title_x=0.5,
            font_size=14,
            showlegend=True,
            legend_orientation="v",  # 改为垂直布局
            legend_x=1.02,  # 放在右侧
            legend_y=0.5,   # 垂直居中
            xaxis_title='时间',
            yaxis_title='累计涨跌幅 (%)',
            xaxis_tickangle=45,
            xaxis_tickformat="%Y-%m-%d",
            yaxis_tickformat=",.2f",
            hovermode='x unified',
            height=700  # 增加图表高度到700px
        )
        
        # 设置y轴范围，确保零线在中间
        if all_cumulative_returns:
            y_min = min(all_cumulative_returns)
            y_max = max(all_cumulative_returns)
            
            # 计算合适的Y轴范围
            y_range = max(abs(y_min), abs(y_max))
            
            # 如果数据范围太小，设置最小范围
            if y_range < 5:
                y_range = 10
            
            # 设置Y轴范围，给数据留出适当的边距
            y_padding = y_range * 0.15  # 15%的边距
            fig.update_layout(
                yaxis_range=[y_min - y_padding, y_max + y_padding]
            )
        
        # 显示图表
        st.plotly_chart(fig, use_container_width=True)
        
        # 添加累计涨跌幅对比柱状图
        st.markdown("---")
        st.subheader("📊 近一年累计涨跌幅对比")
        
        # 准备柱状图数据
        returns_bar_data = []
        for i, (symbol, name, _, _, _, _) in enumerate(all_etfs_result):
            try:
                # 获取历史数据
                df = fetch_etf_data(symbol)
                if not df.empty:
                    # 筛选近一年数据
                    df_filtered = df[(df.index >= start_date) & (df.index <= end_date)]
                    if not df_filtered.empty:
                        # 计算累计涨跌幅
                        first_price = df_filtered.iloc[0]['Close']
                        last_price = df_filtered.iloc[-1]['Close']
                        cumulative_return = (last_price / first_price - 1) * 100
                        
                        returns_bar_data.append({
                            'ETF代码': symbol,
                            'ETF名称': name,
                            '累计涨跌幅': cumulative_return,
                            '颜色': colors[i % len(colors)]  # 使用与趋势图相同的颜色
                        })
            except Exception as e:
                continue
        
        if returns_bar_data:
            returns_bar_df = pd.DataFrame(returns_bar_data)
            returns_bar_df = returns_bar_df.sort_values('累计涨跌幅', ascending=True)  # 升序排列
            
            # 创建横向柱状图
            fig_returns_bar = go.Figure()
            
            for _, row in returns_bar_df.iterrows():
                fig_returns_bar.add_trace(go.Bar(
                    y=[f"{row['ETF代码']} - {row['ETF名称']}"],
                    x=[row['累计涨跌幅']],
                    orientation='h',
                    marker_color=row['颜色'],
                    name=f"{row['ETF代码']} - {row['ETF名称']}",
                    hovertemplate='<b>%{y}</b><br>' +
                                '累计涨跌幅: %{x:.2f}%<br>' +
                                '<extra></extra>'
                ))
            
            # 设置图表样式
            fig_returns_bar.update_layout(
                title_text='近一年累计涨跌幅对比',
                title_x=0.5,
                font_size=12,
                showlegend=False,
                xaxis_title='累计涨跌幅 (%)',
                yaxis_title='ETF',
                height=400,
                xaxis_tickformat=",.2f",
                hovermode='closest'
            )
            
            # 添加零线
            fig_returns_bar.add_vline(x=0, line_width=1, line_dash="dash", line_color="#666666", opacity=0.7)
            
            # 显示柱状图
            st.plotly_chart(fig_returns_bar, use_container_width=True)
            
            # 添加柱状图说明
            st.info("""
            **累计涨跌幅柱状图说明：**
            - 柱长表示累计涨跌幅大小
            - 零线左侧为负收益，右侧为正收益
            - 颜色与上方趋势图保持一致，便于对应
            - 按累计涨跌幅排序，便于识别表现最好和最差的ETF
            """)
        
        # 添加标的相关因子分析
        st.markdown("---")
        st.subheader("🔍 标的相关因子分析")
        
        # 计算相关性矩阵
        try:
            # 准备收益率数据 - 使用所有选中的ETF
            returns_data = {}
            common_dates = None
            
            for symbol in selected_etfs:  # 使用selected_etfs而不是all_etfs_result
                df = fetch_etf_data(symbol)
                if not df.empty:
                    # 筛选近一年数据
                    df_filtered = df[(df.index >= start_date) & (df.index <= end_date)]
                    if not df_filtered.empty:
                        # 计算日收益率
                        df_filtered['Returns'] = df_filtered['Close'].pct_change()
                        returns_data[symbol] = df_filtered['Returns'].dropna()
                        
                        # 找到共同日期
                        if common_dates is None:
                            common_dates = set(returns_data[symbol].index)
                        else:
                            common_dates = common_dates.intersection(set(returns_data[symbol].index))
            
            if common_dates and len(common_dates) > 30:
                # 对齐数据
                aligned_returns = {}
                for symbol in returns_data:
                    aligned_returns[symbol] = returns_data[symbol].loc[list(common_dates)]
                
                # 创建收益率DataFrame
                returns_df = pd.DataFrame(aligned_returns)
                
                # 计算相关性矩阵
                correlation_matrix = returns_df.corr()
                
                # 计算风险指标
                risk_metrics = {}
                for symbol in returns_df.columns:
                    returns = returns_df[symbol].dropna()
                    if len(returns) > 0:
                        # 计算累积净值
                        cumulative_returns = (1 + returns).cumprod()
                        
                        # 获取ETF名称
                        etf_name = all_etfs.get(symbol, symbol)
                        
                        risk_metrics[symbol] = {
                            'ETF名称': etf_name,
                            '年化波动率': returns.std() * np.sqrt(252) * 100,
                            '年化收益率': returns.mean() * 252 * 100,
                            '夏普比率': (returns.mean() * 252 - 0.03) / (returns.std() * np.sqrt(252)) if returns.std() > 0 else 0,
                            '最大回撤': calculate_max_drawdown(cumulative_returns) * 100
                        }
                
                # 显示相关性热力图
                st.markdown("**📊 相关性热力图**")
                
                # 创建带ETF名称的相关性矩阵
                correlation_with_names = correlation_matrix.copy()
                correlation_with_names.columns = [f"{col} - {all_etfs.get(col, col)}" for col in correlation_with_names.columns]
                correlation_with_names.index = [f"{idx} - {all_etfs.get(idx, idx)}" for idx in correlation_with_names.index]
                
                fig_corr = go.Figure(data=go.Heatmap(
                    z=correlation_with_names.values,
                    x=correlation_with_names.columns,
                    y=correlation_with_names.index,
                    colorscale='RdBu',
                    zmid=0,
                    text=correlation_with_names.round(2).values,
                    texttemplate="%{text}",
                    textfont={"size": 10},
                    hoverongaps=False
                ))
                
                fig_corr.update_layout(
                    title_text='ETF日收益率相关性矩阵',
                    title_x=0.5,
                    height=500,
                    xaxis_title='ETF',
                    yaxis_title='ETF'
                )
                
                st.plotly_chart(fig_corr, use_container_width=True)
                
                # 显示风险指标表格
                st.markdown("**📈 风险指标对比**")
                risk_df = pd.DataFrame(risk_metrics).T
                
                # 格式化显示 - 确保保留2位小数
                formatted_risk_df = risk_df.copy()
                
                # 先确保数值类型正确，然后进行格式化
                formatted_risk_df['年化波动率'] = pd.to_numeric(formatted_risk_df['年化波动率'], errors='coerce').round(2).astype(str) + '%'
                formatted_risk_df['年化收益率'] = pd.to_numeric(formatted_risk_df['年化收益率'], errors='coerce').round(2).astype(str) + '%'
                formatted_risk_df['最大回撤'] = pd.to_numeric(formatted_risk_df['最大回撤'], errors='coerce').round(2).astype(str) + '%'
                formatted_risk_df['夏普比率'] = pd.to_numeric(formatted_risk_df['夏普比率'], errors='coerce').round(2)
                
                st.dataframe(formatted_risk_df, use_container_width=True)
                
                # 相关性分析说明
                st.info("""
                **相关因子分析说明：**
                - **相关性矩阵**：数值越接近1表示正相关越强，越接近-1表示负相关越强
                - **年化波动率**：反映价格波动风险，数值越大风险越高
                - **年化收益率**：年化后的收益率表现
                - **夏普比率**：风险调整后收益，数值越高越好（假设无风险利率3%）
                - **最大回撤**：历史最大下跌幅度，反映下行风险
                """)
                
                # 投资组合建议
                st.markdown("**💡 投资组合建议**")
                
                # 找出相关性最低的ETF对
                min_corr = 1.0
                min_corr_pair = None
                for i in range(len(correlation_matrix.columns)):
                    for j in range(i+1, len(correlation_matrix.columns)):
                        corr_val = abs(correlation_matrix.iloc[i, j])
                        if corr_val < min_corr:
                            min_corr = corr_val
                            min_corr_pair = (correlation_matrix.columns[i], correlation_matrix.columns[j])
                
                if min_corr_pair:
                    st.success(f"**低相关性组合推荐**：{min_corr_pair[0]} 和 {min_corr_pair[1]} (相关性: {min_corr:.3f})")
                
                # 找出夏普比率最高的ETF
                best_sharpe = max(risk_metrics.items(), key=lambda x: x[1]['夏普比率'])
                st.info(f"**最佳风险调整收益**：{best_sharpe[0]} (夏普比率: {best_sharpe[1]['夏普比率']:.2f})")
                
            else:
                st.warning("数据不足，无法进行相关因子分析")
                
        except Exception as e:
            st.error(f"相关因子分析失败: {e}")
        
        # 添加BIAS超买超卖分析
        st.markdown("---")
        st.subheader("📊 BIAS超买超卖分析")
        
        try:
            # 计算BIAS指标
            bias_data = []
            
            for symbol in selected_etfs:
                df = fetch_etf_data(symbol)
                if not df.empty:
                    # 筛选近一年数据
                    df_filtered = df[(df.index >= start_date) & (df.index <= end_date)]
                    if not df_filtered.empty:
                        # 计算不同周期的BIAS
                        bias_6 = ((df_filtered['Close'] - df_filtered['Close'].rolling(6).mean()) / df_filtered['Close'].rolling(6).mean() * 100).iloc[-1]
                        bias_12 = ((df_filtered['Close'] - df_filtered['Close'].rolling(12).mean()) / df_filtered['Close'].rolling(12).mean() * 100).iloc[-1]
                        bias_24 = ((df_filtered['Close'] - df_filtered['Close'].rolling(24).mean()) / df_filtered['Close'].rolling(24).mean() * 100).iloc[-1]
                        
                        # 获取当前价格和均线
                        current_price = df_filtered['Close'].iloc[-1]
                        ma_6 = df_filtered['Close'].rolling(6).mean().iloc[-1]
                        ma_12 = df_filtered['Close'].rolling(12).mean().iloc[-1]
                        ma_24 = df_filtered['Close'].rolling(24).mean().iloc[-1]
                        
                        # 判断超买超卖状态
                        def get_bias_status(bias_6, bias_12, bias_24):
                            # 使用统计方法计算动态阈值
                            # 基于历史BIAS数据的标准差来设置阈值
                            def calculate_dynamic_threshold(bias_values, multiplier=2.0):
                                """计算动态阈值：均值 ± (倍数 × 标准差)"""
                                if len(bias_values) > 0:
                                    mean_bias = np.mean(bias_values)
                                    std_bias = np.std(bias_values)
                                    return mean_bias + multiplier * std_bias, mean_bias - multiplier * std_bias
                                return 5, -5  # 默认值
                            
                            # 获取历史BIAS数据用于计算动态阈值
                            try:
                                # 计算过去30个交易日的BIAS值
                                bias_6_history = ((df_filtered['Close'] - df_filtered['Close'].rolling(6).mean()) / df_filtered['Close'].rolling(6).mean() * 100).dropna().tail(30)
                                bias_12_history = ((df_filtered['Close'] - df_filtered['Close'].rolling(12).mean()) / df_filtered['Close'].rolling(12).mean() * 100).dropna().tail(30)
                                bias_24_history = ((df_filtered['Close'] - df_filtered['Close'].rolling(24).mean()) / df_filtered['Close'].rolling(24).mean() * 100).dropna().tail(30)
                                
                                # 计算动态阈值
                                upper_6, lower_6 = calculate_dynamic_threshold(bias_6_history, 2.0)
                                upper_12, lower_12 = calculate_dynamic_threshold(bias_12_history, 2.0)
                                upper_24, lower_24 = calculate_dynamic_threshold(bias_24_history, 2.0)
                                
                                # 使用动态阈值判断
                                if bias_6 > upper_6 and bias_12 > upper_12 and bias_24 > upper_24:
                                    return f"🔴 超买 (6日:{bias_6:.1f}%>{upper_6:.1f}%)", "danger"
                                elif bias_6 < lower_6 and bias_12 < lower_12 and bias_24 < lower_24:
                                    return f"🟢 超卖 (6日:{bias_6:.1f}%<{lower_6:.1f}%)", "success"
                                elif bias_6 > upper_6 * 0.8 or bias_12 > upper_12 * 0.8:
                                    return f"🟡 偏超买 (6日:{bias_6:.1f}%)", "warning"
                                elif bias_6 < lower_6 * 0.8 or bias_12 < lower_12 * 0.8:
                                    return f"🟠 偏超卖 (6日:{bias_6:.1f}%)", "warning"
                                else:
                                    return f"⚪ 正常 (6日:{bias_6:.1f}%)", "info"
                                    
                            except:
                                # 如果动态计算失败，使用传统固定阈值
                                if bias_6 > 5 and bias_12 > 3 and bias_24 > 2:
                                    return "🔴 超买", "danger"
                                elif bias_6 < -5 and bias_12 < -3 and bias_24 < -2:
                                    return "🟢 超卖", "success"
                                elif bias_6 > 3 or bias_12 > 2:
                                    return "🟡 偏超买", "warning"
                                elif bias_6 < -3 or bias_12 < -2:
                                    return "🟠 偏超卖", "warning"
                                else:
                                    return "⚪ 正常", "info"
                        
                        bias_status, status_color = get_bias_status(bias_6, bias_12, bias_24)
                        
                        bias_data.append({
                            'ETF代码': symbol,
                            'ETF名称': all_etfs.get(symbol, symbol),
                            '当前价格': current_price,
                            '6日均线': ma_6,
                            '12日均线': ma_12,
                            '24日均线': ma_24,
                            'BIAS(6)': bias_6,
                            'BIAS(12)': bias_12,
                            'BIAS(24)': bias_24,
                            '状态': bias_status
                        })
            
            if bias_data:
                # 创建BIAS分析表格
                bias_df = pd.DataFrame(bias_data)
                
                # 格式化数值，保留2位小数
                bias_df['当前价格'] = bias_df['当前价格'].round(2)
                bias_df['6日均线'] = bias_df['6日均线'].round(2)
                bias_df['12日均线'] = bias_df['12日均线'].round(2)
                bias_df['24日均线'] = bias_df['24日均线'].round(2)
                bias_df['BIAS(6)'] = bias_df['BIAS(6)'].round(2)
                bias_df['BIAS(12)'] = bias_df['BIAS(12)'].round(2)
                bias_df['BIAS(24)'] = bias_df['BIAS(24)'].round(2)
                
                # 添加百分比符号
                bias_df['BIAS(6)'] = bias_df['BIAS(6)'].astype(str) + '%'
                bias_df['BIAS(12)'] = bias_df['BIAS(12)'].astype(str) + '%'
                bias_df['BIAS(24)'] = bias_df['BIAS(24)'].astype(str) + '%'
                
                st.dataframe(bias_df, use_container_width=True)
                
                # 添加BIAS分析说明
                st.info("""
                **BIAS超买超卖分析说明：**
                - **BIAS指标**：衡量价格偏离均线的程度，正值表示价格高于均线，负值表示价格低于均线
                - **动态阈值**：基于过去30个交易日的BIAS数据，使用均值±2倍标准差计算超买超卖阈值
                - **超买状态**：当前BIAS值超过历史统计上限，可能面临回调风险
                - **超卖状态**：当前BIAS值低于历史统计下限，可能存在反弹机会
                - **统计方法**：阈值 = 历史均值 ± (2.0 × 历史标准差)
                - **备用方案**：如果动态计算失败，使用传统固定阈值(±5%, ±3%, ±2%)
                """)
                
                # 投资建议
                st.markdown("**💡 BIAS投资建议**")
                
                # 找出超买和超卖的ETF
                overbought_etfs = [row for row in bias_data if "超买" in row['状态']]
                oversold_etfs = [row for row in bias_data if "超卖" in row['状态']]
                
                if overbought_etfs:
                    overbought_text = ", ".join([f"{row['ETF代码']}({row['ETF名称']})" for row in overbought_etfs])
                    st.warning(f"**超买ETF**：{overbought_text} - 注意回调风险")
                
                if oversold_etfs:
                    oversold_text = ", ".join([f"{row['ETF代码']}({row['ETF名称']})" for row in oversold_etfs])
                    st.success(f"**超卖ETF**：{oversold_text} - 关注反弹机会")
                
                if not overbought_etfs and not oversold_etfs:
                    st.info("**当前状态**：所有ETF都处于正常区间，无明显超买超卖信号")
                
            else:
                st.warning("无法获取BIAS分析数据")
                
        except Exception as e:
            st.error(f"BIAS分析失败: {e}")
        
        # 添加趋势分析说明
        st.info("""
        **趋势图说明：**
        - 横坐标：时间（近一年）
        - 纵坐标：累计涨跌幅（以年初为基准）
        - 零线：灰色虚线表示无涨跌的基准线
        - 彩色实线：各ETF的走势，便于对比分析
        - 🏆 等权配置：红色虚线表示等权重配置的收益表现
        - 趋势向上表示资产表现良好，趋势向下表示资产表现不佳
        """)
        
    else:
        st.warning("暂无符合条件的ETF，建议空仓")
    
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