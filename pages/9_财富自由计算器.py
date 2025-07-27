import streamlit as st
import os, json
import pandas as pd
import numpy as np
import io
import datetime
from pdf_export import get_pdf_download_link
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.units import cm, inch
import matplotlib.pyplot as plt
import io as _io

st.title("财富自由计算器（4%法则版）")

st.markdown("""
本工具帮助你科学测算实现财富自由所需的目标资产和预计达成时间，采用4%法则（即目标资产=年支出/4%），并考虑当前年龄、年收入、储蓄率、现有储蓄和预期投资收益率。
""")

PARAM_KEYS = ['current_age', 'current_income', 'current_assets', 'saving_rate', 'annual_return', 'target_year_expense']
SAVED_FILE = os.path.join("config", "wealth_freedom_saved.json")

def load_saved():
    if not os.path.exists(SAVED_FILE):
        return {}
    try:
        with open(SAVED_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_saved(saved):
    with open(SAVED_FILE, "w", encoding="utf-8") as f:
        json.dump(saved, f, ensure_ascii=False, indent=2)

# 每次都重新加载方案列表
saved = load_saved()
saved_names = list(saved.keys())

# 默认参数
default_params = dict(zip(PARAM_KEYS, [30, 20.0, 20.0, 30.0, 8.0, 24.0]))

# 方案选择
col_plan, col_del = st.columns([3,1])
with col_plan:
    selected_plan = st.selectbox(
        "选择方案", ["未选择"] + saved_names,
        index=0
    )
with col_del:
    if selected_plan != "未选择" and st.button("删除当前方案"):
        del saved[selected_plan]
        save_saved(saved)
        st.rerun()

# 当前参数来源：选中方案 > session_state > 默认
if selected_plan != "未选择":
    params = saved[selected_plan]
else:
    params = {}
for k in PARAM_KEYS:
    if k not in params:
        params[k] = st.session_state.get(k, default_params[k])

# 参数输入区
col1, col2 = st.columns(2)
with col1:
    current_age = st.number_input("当前年龄", min_value=10, max_value=100, value=params['current_age'], step=1, key='current_age')
    current_income = st.number_input("当前年收入（万元）", min_value=0.0, max_value=10000.0, value=params['current_income'], step=0.1, key='current_income')
    current_assets = st.number_input("当前储蓄总额（万元）", min_value=0.0, max_value=10000.0, value=params['current_assets'], step=0.1, key='current_assets')
with col2:
    saving_rate = st.number_input("年储蓄率（%）", min_value=0.0, max_value=100.0, value=params['saving_rate'], step=0.1, key='saving_rate')
    annual_return = st.number_input("预期投资收益率（%）", min_value=1.0, max_value=20.0, value=params['annual_return'], step=0.1, key='annual_return')
    target_year_expense = st.number_input("预期财富自由年支出（万元）", min_value=1.2, max_value=1000.0, value=params['target_year_expense'], step=0.1, key='target_year_expense')

# 保存为新方案
with st.form("save_plan_form"):
    new_plan_name = st.text_input("保存为新方案名称", value="")
    submitted = st.form_submit_button("保存为方案")
    if submitted:
        name = new_plan_name.strip()
        if not name:
            st.warning("请输入方案名称")
        elif name in saved:
            st.warning("该名称已存在，请更换")
        else:
            saved[name] = {k: st.session_state[k] for k in PARAM_KEYS}
            save_saved(saved)
            st.success(f"方案“{name}”已保存！")
            st.rerun()

run_btn = st.button("开始测算")

if run_btn:
    # 1. 计算目标资产
    safe_withdraw_rate = 0.04
    target_assets = st.session_state['target_year_expense'] / safe_withdraw_rate
    annual_invest = st.session_state['current_income'] * st.session_state['saving_rate'] / 100
    # 2. 计算达成所需年数（定投+复利，数值法）
    r = st.session_state['annual_return'] / 100
    PMT = annual_invest
    P0 = st.session_state['current_assets']
    n = 1
    max_years = 100
    found = False
    asset_curve = []
    while n <= max_years:
        fv = P0 * (1 + r) ** n + PMT * ((1 + r) ** n - 1) / r
        asset_curve.append(fv)
        if fv >= target_assets:
            found = True
            break
        n += 1
    # 3. 用醒目的指标卡展示结果
    st.markdown("---")
    st.markdown("<h3 style='text-align:center;'>🎯 财富自由测算结果</h3>", unsafe_allow_html=True)
    # 第一行指标卡
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            label="💰 目标资产",
            value=f"{target_assets:,.0f} 万元",
            delta=f"年支出 {st.session_state['target_year_expense']:,.1f} 万元 / 4%"
        )
    with col2:
        st.metric(
            label="💸 年投资金额",
            value=f"{annual_invest:,.1f} 万元",
            delta=f"储蓄率 {st.session_state['saving_rate']}%"
        )
    with col3:
        if found:
            st.metric(
                label="⏰ 达成时间",
                value=f"{n} 年",
                delta=f"达成年龄 {st.session_state['current_age'] + n} 岁"
            )
        else:
            st.metric(
                label="⏰ 达成时间",
                value="无法达成",
                delta="100年内无法达成目标"
            )
    # 第二行指标卡（如果达成）
    if found:
        col4, col5, col6 = st.columns(3)
        with col4:
            st.metric(
                label="📈 年化收益率",
                value=f"{st.session_state['annual_return']}%",
                delta="预期投资回报"
            )
        with col5:
            st.metric(
                label="🏦 当前资产",
                value=f"{st.session_state['current_assets']:,.1f} 万元",
                delta="现有储蓄"
            )
        with col6:
            st.metric(
                label="🎯 目标年支出",
                value=f"{st.session_state['target_year_expense']:,.1f} 万元",
                delta="财富自由后年支出"
            )
    st.markdown("---")
    # 4. 详细过程表格
    this_year = datetime.datetime.now().year
    years = []
    ages = []
    start_assets = []
    savings = []
    invest_returns = []
    end_assets = []
    prev = P0
    for i in range(n):
        year = this_year + i
        age = st.session_state['current_age'] + i + 1
        save = PMT
        invest_ret = prev * r
        end_asset = prev * (1 + r) + save
        years.append(year)
        ages.append(age)
        start_assets.append(prev)
        savings.append(save)
        invest_returns.append(invest_ret)
        end_assets.append(end_asset)
        prev = end_asset
    df_detail = pd.DataFrame({
        "年份": years,
        "年龄": ages,
        "初始资产(万元)": start_assets,
        "当年储蓄(万元)": savings,
        "投资收益(万元)": invest_returns,
        "年末资产(万元)": end_assets
    })
    st.subheader("详细过程表格")
    st.dataframe(df_detail.style.format({
        "初始资产(万元)": "{:.2f}",
        "当年储蓄(万元)": "{:.2f}",
        "投资收益(万元)": "{:.2f}",
        "年末资产(万元)": "{:.2f}"
    }), use_container_width=True)
    # 5. 资产增长曲线
    st.subheader("资产增长曲线")
    df_curve = pd.DataFrame({"年龄": ages, "资产(万元)": end_assets})
    import plotly.express as px
    fig = px.area(df_curve, x="年龄", y="资产(万元)", title="财富自由达成过程", 
                   color_discrete_sequence=['#1f77b4'])
    fig.add_hline(y=target_assets, line_dash="dash", line_color="red", annotation_text="目标资产", annotation_position="top left")
    st.plotly_chart(fig, use_container_width=True)
    # 6. 下载分析结果
    st.subheader("下载分析结果")
    output = io.StringIO()
    df_detail.to_csv(output, index=False)
    st.download_button("下载详细过程表格（CSV）", data=output.getvalue(), file_name="wealth_freedom_detail.csv", mime="text/csv")
    # 6. 结果说明与加速建议
    st.caption("本计算器采用4%法则，假设投资收益率恒定、无税费、无通胀影响，仅供参考。实际投资需结合个人风险偏好和市场情况。\n\n"
        "**如何加速实现财富自由？**\n"
        "- 提高储蓄率：每年多存一点，复利效应显著加快积累速度。\n"
        "- 增加收入：主动提升职业技能、拓展副业，增加可投资本金。\n"
        "- 提升投资回报：学习资产配置、长期持有优质资产，争取更高年化收益。\n"
        "- 降低目标支出：适当调整生活方式，降低财富自由所需目标资产。\n"
        "- 保持耐心和纪律：长期坚持定投，避免频繁操作和情绪化决策。\n"
    ) 

batch_btn = st.button("批量测算（收益率7%~20%）")

if batch_btn:
    results = []
    for rate in range(7, 21):
        safe_withdraw_rate = 0.04
        target_assets = st.session_state['target_year_expense'] / safe_withdraw_rate
        annual_invest = st.session_state['current_income'] * st.session_state['saving_rate'] / 100
        r = rate / 100
        PMT = annual_invest
        P0 = st.session_state['current_assets']
        n = 1
        max_years = 100
        found = False
        while n <= max_years:
            fv = P0 * (1 + r) ** n + PMT * ((1 + r) ** n - 1) / r
            if fv >= target_assets:
                found = True
                break
            n += 1
        results.append({
            "收益率%": rate,
            "达成年数": n if found else None,
            "达成年龄": st.session_state['current_age'] + n if found else None,
            "能否达成": "可达成" if found else "无法达成",
            "目标资产(万元)": target_assets
        })
    df = pd.DataFrame(results)
    st.subheader("批量测算结果（不同收益率下达成情况）")
    st.dataframe(df, use_container_width=True)
    # 增加折线图
    df_valid = df[df['能否达成'] == '可达成']
    if not df_valid.empty:
        import plotly.express as px
        fig = px.line(df_valid, x="收益率%", y="达成年数", markers=True, title="不同收益率下达成年数变化")
        fig.update_traces(mode="lines+markers")
        st.plotly_chart(fig, use_container_width=True) 
    # 增加指标卡
    if not df_valid.empty:
        min_year = df_valid['达成年数'].min()
        max_year = df_valid['达成年数'].max()
        min_rate = df_valid['收益率%'].min()
        max_rate = df_valid['收益率%'].max()
        fail_df = df[df['能否达成'] == '无法达成']
        fail_min_rate = fail_df['收益率%'].min() if not fail_df.empty else None
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("最快达成年数", f"{min_year} 年", delta=f"收益率 {max_rate}%")
        with col2:
            st.metric("最慢达成年数", f"{max_year} 年", delta=f"收益率 {min_rate}%")
        with col3:
            st.metric("可达成收益率区间", f"{min_rate}% ~ {max_rate}%")
        with col4:
            st.metric("无法达成的最低收益率", f"{fail_min_rate if fail_min_rate is not None else '-'}%")
        # 增加PDF导出按钮
        pdf_params = {
            "当前年龄": st.session_state['current_age'],
            "当前年收入（万元）": st.session_state['current_income'],
            "当前储蓄总额（万元）": st.session_state['current_assets'],
            "年储蓄率（%）": st.session_state['saving_rate'],
            "预期投资收益率（%）": st.session_state['annual_return'],
            "预期财富自由年支出（万元）": st.session_state['target_year_expense']
        }
        if st.button("下载批量测算PDF报告"):
            pdf_buffer = create_wealth_freedom_pdf(pdf_params, df, df_valid, min_year, max_year, min_rate, max_rate, fail_min_rate, fig)
            st.markdown(get_pdf_download_link(pdf_buffer, filename="wealth_freedom_batch_report.pdf"), unsafe_allow_html=True) 