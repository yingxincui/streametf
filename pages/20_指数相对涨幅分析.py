import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import akshare as ak
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

st.set_page_config(page_title="宽基指数对比分析", page_icon="📊", layout="wide")
st.title("📊 宽基指数对比分析")

# 使用expander折叠说明部分
with st.expander("📖 功能说明与使用指南", expanded=False):
    st.markdown("""
    > 分析主要宽基指数相对于上证指数的表现，帮助判断不同市场风格的表现强弱。
    > 提供多时间窗口的对比分析，识别市场轮动机会。

    **🎯 核心宽基指数：**
    - **上证指数 (000001)**：上海市场基准
    - **沪深300 (000300)**：大盘蓝筹代表
    - **中证500 (000500)**：中盘成长代表
    - **中证800 (000906)**：大中盘代表
    - **中证1000 (000852)**：小盘成长代表
    - **中证全指 (000985)**：全市场代表
    - **科创50 (000688)**：科技创新龙头
    - **中证2000 (932000)**：小微盘代表
    - **国证2000 (399303)**：深市小微盘代表
    - **创业板指 (399006)**：科技创新代表
    - **北证50 (899050)**：北交所龙头代表

    **📈 分析维度：**
    - **20日收益**：短期市场表现
    - **40日收益**：中期市场表现
    - **年初至今**：年度市场表现
    - **最大回撤**：风险控制能力
    - **相对上证**：超额收益分析
    """)

# 大盘强势判断
st.subheader("🏆 大盘强势判断")

# 获取上证指数数据用于均线分析
@st.cache_data(ttl=3600)
def get_shanghai_data():
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=200)  # 获取更多数据用于均线计算
        
        # 尝试获取上证指数数据
        data = pd.DataFrame()
        try:
            data = ak.stock_zh_index_hist_csindex(
                symbol="000001",
                start_date=start_date.strftime('%Y%m%d'),
                end_date=end_date.strftime('%Y%m%d')
            )
        except:
            try:
                data = ak.index_zh_a_hist(
                    symbol="000001", 
                    period="daily",
                    start_date=start_date.strftime('%Y%m%d'),
                    end_date=end_date.strftime('%Y%m%d')
                )
            except:
                try:
                    data = ak.stock_zh_index_hist_sina(
                        symbol="000001",
                        start_date=start_date.strftime('%Y-%m-%d'),
                        end_date=end_date.strftime('%Y-%m-%d')
                    )
                except:
                    return None
        
        if not data.empty:
            # 统一列名
            if '日期' in data.columns:
                data = data.rename(columns={'日期': 'date'})
            if '收盘' in data.columns:
                data = data.rename(columns={'收盘': 'close'})
            if '收盘价' in data.columns:
                data = data.rename(columns={'收盘价': 'close'})
            if 'close' in data.columns:
                data = data.rename(columns={'close': 'close'})
            
            # 确保有必要的列
            if 'date' in data.columns and 'close' in data.columns:
                data['date'] = pd.to_datetime(data['date'])
                data['close'] = pd.to_numeric(data['close'], errors='coerce')
                data = data.dropna(subset=['close'])
                data = data.sort_values('date')
                return data
        
        return None
    except Exception as e:
        st.error(f"获取上证指数数据失败: {str(e)}")
        return None

# 计算均线
def calculate_ma(data, period):
    return data['close'].rolling(window=period).mean()

# 判断大盘强势状态
def analyze_market_strength(data):
    if data is None or data.empty:
        return None
    
    # 计算各期均线
    ma5 = calculate_ma(data, 5)
    ma10 = calculate_ma(data, 10)
    ma20 = calculate_ma(data, 20)
    ma60 = calculate_ma(data, 60)
    ma120 = calculate_ma(data, 120)
    
    # 获取最新数据
    latest = data.iloc[-1]
    latest_close = latest['close']
    
    # 获取最新均线值
    latest_ma5 = ma5.iloc[-1]
    latest_ma10 = ma10.iloc[-1]
    latest_ma20 = ma20.iloc[-1]
    latest_ma60 = ma60.iloc[-1]
    latest_ma120 = ma120.iloc[-1]
    
    # 计算均线排列
    ma_alignment = {
        'ma5': latest_ma5,
        'ma10': latest_ma10,
        'ma20': latest_ma20,
        'ma60': latest_ma60,
        'ma120': latest_ma120
    }
    
    # 判断均线多头排列
    is_bullish_alignment = (latest_ma5 > latest_ma10 > latest_ma20 > latest_ma60 > latest_ma120)
    
    # 判断价格位置
    price_above_ma20 = latest_close > latest_ma20
    price_above_ma60 = latest_close > latest_ma60
    price_above_ma120 = latest_close > latest_ma120
    
    # 计算均线斜率（趋势强度）
    ma20_slope = (ma20.iloc[-1] - ma20.iloc[-5]) / ma20.iloc[-5] * 100  # 5日斜率
    ma60_slope = (ma60.iloc[-1] - ma60.iloc[-5]) / ma60.iloc[-5] * 100  # 5日斜率
    
    # 计算MACD指标（简化版）
    ema12 = data['close'].ewm(span=12).mean()
    ema26 = data['close'].ewm(span=26).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9).mean()
    macd_histogram = macd - signal
    
    latest_macd = macd.iloc[-1]
    latest_signal = signal.iloc[-1]
    latest_histogram = macd_histogram.iloc[-1]
    
    # 判断MACD状态
    macd_bullish = latest_macd > latest_signal and latest_histogram > 0
    
    # 综合判断大盘强势状态
    strength_score = 0
    strength_reasons = []
    
    # 均线排列得分
    if is_bullish_alignment:
        strength_score += 30
        strength_reasons.append("✅ 均线多头排列")
    else:
        strength_reasons.append("❌ 均线空头排列")
    
    # 价格位置得分
    if price_above_ma20:
        strength_score += 20
        strength_reasons.append("✅ 价格在20日均线之上")
    else:
        strength_reasons.append("❌ 价格跌破20日均线")
    
    if price_above_ma60:
        strength_score += 20
        strength_reasons.append("✅ 价格在60日均线之上")
    else:
        strength_reasons.append("❌ 价格跌破60日均线")
    
    if price_above_ma120:
        strength_score += 15
        strength_reasons.append("✅ 价格在120日均线之上")
    else:
        strength_reasons.append("❌ 价格跌破120日均线")
    
    # 趋势强度得分
    if ma20_slope > 0:
        strength_score += 10
        strength_reasons.append(f"✅ 20日均线向上倾斜 ({ma20_slope:.2f}%)")
    else:
        strength_reasons.append(f"❌ 20日均线向下倾斜 ({ma20_slope:.2f}%)")
    
    if ma60_slope > 0:
        strength_score += 5
        strength_reasons.append(f"✅ 60日均线向上倾斜 ({ma60_slope:.2f}%)")
    else:
        strength_reasons.append(f"❌ 60日均线向下倾斜 ({ma60_slope:.2f}%)")
    
    # MACD得分
    if macd_bullish:
        strength_score += 10
        strength_reasons.append("✅ MACD金叉向上")
    else:
        strength_reasons.append("❌ MACD死叉向下")
    
    # 判断强势等级
    if strength_score >= 80:
        strength_level = "🔥 强势"
        strength_color = "success"
    elif strength_score >= 60:
        strength_level = "📈 偏强"
        strength_color = "info"
    elif strength_score >= 40:
        strength_level = "⚖️ 中性"
        strength_color = "warning"
    elif strength_score >= 20:
        strength_level = "📉 偏弱"
        strength_color = "warning"
    else:
        strength_level = "💀 弱势"
        strength_color = "error"
    
    return {
        'strength_score': strength_score,
        'strength_level': strength_level,
        'strength_color': strength_color,
        'strength_reasons': strength_reasons,
        'latest_close': latest_close,
        'ma_alignment': ma_alignment,
        'ma20_slope': ma20_slope,
        'ma60_slope': ma60_slope,
        'macd_bullish': macd_bullish,
        'data': data
    }

# 执行大盘强势分析
shanghai_data = get_shanghai_data()
if shanghai_data is not None:
    market_analysis = analyze_market_strength(shanghai_data)
    
    if market_analysis:
        # 显示强势状态
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "大盘强势评分",
                market_analysis['strength_level'],
                f"{market_analysis['strength_score']}/100"
            )
        
        with col2:
            st.metric(
                "上证指数",
                f"{market_analysis['latest_close']:.2f}",
                f"MA20: {market_analysis['ma_alignment']['ma20']:.2f}"
            )
        
        with col3:
            st.metric(
                "趋势强度",
                f"MA20斜率: {market_analysis['ma20_slope']:.2f}%",
                f"MA60斜率: {market_analysis['ma60_slope']:.2f}%"
            )
        
        # 显示均线排列图
        st.subheader("📊 上证指数均线排列图")
        
        # 准备绘图数据
        plot_data = shanghai_data.copy()
        plot_data['MA5'] = calculate_ma(plot_data, 5)
        plot_data['MA10'] = calculate_ma(plot_data, 10)
        plot_data['MA20'] = calculate_ma(plot_data, 20)
        plot_data['MA60'] = calculate_ma(plot_data, 60)
        plot_data['MA120'] = calculate_ma(plot_data, 120)
        
        # 创建Plotly图表
        fig = go.Figure()
        
        # 添加K线图（简化版，用收盘价线图代替）
        fig.add_trace(go.Scatter(
            x=plot_data['date'],
            y=plot_data['close'],
            mode='lines',
            name='上证指数',
            line=dict(color='#1f77b4', width=2)
        ))
        
        # 添加均线
        fig.add_trace(go.Scatter(
            x=plot_data['date'],
            y=plot_data['MA5'],
            mode='lines',
            name='MA5',
            line=dict(color='#ff7f0e', width=1)
        ))
        
        fig.add_trace(go.Scatter(
            x=plot_data['date'],
            y=plot_data['MA10'],
            mode='lines',
            name='MA10',
            line=dict(color='#2ca02c', width=1)
        ))
        
        fig.add_trace(go.Scatter(
            x=plot_data['date'],
            y=plot_data['MA20'],
            mode='lines',
            name='MA20',
            line=dict(color='#d62728', width=1.5)
        ))
        
        fig.add_trace(go.Scatter(
            x=plot_data['date'],
            y=plot_data['MA60'],
            mode='lines',
            name='MA60',
            line=dict(color='#9467bd', width=1.5)
        ))
        
        fig.add_trace(go.Scatter(
            x=plot_data['date'],
            y=plot_data['MA120'],
            mode='lines',
            name='MA120',
            line=dict(color='#8c564b', width=1.5)
        ))
        
        # 更新布局
        fig.update_layout(
            title='上证指数均线系统分析',
            xaxis_title='日期',
            yaxis_title='点位',
            height=500,
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            hovermode='x unified'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # 显示详细分析
        st.subheader("🔍 详细分析")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**📊 均线排列状态：**")
            for reason in market_analysis['strength_reasons'][:4]:  # 前4个是均线相关
                st.write(reason)
        
        with col2:
            st.markdown("**📈 趋势与指标：**")
            for reason in market_analysis['strength_reasons'][4:]:  # 后几个是趋势和MACD
                st.write(reason)
        
        # 投资建议
        st.subheader("💡 大盘投资建议")
        
        if market_analysis['strength_score'] >= 80:
            st.success("**🔥 强势市场建议：** 大盘处于强势状态，均线多头排列，可积极配置股票资产，重点关注强势板块和个股。")
        elif market_analysis['strength_score'] >= 60:
            st.info("**📈 偏强市场建议：** 大盘整体偏强，但需关注短期调整风险，可适度配置，建议分批建仓。")
        elif market_analysis['strength_score'] >= 40:
            st.warning("**⚖️ 中性市场建议：** 大盘处于震荡状态，建议控制仓位，等待明确方向，可关注防御性板块。")
        elif market_analysis['strength_score'] >= 20:
            st.warning("**📉 偏弱市场建议：** 大盘偏弱，建议降低仓位，关注超跌反弹机会，以防御为主。")
        else:
            st.error("**💀 弱势市场建议：** 大盘处于弱势，建议大幅降低仓位，等待市场企稳，可关注债券等避险资产。")
        
        st.markdown("---")
    else:
        st.error("无法分析大盘强势状态，请检查数据获取")
else:
    st.error("无法获取上证指数数据，请检查网络连接")

# 宽基指数配置
BROAD_INDICES = {
    "000001": {"name": "上证指数", "description": "上海市场基准"},
    "000300": {"name": "沪深300", "description": "大盘蓝筹代表"},
    "000500": {"name": "中证500", "description": "中盘成长代表"},
    "000906": {"name": "中证800", "description": "大中盘代表"},
    "000852": {"name": "中证1000", "description": "小盘成长代表"},
    "000985": {"name": "中证全指", "description": "全市场代表"},
    "000688": {"name": "科创50", "description": "科技创新龙头"},
    "932000": {"name": "中证2000", "description": "小微盘代表"},
    "399303": {"name": "国证2000", "description": "深市小微盘代表"},
    "399006": {"name": "创业板指", "description": "科技创新代表"},
    "899050": {"name": "北证50", "description": "北交所龙头代表"}
}

# 获取指数历史数据
@st.cache_data(ttl=3600)
def get_index_history(symbol, days=180):
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # 尝试不同的接口获取数据
        data = pd.DataFrame()
        data_source = "未知"
        
        # 首先尝试中证指数接口
        try:
            data = ak.stock_zh_index_hist_csindex(
                symbol=symbol,
                start_date=start_date.strftime('%Y%m%d'),
                end_date=end_date.strftime('%Y%m%d')
            )
            if not data.empty:
                data_source = "中证指数接口"
        except:
            pass
        
        # 如果中证接口失败，尝试东方财富接口
        if data.empty:
            try:
                data = ak.index_zh_a_hist(
                    symbol=symbol, 
                    period="daily",
                    start_date=start_date.strftime('%Y%m%d'),
                    end_date=end_date.strftime('%Y%m%d')
                )
                if not data.empty:
                    data_source = "东方财富接口"
            except:
                pass
        
        # 如果还是失败，尝试新浪接口
        if data.empty:
            try:
                data = ak.stock_zh_index_hist_sina(
                    symbol=symbol,
                    start_date=start_date.strftime('%Y-%m-%d'),
                    end_date=end_date.strftime('%Y-%m-%d')
                )
                if not data.empty:
                    data_source = "新浪接口"
            except:
                pass
        
        if not data.empty:
            # 清理数据
            data['日期'] = pd.to_datetime(data['日期'])
            data['收盘'] = pd.to_numeric(data['收盘'], errors='coerce')
            data = data.sort_values('日期').reset_index(drop=True)
            
            # 过滤掉无效数据
            data = data.dropna(subset=['收盘'])
            
            # 添加数据源信息
            data.attrs['data_source'] = data_source
            data.attrs['last_update'] = end_date.strftime('%Y-%m-%d')
            
            return data
        else:
            return pd.DataFrame()
    except Exception as e:
        return pd.DataFrame()

# 计算年初至今涨跌幅
def calculate_ytd_return(index_data):
    try:
        if index_data.empty:
            return np.nan
        
        current_year = datetime.now().year
        current_year_data = index_data[index_data['日期'].dt.year == current_year]
        
        if not current_year_data.empty:
            first_day_price = current_year_data.iloc[0]['收盘']
            latest_price = index_data.iloc[-1]['收盘']
            
            if first_day_price != 0:
                ytd_change = (latest_price - first_day_price) / first_day_price * 100
                return ytd_change
            else:
                return np.nan
        else:
            return np.nan
    except Exception as e:
        return np.nan

# 计算最大回撤
def calculate_max_drawdown(index_data):
    try:
        if index_data.empty or len(index_data) < 2:
            return np.nan, np.nan, np.nan, np.nan
        
        # 计算累计收益率
        prices = index_data['收盘'].values
        cumulative_returns = []
        peak_prices = []
        drawdowns = []
        
        for i in range(len(prices)):
            if i == 0:
                cumulative_returns.append(0)
                peak_prices.append(prices[i])
                drawdowns.append(0)
            else:
                # 累计收益率
                cumulative_return = (prices[i] - prices[0]) / prices[0] * 100
                cumulative_returns.append(cumulative_return)
                
                # 历史最高点
                peak_price = max(prices[:i+1])
                peak_prices.append(peak_price)
                
                # 回撤
                if peak_price != 0:
                    drawdown = (prices[i] - peak_price) / peak_price * 100
                else:
                    drawdown = 0
                drawdowns.append(drawdown)
        
        # 找到最大回撤
        max_drawdown = min(drawdowns)
        max_drawdown_idx = drawdowns.index(max_drawdown)
        
        # 找到回撤开始点（历史最高点）
        peak_idx = None
        for i in range(max_drawdown_idx, -1, -1):
            if prices[i] == peak_prices[max_drawdown_idx]:
                peak_idx = i
                break
        
        # 计算回撤区间
        if peak_idx is not None:
            peak_date = index_data.iloc[peak_idx]['日期']
            trough_date = index_data.iloc[max_drawdown_idx]['日期']
            recovery_date = None
            
            # 寻找回撤恢复点（回到历史最高点）
            for i in range(max_drawdown_idx + 1, len(prices)):
                if prices[i] >= peak_prices[max_drawdown_idx]:
                    recovery_date = index_data.iloc[i]['日期']
                    break
            
            return max_drawdown, peak_date, trough_date, recovery_date
        else:
            return max_drawdown, None, None, None
            
    except Exception as e:
        return np.nan, np.nan, np.nan, np.nan

# 计算所有指数的收益指标
def calculate_all_returns():
    returns_data = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, (index_code, index_info) in enumerate(BROAD_INDICES.items()):
        status_text.text(f"正在计算 {index_info['name']} ({index_code}) 的收益指标...")
        
        index_data = get_index_history(index_code, days=180)
        
        if not index_data.empty:
            # 计算20日涨跌幅
            if len(index_data) >= 20:
                start_20d = index_data.iloc[-20]['收盘']
                end_20d = index_data.iloc[-1]['收盘']
                change_20d = (end_20d - start_20d) / start_20d * 100
            else:
                change_20d = np.nan
            
            # 计算40日涨跌幅
            if len(index_data) >= 40:
                start_40d = index_data.iloc[-40]['收盘']
                end_40d = index_data.iloc[-1]['收盘']
                change_40d = (end_40d - start_40d) / start_40d * 100
            else:
                change_40d = np.nan
            
            # 计算年初至今涨跌幅
            change_ytd = calculate_ytd_return(index_data)
            
            # 计算最大回撤
            max_drawdown, peak_date, trough_date, recovery_date = calculate_max_drawdown(index_data)
            
            returns_data.append({
                '指数代码': index_code,
                '指数名称': index_info['name'],
                '指数描述': index_info['description'],
                '20日涨跌幅': change_20d,
                '40日涨跌幅': change_40d,
                '年初至今涨跌幅': change_ytd,
                '最大回撤': max_drawdown,
                '历史数据': index_data  # 存储历史数据，供趋势图使用
            })
            
            st.success(f"✅ {index_info['name']} 数据获取成功，共 {len(index_data)} 条记录")
        else:
            st.error(f"❌ {index_info['name']} ({index_code}) 数据获取失败")
            # 尝试使用备用代码
            if index_code == "399006":  # 创业板指
                st.info("🔄 尝试使用备用代码获取创业板指数据...")
                # 创业板指的备用代码
                backup_codes = ["399006", "399006.SZ", "399006.SZE"]
                for backup_code in backup_codes:
                    try:
                        backup_data = ak.index_zh_a_hist(
                            symbol=backup_code, 
                            period="daily",
                            start_date=(end_date - timedelta(days=180)).strftime('%Y%m%d'),
                            end_date=end_date.strftime('%Y%m%d')
                        )
                        if not backup_data.empty:
                            st.success(f"✅ 使用备用代码 {backup_code} 成功获取创业板指数据")
                            # 重新计算收益指标
                            if len(backup_data) >= 20:
                                start_20d = backup_data.iloc[-20]['收盘']
                                end_20d = backup_data.iloc[-1]['收盘']
                                change_20d = (end_20d - start_20d) / start_20d * 100
                            else:
                                change_20d = np.nan
                            
                            if len(backup_data) >= 40:
                                start_40d = backup_data.iloc[-40]['收盘']
                                end_40d = backup_data.iloc[-1]['收盘']
                                change_40d = (end_40d - start_40d) / start_40d * 100
                            else:
                                change_40d = np.nan
                            
                            change_ytd = calculate_ytd_return(backup_data)
                            max_drawdown, peak_date, trough_date, recovery_date = calculate_max_drawdown(backup_data)
                            
                            returns_data.append({
                                '指数代码': index_code,
                                '指数名称': index_info['name'],
                                '指数描述': index_info['description'],
                                '20日涨跌幅': change_20d,
                                '40日涨跌幅': change_40d,
                                '年初至今涨跌幅': change_ytd,
                                '最大回撤': max_drawdown,
                                '历史数据': backup_data  # 存储历史数据，供趋势图使用
                            })
                            break
                    except:
                        continue
        
        progress_bar.progress((i + 1) / len(BROAD_INDICES))
    
    progress_bar.empty()
    status_text.empty()
    
    if returns_data:
        df = pd.DataFrame(returns_data)
        
        # 计算相对上证指数的超额收益
        shanghai_data = df[df['指数代码'] == '000001'].iloc[0] if not df[df['指数代码'] == '000001'].empty else None
        
        if shanghai_data is not None:
            df['相对上证20日超额收益'] = df['20日涨跌幅'] - shanghai_data['20日涨跌幅']
            df['相对上证40日超额收益'] = df['40日涨跌幅'] - shanghai_data['40日涨跌幅']
            df['相对上证年初至今超额收益'] = df['年初至今涨跌幅'] - shanghai_data['年初至今涨跌幅']
        
        return df
    
    return pd.DataFrame()

# 页面控制
st.subheader("🔍 分析参数设置")

# 运行分析按钮
run_btn = st.button("🚀 运行宽基指数对比分析")

if run_btn:
    st.subheader("📊 宽基指数收益分析")
    
    # 数据获取日志折叠区域
    with st.expander("📋 数据获取进度（点击展开查看详情）", expanded=False):
        with st.spinner("正在计算所有宽基指数的收益指标..."):
            returns_df = calculate_all_returns()
    
    if not returns_df.empty:
        # 显示数据获取状态
        st.subheader("📊 数据获取状态")
        
        # 检查哪些指数成功获取了数据
        available_indices = returns_df['指数名称'].tolist()
        missing_indices = []
        
        for code, info in BROAD_INDICES.items():
            if info['name'] not in available_indices:
                missing_indices.append(f"{info['name']} ({code})")
        
        if missing_indices:
            st.warning(f"⚠️ 以下指数数据获取失败：{', '.join(missing_indices)}")
        else:
            st.success("✅ 所有指数数据获取成功！")
        
        st.markdown("---")
        
        # 20日收益横向柱状图
        st.subheader("📈 20日收益横向柱状图")
        
        # 按20日涨跌幅排序，方便查看
        returns_df_sorted_20d = returns_df.sort_values('20日涨跌幅', ascending=False)
        
        # 创建20日收益横向柱状图
        fig_returns_20d = go.Figure()
        
        # 添加柱状图
        fig_returns_20d.add_trace(go.Bar(
            y=returns_df_sorted_20d['指数名称'],
            x=returns_df_sorted_20d['20日涨跌幅'],
            orientation='h',
            marker=dict(
                color=returns_df_sorted_20d['20日涨跌幅'],
                colorscale='RdYlGn_r',
                cmin=returns_df_sorted_20d['20日涨跌幅'].min(),
                cmax=returns_df_sorted_20d['20日涨跌幅'].max(),
                showscale=True,
                colorbar=dict(title="涨跌幅(%)", x=1.1)
            ),
            text=returns_df_sorted_20d['20日涨跌幅'].round(2),
            textposition='auto',
            hovertemplate='<b>%{y}</b><br>20日涨跌幅: %{x:.2f}%<extra></extra>'
        ))
        
        # 添加上证指数基准参考线
        shanghai_20d = returns_df[returns_df['指数代码'] == '000001']['20日涨跌幅'].iloc[0] if not returns_df.empty else 0
        fig_returns_20d.add_vline(
            x=shanghai_20d,
            line_dash="dash",
            line_color="blue",
            line_width=3,
            annotation_text=f"上证指数基准({shanghai_20d:.2f}%)",
            annotation_position="top right"
        )
        
        # 添加零线参考
        fig_returns_20d.add_vline(
            x=0,
            line_dash="dot",
            line_color="gray",
            line_width=2,
            annotation_text="零线",
            annotation_position="bottom right"
        )
        
        fig_returns_20d.update_layout(
            title="宽基指数 20日收益横向对比图",
            xaxis_title="20日涨跌幅 (%)",
            yaxis_title="指数",
            height=600,
            showlegend=False
        )
        
        st.plotly_chart(fig_returns_20d, use_container_width=True)
        
        # 20日收益柱状图说明
        st.markdown("""
        **📈 20日收益柱状图说明：**
        - **蓝色虚线**：上证指数基准线，表示市场整体表现
        - **灰色点线**：零线，区分正负收益
        - **颜色渐变**：红色表示正收益，绿色表示负收益
        - **柱长对比**：柱长越长表示收益越高（正收益）或亏损越大（负收益）
        """)
        
        # 20日收益趋势图
        st.subheader("📈 20日收益趋势图")
        
        # 创建20日收益趋势图
        fig_trend_20d = go.Figure()
        
        # 为每个指数添加趋势线
        for _, row in returns_df.iterrows():
            index_code = row['指数代码']
            index_name = row['指数名称']
            
            # 使用与柱状图相同的历史数据
            index_data = row['历史数据']
            
            if not index_data.empty and len(index_data) >= 20:
                # 计算20日滚动涨跌幅
                rolling_20d = []
                dates = []
                
                for i in range(19, len(index_data)):
                    start_price = index_data.iloc[i-19]['收盘']
                    end_price = index_data.iloc[i]['收盘']
                    if start_price != 0:
                        change = (end_price - start_price) / start_price * 100
                        rolling_20d.append(change)
                        dates.append(index_data.iloc[i]['日期'])
                
                if rolling_20d:
                    # 添加趋势线
                    fig_trend_20d.add_trace(go.Scatter(
                        x=dates,
                        y=rolling_20d,
                        mode='lines',
                        name=index_name,
                        line=dict(width=2),
                        hovertemplate='<b>%{fullData.name}</b><br>日期: %{x}<br>20日涨跌幅: %{y:.2f}%<extra></extra>'
                    ))
        
        # 添加零线参考
        fig_trend_20d.add_hline(
            y=0,
            line_dash="dot",
            line_color="gray",
            line_width=2,
            annotation_text="零线"
        )
        
        fig_trend_20d.update_layout(
            title="宽基指数 20日收益趋势图",
            xaxis_title="日期",
            yaxis_title="20日涨跌幅 (%)",
            height=500,
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        st.plotly_chart(fig_trend_20d, use_container_width=True)
        
        # 40日收益横向柱状图
        st.subheader("📈 40日收益横向柱状图")
        
        # 按40日涨跌幅排序，方便查看
        returns_df_sorted_40d = returns_df.sort_values('40日涨跌幅', ascending=False)
        
        # 创建40日收益横向柱状图
        fig_returns_40d = go.Figure()
        
        # 添加柱状图
        fig_returns_40d.add_trace(go.Bar(
            y=returns_df_sorted_40d['指数名称'],
            x=returns_df_sorted_40d['40日涨跌幅'],
            orientation='h',
            marker=dict(
                color=returns_df_sorted_40d['40日涨跌幅'],
                colorscale='RdYlGn_r',
                cmin=returns_df_sorted_40d['40日涨跌幅'].min(),
                cmax=returns_df_sorted_40d['40日涨跌幅'].max(),
                showscale=True,
                colorbar=dict(title="涨跌幅(%)", x=1.1)
            ),
            text=returns_df_sorted_40d['40日涨跌幅'].round(2),
            textposition='auto',
            hovertemplate='<b>%{y}</b><br>40日涨跌幅: %{x:.2f}%<extra></extra>'
        ))
        
        # 添加上证指数基准参考线（40日）
        shanghai_40d = returns_df[returns_df['指数代码'] == '000001']['40日涨跌幅'].iloc[0] if not returns_df.empty else 0
        fig_returns_40d.add_vline(
            x=shanghai_40d,
            line_dash="dash",
            line_color="blue",
            line_width=3,
            annotation_text=f"上证指数基准({shanghai_40d:.2f}%)",
            annotation_position="top right"
        )
        
        # 添加零线参考
        fig_returns_40d.add_vline(
            x=0,
            line_dash="dot",
            line_color="gray",
            line_width=2,
            annotation_text="零线",
            annotation_position="bottom right"
        )
        
        fig_returns_40d.update_layout(
            title="宽基指数 40日收益横向对比图",
            xaxis_title="40日涨跌幅 (%)",
            yaxis_title="指数",
            height=600,
            showlegend=False
        )
        
        st.plotly_chart(fig_returns_40d, use_container_width=True)
        
        # 40日收益柱状图说明
        st.markdown("""
        **📈 40日收益柱状图说明：**
        - **蓝色虚线**：上证指数基准线，表示市场整体表现
        - **灰色点线**：零线，区分正负收益
        - **颜色渐变**：红色表示正收益，绿色表示负收益
        - **柱长对比**：柱长越长表示收益越高（正收益）或亏损越大（负收益）
        - **时间窗口**：40日收益反映中期市场表现，相比20日收益波动更平滑
        """)
        
        # 40日收益趋势图
        st.subheader("📈 40日收益趋势图")
        
        # 创建40日收益趋势图
        fig_trend_40d = go.Figure()
        
        # 为每个指数添加趋势线
        for _, row in returns_df.iterrows():
            index_code = row['指数代码']
            index_name = row['指数名称']
            
            # 使用与柱状图相同的历史数据
            index_data = row['历史数据']
            
            if not index_data.empty and len(index_data) >= 40:
                # 计算40日滚动涨跌幅
                rolling_40d = []
                dates = []
                
                for i in range(39, len(index_data)):
                    start_price = index_data.iloc[i-39]['收盘']
                    end_price = index_data.iloc[i]['收盘']
                    if start_price != 0:
                        change = (end_price - start_price) / start_price * 100
                        rolling_40d.append(change)
                        dates.append(index_data.iloc[i]['日期'])
                
                if rolling_40d:
                    # 添加趋势线
                    fig_trend_40d.add_trace(go.Scatter(
                        x=dates,
                        y=rolling_40d,
                        mode='lines',
                        name=index_name,
                        line=dict(width=2),
                        hovertemplate='<b>%{fullData.name}</b><br>日期: %{x}<br>40日涨跌幅: %{y:.2f}%<extra></extra>'
                    ))
        
        # 添加零线参考
        fig_trend_40d.add_hline(
            y=0,
            line_dash="dot",
            line_color="gray",
            line_width=2,
            annotation_text="零线"
        )
        
        fig_trend_40d.update_layout(
            title="宽基指数 40日收益趋势图",
            xaxis_title="日期",
            yaxis_title="40日涨跌幅 (%)",
            height=500,
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        st.plotly_chart(fig_trend_40d, use_container_width=True)
        
        # 年初至今收益横向柱状图
        st.subheader("📈 年初至今收益横向柱状图")
        
        # 按年初至今涨跌幅排序，方便查看
        returns_df_sorted_ytd = returns_df.sort_values('年初至今涨跌幅', ascending=False)
        
        # 创建年初至今收益横向柱状图
        fig_returns_ytd = go.Figure()
        
        # 添加柱状图
        fig_returns_ytd.add_trace(go.Bar(
            y=returns_df_sorted_ytd['指数名称'],
            x=returns_df_sorted_ytd['年初至今涨跌幅'],
            orientation='h',
            marker=dict(
                color=returns_df_sorted_ytd['年初至今涨跌幅'],
                colorscale='RdYlGn_r',
                cmin=returns_df_sorted_ytd['年初至今涨跌幅'].min(),
                cmax=returns_df_sorted_ytd['年初至今涨跌幅'].max(),
                showscale=True,
                colorbar=dict(title="涨跌幅(%)", x=1.1)
            ),
            text=returns_df_sorted_ytd['年初至今涨跌幅'].round(2),
            textposition='auto',
            hovertemplate='<b>%{y}</b><br>年初至今涨跌幅: %{x:.2f}%<extra></extra>'
        ))
        
        # 添加上证指数基准参考线（年初至今）
        shanghai_ytd = returns_df[returns_df['指数代码'] == '000001']['年初至今涨跌幅'].iloc[0] if not returns_df.empty else 0
        fig_returns_ytd.add_vline(
            x=shanghai_ytd,
            line_dash="dash",
            line_color="blue",
            line_width=3,
            annotation_text=f"上证指数基准({shanghai_ytd:.2f}%)",
            annotation_position="top right"
        )
        
        # 添加零线参考
        fig_returns_ytd.add_vline(
            x=0,
            line_dash="dot",
            line_color="gray",
            line_width=2,
            annotation_text="零线",
            annotation_position="bottom right"
        )
        
        fig_returns_ytd.update_layout(
            title="宽基指数 年初至今收益横向对比图",
            xaxis_title="年初至今涨跌幅 (%)",
            yaxis_title="指数",
            height=600,
            showlegend=False
        )
        
        st.plotly_chart(fig_returns_ytd, use_container_width=True)
        
        # 年初至今收益柱状图说明
        st.markdown("""
        **📈 年初至今收益柱状图说明：**
        - **蓝色虚线**：上证指数基准线，表示市场整体表现
        - **灰色点线**：零线，区分正负收益
        - **颜色渐变**：红色表示正收益，绿色表示负收益
        - **柱长对比**：柱长越长表示收益越高（正收益）或亏损越大（负收益）
        - **时间窗口**：年初至今收益反映全年市场表现，适合年度投资策略评估
        """)
        
        # 年初至今收益趋势图
        st.subheader("📈 年初至今收益趋势图")
        
        # 创建年初至今收益趋势图
        fig_trend_ytd = go.Figure()
        
        # 为每个指数添加趋势线
        for _, row in returns_df.iterrows():
            index_code = row['指数代码']
            index_name = row['指数名称']
            
            # 使用与柱状图相同的历史数据
            index_data = row['历史数据']
            
            if not index_data.empty:
                # 使用与柱状图完全相同的计算逻辑
                rolling_ytd = []
                dates = []
                current_year = datetime.now().year
                
                # 筛选今年数据
                current_year_data = index_data[index_data['日期'].dt.year == current_year]
                
                if not current_year_data.empty:
                    # 获取今年第一个交易日的价格（与柱状图计算保持一致）
                    first_day_price = current_year_data.iloc[0]['收盘']
                    
                    # 计算每个交易日的年初至今涨跌幅
                    for _, day_data in current_year_data.iterrows():
                        current_price = day_data['收盘']
                        if first_day_price != 0:
                            change = (current_price - first_day_price) / first_day_price * 100
                            rolling_ytd.append(change)
                            dates.append(day_data['日期'])
                
                if rolling_ytd:
                    # 添加趋势线
                    fig_trend_ytd.add_trace(go.Scatter(
                        x=dates,
                        y=rolling_ytd,
                        mode='lines',
                        name=index_name,
                        line=dict(width=2),
                        hovertemplate='<b>%{fullData.name}</b><br>日期: %{x}<br>年初至今涨跌幅: %{y:.2f}%<extra></extra>'
                    ))
        
        # 添加零线参考
        fig_trend_ytd.add_hline(
            y=0,
            line_dash="dot",
            line_color="gray",
            line_width=2,
            annotation_text="零线"
        )
        
        fig_trend_ytd.update_layout(
            title="宽基指数 年初至今收益趋势图",
            xaxis_title="日期",
            yaxis_title="年初至今涨跌幅 (%)",
            height=500,
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        st.plotly_chart(fig_trend_ytd, use_container_width=True)
        
        # 数据一致性说明
        st.info("✅ **数据一致性**：柱状图和趋势图使用相同数据源和计算逻辑")
        
        # 最大回撤分析图
        st.subheader("📉 最大回撤分析图")
        
        # 创建最大回撤趋势图
        fig_drawdown = go.Figure()
        
        # 为每个指数添加回撤趋势线
        for _, row in returns_df.iterrows():
            index_code = row['指数代码']
            index_name = row['指数名称']
            
            # 使用与柱状图相同的历史数据
            index_data = row['历史数据']
            
            if not index_data.empty and len(index_data) >= 2:
                # 计算滚动回撤
                dates = []
                drawdowns = []
                
                for i in range(len(index_data)):
                    current_date = index_data.iloc[i]['日期']
                    current_price = index_data.iloc[i]['收盘']
                    
                    # 计算到当前时点的历史最高价
                    historical_peak = max(index_data.iloc[:i+1]['收盘'])
                    
                    # 计算回撤
                    if historical_peak != 0:
                        drawdown = (current_price - historical_peak) / historical_peak * 100
                    else:
                        drawdown = 0
                    
                    dates.append(current_date)
                    drawdowns.append(drawdown)
                
                if drawdowns:
                    # 添加趋势线
                    fig_drawdown.add_trace(go.Scatter(
                        x=dates,
                        y=drawdowns,
                        mode='lines',
                        name=index_name,
                        line=dict(width=2),
                        hovertemplate='<b>%{fullData.name}</b><br>日期: %{x}<br>回撤: %{y:.2f}%<extra></extra>'
                    ))
        
        # 添加零线参考
        fig_drawdown.add_hline(
            y=0,
            line_dash="dot",
            line_color="gray",
            line_width=2,
            annotation_text="无回撤线"
        )
        
        # 添加回撤参考线
        fig_drawdown.add_hline(
            y=-10,
            line_dash="dash",
            line_color="orange",
            line_width=1,
            annotation_text="-10%回撤线"
        )
        
        fig_drawdown.add_hline(
            y=-20,
            line_dash="dash",
            line_color="red",
            line_width=1,
            annotation_text="-20%回撤线"
        )
        
        fig_drawdown.update_layout(
            title="宽基指数回撤趋势图",
            xaxis_title="日期",
            yaxis_title="回撤 (%)",
            height=600,
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        # 反转Y轴，让回撤显示更直观（负值在上方）
        # fig_drawdown.update_yaxes(autorange="reversed")
        
        st.plotly_chart(fig_drawdown, use_container_width=True)
        
        # 最大回撤说明
        st.markdown("""
        **📉 最大回撤说明：**
        - **回撤定义**：从历史最高点到当前价格的跌幅
        - **回撤为负值**：数值越小（越负）表示回撤越大
        - **参考线**：橙色虚线(-10%)和红色虚线(-20%)为重要回撤水平
        - **投资参考**：回撤越小表示风险控制越好，回撤恢复越快表示弹性越强
        """)
        
        # 最大回撤详细分析
        st.subheader("🔍 最大回撤详细分析")
        
        # 创建最大回撤详细分析表格
        drawdown_details = []
        for _, row in returns_df.iterrows():
            index_code = row['指数代码']
            index_name = row['指数名称']
            max_dd = row['最大回撤']
            
            # 获取该指数的历史数据来计算回撤区间
            index_data = row['历史数据']
            if not index_data.empty:
                _, peak_date, trough_date, recovery_date = calculate_max_drawdown(index_data)
                
                # 格式化日期
                peak_str = peak_date.strftime('%Y-%m-%d') if peak_date else '未知'
                trough_str = trough_date.strftime('%Y-%m-%d') if trough_date else '未知'
                recovery_str = recovery_date.strftime('%Y-%m-%d') if recovery_date else '未恢复'
                
                drawdown_details.append({
                    '指数名称': index_name,
                    '指数代码': index_code,
                    '最大回撤': f"{max_dd:.2f}%",
                    '回撤开始': peak_str,
                    '回撤底部': trough_str,
                    '恢复状态': recovery_str
                })
        
        if drawdown_details:
            drawdown_df = pd.DataFrame(drawdown_details)
            
            # 应用样式
            def color_drawdown(val):
                if pd.isna(val):
                    return ''
                try:
                    dd_value = float(val.replace('%', ''))
                    if dd_value <= -20:
                        return 'background-color: #ffebee; color: #c62828'  # 深红
                    elif dd_value <= -10:
                        return 'background-color: #fff3e0; color: #ef6c00'  # 橙色
                    elif dd_value <= -5:
                        return 'background-color: #fff8e1; color: #f57f17'  # 浅橙
                    else:
                        return 'background-color: #e8f5e8; color: #2e7d32'  # 绿色
                except:
                    return ''
            
            styled_dd_df = drawdown_df.style.apply(
                lambda x: [color_drawdown(val) if col == '最大回撤' else '' for col, val in x.items()],
                subset=['最大回撤']
            )
            
            st.dataframe(styled_dd_df, use_container_width=True)
            
            # 回撤区间说明
            st.info("""
            **📊 回撤区间解读：**
            - **回撤开始**：指数达到历史最高点的日期
            - **回撤底部**：指数跌到最低点的日期
            - **恢复状态**：指数重新回到历史最高点的日期（如果已恢复）
            - **风险等级**：回撤≤-20%为高风险，≤-10%为中风险，≤-5%为低风险
            """)
        
        # 显示收益排名表格
        st.subheader("📋 收益指标排名表")
        
        # 创建用于显示的DataFrame（去掉历史数据列）
        display_df = returns_df.drop(columns=['历史数据'])
        
        # 格式化表格显示 - 使用自定义颜色函数确保正确的配色
        def color_positive_negative(val):
            if pd.isna(val):
                return ''
            try:
                if val > 0:
                    return 'background-color: #ffcdd2; color: #b71c1c'  # 红色背景，深红文字
                elif val < 0:
                    return 'background-color: #c8e6c9; color: #1b5e20'  # 绿色背景，深绿文字
                else:
                    return 'background-color: #f5f5f5; color: #424242'  # 灰色背景，深灰文字
            except:
                return ''
        
        def color_drawdown(val):
            if pd.isna(val):
                return ''
            try:
                if val <= -20:
                    return 'background-color: #ffcdd2; color: #b71c1c'  # 深红背景，深红文字
                elif val <= -10:
                    return 'background-color: #ffccbc; color: #bf360c'  # 橙红背景，深橙文字
                elif val <= -5:
                    return 'background-color: #ffe0b2; color: #e65100'  # 浅橙背景，橙文字
                elif val <= 0:
                    return 'background-color: #c8e6c9; color: #1b5e20'  # 绿色背景，深绿文字
                else:
                    return 'background-color: #e1bee7; color: #4a148c'  # 紫色背景，深紫文字
            except:
                return ''
        
        # 应用样式
        styled_df = display_df.style
        
        # 为收益指标列添加颜色
        for col in ['20日涨跌幅', '40日涨跌幅', '年初至今涨跌幅']:
            if col in display_df.columns:
                styled_df = styled_df.apply(
                    lambda x: [color_positive_negative(val) if col_name == col else '' for col_name, val in x.items()],
                    subset=[col]
                )
        
        # 为超额收益列添加颜色
        for col in ['相对上证20日超额收益', '相对上证40日超额收益', '相对上证年初至今超额收益']:
            if col in display_df.columns:
                styled_df = styled_df.apply(
                    lambda x: [color_positive_negative(val) if col_name == col else '' for col_name, val in x.items()],
                    subset=[col]
                )
        
        # 为最大回撤列添加颜色
        if '最大回撤' in display_df.columns:
            styled_df = styled_df.apply(
                lambda x: [color_drawdown(val) if col_name == '最大回撤' else '' for col_name, val in x.items()],
                subset=['最大回撤']
            )
        
        # 格式化数值
        styled_df = styled_df.format({
            '20日涨跌幅': '{:.2f}%',
            '40日涨跌幅': '{:.2f}%',
            '年初至今涨跌幅': '{:.2f}%',
            '最大回撤': '{:.2f}%',
            '相对上证20日超额收益': '{:.2f}%',
            '相对上证40日超额收益': '{:.2f}%',
            '相对上证年初至今超额收益': '{:.2f}%'
        })
        
        st.dataframe(styled_df, use_container_width=True)
        
        # 表现分析
        st.subheader("🚨 表现分析")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # 跑赢上证指数的数量
            outperform_20d = len(returns_df[returns_df['相对上证20日超额收益'] > 0])
            outperform_40d = len(returns_df[returns_df['相对上证40日超额收益'] > 0])
            outperform_ytd = len(returns_df[returns_df['相对上证年初至今超额收益'] > 0])
            
            st.info(f"📊 **20日跑赢上证：** {outperform_20d}/{len(returns_df)} 个指数")
            st.info(f"📊 **40日跑赢上证：** {outperform_40d}/{len(returns_df)} 个指数")
            st.info(f"📊 **年初至今跑赢上证：** {outperform_ytd}/{len(returns_df)} 个指数")
        
        with col2:
            # 表现最佳和最差的指数
            best_20d = returns_df.loc[returns_df['相对上证20日超额收益'].idxmax()]
            worst_20d = returns_df.loc[returns_df['相对上证20日超额收益'].idxmin()]
            
            st.success(f"🏆 **20日最佳：** {best_20d['指数名称']} (+{best_20d['相对上证20日超额收益']:.2f}%)")
            st.error(f"📉 **20日最差：** {worst_20d['指数名称']} ({worst_20d['相对上证20日超额收益']:.2f}%)")
        
        # 投资建议（折叠显示）
        with st.expander("💡 投资建议（点击展开查看）", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**📈 短期策略（20日）：**")
                strong_20d = returns_df[returns_df['相对上证20日超额收益'] > 0]
                if not strong_20d.empty:
                    for _, row in strong_20d.iterrows():
                        st.write(f"• **{row['指数名称']}** ({row['指数代码']})")
                        st.write(f"  - 超额收益: +{row['相对上证20日超额收益']:.2f}%")
                        st.write(f"  - 描述: {row['指数描述']}")
                        st.write("---")
                else:
                    st.write("暂无跑赢上证指数的指数")
            
            with col2:
                st.markdown("**📊 中期策略（40日）：**")
                strong_40d = returns_df[returns_df['相对上证40日超额收益'] > 0]
                if not strong_40d.empty:
                    for _, row in strong_40d.iterrows():
                        st.write(f"• **{row['指数名称']}** ({row['指数代码']})")
                        st.write(f"  - 超额收益: +{row['相对上证40日超额收益']:.2f}%")
                        st.write(f"  - 描述: {row['指数描述']}")
                        st.write("---")
                else:
                    st.write("暂无跑赢上证指数的指数")
        
        # 市场风格判断
        st.subheader("🎭 市场风格判断")
        
        # 计算各风格指数的平均表现
        style_analysis = {}
        
        # 大盘蓝筹风格（沪深300、中证800）
        large_cap = returns_df[returns_df['指数代码'].isin(['000300', '000906'])]
        if not large_cap.empty:
            style_analysis['大盘蓝筹'] = {
                '20日': large_cap['相对上证20日超额收益'].mean(),
                '40日': large_cap['相对上证40日超额收益'].mean(),
                '年初至今': large_cap['相对上证年初至今超额收益'].mean(),
                '指数': list(large_cap['指数名称'])
            }
        
        # 中盘成长风格（中证500、中证1000）
        mid_cap = returns_df[returns_df['指数代码'].isin(['000500', '000852'])]
        if not mid_cap.empty:
            style_analysis['中盘成长'] = {
                '20日': mid_cap['相对上证20日超额收益'].mean(),
                '40日': mid_cap['相对上证40日超额收益'].mean(),
                '年初至今': mid_cap['相对上证年初至今超额收益'].mean(),
                '指数': list(mid_cap['指数名称'])
            }
        
        # 小盘成长风格（中证2000、国证2000）
        small_cap = returns_df[returns_df['指数代码'].isin(['932000', '399303'])]
        if not small_cap.empty:
            style_analysis['小盘成长'] = {
                '20日': small_cap['相对上证20日超额收益'].mean(),
                '40日': small_cap['相对上证40日超额收益'].mean(),
                '年初至今': small_cap['相对上证年初至今超额收益'].mean(),
                '指数': list(small_cap['指数名称'])
            }
        
        # 科技创新风格（科创50、创业板指）
        tech_innovation = returns_df[returns_df['指数代码'].isin(['000688', '399006'])]
        if not tech_innovation.empty:
            style_analysis['科技创新'] = {
                '20日': tech_innovation['相对上证20日超额收益'].mean(),
                '40日': tech_innovation['相对上证40日超额收益'].mean(),
                '年初至今': tech_innovation['相对上证年初至今超额收益'].mean(),
                '指数': list(tech_innovation['指数名称'])
            }
        
        # 全市场风格（中证全指、北证50）
        broad_market = returns_df[returns_df['指数代码'].isin(['000985', '899050'])]
        if not broad_market.empty:
            style_analysis['全市场'] = {
                '20日': broad_market['相对上证20日超额收益'].mean(),
                '40日': broad_market['相对上证40日超额收益'].mean(),
                '年初至今': broad_market['相对上证年初至今超额收益'].mean(),
                '指数': list(broad_market['指数名称'])
            }
        
        # 显示市场风格分析结果
        if style_analysis:
            # 创建风格分析表格
            style_data = []
            for style, data in style_analysis.items():
                style_data.append({
                    '市场风格': style,
                    '代表指数': ', '.join(data['指数']),
                    '20日超额收益': f"{data['20日']:.2f}%",
                    '40日超额收益': f"{data['40日']:.2f}%",
                    '年初至今超额收益': f"{data['年初至今']:.2f}%"
                })
            
            style_df = pd.DataFrame(style_data)
            
            # 应用颜色样式
            def color_style_returns(val):
                if pd.isna(val):
                    return ''
                try:
                    num_val = float(val.replace('%', ''))
                    if num_val > 0:
                        return 'background-color: #f8d7da; color: #721c24'  # 红色背景（涨）
                    elif num_val < 0:
                        return 'background-color: #d4edda; color: #155724'  # 绿色背景（跌）
                    else:
                        return ''
                except:
                    return ''
            
            styled_style_df = style_df.style.apply(
                lambda x: [color_style_returns(val) if col in ['20日超额收益', '40日超额收益', '年初至今超额收益'] else '' 
                          for col, val in x.items()], 
                subset=['20日超额收益', '40日超额收益', '年初至今超额收益']
            )
            
            st.dataframe(styled_style_df, use_container_width=True)
            
            # 市场风格判断结论
            st.subheader("🎯 市场风格判断结论")
            
            # 找出各时间窗口表现最好的风格
            best_20d_style = max(style_analysis.items(), key=lambda x: x[1]['20日'])
            best_40d_style = max(style_analysis.items(), key=lambda x: x[1]['40日'])
            best_ytd_style = max(style_analysis.items(), key=lambda x: x[1]['年初至今'])
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    "20日最强风格",
                    best_20d_style[0],
                    f"+{best_20d_style[1]['20日']:.2f}%"
                )
            
            with col2:
                st.metric(
                    "40日最强风格",
                    best_40d_style[0],
                    f"+{best_40d_style[1]['40日']:.2f}%"
                )
            
            with col3:
                st.metric(
                    "年初至今最强风格",
                    best_ytd_style[0],
                    f"+{best_ytd_style[1]['年初至今']:.2f}%"
                )
            
            # 风格轮动分析
            st.markdown("**🔄 风格轮动分析：**")
            
            # 计算风格轮动强度
            style_rotation = {}
            for style, data in style_analysis.items():
                # 计算短期vs中期的风格变化
                short_vs_mid = data['20日'] - data['40日']
                # 计算中期vs长期的风格变化
                mid_vs_long = data['40日'] - data['年初至今']
                style_rotation[style] = {
                    '短期vs中期': short_vs_mid,
                    '中期vs长期': mid_vs_long,
                    '轮动强度': abs(short_vs_mid) + abs(mid_vs_long)
                }
            
            # 找出轮动最活跃的风格
            most_active_style = max(style_rotation.items(), key=lambda x: x[1]['轮动强度'])
            
            st.info(f"**最活跃风格：** {most_active_style[0]} (轮动强度: {most_active_style[1]['轮动强度']:.2f})")
            
            # 投资策略建议
            st.markdown("**💡 投资策略建议：**")
            
            # 根据风格表现给出建议
            if best_20d_style[1]['20日'] > 0 and best_40d_style[1]['40日'] > 0:
                st.success(f"**强势风格确认：** {best_20d_style[0]}和{best_40d_style[0]}在短期和中期都表现强势，建议重点关注")
            elif best_20d_style[1]['20日'] > 0 and best_40d_style[1]['40日'] < 0:
                st.warning(f"**风格切换信号：** {best_20d_style[0]}短期走强，但中期仍弱，需观察持续性")
            elif best_20d_style[1]['20日'] < 0 and best_40d_style[1]['40日'] > 0:
                st.warning(f"**风格调整信号：** {best_40d_style[0]}中期走强，但短期调整，可逢低关注")
            else:
                st.error("**弱势风格：** 各风格指数普遍跑输上证指数，建议谨慎操作，等待市场企稳")
        
        # 下载功能
        st.subheader("💾 下载分析结果")
        
        col1, col2 = st.columns(2)
        
        with col1:
            csv = display_df.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="📥 下载CSV报告",
                data=csv,
                file_name=f"宽基指数对比分析_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        
        with col2:
            try:
                import io
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    display_df.to_excel(writer, sheet_name='宽基指数对比', index=False)
                excel_data = output.getvalue()
                st.download_button(
                    label="📥 下载Excel报告",
                    data=excel_data,
                    file_name=f"宽基指数对比分析_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            except ImportError:
                st.info("💡 安装 openpyxl 可下载Excel格式报告")
    
    else:
        st.error("无法获取指数数据，请检查网络连接")

else:
    st.info("👆 请点击运行按钮开始分析")

# 页面底部说明
st.markdown("---")
st.markdown("""
**💡 使用说明：**
1. **点击运行按钮**：系统将自动获取所有宽基指数的数据
2. **查看图表**：三个横向柱状图分别展示20日、40日、年初至今的收益表现
3. **基准对比**：蓝色虚线表示上证指数基准，便于对比各指数相对表现
4. **颜色解读**：红色表示正收益，绿色表示负收益（符合中国股市习惯）

**🔍 投资策略解读：**
- **跑赢上证指数**：表示该指数相对强势，可重点关注
- **跑输上证指数**：表示该指数相对弱势，需谨慎对待
- **多时间窗口对比**：短期、中期、长期表现综合分析，识别趋势持续性

**⚠️ 风险提示：**
- 历史表现不代表未来收益
- 投资有风险，入市需谨慎
- 建议结合基本面分析和其他技术指标
""")
