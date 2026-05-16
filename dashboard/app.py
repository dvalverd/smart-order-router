
import sys
import os
import time
import random
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from router import RoutingEngine, Order, Side, OrderType, RoutingStrategy
from router.venues import VENUE_CONFIGS

st.set_page_config(page_title="Smart Order Router", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Libre+Baskerville:wght@400;700&display=swap');
html, body, [class*="css"], p, div, span, label, input, button, select {
    font-family: 'Libre Baskerville', Georgia, serif !important;
}
.stApp { background-color: #d4c7ca; color: #d4c7ca; }
#MainMenu, footer, header { visibility: hidden; }
[data-testid="collapsedControl"] { display: none; }
[data-testid="stSidebar"] { display: none; }
.block-container { max-width: 1120px !important; padding: 2.5rem 2rem !important; }
.page-header { margin-bottom: 2rem; padding-bottom: 1rem; border-bottom: 2px solid #1c1018; }
.page-title { font-size: 28px; font-weight: 700; color: #1c1018; letter-spacing: -0.01em; margin-bottom: 4px; }
.page-meta { font-size: 13px; color: #7a5f72; }
.section-head { font-size: 10px; font-weight: 700; letter-spacing: 0.16em; text-transform: uppercase; color: #7a5f72; margin: 2rem 0 0.75rem 0; padding-bottom: 6px; border-bottom: 1px solid #d9ccd6; }
[data-testid="stMetric"] { background: #f7f2f6; border: 1px solid #d9ccd6; border-radius: 0; padding: 16px 20px !important; }
[data-testid="stMetricLabel"] { font-size: 10px !important; font-weight: 700 !important; letter-spacing: 0.14em !important; text-transform: uppercase !important; color: #7a5f72 !important; }
[data-testid="stMetricValue"] { font-size: 24px !important; font-weight: 700 !important; color: #1c1018 !important; }
.stTabs [data-baseweb="tab-list"] { background: transparent; border-bottom: 2px solid #1c1018; }
.stTabs [data-baseweb="tab"] { background: transparent; font-size: 12px; color: #7a5f72; padding: 10px 24px 10px 0; border: none; border-bottom: 2px solid transparent; text-transform: uppercase; letter-spacing: 0.06em; }
.stTabs [aria-selected="true"] { color: #1c1018 !important; border-bottom: 2px solid #5e1f4a !important; font-weight: 700 !important; }
.stButton button { background: #5e1f4a !important; color: #f0ebf0 !important; border: none !important; border-radius: 0 !important; font-size: 11px !important; font-weight: 700 !important; letter-spacing: 0.12em !important; text-transform: uppercase !important; padding: 10px 28px !important; }
.stButton button:hover { background: #7a2960 !important; }
.stSelectbox label, .stSlider label, .stRadio > label { font-size: 10px !important; font-weight: 700 !important; letter-spacing: 0.14em !important; text-transform: uppercase !important; color: #7a5f72 !important; }
.stSelectbox > div > div { background: #f7f2f6 !important; border: 1px solid #d9ccd6 !important; border-radius: 0 !important;  color: #1c1018 !important;}
.stSelectbox > div > div > div { color: #1c1018 !important;}
[data-testid="stDataFrame"] { border: 1px solid #d9ccd6 !important; border-radius: 0 !important; }
</style>
""", unsafe_allow_html=True)

PLOT = dict(
    paper_bgcolor="#d4c7ca",
    plot_bgcolor="#d4c7ca",
    font=dict(family="Libre Baskerville, Georgia, serif", color="#1c1018", size=12),
    xaxis=dict(gridcolor="#e8dfe5", linecolor="#d9ccd6", tickfont=dict(color="#7a5f72", size=11)),
    yaxis=dict(gridcolor="#e8dfe5", linecolor="#d9ccd6", tickfont=dict(color="#7a5f72", size=11)),
    margin=dict(l=0, r=0, t=28, b=0),
)

VENUE_COLORS = {
    "NYSE": "#3d7a5a",
    "NASDAQ": "#5e1f4a",
    "BATS": "#7a2940",
    "IEX": "#9b8a94",
    "DARK": "#1c1018",
}


@st.cache_resource
def get_engine():
    return RoutingEngine(ticker="AAPL", initial_price=185.00)


engine = get_engine()

if "order_log" not in st.session_state:
    st.session_state.order_log = []


st.markdown("""
<div class="page-header">
    <div class="page-title">Smart Order Router</div>
    <div class="page-meta">Equities routing across simulated venues, Python with C++</div>
</div>
""", unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["Order Book", "Route an Order", "Strategy Comparison", "History"])


with tab1:
    if st.button("Refresh quotes"):
        engine.market.tick()

    nbbo = engine.get_nbbo()
    quotes = engine.get_all_quotes()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Best Bid", f"${nbbo['best_bid']:.4f}", nbbo["best_bid_venue"])
    c2.metric("Best Ask", f"${nbbo['best_ask']:.4f}", nbbo["best_ask_venue"])
    c3.metric("Spread", f"${nbbo['spread']:.4f}")
    c4.metric("Mid", f"${nbbo['mid']:.4f}")

    st.markdown("<div class='section-head'>Live venue quotes</div>", unsafe_allow_html=True)
    df_quotes = pd.DataFrame(quotes)
    df_quotes["spread"] = (df_quotes["ask"] - df_quotes["bid"]).round(4)
    df_quotes["fee_per_share"] = df_quotes["fee_per_share"].map("${:.4f}".format)
    df_quotes["bid"] = df_quotes["bid"].map("${:.4f}".format)
    df_quotes["ask"] = df_quotes["ask"].map("${:.4f}".format)
    df_quotes["spread"] = df_quotes["spread"].map("${:.4f}".format)
    df_quotes.columns = ["Venue", "Bid", "Ask", "Bid Size", "Ask Size", "Fee/Share", "Spread"]
    st.dataframe(df_quotes, use_container_width=True, hide_index=True)

    st.markdown("<div class='section-head'>Depth by venue</div>", unsafe_allow_html=True)
    raw_quotes = engine.get_all_quotes()
    depth_data = []
    for q in raw_quotes:
        depth_data.extend([
            {"venue": q["venue"], "side": "Bid", "size": q["bid_size"]},
            {"venue": q["venue"], "side": "Ask", "size": q["ask_size"]},
        ])
    df_depth = pd.DataFrame(depth_data)
    fig = px.bar(df_depth, x="venue", y="size", color="side",
                 barmode="group",
                 color_discrete_map={"Bid": "#3d7a5a", "Ask": "#7a2940"})
    fig.update_layout(**PLOT, height=280, showlegend=True)
    fig.update_traces(marker_line_width=0)
    st.plotly_chart(fig, use_container_width=True)



with tab2:
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        ticker = st.selectbox("Ticker", ["AAPL", "MSFT", "NVDA", "AMZN"])
    with c2:
        side = st.selectbox("Side", ["buy", "sell"])
    with c3:
        qty = st.slider("Quantity", 100, 10000, 500, 100)
    with c4:
        strategy = st.selectbox("Strategy", ["best_price", "split"])

    max_venues = st.slider("Max venues (split only)", 2, 5, 3) if strategy == "split" else 1

    if st.button("Route order"):
        order = Order(
            ticker=ticker,
            side=Side(side),
            qty=qty,
            strategy=RoutingStrategy(strategy),
            max_venues=max_venues,
        )
        result = engine.route(order)
        st.session_state.order_log.append(result.to_dict())

        st.markdown("<div class='section-head'>Fill result</div>", unsafe_allow_html=True)
        r1, r2, r3, r4 = st.columns(4)
        r1.metric("Avg fill price", f"${result.avg_fill_price:.4f}")
        r2.metric("Slippage", f"{result.total_slippage_bps:.2f} bps")
        r3.metric("VWAP deviation", f"{result.vwap_deviation_bps:.2f} bps")
        r4.metric("Fill rate", f"{result.fill_rate:.0%}")

        st.markdown("<div class='section-head'>Fill breakdown</div>", unsafe_allow_html=True)
        fills_data = [
            {
                "Venue": f.venue,
                "Qty": f.fill_qty,
                "Fill Price": f"${f.fill_price:.4f}",
                "Fees": f"${f.fees:.4f}",
                "Net Cost": f"${f.net_cost:.2f}",
                "Slippage (bps)": f"{f.slippage_bps:.2f}",
                "Latency (us)": f"{f.latency_us:.1f}",
            }
            for f in result.fills
        ]
        st.dataframe(pd.DataFrame(fills_data), use_container_width=True, hide_index=True)



with tab3:
    st.markdown("<div class='section-head'>Compare routing strategies head to head</div>", unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        cmp_side = st.selectbox("Side", ["buy", "sell"], key="cmp_side")
        cmp_qty = st.slider("Quantity", 100, 10000, 1000, 100, key="cmp_qty")
    with c2:
        n_runs = st.slider("Simulation runs", 10, 200, 50)

    if st.button("Run comparison"):
        results = {"best_price": [], "split": []}

        for _ in range(n_runs):
            for strat in ["best_price", "split"]:
                order = Order(
                    ticker="AAPL",
                    side=Side(cmp_side),
                    qty=cmp_qty,
                    strategy=RoutingStrategy(strat),
                    max_venues=3,
                )
                r = engine.route(order)
                results[strat].append(r.to_dict())

        df_results = pd.DataFrame([
            {
                "strategy": r["strategy"],
                "slippage_bps": r["slippage_bps"],
                "vwap_deviation_bps": r["vwap_deviation_bps"],
                "latency_us": r["total_latency_us"],
                "n_venues": len(r["venues_used"]),
            }
            for strat_results in results.values()
            for r in strat_results
        ])

        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("<div class='section-head'>Slippage distribution</div>", unsafe_allow_html=True)
            fig = px.box(df_results, x="strategy", y="slippage_bps",
                         color="strategy",
                         color_discrete_map={"best_price": "#3d7a5a", "split": "#5e1f4a"})
            fig.update_layout(**PLOT, showlegend=False, height=300)
            st.plotly_chart(fig, use_container_width=True)

        with col_b:
            st.markdown("<div class='section-head'>VWAP deviation distribution</div>", unsafe_allow_html=True)
            fig2 = px.box(df_results, x="strategy", y="vwap_deviation_bps",
                          color="strategy",
                          color_discrete_map={"best_price": "#3d7a5a", "split": "#5e1f4a"})
            fig2.update_layout(**PLOT, showlegend=False, height=300)
            st.plotly_chart(fig2, use_container_width=True)

        st.markdown("<div class='section-head'>Summary statistics</div>", unsafe_allow_html=True)
        summary = df_results.groupby("strategy").agg(
            avg_slippage=("slippage_bps", "mean"),
            median_slippage=("slippage_bps", "median"),
            avg_vwap_dev=("vwap_deviation_bps", "mean"),
            avg_latency=("latency_us", "mean"),
        ).round(4)
        st.dataframe(summary, use_container_width=True)


with tab4:
    if not st.session_state.order_log:
        st.info("No orders routed yet. Go to the Route an Order tab to submit orders.")
    else:
        df_hist = pd.DataFrame(st.session_state.order_log)
        st.markdown("<div class='section-head'>Order history</div>", unsafe_allow_html=True)

        c1, c2, c3 = st.columns(3)
        c1.metric("Total orders", len(df_hist))
        c2.metric("Avg slippage", f"{df_hist['slippage_bps'].mean():.2f} bps")
        c3.metric("Avg latency", f"{df_hist['total_latency_us'].mean():.1f} us")

        st.markdown("<div class='section-head'>Slippage over time</div>", unsafe_allow_html=True)
        fig = px.line(df_hist.reset_index(), x="index", y="slippage_bps",
                      color="strategy",
                      color_discrete_map={"best_price": "#3d7a5a", "split": "#5e1f4a"})
        fig.update_layout(**PLOT, height=280)
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("<div class='section-head'>All orders</div>", unsafe_allow_html=True)
        display_cols = ["order_id", "ticker", "side", "qty", "strategy",
                        "avg_fill_price", "slippage_bps", "vwap_deviation_bps",
                        "venues_used", "fill_rate"]
        st.dataframe(df_hist[display_cols], use_container_width=True, hide_index=True)
        csv = df_hist.to_csv(index=False)
        st.download_button("Export CSV", csv, "sor_history.csv", "text/csv")
