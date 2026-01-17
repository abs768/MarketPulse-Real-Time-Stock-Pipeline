import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px

st.set_page_config(page_title="Stock Market Analytics", layout="wide", initial_sidebar_state="expanded")

@st.cache_data
def load_data():
    df = pd.read_csv('C:/Users/bhavani/real-time-stocks-mds/visualization/stock_data.csv')
    df['CANDLE_TIME'] = pd.to_datetime(df['CANDLE_TIME'])
    df = df.sort_values(['SYMBOL', 'CANDLE_TIME'])
    
    for symbol in df['SYMBOL'].unique():
        mask = df['SYMBOL'] == symbol
        df.loc[mask, 'daily_return'] = df.loc[mask, 'CANDLE_CLOSE'].pct_change() * 100
        df.loc[mask, 'cumulative_return'] = (df.loc[mask, 'CANDLE_CLOSE'] / df.loc[mask, 'CANDLE_CLOSE'].iloc[0] - 1) * 100
        df.loc[mask, 'volatility_rolling'] = df.loc[mask, 'daily_return'].rolling(window=20).std()
    
    return df

df = load_data()
symbols = sorted(df['SYMBOL'].unique())

# Sidebar
st.sidebar.markdown("## Filters & Options")

st.sidebar.markdown("### Select Stock")
selected_stock = st.sidebar.selectbox("", symbols, label_visibility="collapsed")

st.sidebar.markdown("### Date Range")
min_date = df['CANDLE_TIME'].min().date()
max_date = df['CANDLE_TIME'].max().date()
date_range = st.sidebar.date_input("", [min_date, max_date], min_value=min_date, max_value=max_date, label_visibility="collapsed")

st.sidebar.markdown("### Chart Type")
show_candlestick = st.sidebar.checkbox("Candlestick", value=True)
show_line = st.sidebar.checkbox("Line", value=False)
show_ohlc = st.sidebar.checkbox("OHLC", value=False)
show_trend = st.sidebar.checkbox("Show Trend Line", value=True)

st.sidebar.markdown("### About")
st.sidebar.info("This dashboard provides comprehensive stock market analysis with interactive charts, performance metrics, and comparative analytics.")

# Filter data based on selection
stock_df = df[df['SYMBOL'] == selected_stock].copy()
if len(date_range) == 2:
    stock_df = stock_df[(stock_df['CANDLE_TIME'].dt.date >= date_range[0]) & 
                        (stock_df['CANDLE_TIME'].dt.date <= date_range[1])]

# Stock Overview Section
st.markdown(f"## {selected_stock} Overview")

col1, col2, col3, col4, col5 = st.columns(5)

current_price = stock_df['CANDLE_CLOSE'].iloc[-1]
price_change = stock_df['CANDLE_CLOSE'].iloc[-1] - stock_df['CANDLE_CLOSE'].iloc[0]
price_change_pct = (price_change / stock_df['CANDLE_CLOSE'].iloc[0]) * 100
period_high = stock_df['CANDLE_HIGH'].max()
period_low = stock_df['CANDLE_LOW'].min()
volatility = stock_df['daily_return'].std()

with col1:
    st.markdown("**Current Price**")
    st.markdown(f"<h2 style='color: #00ff00; margin: 0;'>${current_price:.2f}</h2>", unsafe_allow_html=True)
    if price_change >= 0:
        st.markdown(f"<span style='color: #00ff00;'>▲ +{price_change_pct:.2f}%</span>", unsafe_allow_html=True)
    else:
        st.markdown(f"<span style='color: #ff4444;'>▼ {price_change_pct:.2f}%</span>", unsafe_allow_html=True)

with col2:
    st.markdown("**Price Change**")
    st.markdown(f"<h2 style='color: {'#00ff00' if price_change >= 0 else '#ff4444'}; margin: 0;'>${abs(price_change):.2f}</h2>", unsafe_allow_html=True)
    if price_change >= 0:
        st.markdown(f"<span style='color: #00ff00;'>▲ +{price_change_pct:.2f}%</span>", unsafe_allow_html=True)
    else:
        st.markdown(f"<span style='color: #ff4444;'>▼ {price_change_pct:.2f}%</span>", unsafe_allow_html=True)

with col3:
    st.markdown("**Period High**")
    st.markdown(f"<h2 style='margin: 0;'>${period_high:.2f}</h2>", unsafe_allow_html=True)

with col4:
    st.markdown("**Period Low**")
    st.markdown(f"<h2 style='margin: 0;'>${period_low:.2f}</h2>", unsafe_allow_html=True)

with col5:
    st.markdown("**Volatility (Annual)**")
    st.markdown(f"<h2 style='margin: 0;'>{volatility * np.sqrt(252):.2f}%</h2>", unsafe_allow_html=True)

# Price Chart
st.markdown(f"## {selected_stock} Price Chart")

fig = go.Figure()

if show_candlestick:
    fig.add_trace(go.Candlestick(
        x=stock_df['CANDLE_TIME'],
        open=stock_df['CANDLE_OPEN'],
        high=stock_df['CANDLE_HIGH'],
        low=stock_df['CANDLE_LOW'],
        close=stock_df['CANDLE_CLOSE'],
        name='Close Price',
        increasing_line_color='#26a69a',
        decreasing_line_color='#ef5350'
    ))

if show_line:
    fig.add_trace(go.Scatter(
        x=stock_df['CANDLE_TIME'],
        y=stock_df['CANDLE_CLOSE'],
        mode='lines',
        name='Close Price',
        line=dict(color='#2196F3', width=2)
    ))

if show_ohlc:
    fig.add_trace(go.Ohlc(
        x=stock_df['CANDLE_TIME'],
        open=stock_df['CANDLE_OPEN'],
        high=stock_df['CANDLE_HIGH'],
        low=stock_df['CANDLE_LOW'],
        close=stock_df['CANDLE_CLOSE'],
        name='OHLC',
        increasing_line_color='#26a69a',
        decreasing_line_color='#ef5350'
    ))

if show_trend:
    fig.add_trace(go.Scatter(
        x=stock_df['CANDLE_TIME'],
        y=stock_df['TREND_LINE'],
        mode='lines',
        name='Trend Line',
        line=dict(color='#FFA500', width=2, dash='dash')
    ))

fig.update_layout(
    height=500,
    xaxis_title="Date",
    yaxis_title="Price ($)",
    hovermode='x unified',
    template='plotly_dark',
    xaxis_rangeslider_visible=False
)

st.plotly_chart(fig, use_container_width=True)

# Distribution and Cumulative Returns
col1, col2 = st.columns(2)

with col1:
    st.markdown("## Daily Returns Distribution")
    
    returns = stock_df['daily_return'].dropna()
    
    fig_dist = go.Figure()
    fig_dist.add_trace(go.Histogram(
        x=returns,
        nbinsx=30,
        name='Frequency',
        marker_color='#2196F3'
    ))
    
    fig_dist.update_layout(
        xaxis_title="Daily Return (%)",
        yaxis_title="Frequency",
        height=350,
        template='plotly_dark',
        showlegend=False
    )
    
    st.plotly_chart(fig_dist, use_container_width=True)

with col2:
    st.markdown("## Cumulative Returns")
    
    fig_cum = go.Figure()
    fig_cum.add_trace(go.Scatter(
        x=stock_df['CANDLE_TIME'],
        y=stock_df['cumulative_return'],
        mode='lines',
        name='Cumulative Return',
        line=dict(color='#4CAF50', width=2),
        fill='tozeroy',
        fillcolor='rgba(76, 175, 80, 0.3)'
    ))
    
    fig_cum.update_layout(
        xaxis_title="Date",
        yaxis_title="Cumulative Return (%)",
        height=350,
        template='plotly_dark',
        showlegend=False
    )
    
    st.plotly_chart(fig_cum, use_container_width=True)

# Stock Comparison Section
st.markdown("## Stock Comparison")

comparison_stocks = st.multiselect(
    "Select stocks to compare",
    options=symbols,
    default=symbols[:3]
)

if comparison_stocks:
    # Normalized comparison chart
    fig_comp = go.Figure()
    
    for symbol in comparison_stocks:
        symbol_data = df[df['SYMBOL'] == symbol].copy()
        if len(date_range) == 2:
            symbol_data = symbol_data[(symbol_data['CANDLE_TIME'].dt.date >= date_range[0]) & 
                                     (symbol_data['CANDLE_TIME'].dt.date <= date_range[1])]
        
        symbol_data['normalized'] = (symbol_data['CANDLE_CLOSE'] / symbol_data['CANDLE_CLOSE'].iloc[0]) * 100
        
        fig_comp.add_trace(go.Scatter(
            x=symbol_data['CANDLE_TIME'],
            y=symbol_data['normalized'],
            mode='lines',
            name=symbol,
            line=dict(width=3)
        ))
    
    fig_comp.update_layout(
        xaxis_title="Date",
        yaxis_title="Normalized Price (Base 100)",
        height=400,
        template='plotly_dark',
        hovermode='x unified'
    )
    
    st.plotly_chart(fig_comp, use_container_width=True)
    
    # Performance comparison table
    st.markdown("## Performance Comparison Table")
    
    comparison_data = []
    for symbol in comparison_stocks:
        symbol_data = df[df['SYMBOL'] == symbol]
        if len(date_range) == 2:
            symbol_data = symbol_data[(symbol_data['CANDLE_TIME'].dt.date >= date_range[0]) & 
                                     (symbol_data['CANDLE_TIME'].dt.date <= date_range[1])]
        
        start_price = symbol_data['CANDLE_CLOSE'].iloc[0]
        current_price = symbol_data['CANDLE_CLOSE'].iloc[-1]
        change_pct = ((current_price - start_price) / start_price) * 100
        period_high = symbol_data['CANDLE_HIGH'].max()
        period_low = symbol_data['CANDLE_LOW'].min()
        vol = symbol_data['daily_return'].std() * np.sqrt(252)
        
        comparison_data.append({
            'SYMBOL': symbol,
            'Start Price': f"${start_price:.2f}",
            'Current Price': f"${current_price:.2f}",
            'Change %': f"{change_pct:.2f}%",
            'Period High': f"${period_high:.2f}",
            'Period Low': f"${period_low:.2f}",
            'Volatility %': f"{vol:.2f}%"
        })
    
    comp_df = pd.DataFrame(comparison_data)
    st.dataframe(comp_df, use_container_width=True, hide_index=True)

# Volatility Analysis
st.markdown("## Volatility Analysis")

rolling_window = st.slider("Rolling window (days)", min_value=5, max_value=60, value=20, step=5)

# Calculate rolling volatility with selected window
volatility_data = []
for symbol in comparison_stocks if comparison_stocks else [selected_stock]:
    symbol_data = df[df['SYMBOL'] == symbol].copy()
    if len(date_range) == 2:
        symbol_data = symbol_data[(symbol_data['CANDLE_TIME'].dt.date >= date_range[0]) & 
                                 (symbol_data['CANDLE_TIME'].dt.date <= date_range[1])]
    
    symbol_data['rolling_vol'] = symbol_data['daily_return'].rolling(window=rolling_window).std()
    volatility_data.append(symbol_data)

fig_vol = go.Figure()

for data in volatility_data:
    symbol = data['SYMBOL'].iloc[0]
    fig_vol.add_trace(go.Scatter(
        x=data['CANDLE_TIME'],
        y=data['rolling_vol'],
        mode='lines',
        name=symbol,
        line=dict(width=3)
    ))

fig_vol.update_layout(
    xaxis_title="Date",
    yaxis_title="Rolling Volatility (Annualized %)",
    height=400,
    template='plotly_dark',
    hovermode='x unified'
)

st.plotly_chart(fig_vol, use_container_width=True)
