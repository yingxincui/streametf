import json
import streamlit as st
import pandas as pd

FRONTIER_PORTFOLIOS_FILE = 'frontier_portfolios.json'

@st.cache_data
def load_frontier_portfolios():
    try:
        with open(FRONTIER_PORTFOLIOS_FILE, 'r', encoding='utf-8-sig') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_frontier_portfolios(portfolios):
    try:
        with open(FRONTIER_PORTFOLIOS_FILE, 'w', encoding='utf-8') as f:
            json.dump(portfolios, f, indent=4, ensure_ascii=False)
    except Exception as e:
        st.error(f"保存前沿组合失败: {e}")

def add_frontier_portfolio(name, etfs, weights, date_range, risk_free_rate, num_portfolios):
    portfolios = load_frontier_portfolios()
    portfolios[name] = {
        'etfs': etfs,
        'weights': weights,
        'date_range': date_range,
        'risk_free_rate': risk_free_rate,
        'num_portfolios': num_portfolios,
        'saved_at': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    save_frontier_portfolios(portfolios)
    st.cache_data.clear()

def delete_frontier_portfolio(name):
    portfolios = load_frontier_portfolios()
    if name in portfolios:
        del portfolios[name]
        save_frontier_portfolios(portfolios)
        st.cache_data.clear() 