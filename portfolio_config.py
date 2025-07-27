import json
import streamlit as st

PORTFOLIOS_FILE = 'portfolios.json'

@st.cache_data
def load_portfolios():
    try:
        with open(PORTFOLIOS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_portfolios(portfolios):
    try:
        with open(PORTFOLIOS_FILE, 'w', encoding='utf-8') as f:
            json.dump(portfolios, f, indent=4, ensure_ascii=False)
    except Exception as e:
        st.error(f"保存组合失败: {e}")

def add_portfolio(name, etfs, weights):
    portfolios = load_portfolios()
    portfolios[name] = {'etfs': etfs, 'weights': weights}
    save_portfolios(portfolios)
    st.cache_data.clear()

def delete_portfolio(name):
    portfolios = load_portfolios()
    if name in portfolios:
        del portfolios[name]
        save_portfolios(portfolios)
        st.cache_data.clear() 