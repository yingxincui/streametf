import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import akshare as ak
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

st.set_page_config(page_title="行业ETF强弱跟踪系统", page_icon="📊", layout="wide")
st.title("📊 行业ETF强弱跟踪系统")

st.markdown("""
> 基于RS（Relative Strength）指标的行业ETF强弱跟踪系统，通过多时间窗口动量分析识别行业轮动机会。
> 提供实时排名、历史走势、热力图可视化和智能预警功能。

**🎯 核心功能：**
- **RS指标计算**：20日、40日、60日多时间窗口动量分析
- **实时排名与热力图**：31个行业ETF的相对强弱排名和可视化对比
- **走势跟踪**：行业指数与滚动RS指标的双坐标走势图
- **智能预警**：RS突破90或跌破10的及时提醒
- **配置建议**：基于RS排名的行业配置策略

**📊 RS指标说明：**
- **RS_20**：过去20个交易日的相对强弱
- **RS_40**：过去40个交易日的相对强弱  
- **RS_60**：过去60个交易日的相对强弱
- **综合RS**：三个时间窗口的加权平均
- **归一化范围**：[0,100]，100为最强，0为最弱
- **实际天数**：如果数据不足指定天数，将使用最近可用的交易日数计算

**📈 滚动RS指标特点：**
- **滚动计算**：每个交易日都计算所有行业的20日、40日、60日涨跌幅，然后计算相对排名和归一化RS指标
- **综合RS**：将三个时间窗口的RS指标平均，得到综合RS指标
- **实时反映**：能够及时反映行业相对于其他行业的强弱变化趋势
- **单位**：RS指标范围为[0,100]，100为最强，0为最弱

**🎨 颜色规则：**
- **涨（正值）**：红色 🔴
- **跌（负值）**：绿色 🟢
（符合中国股市习惯）

**📈 数据说明：**
- **使用前复权数据**：避免因分红送股导致的价格跳跃，确保技术分析的准确性
- **数据来源**：通过Akshare接口获取实时市场数据
- **更新频率**：数据缓存1小时，确保分析时效性
""")

# 行业ETF配置
INDUSTRY_ETFS = {
    "农林牧渔": {"code": "159865", "name": "养殖ETF", "index": "中证畜牧养殖指数"},
    "采掘": {"code": "159930", "name": "能源ETF", "index": "煤炭、石油等资源类"},
    "化工": {"code": "516020", "name": "化工ETF", "index": "中证细分化工产业主题指数"},
    "钢铁": {"code": "515210", "name": "钢铁ETF", "index": "中证钢铁指数"},
    "有色金属": {"code": "512400", "name": "有色ETF", "index": "中证有色金属指数"},
    "电子": {"code": "512480", "name": "半导体ETF", "index": "芯片、电子元器件等"},
    "家用电器": {"code": "159730", "name": "家电ETF", "index": "中证全指家用电器指数"},
    "食品饮料": {"code": "159928", "name": "消费ETF", "index": "中证主要消费指数"},
    "纺织服装": {"code": "513910", "name": "服装ETF", "index": "中证纺织服装指数"},
    "轻工制造": {"code": "562900", "name": "轻工ETF", "index": "家居、造纸等细分领域"},
    "医药生物": {"code": "512170", "name": "医疗ETF", "index": "中证医疗指数"},
    "公用事业": {"code": "159611", "name": "电力ETF", "index": "中证全指电力公用事业指数"},
    "交通运输": {"code": "516910", "name": "物流ETF", "index": "中证现代物流指数"},
    "房地产": {"code": "512200", "name": "房地产ETF", "index": "中证全指房地产指数"},
    "商业贸易": {"code": "560280", "name": "零售ETF", "index": "中证主要消费指数"},
    "休闲服务": {"code": "159766", "name": "旅游ETF", "index": "中证旅游主题指数"},
    "综合": {"code": "512950", "name": "央企改革ETF", "index": "多行业综合型央企"},
    "建筑材料": {"code": "159745", "name": "建材ETF", "index": "中证全指建筑材料指数"},
    "建筑装饰": {"code": "516950", "name": "基建ETF", "index": "建筑工程、装饰等"},
    "电气设备": {"code": "515030", "name": "新能源车ETF", "index": "中证新能源汽车指数"},
    "机械设备": {"code": "516960", "name": "机械ETF", "index": "中证细分机械指数"},
    "国防军工": {"code": "512660", "name": "军工ETF", "index": "中证军工指数"},
    "计算机": {"code": "512720", "name": "计算机ETF", "index": "中证计算机主题指数"},
    "传媒": {"code": "512980", "name": "传媒ETF", "index": "中证传媒指数"},
    "通信": {"code": "515880", "name": "通信ETF", "index": "中证5G通信主题指数"},
    "银行": {"code": "512800", "name": "银行ETF", "index": "中证银行指数"},
    "非银金融": {"code": "512880", "name": "证券ETF", "index": "券商、保险等"},
    "汽车": {"code": "516110", "name": "汽车ETF", "index": "中证全指汽车指数"},
    "高端装备": {"code": "516320", "name": "高端装备ETF", "index": "工业机械、自动化等"},
    "环保": {"code": "512580", "name": "环保ETF", "index": "中证环保产业指数"},
    "综合金融": {"code": "516860", "name": "金融科技ETF", "index": "支付、区块链等金融相关科技"}
}

# 获取ETF历史数据
@st.cache_data(ttl=3600)  # 缓存1小时
def get_etf_history(etf_code, days=180):  # 增加到180天，确保有足够数据计算60天滚动RS
    """获取ETF历史数据"""
    try:
        # 计算开始日期
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # 获取历史数据 - 使用前复权数据避免分红送股导致的价格跳跃
        data = ak.fund_etf_hist_em(symbol=etf_code, period="daily", 
                                   start_date=start_date.strftime('%Y%m%d'),
                                   end_date=end_date.strftime('%Y%m%d'),
                                   adjust="qfq")  # 使用前复权数据
        
        if not data.empty:
            # 清理数据
            data['日期'] = pd.to_datetime(data['日期'])
            data['收盘'] = pd.to_numeric(data['收盘'], errors='coerce')
            data = data.sort_values('日期').reset_index(drop=True)
            
            # 过滤掉无效数据
            data = data.dropna(subset=['收盘'])
            
            return data
        else:
            return pd.DataFrame()
    except Exception as e:
        return pd.DataFrame()

# 计算RS指标
def calculate_rs_indicators(etf_data, periods=[20, 40, 60]):
    """计算RS指标"""
    if etf_data.empty:
        return None
    
    results = {}
    
    for period in periods:
        # 如果数据不足指定天数，就用最近可用的日期
        actual_period = min(period, len(etf_data) - 1)
        if actual_period > 0:
            # 计算涨跌幅
            start_price = etf_data.iloc[-actual_period]['收盘']
            end_price = etf_data.iloc[-1]['收盘']
            change_pct = (end_price - start_price) / start_price * 100
            results[f'change_{period}d'] = change_pct
            # 记录实际使用的天数
            results[f'actual_days_{period}d'] = actual_period
    
    return results

# 计算所有ETF的RS指标
def calculate_all_rs():
    """计算所有ETF的RS指标"""
    rs_data = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, (industry, etf_info) in enumerate(INDUSTRY_ETFS.items()):
        status_text.text(f"正在计算 {industry} ({etf_info['name']}) 的RS指标...")
        
        etf_code = etf_info['code']
        etf_data = get_etf_history(etf_code, days=180)  # 增加到180天，确保有足够数据
        
        if not etf_data.empty:
            rs_indicators = calculate_rs_indicators(etf_data)
            if rs_indicators:
                rs_data.append({
                    '行业': industry,
                    'ETF代码': etf_code,
                    'ETF名称': etf_info['name'],
                    '跟踪指数': etf_info['index'],
                    '20日涨跌幅': rs_indicators.get('change_20d', np.nan),
                    '40日涨跌幅': rs_indicators.get('change_40d', np.nan),
                    '60日涨跌幅': rs_indicators.get('change_60d', np.nan),
                    '20日实际天数': rs_indicators.get('actual_days_20d', np.nan),
                    '40日实际天数': rs_indicators.get('actual_days_40d', np.nan),
                    '60日实际天数': rs_indicators.get('actual_days_60d', np.nan)
                })
        
        progress_bar.progress((i + 1) / len(INDUSTRY_ETFS))
    
    progress_bar.empty()
    status_text.empty()
    
    if rs_data:
        df = pd.DataFrame(rs_data)
        
        # 获取沪深300的20日涨跌幅作为基准
        csi300_data = get_etf_history("510300", days=180)
        csi300_20d_change = 0
        csi300_40d_change = 0
        if not csi300_data.empty and len(csi300_data) >= 40:
            if len(csi300_data) >= 20:
                csi300_start_20d = csi300_data.iloc[-20]['收盘']
                csi300_end = csi300_data.iloc[-1]['收盘']
                csi300_20d_change = (csi300_end - csi300_start_20d) / csi300_start_20d * 100
            
            csi300_start_40d = csi300_data.iloc[-40]['收盘']
            csi300_end = csi300_data.iloc[-1]['收盘']
            csi300_40d_change = (csi300_end - csi300_start_40d) / csi300_start_40d * 100
        
        # 获取上证综指ETF的20日和40日涨跌幅作为基准
        shanghai_data = get_etf_history("510760", days=180)
        shanghai_20d_change = 0
        shanghai_40d_change = 0
        if not shanghai_data.empty and len(shanghai_data) >= 40:
            if len(shanghai_data) >= 20:
                shanghai_start_20d = shanghai_data.iloc[-20]['收盘']
                shanghai_end = shanghai_data.iloc[-1]['收盘']
                shanghai_20d_change = (shanghai_end - shanghai_start_20d) / shanghai_start_20d * 100
            
            shanghai_start_40d = shanghai_data.iloc[-40]['收盘']
            shanghai_end = shanghai_data.iloc[-1]['收盘']
            shanghai_40d_change = (shanghai_end - shanghai_start_40d) / shanghai_start_40d * 100
        
        # 添加沪深300基准列和超额收益列
        df['沪深300_20日涨跌幅'] = csi300_20d_change
        df['沪深300_40日涨跌幅'] = csi300_40d_change
        df['相对沪深300超额收益'] = df['20日涨跌幅'] - csi300_20d_change
        
        # 添加上证综指基准列
        df['上证综指_20日涨跌幅'] = shanghai_20d_change
        df['上证综指_40日涨跌幅'] = shanghai_40d_change
        
        # 计算排名和RS指标
        for period in [20, 40, 60]:
            col_name = f'{period}日涨跌幅'
            rank_col = f'{period}日排名'
            rs_col = f'RS_{period}'
            
            # 排名（1为最高）
            df[rank_col] = df[col_name].rank(ascending=False, method='min')
            
            # 归一化RS指标，范围改为[0,100]
            df[rs_col] = ((len(df) - df[rank_col]) / (len(df) - 1)) * 100
        
        # 计算综合RS指标
        df['综合RS'] = (df['RS_20'] + df['RS_40'] + df['RS_60']) / 3
        df['综合RS'] = df['综合RS'].round(2)
        
        # 按综合RS排序
        df = df.sort_values('综合RS', ascending=False).reset_index(drop=True)
        
        return df
    
    return pd.DataFrame()

# 生成行业RS走势图数据
def generate_rs_trend_data(selected_industry, days=60):
    """生成行业RS走势图数据 - 使用滚动综合RS指标"""
    if selected_industry not in INDUSTRY_ETFS:
        return None, None
    
    # 获取所有行业的历史数据
    all_industry_data = {}
    min_data_length = float('inf')
    
    # 先获取所有行业的数据，找到最短的数据长度
    for industry, etf_info in INDUSTRY_ETFS.items():
        etf_code = etf_info['code']
        etf_data = get_etf_history(etf_code, days=180) # 增加到180天，确保有足够数据计算60天滚动RS
        if not etf_data.empty:
            all_industry_data[industry] = etf_data
            min_data_length = min(min_data_length, len(etf_data))
    
    if not all_industry_data or min_data_length < 60:
        return None, None
    
    # 计算每日滚动综合RS指标
    trend_data = []
    
    # 从第60个交易日开始计算（确保有足够数据计算20日、40日、60日涨跌幅）
    for i in range(59, min_data_length):
        # 计算所有行业在这一天的涨跌幅
        daily_changes = {}
        
        for industry, etf_data in all_industry_data.items():
            if i < len(etf_data):
                changes = {}
                for period in [20, 40, 60]:
                    if i >= period - 1:
                        start_price = etf_data.iloc[i-period+1]['收盘']
                        end_price = etf_data.iloc[i]['收盘']
                        change_pct = (end_price - start_price) / start_price * 100
                        changes[f'change_{period}d'] = change_pct
                
                # 如果三个时间窗口都有数据，记录涨跌幅
                if len(changes) == 3:
                    daily_changes[industry] = changes
        
        # 如果所有行业都有数据，计算排名和RS指标
        if len(daily_changes) == len(INDUSTRY_ETFS):
            # 计算20日、40日、60日的排名和RS指标
            rs_data = {}
            for period in [20, 40, 60]:
                col_name = f'change_{period}d'
                # 获取所有行业的涨跌幅
                period_changes = [daily_changes[industry][col_name] for industry in daily_changes.keys()]
                # 计算排名（1为最高）
                rankings = pd.Series(period_changes).rank(ascending=False, method='min')
                
                # 计算每个行业的RS指标
                for j, industry in enumerate(daily_changes.keys()):
                    if industry not in rs_data:
                        rs_data[industry] = {}
                    rank = rankings.iloc[j]
                    # 归一化RS指标，范围改为[0,100]
                    rs_data[industry][f'RS_{period}'] = ((len(rankings) - rank) / (len(rankings) - 1)) * 100
            
            # 计算综合RS指标
            for industry in rs_data.keys():
                rs_20 = rs_data[industry].get('RS_20', 0)
                rs_40 = rs_data[industry].get('RS_40', 0)
                rs_60 = rs_data[industry].get('RS_60', 0)
                rs_data[industry]['综合RS'] = (rs_20 + rs_40 + rs_60) / 3
            
            # 获取选中行业的数据
            if selected_industry in rs_data:
                selected_rs = rs_data[selected_industry]
                selected_etf_data = all_industry_data[selected_industry]
                
                trend_data.append({
                    '日期': selected_etf_data.iloc[i]['日期'],
                    '收盘价': selected_etf_data.iloc[i]['收盘'],
                    'RS指标': selected_rs['综合RS'],  # 使用综合RS指标
                    'RS_20': selected_rs['RS_20'],
                    'RS_40': selected_rs['RS_40'],
                    'RS_60': selected_rs['RS_60'],
                    '20日涨跌幅': daily_changes[selected_industry]['change_20d'],
                    '40日涨跌幅': daily_changes[selected_industry]['change_40d'],
                    '60日涨跌幅': daily_changes[selected_industry]['change_60d']
                })
    
    if trend_data:
        trend_df = pd.DataFrame(trend_data)
        return all_industry_data[selected_industry], trend_df
    else:
        return None, None

# 计算年初至今涨跌幅
def calculate_ytd_return(etf_code):
    """计算ETF年初至今的涨跌幅"""
    try:
        # 获取当前年份
        current_year = datetime.now().year
        
        # 获取该ETF的历史数据，确保有足够数据
        etf_data = get_etf_history(etf_code, days=365)
        
        if not etf_data.empty:
            # 找到今年第一个交易日的数据
            current_year_data = etf_data[etf_data['日期'].dt.year == current_year]
            
            if not current_year_data.empty:
                # 获取今年第一个交易日的收盘价
                first_day_price = current_year_data.iloc[0]['收盘']
                
                # 获取最新交易日的收盘价
                latest_price = etf_data.iloc[-1]['收盘']
                
                # 计算年初至今的涨跌幅
                if first_day_price != 0:
                    ytd_change = (latest_price - first_day_price) / first_day_price * 100
                    return ytd_change
                else:
                    return np.nan
            else:
                return np.nan
        else:
            return np.nan
    except Exception as e:
        return np.nan

# 页面控制
st.subheader("�� 分析参数设置")

# 分析模式选择
analysis_mode = st.selectbox(
    "选择分析模式",
    options=["实时RS排名与热力图", "行业RS走势图"],
    index=0,
    help="选择要进行的分析类型"
)

# 如果是行业RS走势图模式，提前显示行业选择
if analysis_mode == "行业RS走势图":
    st.subheader("🏭 选择分析行业")
    selected_industry = st.selectbox(
        "选择要分析的行业",
        options=list(INDUSTRY_ETFS.keys()),
        index=0,
        help="选择要查看RS走势图的行业"
    )
    
    # 添加说明
    st.info("💡 **重要提示**：滚动RS指标计算需要获取所有行业的历史数据，系统获取180天数据以确保有足够数据计算60天的滚动RS指标。")

# 运行分析按钮
run_btn = st.button("🚀 运行行业ETF强弱分析")

if run_btn:
    if analysis_mode == "实时RS排名与热力图":
        st.subheader("📊 实时RS排名与热力图分析")
        
        # 数据获取日志折叠区域
        with st.expander("📋 数据获取进度（点击展开查看详情）", expanded=False):
            with st.spinner("正在计算所有行业ETF的RS指标..."):
                rs_df = calculate_all_rs()
        
        if not rs_df.empty:
            # 生成热力图
            st.subheader("🔥 行业RS热力图")
            
            # 创建热力图数据
            heatmap_data = rs_df[['行业', 'RS_20', 'RS_40', 'RS_60', '综合RS']].copy()
            
            # 创建热力图
            fig = go.Figure(data=go.Heatmap(
                z=heatmap_data[['RS_20', 'RS_40', 'RS_60', '综合RS']].values,
                x=['RS_20', 'RS_40', 'RS_60', '综合RS'],
                y=heatmap_data['行业'],
                colorscale='RdYlGn_r',  # 反向红绿配色，红色表示强，绿色表示弱
                zmid=50,  # 中间值设为50
                text=heatmap_data[['RS_20', 'RS_40', 'RS_60', '综合RS']].round(1).values,
                texttemplate="%{text}",
                textfont={"size": 10},
                hoverongaps=False
            ))
            
            fig.update_layout(
                title="行业ETF RS指标热力图",
                xaxis_title="RS指标类型",
                yaxis_title="行业",
                height=800,
                yaxis=dict(tickmode='array', tickvals=list(range(len(heatmap_data))), ticktext=heatmap_data['行业'])
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # 热力图说明
            st.markdown("""
            **🎨 热力图说明：**
            - **红色区域**：RS指标较高，表示行业相对强势
            - **绿色区域**：RS指标较低，表示行业相对弱势
            - **黄色区域**：RS指标中等，表示行业表现一般
            - **数值范围**：[0,100]，100为最强，0为最弱
            """)
            
            # 热力图统计
            st.subheader("📊 热力图统计")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                strong_count = len(rs_df[rs_df['综合RS'] >= 70])
                st.metric("强势行业数量", f"{strong_count}个")
            
            with col2:
                medium_count = len(rs_df[(rs_df['综合RS'] >= 30) & (rs_df['综合RS'] < 70)])
                st.metric("中等行业数量", f"{medium_count}个")
            
            with col3:
                weak_count = len(rs_df[rs_df['综合RS'] < 30])
                st.metric("弱势行业数量", f"{weak_count}个")
            
            # 综合RS横向柱状图
            st.subheader("📊 综合RS横向柱状图")
            
            # 创建横向柱状图
            fig_bar = go.Figure()
            
            # 添加柱状图
            fig_bar.add_trace(go.Bar(
                y=rs_df['行业'],
                x=rs_df['综合RS'],
                orientation='h',
                marker=dict(
                    color=rs_df['综合RS'],
                    colorscale='RdYlGn_r',
                    cmin=0,
                    cmax=100,
                    showscale=True,
                    colorbar=dict(title="RS值", x=1.1)
                ),
                text=rs_df['综合RS'].round(1),
                textposition='auto',
                hovertemplate='<b>%{y}</b><br>综合RS: %{x:.2f}<extra></extra>'
            ))
            
            # 添加参考线
            fig_bar.add_vline(x=90, line_dash="dash", line_color="red", 
                             annotation_text="强势预警线(90)", annotation_position="top right")
            fig_bar.add_vline(x=70, line_dash="dash", line_color="orange", 
                             annotation_text="强势分界线(70)", annotation_position="top right")
            fig_bar.add_vline(x=30, line_dash="dash", line_color="orange", 
                             annotation_text="弱势分界线(30)", annotation_position="top right")
            fig_bar.add_vline(x=10, line_dash="dash", line_color="red", 
                             annotation_text="弱势预警线(10)", annotation_position="top right")
            
            fig_bar.update_layout(
                title="行业ETF综合RS指标横向排名图",
                xaxis_title="综合RS指标",
                yaxis_title="行业",
                height=800,
                xaxis=dict(range=[0, 100]),
                showlegend=False
            )
            
            st.plotly_chart(fig_bar, use_container_width=True)
            
            # 柱状图说明
            st.markdown("""
            **📊 柱状图说明：**
            - **红色虚线(90)**：强势预警线，RS≥90表示行业极强势
            - **橙色虚线(70)**：强势分界线，RS≥70表示行业强势
            - **橙色虚线(30)**：弱势分界线，RS≤30表示行业弱势  
            - **红色虚线(10)**：弱势预警线，RS≤10表示行业极弱势
            - **颜色渐变**：红色表示强，绿色表示弱
            """)
            
            # 20日收益横向柱状图
            st.subheader("📈 20日收益横向柱状图")
            
            # 按20日涨跌幅排序，方便查看
            rs_df_sorted = rs_df.sort_values('20日涨跌幅', ascending=False)
            
            # 创建20日收益横向柱状图
            fig_returns = go.Figure()
            
            # 添加柱状图
            fig_returns.add_trace(go.Bar(
                y=rs_df_sorted['行业'],
                x=rs_df_sorted['20日涨跌幅'],
                orientation='h',
                marker=dict(
                    color=rs_df_sorted['20日涨跌幅'],
                    colorscale='RdYlGn_r',  # 反向红绿配色，红色表示涨，绿色表示跌
                    cmin=rs_df_sorted['20日涨跌幅'].min(),
                    cmax=rs_df_sorted['20日涨跌幅'].max(),
                    showscale=True,
                    colorbar=dict(title="涨跌幅(%)", x=1.1)
                ),
                text=rs_df_sorted['20日涨跌幅'].round(2),
                textposition='auto',
                hovertemplate='<b>%{y}</b><br>20日涨跌幅: %{x:.2f}%<extra></extra>'
            ))
            
            # 添加沪深300基准参考线
            csi300_20d = rs_df['沪深300_20日涨跌幅'].iloc[0] if not rs_df.empty else 0
            fig_returns.add_vline(
                x=csi300_20d, 
                line_dash="dash", 
                line_color="blue", 
                line_width=3,
                annotation_text=f"沪深300基准({csi300_20d:.2f}%)", 
                annotation_position="top right"
            )
            
            # 添加上证综指ETF基准参考线
            shanghai_20d = rs_df['上证综指_20日涨跌幅'].iloc[0] if not rs_df.empty else 0
            fig_returns.add_vline(
                x=shanghai_20d, 
                line_dash="dash", 
                line_color="purple", 
                line_width=3,
                annotation_text=f"上证综指基准({shanghai_20d:.2f}%)", 
                annotation_position="top left"
            )
            
            # 添加零线参考
            fig_returns.add_vline(
                x=0, 
                line_dash="dot", 
                line_color="gray", 
                line_width=2,
                annotation_text="零线", 
                annotation_position="bottom right"
            )
            
            fig_returns.update_layout(
                title="行业ETF 20日收益横向对比图",
                xaxis_title="20日涨跌幅 (%)",
                yaxis_title="行业",
                height=800,
                showlegend=False
            )
            
            st.plotly_chart(fig_returns, use_container_width=True)
            
            # 20日收益柱状图说明
            st.markdown("""
            **📈 20日收益柱状图说明：**
            - **蓝色虚线**：沪深300基准线，表示市场整体表现
            - **紫色虚线**：上证综指基准线，表示上海市场整体表现
            - **灰色点线**：零线，区分正负收益
            - **颜色渐变**：红色表示正收益，绿色表示负收益
            - **柱长对比**：柱长越长表示收益越高（正收益）或亏损越大（负收益）
            """)
            
            # 40日收益横向柱状图
            st.subheader("📈 40日收益横向柱状图")
            
            # 按40日涨跌幅排序，方便查看
            rs_df_sorted_40d = rs_df.sort_values('40日涨跌幅', ascending=False)
            
            # 创建40日收益横向柱状图
            fig_returns_40d = go.Figure()
            
            # 添加柱状图
            fig_returns_40d.add_trace(go.Bar(
                y=rs_df_sorted_40d['行业'],
                x=rs_df_sorted_40d['40日涨跌幅'],
                orientation='h',
                marker=dict(
                    color=rs_df_sorted_40d['40日涨跌幅'],
                    colorscale='RdYlGn_r',  # 反向红绿配色，红色表示涨，绿色表示跌
                    cmin=rs_df_sorted_40d['40日涨跌幅'].min(),
                    cmax=rs_df_sorted_40d['40日涨跌幅'].max(),
                    showscale=True,
                    colorbar=dict(title="涨跌幅(%)", x=1.1)
                ),
                text=rs_df_sorted_40d['40日涨跌幅'].round(2),
                textposition='auto',
                hovertemplate='<b>%{y}</b><br>40日涨跌幅: %{x:.2f}%<extra></extra>'
            ))
            
            # 添加沪深300基准参考线（40日）
            csi300_40d = rs_df['沪深300_40日涨跌幅'].iloc[0] if '沪深300_40日涨跌幅' in rs_df.columns else 0
            fig_returns_40d.add_vline(
                x=csi300_40d, 
                line_dash="dash", 
                line_color="blue", 
                line_width=3,
                annotation_text=f"沪深300基准({csi300_40d:.2f}%)", 
                annotation_position="top right"
            )
            
            # 添加上证综指ETF基准参考线（40日）
            shanghai_40d = rs_df['上证综指_40日涨跌幅'].iloc[0] if '上证综指_40日涨跌幅' in rs_df.columns else 0
            fig_returns_40d.add_vline(
                x=shanghai_40d, 
                line_dash="dash", 
                line_color="purple", 
                line_width=3,
                annotation_text=f"上证综指基准({shanghai_40d:.2f}%)", 
                annotation_position="top left"
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
                title="行业ETF 40日收益横向对比图",
                xaxis_title="40日涨跌幅 (%)",
                yaxis_title="行业",
                height=800,
                showlegend=False
            )
            
            st.plotly_chart(fig_returns_40d, use_container_width=True)
            
            # 40日收益柱状图说明
            st.markdown("""
            **📈 40日收益柱状图说明：**
            - **蓝色虚线**：沪深300基准线，表示市场整体表现
            - **紫色虚线**：上证综指基准线，表示上海市场整体表现
            - **灰色点线**：零线，区分正负收益
            - **颜色渐变**：红色表示正收益，绿色表示负收益
            - **柱长对比**：柱长越长表示收益越高（正收益）或亏损越大（负收益）
            - **时间窗口**：40日收益反映中期市场表现，相比20日收益波动更平滑
            """)
            
            # 年初至今收益横向柱状图
            st.subheader("📈 年初至今收益横向柱状图")
            
            # 计算年初至今涨跌幅
            rs_df['年初至今涨跌幅'] = rs_df.apply(lambda row: 
                calculate_ytd_return(row['ETF代码']), axis=1)
            
            # 按年初至今涨跌幅排序，方便查看
            rs_df_sorted_ytd = rs_df.sort_values('年初至今涨跌幅', ascending=False)
            
            # 创建年初至今收益横向柱状图
            fig_returns_ytd = go.Figure()
            
            # 添加柱状图
            fig_returns_ytd.add_trace(go.Bar(
                y=rs_df_sorted_ytd['行业'],
                x=rs_df_sorted_ytd['年初至今涨跌幅'],
                orientation='h',
                marker=dict(
                    color=rs_df_sorted_ytd['年初至今涨跌幅'],
                    colorscale='RdYlGn_r',  # 反向红绿配色，红色表示涨，绿色表示跌
                    cmin=rs_df_sorted_ytd['年初至今涨跌幅'].min(),
                    cmax=rs_df_sorted_ytd['年初至今涨跌幅'].max(),
                    showscale=True,
                    colorbar=dict(title="涨跌幅(%)", x=1.1)
                ),
                text=rs_df_sorted_ytd['年初至今涨跌幅'].round(2),
                textposition='auto',
                hovertemplate='<b>%{y}</b><br>年初至今涨跌幅: %{x:.2f}%<extra></extra>'
            ))
            
            # 添加沪深300基准参考线（年初至今）
            csi300_ytd = calculate_ytd_return("510300")
            fig_returns_ytd.add_vline(
                x=csi300_ytd, 
                line_dash="dash", 
                line_color="blue", 
                line_width=3,
                annotation_text=f"沪深300基准({csi300_ytd:.2f}%)", 
                annotation_position="top right"
            )
            
            # 添加上证综指ETF基准参考线（年初至今）
            shanghai_ytd = calculate_ytd_return("510760")
            fig_returns_ytd.add_vline(
                x=shanghai_ytd, 
                line_dash="dash", 
                line_color="purple", 
                line_width=3,
                annotation_text=f"上证综指基准({shanghai_ytd:.2f}%)", 
                annotation_position="top left"
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
                title="行业ETF 年初至今收益横向对比图",
                xaxis_title="年初至今涨跌幅 (%)",
                yaxis_title="行业",
                height=800,
                showlegend=False
            )
            
            st.plotly_chart(fig_returns_ytd, use_container_width=True)
            
            # 年初至今收益柱状图说明
            st.markdown("""
            **📈 年初至今收益柱状图说明：**
            - **蓝色虚线**：沪深300基准线，表示市场整体表现
            - **紫色虚线**：上证综指基准线，表示上海市场整体表现
            - **灰色点线**：零线，区分正负收益
            - **颜色渐变**：红色表示正收益，绿色表示负收益
            - **柱长对比**：柱长越长表示收益越高（正收益）或亏损越大（负收益）
            - **时间窗口**：年初至今收益反映全年市场表现，适合年度投资策略评估
            """)
            
            # 显示RS排名表格
            st.subheader("📋 RS指标排名表")
            
            # 格式化表格显示
            def color_rs(val):
                """根据RS值设置颜色"""
                if pd.isna(val):
                    return ''
                if val >= 80:
                    return 'background-color: #d4edda; color: #155724'  # 绿色背景（强）
                elif val <= 20:
                    return 'background-color: #f8d7da; color: #721c24'  # 红色背景（弱）
                else:
                    return ''
            
            def color_excess_return(val):
                """根据超额收益值设置颜色"""
                if pd.isna(val):
                    return ''
                if val > 0:
                    return 'background-color: #d4edda; color: #155724'  # 绿色背景（正收益）
                elif val < 0:
                    return 'background-color: #f8d7da; color: #721c24'  # 红色背景（负收益）
                else:
                    return ''
            
            # 应用样式
            styled_df = rs_df.style.apply(
                lambda x: [color_rs(val) if col == '综合RS' else '' for col, val in x.items()], 
                subset=['综合RS']
            ).apply(
                lambda x: [color_excess_return(val) if col == '相对沪深300超额收益' else '' for col, val in x.items()],
                subset=['相对沪深300超额收益']
            ).format({
                '20日涨跌幅': '{:.2f}%',
                '40日涨跌幅': '{:.2f}%',
                '60日涨跌幅': '{:.2f}%',
                '年初至今涨跌幅': '{:.2f}%',
                '沪深300_20日涨跌幅': '{:.2f}%',
                '沪深300_40日涨跌幅': '{:.2f}%',
                '上证综指_20日涨跌幅': '{:.2f}%',
                '上证综指_40日涨跌幅': '{:.2f}%',
                '相对沪深300超额收益': '{:.2f}%',
                '20日实际天数': '{:.0f}',
                '40日实际天数': '{:.0f}',
                '60日实际天数': '{:.0f}',
                'RS_20': '{:.2f}',
                'RS_40': '{:.2f}',
                'RS_60': '{:.2f}',
                '综合RS': '{:.2f}'
            })
            
            st.dataframe(styled_df, use_container_width=True)
            
            # 预警系统
            st.subheader("🚨 预警系统")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # RS突破90预警
                strong_etfs = rs_df[rs_df['综合RS'] >= 90]
                if not strong_etfs.empty:
                    st.warning(f"🔥 **RS突破90预警**：{len(strong_etfs)}个行业ETF")
                    for _, row in strong_etfs.iterrows():
                        st.write(f"• {row['行业']} ({row['ETF名称']} {row['ETF代码']}): RS={row['综合RS']:.2f}")
                else:
                    st.info("✅ 暂无RS突破90的行业ETF")
            
            with col2:
                # RS跌破10预警
                weak_etfs = rs_df[rs_df['综合RS'] <= 10]
                if not weak_etfs.empty:
                    st.error(f"📉 **RS跌破10预警**：{len(weak_etfs)}个行业ETF")
                    for _, row in weak_etfs.iterrows():
                        st.write(f"• {row['行业']} ({row['ETF名称']} {row['ETF代码']}): RS={row['综合RS']:.2f}")
                else:
                    st.info("✅ 暂无RS跌破10的行业ETF")
            
            # 投资建议（折叠显示）
            with st.expander("💡 投资建议（点击展开查看）", expanded=False):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**🏆 强势行业（RS ≥ 70）：**")
                    strong_industries = rs_df[rs_df['综合RS'] >= 70]
                    if not strong_industries.empty:
                        for _, row in strong_industries.iterrows():
                            st.write(f"• **{row['行业']}** ({row['ETF名称']} {row['ETF代码']})")
                            st.write(f"  - RS: {row['综合RS']:.4f}")
                            st.write(f"  - 20日: {row['20日涨跌幅']:.2f}%")
                            st.write(f"  - 跟踪指数: {row['跟踪指数']}")
                            st.write("---")
                
                with col2:
                    st.markdown("**📉 弱势行业（RS ≤ 30）：**")
                    weak_industries = rs_df[rs_df['综合RS'] <= 30]
                    if not weak_industries.empty:
                        for _, row in weak_industries.iterrows():
                            st.write(f"• **{row['行业']}** ({row['ETF名称']} {row['ETF代码']})")
                            st.write(f"  - RS: {row['综合RS']:.4f}")
                            st.write(f"  - 20日: {row['20日涨跌幅']:.2f}%")
                            st.write(f"  - 跟踪指数: {row['跟踪指数']}")
                            st.write("---")
            
            # 下载功能
            st.subheader("💾 下载分析结果")
            
            col1, col2 = st.columns(2)
            
            with col1:
                csv = rs_df.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="📥 下载CSV报告",
                    data=csv,
                    file_name=f"行业ETF_RS排名_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
            
            with col2:
                try:
                    import io
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        rs_df.to_excel(writer, sheet_name='RS排名结果', index=False)
                    excel_data = output.getvalue()
                    st.download_button(
                        label="📥 下载Excel报告",
                        data=excel_data,
                        file_name=f"行业ETF_RS排名_{datetime.now().strftime('%Y%m%d')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                except ImportError:
                    st.info("💡 安装 openpyxl 可下载Excel格式报告")

    elif analysis_mode == "行业RS走势图":
        st.subheader("📈 行业RS走势图分析")
        
        # 使用之前选择的行业
        if analysis_mode == "行业RS走势图" and 'selected_industry' in locals():
            with st.spinner(f"正在生成{selected_industry}的RS走势图..."):
                etf_data, trend_data = generate_rs_trend_data(selected_industry, days=60) # 固定为60天
            
            if etf_data is not None and trend_data is not None and not trend_data.empty:
                # 只取最近60天的ETF数据，与RS趋势数据保持一致
                etf_data_60d = etf_data.tail(60).reset_index(drop=True)
                
                # 数据信息折叠区域
                with st.expander("📋 数据获取详情（点击展开）", expanded=False):
                    st.info(f"正在分析行业：{selected_industry} (ETF代码: {INDUSTRY_ETFS[selected_industry]['code']})")
                    st.success(f"获取到{selected_industry}数据：{len(etf_data)}条记录")
                    st.info(f"分析数据范围：最近60天（{etf_data_60d['日期'].min().strftime('%Y-%m-%d')} 到 {etf_data_60d['日期'].max().strftime('%Y-%m-%d')}）")
                    st.success(f"成功生成{len(trend_data)}个数据点的RS趋势数据")
                
                # 验证数据完整性
                if len(trend_data) < 5:
                    st.warning(f"⚠️ 警告：{selected_industry}的RS趋势数据点较少（{len(trend_data)}个），可能影响分析准确性")
                
                # 创建双坐标图
                fig = make_subplots(
                    rows=2, cols=1,
                    shared_xaxes=True,
                    vertical_spacing=0.1,
                    subplot_titles=(f'{selected_industry}指数走势（最近60天）', f'{selected_industry}滚动综合RS指标走势（最近60天）'),
                    row_heights=[0.7, 0.3]
                )
                
                # 上方：行业指数走势（最近60天）
                fig.add_trace(
                    go.Scatter(
                        x=etf_data_60d['日期'],
                        y=etf_data_60d['收盘'],
                        mode='lines',
                        name=f'{selected_industry}指数',
                        line=dict(color='#1f77b4', width=2),
                        hovertemplate='<b>%{x}</b><br>收盘价: %{y:.2f}<extra></extra>'
                    ),
                    row=1, col=1
                )
                
                # 下方：滚动综合RS指标走势
                fig.add_trace(
                    go.Scatter(
                        x=trend_data['日期'],
                        y=trend_data['RS指标'],
                        mode='lines',
                        name='滚动综合RS指标',
                        line=dict(color='#d62728', width=2),
                        hovertemplate='<b>%{x}</b><br>综合RS指标: %{y:.2f}<extra></extra>'
                    ),
                    row=2, col=1
                )
                
                # 添加参考线
                for y_val, color, name in [(90, '#2ca02c', 'RS=90'), (70, '#ff7f0e', 'RS=70'), (30, '#d62728', 'RS=30'), (10, '#1f77b4', 'RS=10')]:
                    fig.add_hline(
                        y=y_val, 
                        line_dash="dash", 
                        line_color=color, 
                        opacity=0.5,
                        annotation_text=name,
                        row=2, col=1
                    )
                
                fig.update_layout(
                    title=f'{selected_industry}行业ETF走势与滚动综合RS指标分析',
                    height=600,
                    showlegend=True
                )
                
                fig.update_xaxes(title_text="日期", row=2, col=1)
                fig.update_yaxes(title_text="指数价格", row=1, col=1)
                fig.update_yaxes(title_text="滚动综合RS指标", row=2, col=1)
                
                # 设置RS指标图的y轴范围
                fig.update_yaxes(range=[0, 100], row=2, col=1)
                
                # 设置x轴日期格式为中文
                fig.update_xaxes(
                    tickformat="%m月%d日",
                    tickmode='auto',
                    nticks=10,
                    row=1, col=1
                )
                fig.update_xaxes(
                    tickformat="%m月%d日", 
                    tickmode='auto',
                    nticks=10,
                    row=2, col=1
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # 显示统计信息
                st.subheader("📊 滚动综合RS指标统计")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    current_rs = trend_data['RS指标'].iloc[-1] if not trend_data.empty else np.nan
                    st.metric(
                        "当前综合RS指标",
                        f"{current_rs:.2f}" if not pd.isna(current_rs) else "N/A",
                        delta_color="normal" if current_rs >= 0 else "inverse"
                    )
                
                with col2:
                    rs_volatility = trend_data['RS指标'].std() if not trend_data.empty else np.nan
                    st.metric(
                        "综合RS波动率",
                        f"{rs_volatility:.2f}" if not pd.isna(rs_volatility) else "N/A"
                    )
                
                with col3:
                    rs_trend = "上升" if len(trend_data) >= 2 and trend_data['RS指标'].iloc[-1] > trend_data['RS指标'].iloc[-2] else "下降"
                    st.metric(
                        "综合RS趋势",
                        rs_trend,
                        delta_color="normal" if rs_trend == "上升" else "inverse"
                    )
                
                # 显示数据质量信息
                st.subheader("📋 数据质量信息")
                col1, col2 = st.columns(2)
                
                with col1:
                    st.metric("总数据点数", len(etf_data))
                    st.metric("综合RS趋势数据点", len(trend_data))
                
                with col2:
                    # 计算综合RS指标的范围
                    if not trend_data.empty:
                        rs_min = trend_data['RS指标'].min()
                        rs_max = trend_data['RS指标'].max()
                        st.metric("综合RS最小值", f"{rs_min:.2f}%")
                        st.metric("综合RS最大值", f"{rs_max:.2f}%")
            else:
                st.error(f"无法生成{selected_industry}的RS走势图，请检查数据")
                if etf_data is not None:
                    st.info(f"ETF数据状态：{len(etf_data)}条记录")
                if trend_data is not None:
                    st.info(f"趋势数据状态：{len(trend_data) if hasattr(trend_data, '__len__') else 'N/A'}条记录")
        else:
            st.error("请先选择要分析的行业")
    
else:
    if analysis_mode == "行业RS走势图":
        st.info("👆 请选择要分析的行业，然后点击运行按钮生成RS走势图")
    else:
        st.info("👆 请选择分析模式并点击运行按钮开始分析")

# 页面底部说明
st.markdown("---")
st.markdown("""
**💡 使用说明：**
1. **实时RS排名与热力图**：查看所有行业ETF的当前RS排名和预警信息，并直观对比各行业在不同时间窗口的RS表现
2. **行业RS走势图**：分析特定行业的RS指标历史走势

**🔍 RS指标解读：**
- **RS ≥ 80**：行业处于强势，可考虑配置
- **30 ≤ RS < 80**：行业表现中等，可观察
- **RS < 30**：行业处于弱势，谨慎配置

**⚠️ 风险提示：**
- RS指标仅供参考，不构成投资建议
- 投资有风险，入市需谨慎
- 建议结合基本面分析和其他技术指标
""")
