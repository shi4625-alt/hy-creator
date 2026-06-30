import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import io

st.set_page_config(page_title="HY 인사이트", layout="wide")

# ---------- CSS ----------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700;900&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }
.stApp { background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); }
.main-header {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 1.5rem 2rem; border-radius: 20px; color: white;
    margin-bottom: 2rem; box-shadow: 0 10px 30px rgba(102,126,234,0.4);
}
.main-header h1 { margin: 0; font-weight: 900; font-size: 2.2rem; }
.main-header p { margin: 0.3rem 0 0; opacity: 0.85; font-weight: 300; }
.card {
    background: white; border-radius: 16px; padding: 1.5rem;
    box-shadow: 0 4px 20px rgba(0,0,0,0.06); margin-bottom: 1.5rem;
    border: 1px solid rgba(255,255,255,0.8);
}
.card h3 { color: #333; font-weight: 700; margin-top: 0; font-size: 1.1rem; }
.metric-box {
    background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%);
    border-radius: 12px; padding: 1.2rem; text-align: center;
    border: 1px solid #667eea20;
}
.metric-box .val {
    font-size: 1.8rem; font-weight: 900;
    background: linear-gradient(135deg, #667eea, #764ba2);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.metric-box .label { font-size: 0.8rem; color: #666; font-weight: 500; margin-top: 0.2rem; }
.stButton button {
    border-radius: 12px !important; font-weight: 600 !important;
    border: none !important; transition: all 0.2s !important;
}
.stButton button:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0,0,0,0.12) !important; }
div[data-testid="stDataFrame"] { border-radius: 12px; overflow: hidden; border: 1px solid #eee; }
.insight-badge {
    display: inline-block;
    background: linear-gradient(135deg, #667eea, #764ba2);
    color: white; padding: 0.25rem 0.8rem; border-radius: 20px;
    font-size: 0.75rem; font-weight: 600;
}
</style>
""", unsafe_allow_html=True)

# ---------- Session ----------
if "df" not in st.session_state:
    st.session_state.df = None

# ---------- Header ----------
st.markdown("""
<div class="main-header">
    <h1>📊 HY 인사이트</h1>
    <p>데이터를 업로드하면 AI가 자동으로 분석하고 예쁜 그래프를 만들어드립니다</p>
</div>
""", unsafe_allow_html=True)

# ---------- Upload ----------
col_upload, col_preview = st.columns([1.2, 2.8])

with col_upload:
    uploaded = st.file_uploader("CSV 또는 Excel 파일 업로드", type=["csv", "xlsx", "xls"],
                                label_visibility="collapsed")
    if uploaded:
        try:
            if uploaded.name.endswith(".csv"):
                df = pd.read_csv(uploaded)
            else:
                df = pd.read_excel(uploaded)
            st.session_state.df = df
            st.success(f"✅ {df.shape[0]}행 × {df.shape[1]}열 불러오기 완료")
        except Exception as e:
            st.error(f"오류: {e}")

    if st.session_state.df is not None and st.button("🔄 새 파일 업로드"):
        st.session_state.df = None
        st.rerun()

if st.session_state.df is None:
    st.info("👈 CSV 또는 Excel 파일을 업로드해주세요.")
    st.stop()

df = st.session_state.df
num_cols = df.select_dtypes(include="number").columns.tolist()
cat_cols = df.select_dtypes(include="object").columns.tolist()
all_cols = df.columns.tolist()

# ================================================================
# TAB 1: 데이터 미리보기
# ================================================================
tab1, tab2, tab3 = st.tabs(["📋 데이터 개요", "📊 인사이트 & 분포", "🎨 그래프 스튜디오"])

with tab1:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<div class="metric-box"><div class="val">{df.shape[0]}</div><div class="label">전체 행</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="metric-box"><div class="val">{df.shape[1]}</div><div class="label">전체 컬럼</div></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="metric-box"><div class="val">{len(num_cols)}</div><div class="label">숫자 컬럼</div></div>', unsafe_allow_html=True)
    with col4:
        st.markdown(f'<div class="metric-box"><div class="val">{len(cat_cols)}</div><div class="label">텍스트 컬럼</div></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card"><h3>📋 데이터 미리보기</h3>', unsafe_allow_html=True)
    st.dataframe(df.head(500), use_container_width=True, height=350)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card"><h3>📌 컬럼 정보</h3>', unsafe_allow_html=True)
    info = pd.DataFrame({
        "컬럼명": df.columns,
        "타입": df.dtypes.astype(str).values,
        "널(null)": df.isnull().sum().values,
        "널(%)": (df.isnull().sum() / len(df) * 100).round(1).values,
        "고유값": [df[c].nunique() for c in df.columns]
    })
    st.dataframe(info, use_container_width=True, hide_index=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ================================================================
# TAB 2: 인사이트 & 분포
# ================================================================
with tab2:
    if not num_cols:
        st.warning("숫자 컬럼이 없어 인사이트를 생성할 수 없습니다.")
    else:
        # --- Auto Insights ---
        st.markdown('<div class="card"><h3>💡 주요 인사이트</h3>', unsafe_allow_html=True)
        insight_cols = st.columns(3)

        insights = []
        for c in num_cols[:6]:
            s = df[c].dropna()
            if len(s) == 0:
                continue
            insights.append({
                "col": c,
                "mean": s.mean(),
                "median": s.median(),
                "min": s.min(),
                "max": s.max(),
                "std": s.std(),
                "q1": s.quantile(0.25),
                "q3": s.quantile(0.75),
                "skew": s.skew(),
            })

        for idx, ins in enumerate(insights):
            with insight_cols[idx % 3]:
                st.markdown(f"""
                <div class="metric-box" style="margin-bottom:0.8rem;">
                    <div style="font-size:0.85rem;font-weight:700;color:#333;margin-bottom:0.3rem;">📌 {ins['col']}</div>
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.3rem;font-size:0.8rem;">
                        <span>평균 <b>{ins['mean']:.1f}</b></span>
                        <span>중앙 <b>{ins['median']:.1f}</b></span>
                        <span>최소 <b>{ins['min']:.1f}</b></span>
                        <span>최대 <b>{ins['max']:.1f}</b></span>
                        <span>Q1 <b>{ins['q1']:.1f}</b></span>
                        <span>Q3 <b>{ins['q3']:.1f}</b></span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

        # --- Distribution / Binning / Ranking ---
        st.markdown('<div class="card"><h3>📊 분포 분석 & 구간 보기</h3>', unsafe_allow_html=True)

        col_a, col_b = st.columns([1, 1])
        with col_a:
            target_col = st.selectbox("분석할 컬럼", num_cols, key="ins_col")
        with col_b:
            mode = st.radio("보기 모드", ["📊 히스토그램", "🎯 구간(bin) 보기", "🏆 내 위치는?"],
                            horizontal=True, label_visibility="collapsed")

        col = target_col
        s = df[col].dropna()

        if mode == "📊 히스토그램":
            bin_size = st.slider("구간(bin) 크기", 2, 50, 10, key="hist_bin")
            fig = px.histogram(df, x=col, nbins=bin_size,
                               title=f"📊 {col} 분포 (히스토그램)",
                               color_discrete_sequence=["#667eea"],
                               template="plotly_white")
            fig.update_layout(
                title_font=dict(size=18, family="Noto Sans KR"),
                bargap=0.08,
                xaxis_title=col,
                yaxis_title="빈도",
                font=dict(family="Noto Sans KR"),
                plot_bgcolor="rgba(0,0,0,0)",
            )
            fig.update_traces(marker_line_color="white", marker_line_width=1.2)
            st.plotly_chart(fig, use_container_width=True)

            with st.expander("📋 구간별 데이터 보기"):
                bins = pd.cut(df[col], bins=bin_size)
                bin_df = df.groupby(bins, observed=False).size().reset_index(name="빈도")
                bin_df.columns = ["구간", "빈도"]
                bin_df["비율(%)"] = (bin_df["빈도"] / bin_df["빈도"].sum() * 100).round(1)
                st.dataframe(bin_df.sort_values("구간"), use_container_width=True, hide_index=True)

        elif mode == "🎯 구간(bin) 보기":
            st.markdown(f"##### 자동 구간 분석 — {col}")
            auto_bins = st.slider("구간 개수", 2, 10, 5, key="auto_bin")

            # auto bin boundaries
            min_v, max_v = s.min(), s.max()
            step = (max_v - min_v) / auto_bins
            boundaries = [min_v + i * step for i in range(auto_bins + 1)]
            labels = [f"{boundaries[i]:.0f}~{boundaries[i+1]:.0f}" for i in range(auto_bins)]

            df_temp = df.copy()
            df_temp["구간"] = pd.cut(df[col], bins=auto_bins, labels=labels, include_lowest=True)

            bin_summary = df_temp.groupby("구간", observed=False).agg(
                개수=("구간", "count"),
                평균=(col, "mean"),
                최소=(col, "min"),
                최대=(col, "max"),
            ).reset_index()
            bin_summary["비율(%)"] = (bin_summary["개수"] / bin_summary["개수"].sum() * 100).round(1)
            bin_summary["평균"] = bin_summary["평균"].round(1)

            col_b1, col_b2 = st.columns([1.2, 2.8])
            with col_b1:
                st.dataframe(bin_summary, use_container_width=True, hide_index=True)

            with col_b2:
                fig = px.bar(bin_summary, x="구간", y="개수",
                             text="비율(%)", color="개수",
                             color_continuous_scale="purples",
                             template="plotly_white", title=f"📊 {col} 구간 분포")
                fig.update_traces(texttemplate="%{text}%", textposition="outside")
                fig.update_layout(
                    title_font=dict(size=16, family="Noto Sans KR"),
                    font=dict(family="Noto Sans KR"),
                    plot_bgcolor="rgba(0,0,0,0)",
                    yaxis_title="개수", xaxis_title="구간",
                )
                st.plotly_chart(fig, use_container_width=True)

        elif mode == "🏆 내 위치는?":
            my_val = st.number_input(f"내 {col} 값 입력", value=float(s.mean()), key="my_val")
            rank_pct = (s < my_val).sum() / len(s) * 100
            above_pct = (s > my_val).sum() / len(s) * 100
            rank_n = int((s > my_val).sum()) + 1
            total_n = len(s)

            col_r1, col_r2, col_r3 = st.columns(3)
            with col_r1:
                st.markdown(f'<div class="metric-box"><div class="val">{rank_pct:.1f}%</div><div class="label">나보다 낮은 사람 비율</div></div>', unsafe_allow_html=True)
            with col_r2:
                st.markdown(f'<div class="metric-box"><div class="val">{above_pct:.1f}%</div><div class="label">나보다 높은 사람 비율</div></div>', unsafe_allow_html=True)
            with col_r3:
                st.markdown(f'<div class="metric-box"><div class="val">{rank_n}/{total_n}</div><div class="label">전체 등수</div></div>', unsafe_allow_html=True)

            fig = go.Figure()
            fig.add_trace(go.Histogram(x=s, name="전체 분포",
                                        marker_color="#c3cfe2", marker_line_color="white",
                                        marker_line_width=1, nbinsx=20))
            fig.add_vline(x=my_val, line_dash="dash", line_color="#764ba2",
                          line_width=3,
                          annotation_text=f"내 점수: {my_val}",
                          annotation_font_size=14,
                          annotation_font_color="#764ba2",
                          annotation_position="top")
            fig.update_layout(
                title=f"📊 {col} 분포에서 내 위치",
                template="plotly_white",
                font=dict(family="Noto Sans KR"),
                plot_bgcolor="rgba(0,0,0,0)",
                yaxis_title="인원", xaxis_title=col,
                showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True)

        st.markdown('</div>', unsafe_allow_html=True)

# ================================================================
# TAB 3: 그래프 스튜디오
# ================================================================
with tab3:
    st.markdown('<div class="card"><h3>🎨 그래프 스튜디오</h3>', unsafe_allow_html=True)

    col_s1, col_s2 = st.columns([1, 1.5])

    with col_s1:
        chart_type = st.selectbox("차트 종류", [
            "📊 막대", "📈 라인", "🥧 파이", "🔵 산점도",
            "📦 박스플롯", "🌡️ 히트맵", "📊 누적막대", "📈 면적"
        ])
        chart_key = chart_type.split(" ")[-1]

        x_col = st.selectbox("X축", all_cols)

        if chart_key not in ["파이", "히트맵"]:
            y_col = st.selectbox("Y축 (수치)", num_cols) if num_cols else st.text_input("Y축", disabled=True)
        else:
            y_col = st.selectbox("값", num_cols) if num_cols else None

        color_col = st.selectbox("색상 구분", ["없음"] + all_cols)
        color_col = None if color_col == "없음" else color_col

        title_text = st.text_input("그래프 제목", placeholder="자동 생성")

        theme = st.selectbox("테마", ["plotly_white", "plotly_dark", "ggplot2", "seaborn", "simple_white"])
        palette = st.selectbox("컬러 팔레트", [
            "모던 퍼플", "오션 블루", "선셋 오렌지", "포레스트 그린",
            "로즈 핑크", "블랙 & 화이트"
        ])

        palette_map = {
            "모던 퍼플": ["#667eea", "#764ba2", "#a78bfa", "#8b5cf6", "#7c3aed"],
            "오션 블루": ["#06b6d4", "#0891b2", "#22d3ee", "#0e7490", "#38bdf8"],
            "선셋 오렌지": ["#f97316", "#ea580c", "#fdba74", "#d97706", "#fb923c"],
            "포레스트 그린": ["#22c55e", "#16a34a", "#4ade80", "#15803d", "#86efac"],
            "로즈 핑크": ["#ec4899", "#db2777", "#f472b6", "#be185d", "#fbcfe8"],
            "블랙 & 화이트": ["#1f2937", "#4b5563", "#9ca3af", "#d1d5db", "#f3f4f6"],
        }
        colors = palette_map[palette]

    with col_s2:
        st.markdown('<div style="height:0.5rem;"></div>', unsafe_allow_html=True)
        generate = st.button("🎯 그래프 생성", type="primary", use_container_width=True)

        if generate:
            try:
                fig = None
                if chart_key == "막대":
                    fig = px.bar(df, x=x_col, y=y_col, color=color_col,
                                 title=title_text or f"{y_col} by {x_col}",
                                 template=template if "template" in dir() else theme,
                                 text_auto=True, barmode="group",
                                 color_discrete_sequence=colors)
                elif chart_key == "라인":
                    fig = px.line(df, x=x_col, y=y_col, color=color_col,
                                  title=title_text or f"{y_col} 추세",
                                  template=theme, markers=True,
                                  color_discrete_sequence=colors)
                elif chart_key == "파이":
                    fig = px.pie(df, names=x_col, values=y_col,
                                 title=title_text or f"{y_col} 분포",
                                 color_discrete_sequence=colors)
                elif chart_key == "산점도":
                    fig = px.scatter(df, x=x_col, y=y_col, color=color_col,
                                     title=title_text or f"{x_col} vs {y_col}",
                                     template=theme, color_discrete_sequence=colors,
                                     hover_data=df.columns)
                elif chart_key == "박스플롯":
                    fig = px.box(df, x=x_col if df[x_col].dtype == "object" else None,
                                 y=y_col, color=color_col,
                                 title=title_text or "Box Plot",
                                 template=theme, color_discrete_sequence=colors)
                elif chart_key == "히트맵":
                    corr = df.select_dtypes(include="number").corr()
                    fig = px.imshow(corr, text_auto=".2f", aspect="auto",
                                    title=title_text or "Correlation",
                                    color_continuous_scale="Purples",
                                    template=theme)
                elif chart_key == "누적막대":
                    fig = px.bar(df, x=x_col, y=y_col, color=color_col,
                                 title=title_text or f"Stacked {y_col}",
                                 template=theme, barmode="stack", text_auto=True,
                                 color_discrete_sequence=colors)
                elif chart_key == "면적":
                    fig = px.area(df, x=x_col, y=y_col, color=color_col,
                                  title=title_text or f"{y_col} Area",
                                  template=theme, color_discrete_sequence=colors)

                if fig:
                    fig.update_layout(
                        font=dict(family="Noto Sans KR", size=13),
                        title_font=dict(size=18, family="Noto Sans KR"),
                        legend_title_text="",
                        hovermode="x unified",
                        margin=dict(l=40, r=40, t=60, b=40),
                        plot_bgcolor="rgba(0,0,0,0)",
                        paper_bgcolor="rgba(0,0,0,0)",
                    )
                    st.plotly_chart(fig, use_container_width=True)

                    # Export
                    col_e1, col_e2 = st.columns(2)
                    with col_e1:
                        html_bytes = fig.to_html(include_plotlyjs="cdn").encode()
                        st.download_button("🌐 HTML 다운로드", data=html_bytes,
                                           file_name=f"{title_text or 'chart'}.html",
                                           mime="text/html", use_container_width=True)
                    with col_e2:
                        csv_data = df.to_csv(index=False).encode()
                        st.download_button("📄 CSV 다운로드", data=csv_data,
                                           file_name="data.csv", mime="text/csv",
                                           use_container_width=True)

                    st.session_state._last_fig = fig
                    st.session_state._last_title = title_text or ""

            except Exception as e:
                st.error(f"그래프 생성 실패: {e}")

    st.markdown('</div>', unsafe_allow_html=True)

    # ---------- Quick Charts ----------
    st.markdown('<div class="card"><h3>⚡ 빠른 차트</h3>', unsafe_allow_html=True)
    st.markdown("자주 쓰는 차트를 바로 생성해보세요.")

    q1, q2, q3, q4 = st.columns(4)
    with q1:
        if st.button("📊 전체 분포 히트맵", use_container_width=True):
            if len(num_cols) >= 2:
                corr = df[num_cols].corr()
                fig = px.imshow(corr, text_auto=".2f", color_continuous_scale="Purples",
                                template="plotly_white", aspect="auto", title="Correlation Matrix")
                fig.update_layout(font=dict(family="Noto Sans KR"), plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig, use_container_width=True)
    with q2:
        if st.button("📈 모든 숫자 분포", use_container_width=True):
            if num_cols:
                n = min(len(num_cols), 6)
                fig = make_subplots(rows=n, cols=1, subplot_titles=num_cols[:n])
                for i, c in enumerate(num_cols[:n], 1):
                    fig.add_trace(go.Histogram(x=df[c].dropna(), name=c,
                                                marker_color=colors[i % len(colors)]), row=i, col=1)
                fig.update_layout(height=250*n, showlegend=False, template="plotly_white",
                                  title_text="📊 숫자 컬럼 분포", font=dict(family="Noto Sans KR"))
                fig.update_traces(marker_line_color="white", marker_line_width=1)
                st.plotly_chart(fig, use_container_width=True)
    with q3:
        if st.button("🥧 카테고리 비율", use_container_width=True):
            if cat_cols:
                c = cat_cols[0]
                vc = df[c].value_counts().reset_index()
                vc.columns = [c, "count"]
                fig = px.pie(vc, names=c, values="count", title=f"{c} 비율",
                             color_discrete_sequence=colors)
                fig.update_layout(font=dict(family="Noto Sans KR"))
                st.plotly_chart(fig, use_container_width=True)
    with q4:
        if st.button("🏆 상위 10개", use_container_width=True):
            if num_cols:
                c = num_cols[0]
                top = df.nlargest(10, c)[[c] + ([cat_cols[0]] if cat_cols else [])]
                fig = px.bar(top, x=top.index.astype(str), y=c,
                             title=f"🏆 {c} Top 10",
                             color_discrete_sequence=["#667eea"])
                fig.update_layout(font=dict(family="Noto Sans KR"), plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig, use_container_width=True)

    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("""
<div style="text-align:center;padding:2rem 0;color:#999;font-size:0.8rem;">
    HY 인사이트 · 데이터는 서버에 저장되지 않습니다
</div>
""", unsafe_allow_html=True)
