import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from data import fetch_etf_data_with_retry, get_etf_list
from ai_utils import ai_chat, get_api_key

st.set_page_config(page_title="常见技术指标回测", page_icon="📈", layout="centered")
st.title("📈 常见技术指标回测 - MA均线策略")

st.markdown("""
> 策略规则：收盘价大于N日均线则持有，小于则空仓。支持多ETF回测。
""")

# 参数区
etf_list = get_etf_list()
if etf_list.empty:
    st.error("无法获取ETF列表，请检查网络连接或数据源是否可用")
    st.stop()
from utils import get_favorite_etfs
all_etfs = {row['symbol']: row['name'] for _, row in etf_list.iterrows()}
favorite_etfs = get_favorite_etfs()

# 优先显示自选ETF
etf_options = list(all_etfs.keys())
if favorite_etfs:
    favorite_in_options = [etf for etf in favorite_etfs if etf in etf_options]
    other_etfs = [etf for etf in etf_options if etf not in favorite_etfs]
    etf_options = favorite_in_options + other_etfs

# 确保默认值存在于选项中
default_etf = "510300"
if default_etf not in etf_options and etf_options:
    default_etf = etf_options[0]

selected_codes = st.multiselect(
    "选择ETF（可多选）",
    options=etf_options,
    default=[default_etf] if etf_options else [],
    format_func=lambda x: f"{x} - {all_etfs.get(x, x)}"
)
start_date = st.date_input("开始日期", pd.to_datetime("2022-01-01"))
end_date = st.date_input("结束日期", pd.to_datetime("today"))
# 均线参数区
col1, col2, col3 = st.columns(3)
with col1:
    N_start = st.number_input("均线N起始", min_value=2, max_value=100, value=10, step=1)
with col2:
    N_end = st.number_input("均线N结束", min_value=N_start+1, max_value=200, value=120, step=1)
with col3:
    N_step = st.number_input("步长", min_value=1, max_value=30, value=10, step=1)
run_btn = st.button("批量回测")
ai_analysis = st.checkbox("是否需要AI分析", value=False)

def ma_backtest(df, N):
    df = df.copy()
    df['MA'] = df['close'].rolling(N).mean()
    df['signal'] = np.where(df['close'] > df['MA'], 1, 0)
    df['ret'] = df['close'].pct_change().fillna(0)
    df['strategy_ret'] = df['ret'] * df['signal'].shift(1).fillna(0)
    df['net_value'] = (1 + df['strategy_ret']).cumprod()
    df['bench_value'] = (1 + df['ret']).cumprod()
    return df

def plot_ma(df, symbol_name, N):
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(df.index, df['close'], label='收盘价')
    ax.plot(df.index, df['MA'], label=f'{N}日均线')
    ax.fill_between(df.index, df['close'], df['MA'], where=df['signal']>0, color='red', alpha=0.1, label='持有区间')
    ax.set_title(f"{symbol_name} 收盘价与{N}日均线")
    ax.legend()
    return fig

def plot_nav(df, symbol_name):
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(df.index, df['net_value'], label='策略净值')
    ax.plot(df.index, df['bench_value'], label='买入持有')
    ax.set_title(f"{symbol_name} 策略净值 vs 买入持有")
    ax.legend()
    return fig

if run_btn and selected_codes:
    for code in selected_codes:
        st.subheader(f"{code} - {all_etfs.get(code, code)}")
        df = fetch_etf_data_with_retry(code, start_date, end_date, etf_list)
        if df.empty or len(df) < N_start+10:
            st.warning(f"{code} 数据不足，跳过")
            continue
        close_col = df.columns[0]
        data = df[[close_col]].rename(columns={close_col: 'close'})
        data = data.sort_index()
        # 批量回测
        results = []
        navs = {}
        for N in range(int(N_start), int(N_end)+1, int(N_step)):
            bt_df = ma_backtest(data, N)
            total_ret = bt_df['net_value'].iloc[-1] - 1
            bench_ret = bt_df['bench_value'].iloc[-1] - 1
            annual = (bt_df['net_value'].iloc[-1]) ** (252/len(bt_df)) - 1 if len(bt_df) > 0 else np.nan
            bench_annual = (bt_df['bench_value'].iloc[-1]) ** (252/len(bt_df)) - 1 if len(bt_df) > 0 else np.nan
            win_rate = (bt_df['strategy_ret'] > 0).mean()
            # 计算超额收益
            excess = (annual - bench_annual) * 100
            results.append({
                'N': N,
                '策略总收益率%': f"{total_ret*100:.2f}",
                '策略年化%': f"{annual*100:.2f}",
                '胜率%': f"{win_rate*100:.2f}",
                '买入持有总收益率%': f"{bench_ret*100:.2f}",
                '买入持有年化%': f"{bench_annual*100:.2f}",
                '超额收益%': f"{excess:.2f}"
            })
            navs[N] = bt_df['net_value']
        # 结果表格
        st.markdown(f"**回测区间：{start_date} ~ {end_date}**")
        st.markdown("**参数回测对比表：**")
        result_df = pd.DataFrame(results)
        # 找到策略年化%最高的行索引
        try:
            annuals = result_df['策略年化%'].astype(float)
            max_idx = annuals.idxmax()
        except:
            max_idx = None
        # 年化越高颜色越深红，最高行黄色
        def color_annual(val):
            try:
                v = float(val)
                norm = min(max((v-0)/20, 0), 1)
                r = int(255)
                g = int(255*(1-norm))
                b = int(255*(1-norm))
                return f'background-color: rgb({r},{g},{g})'
            except:
                return ''
        def highlight_max(row):
            if max_idx is not None and row.name == max_idx:
                return ['background-color: yellow']*len(row)
            return ['']*len(row)
        # 在表格美化时，超额收益%也可用红绿色（正红负绿）
        def color_excess(val):
            try:
                v = float(val)
                if v > 0:
                    return 'color:red;'
                elif v < 0:
                    return 'color:green;'
            except:
                pass
            return ''
        styled = result_df.style.applymap(color_annual, subset=['策略年化%']).applymap(color_excess, subset=['超额收益%']).apply(highlight_max, axis=1)
        st.dataframe(styled, use_container_width=True)
        # 净值曲线对比
        st.markdown("**不同N参数下策略净值曲线对比：**")
        fig, ax = plt.subplots(figsize=(10, 4))
        for N, nav in navs.items():
            ax.plot(nav.index, nav, label=f'N={N}')
        ax.set_title(f"{all_etfs.get(code, code)} 不同N参数策略净值对比")
        ax.legend()
        st.pyplot(fig)
        if ai_analysis:
            api_key = get_api_key()
            prompt = f"ETF：{all_etfs.get(code, code)}\n回测区间：{start_date}~{end_date}\n参数回测表：\n{result_df.to_csv(index=False)}\n请作为专业量化分析师，分析该MA策略参数表现，总结最优参数区间、策略优缺点及改进建议。"
            with st.spinner(f"AI正在分析（{code} MA）..."):
                ai_result = ai_chat(prompt, api_key=api_key)
            st.markdown("**AI分析结论：**")
            st.write(ai_result)

# 新增：ROC策略回测
st.header("ROC动量策略批量回测")
st.markdown(
    "> 策略规则：N日ROC（收盘价变动率）大于0买入，小于0空仓。支持多ETF批量参数回测。"
)
col1, col2, col3 = st.columns(3)
with col1:
    roc_N_start = st.number_input("ROC N起始", min_value=2, max_value=30, value=5, step=1, key='roc_n_start')
with col2:
    roc_N_end = st.number_input("ROC N结束", min_value=roc_N_start+1, max_value=90, value=45, step=1, key='roc_n_end')
with col3:
    roc_N_step = st.number_input("步长", min_value=1, max_value=20, value=5, step=1, key='roc_n_step')
roc_run_btn = st.button("批量回测（ROC策略）")

def roc_backtest(df, N):
    df = df.copy()
    df['ROC'] = df['close'].pct_change(N)
    df['signal'] = np.where(df['ROC'] > 0, 1, 0)
    df['ret'] = df['close'].pct_change().fillna(0)
    df['strategy_ret'] = df['ret'] * df['signal'].shift(1).fillna(0)
    df['net_value'] = (1 + df['strategy_ret']).cumprod()
    df['bench_value'] = (1 + df['ret']).cumprod()
    return df

if roc_run_btn and selected_codes:
    for code in selected_codes:
        st.subheader(f"{code} - {all_etfs.get(code, code)} (ROC策略)")
        df = fetch_etf_data_with_retry(code, start_date, end_date, etf_list)
        if df.empty or len(df) < roc_N_start+10:
            st.warning(f"{code} 数据不足，跳过")
            continue
        close_col = df.columns[0]
        data = df[[close_col]].rename(columns={close_col: 'close'})
        data = data.sort_index()
        # 批量回测
        results = []
        navs = {}
        for N in range(int(roc_N_start), int(roc_N_end)+1, int(roc_N_step)):
            bt_df = roc_backtest(data, N)
            total_ret = bt_df['net_value'].iloc[-1] - 1
            bench_ret = bt_df['bench_value'].iloc[-1] - 1
            annual = (bt_df['net_value'].iloc[-1]) ** (252/len(bt_df)) - 1 if len(bt_df) > 0 else np.nan
            bench_annual = (bt_df['bench_value'].iloc[-1]) ** (252/len(bt_df)) - 1 if len(bt_df) > 0 else np.nan
            win_rate = (bt_df['strategy_ret'] > 0).mean()
            # 计算超额收益
            excess = (annual - bench_annual) * 100
            results.append({
                'N': N,
                '策略总收益率%': f"{total_ret*100:.2f}",
                '策略年化%': f"{annual*100:.2f}",
                '胜率%': f"{win_rate*100:.2f}",
                '买入持有总收益率%': f"{bench_ret*100:.2f}",
                '买入持有年化%': f"{bench_annual*100:.2f}",
                '超额收益%': f"{excess:.2f}"
            })
            navs[N] = bt_df['net_value']
        # 结果表格
        st.markdown(f"**回测区间：{start_date} ~ {end_date}**")
        st.markdown("**参数回测对比表：**")
        result_df = pd.DataFrame(results)
        try:
            annuals = result_df['策略年化%'].astype(float)
            max_idx = annuals.idxmax()
        except:
            max_idx = None
        def color_annual(val):
            try:
                v = float(val)
                norm = min(max((v-0)/20, 0), 1)
                r = int(255)
                g = int(255*(1-norm))
                b = int(255*(1-norm))
                return f'background-color: rgb({r},{g},{g})'
            except:
                return ''
        def highlight_max(row):
            if max_idx is not None and row.name == max_idx:
                return ['background-color: yellow']*len(row)
            return ['']*len(row)
        # 在表格美化时，超额收益%也可用红绿色（正红负绿）
        def color_excess(val):
            try:
                v = float(val)
                if v > 0:
                    return 'color:red;'
                elif v < 0:
                    return 'color:green;'
            except:
                pass
            return ''
        styled = result_df.style.applymap(color_annual, subset=['策略年化%']).applymap(color_excess, subset=['超额收益%']).apply(highlight_max, axis=1)
        st.dataframe(styled, use_container_width=True)
        # 净值曲线对比
        st.markdown("**不同N参数下策略净值曲线对比：**")
        fig, ax = plt.subplots(figsize=(10, 4))
        for N, nav in navs.items():
            ax.plot(nav.index, nav, label=f'N={N}')
        ax.set_title(f"{all_etfs.get(code, code)} 不同N参数ROC策略净值对比")
        ax.legend()
        st.pyplot(fig)
        if ai_analysis:
            api_key = get_api_key()
            prompt = f"ETF：{all_etfs.get(code, code)}\n回测区间：{start_date}~{end_date}\n参数回测表：\n{result_df.to_csv(index=False)}\n请作为专业量化分析师，分析该ROC策略参数表现，总结最优参数区间、策略优缺点及改进建议。"
            with st.spinner(f"AI正在分析（{code} ROC）..."):
                ai_result = ai_chat(prompt, api_key=api_key)
            st.markdown("**AI分析结论：**")
            st.write(ai_result)

# 新增：BOLL策略回测
st.header("BOLL布林带策略批量回测")
st.markdown(
    "> 策略规则：K=2，N日BOLL。收盘价在上轨与中轨之间做多，在中轨和下轨之间做空。支持多ETF批量参数回测。"
)
boll_N_start = st.number_input("BOLL N起始", min_value=10, max_value=100, value=40, step=1, key='boll_n_start')
boll_N_end = st.number_input("BOLL N结束", min_value=boll_N_start+1, max_value=120, value=48, step=1, key='boll_n_end')
boll_run_btn = st.button("批量回测（BOLL策略）")
K = 2

def boll_backtest(df, N, K=2):
    df = df.copy()
    df['MA'] = df['close'].rolling(N).mean()
    df['STD'] = df['close'].rolling(N).std()
    df['UP'] = df['MA'] + K*df['STD']
    df['DOWN'] = df['MA'] - K*df['STD']
    # 信号：上轨与中轨之间做多，中轨和下轨之间做空
    df['signal'] = np.where(df['close'] >= df['MA'], 1, np.where(df['close'] < df['MA'], -1, 0))
    df['signal'] = np.where(df['close'] > df['UP'], 0, df['signal'])  # 超过上轨不持仓
    df['signal'] = np.where(df['close'] < df['DOWN'], 0, df['signal'])  # 低于下轨不持仓
    df['ret'] = df['close'].pct_change().fillna(0)
    df['strategy_ret'] = df['ret'] * df['signal'].shift(1).fillna(0)
    df['net_value'] = (1 + df['strategy_ret']).cumprod()
    df['bench_value'] = (1 + df['ret']).cumprod()
    return df

if boll_run_btn and selected_codes:
    for code in selected_codes:
        st.subheader(f"{code} - {all_etfs.get(code, code)} (BOLL策略)")
        df = fetch_etf_data_with_retry(code, start_date, end_date, etf_list)
        if df.empty or len(df) < boll_N_start+10:
            st.warning(f"{code} 数据不足，跳过")
            continue
        close_col = df.columns[0]
        data = df[[close_col]].rename(columns={close_col: 'close'})
        data = data.sort_index()
        # 批量回测
        results = []
        navs = {}
        for N in range(int(boll_N_start), int(boll_N_end)+1):
            bt_df = boll_backtest(data, N, K)
            total_ret = bt_df['net_value'].iloc[-1] - 1
            bench_ret = bt_df['bench_value'].iloc[-1] - 1
            annual = (bt_df['net_value'].iloc[-1]) ** (252/len(bt_df)) - 1 if len(bt_df) > 0 else np.nan
            bench_annual = (bt_df['bench_value'].iloc[-1]) ** (252/len(bt_df)) - 1 if len(bt_df) > 0 else np.nan
            win_rate = (bt_df['strategy_ret'] > 0).mean()
            # 计算超额收益
            excess = (annual - bench_annual) * 100
            results.append({
                'N': N,
                '策略总收益率%': f"{total_ret*100:.2f}",
                '策略年化%': f"{annual*100:.2f}",
                '胜率%': f"{win_rate*100:.2f}",
                '买入持有总收益率%': f"{bench_ret*100:.2f}",
                '买入持有年化%': f"{bench_annual*100:.2f}",
                '超额收益%': f"{excess:.2f}"
            })
            navs[N] = bt_df['net_value']
        # 结果表格
        st.markdown(f"**回测区间：{start_date} ~ {end_date}**")
        st.markdown("**参数回测对比表：**")
        result_df = pd.DataFrame(results)
        try:
            annuals = result_df['策略年化%'].astype(float)
            max_idx = annuals.idxmax()
        except:
            max_idx = None
        def color_annual(val):
            try:
                v = float(val)
                norm = min(max((v-0)/20, 0), 1)
                r = int(255)
                g = int(255*(1-norm))
                b = int(255*(1-norm))
                return f'background-color: rgb({r},{g},{g})'
            except:
                return ''
        def highlight_max(row):
            if max_idx is not None and row.name == max_idx:
                return ['background-color: yellow']*len(row)
            return ['']*len(row)
        # 在表格美化时，超额收益%也可用红绿色（正红负绿）
        def color_excess(val):
            try:
                v = float(val)
                if v > 0:
                    return 'color:red;'
                elif v < 0:
                    return 'color:green;'
            except:
                pass
            return ''
        styled = result_df.style.applymap(color_annual, subset=['策略年化%']).applymap(color_excess, subset=['超额收益%']).apply(highlight_max, axis=1)
        st.dataframe(styled, use_container_width=True)
        # 净值曲线对比
        st.markdown("**不同N参数下策略净值曲线对比：**")
        fig, ax = plt.subplots(figsize=(10, 4))
        for N, nav in navs.items():
            ax.plot(nav.index, nav, label=f'N={N}')
        ax.set_title(f"{all_etfs.get(code, code)} 不同N参数BOLL策略净值对比")
        ax.legend()
        st.pyplot(fig)
        if ai_analysis:
            api_key = get_api_key()
            prompt = f"ETF：{all_etfs.get(code, code)}\n回测区间：{start_date}~{end_date}\n参数回测表：\n{result_df.to_csv(index=False)}\n请作为专业量化分析师，分析该BOLL策略参数表现，总结最优参数区间、策略优缺点及改进建议。"
            with st.spinner(f"AI正在分析（{code} BOLL）..."):
                ai_result = ai_chat(prompt, api_key=api_key)
            st.markdown("**AI分析结论：**")
            st.write(ai_result)

# 新增：BIAS策略回测
st.header("BIAS乖离率策略批量回测")
st.markdown(
    "> 策略规则：BIAS=(收盘-均线)/均线。大于10%卖出，0~10%买入，-10%~0卖出，小于-10%买入。N从10到26，步长2。"
)
bias_N_start = st.number_input("BIAS N起始", min_value=2, max_value=20, value=10, step=2, key='bias_n_start')
bias_N_end = st.number_input("BIAS N结束", min_value=bias_N_start+2, max_value=40, value=26, step=2, key='bias_n_end')
bias_run_btn = st.button("批量回测（BIAS策略）")

def bias_backtest(df, N):
    df = df.copy()
    df['MA'] = df['close'].rolling(N).mean()
    df['BIAS'] = (df['close'] - df['MA']) / df['MA']
    # 策略信号
    cond1 = df['BIAS'] > 0.10
    cond2 = (df['BIAS'] > 0) & (df['BIAS'] <= 0.10)
    cond3 = (df['BIAS'] > -0.10) & (df['BIAS'] <= 0)
    cond4 = df['BIAS'] <= -0.10
    df['signal'] = 0
    df.loc[cond1, 'signal'] = -1
    df.loc[cond2, 'signal'] = 1
    df.loc[cond3, 'signal'] = -1
    df.loc[cond4, 'signal'] = 1
    df['ret'] = df['close'].pct_change().fillna(0)
    df['strategy_ret'] = df['ret'] * df['signal'].shift(1).fillna(0)
    df['net_value'] = (1 + df['strategy_ret']).cumprod()
    df['bench_value'] = (1 + df['ret']).cumprod()
    return df

if bias_run_btn and selected_codes:
    for code in selected_codes:
        st.subheader(f"{code} - {all_etfs.get(code, code)} (BIAS策略)")
        df = fetch_etf_data_with_retry(code, start_date, end_date, etf_list)
        if df.empty or len(df) < bias_N_start+10:
            st.warning(f"{code} 数据不足，跳过")
            continue
        close_col = df.columns[0]
        data = df[[close_col]].rename(columns={close_col: 'close'})
        data = data.sort_index()
        # 批量回测
        results = []
        navs = {}
        for N in range(int(bias_N_start), int(bias_N_end)+1, 2):
            bt_df = bias_backtest(data, N)
            total_ret = bt_df['net_value'].iloc[-1] - 1
            bench_ret = bt_df['bench_value'].iloc[-1] - 1
            annual = (bt_df['net_value'].iloc[-1]) ** (252/len(bt_df)) - 1 if len(bt_df) > 0 else np.nan
            bench_annual = (bt_df['bench_value'].iloc[-1]) ** (252/len(bt_df)) - 1 if len(bt_df) > 0 else np.nan
            win_rate = (bt_df['strategy_ret'] > 0).mean()
            # 计算超额收益
            excess = (annual - bench_annual) * 100
            results.append({
                'N': N,
                '策略总收益率%': f"{total_ret*100:.2f}",
                '策略年化%': f"{annual*100:.2f}",
                '胜率%': f"{win_rate*100:.2f}",
                '买入持有总收益率%': f"{bench_ret*100:.2f}",
                '买入持有年化%': f"{bench_annual*100:.2f}",
                '超额收益%': f"{excess:.2f}"
            })
            navs[N] = bt_df['net_value']
        # 结果表格
        st.markdown(f"**回测区间：{start_date} ~ {end_date}**")
        st.markdown("**参数回测对比表：**")
        result_df = pd.DataFrame(results)
        try:
            annuals = result_df['策略年化%'].astype(float)
            max_idx = annuals.idxmax()
        except:
            max_idx = None
        def color_annual(val):
            try:
                v = float(val)
                norm = min(max((v-0)/20, 0), 1)
                r = int(255)
                g = int(255*(1-norm))
                b = int(255*(1-norm))
                return f'background-color: rgb({r},{g},{g})'
            except:
                return ''
        def highlight_max(row):
            if max_idx is not None and row.name == max_idx:
                return ['background-color: yellow']*len(row)
            return ['']*len(row)
        # 在表格美化时，超额收益%也可用红绿色（正红负绿）
        def color_excess(val):
            try:
                v = float(val)
                if v > 0:
                    return 'color:red;'
                elif v < 0:
                    return 'color:green;'
            except:
                pass
            return ''
        styled = result_df.style.applymap(color_annual, subset=['策略年化%']).applymap(color_excess, subset=['超额收益%']).apply(highlight_max, axis=1)
        st.dataframe(styled, use_container_width=True)
        # 净值曲线对比
        st.markdown("**不同N参数下策略净值曲线对比：**")
        fig, ax = plt.subplots(figsize=(10, 4))
        for N, nav in navs.items():
            ax.plot(nav.index, nav, label=f'N={N}')
        ax.set_title(f"{all_etfs.get(code, code)} 不同N参数BIAS策略净值对比")
        ax.legend()
        st.pyplot(fig)
        if ai_analysis:
            api_key = get_api_key()
            prompt = f"ETF：{all_etfs.get(code, code)}\n回测区间：{start_date}~{end_date}\n参数回测表：\n{result_df.to_csv(index=False)}\n请作为专业量化分析师，分析该BIAS策略参数表现，总结最优参数区间、策略优缺点及改进建议。"
            with st.spinner(f"AI正在分析（{code} BIAS）..."):
                ai_result = ai_chat(prompt, api_key=api_key)
            st.markdown("**AI分析结论：**")
            st.write(ai_result) 