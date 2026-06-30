import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import re

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
.st-emotion-cache-1aehpvj { color: #667eea !important; }
.st-emotion-cache-1aehpvj p, .st-emotion-cache-1aehpvj span { color: #667eea !important; }
div[role="radiogroup"] label p, div[role="radiogroup"] label span { color: #333 !important; }
div[role="radiogroup"] label { color: #333 !important; }
.stRadio div[data-testid="stMarkdownContainer"] p { color: #333 !important; }
</style>
""", unsafe_allow_html=True)

# ---------- Session ----------
if "df" not in st.session_state:
    st.session_state.df = None

# ---------- Header ----------
st.markdown("""
<div class="main-header">
    <h1>📊 HY 인사이트</h1>
    <p>데이터 종류를 자동 감지하고 맞춤 분석을 제공합니다</p>
</div>
""", unsafe_allow_html=True)

# ================================================================
# 데이터 타입 감지 함수
# ================================================================
def detect_data_type(df):
    hints = set()
    col_lower = {c.lower(): c for c in df.columns}

    # 키워드 기반 감지
    kw_map = {
        "before_after": ["전", "후", "before", "after", "개선", "변화", "차이", "증가", "감소",
                         "전년", "당년", "전월", "당월", "전주", "당주", "yoY", "mom", "차이"],
        "score": ["점수", "score", "성적", "grade", "평가", "총점", "득점", "합격", "커트"],
        "sales": ["매출", "sales", "판매", "revenue", "profit", "이익", "수익", "매입",
                  "주문", "order", "amount", "price", "금액", "단가"],
        "survey": ["만족", "satisfaction", "설문", "survey", "응답", "답변", "리커트",
                   "likert", "nps", "추천", "의견"],
        "time_series": ["날짜", "date", "일자", "년도", "year", "월", "month", "분기",
                        "quarter", "일", "day", "기간", "period", "연도"],
        "hr": ["직원", "employee", "부서", "team", "직급", "position", "연차", "근속",
               "급여", "salary", "work", "근무"],
        "ratio": ["비율", "ratio", "%", "퍼센트", "rate", "율", "share", "점유", "구성비"],
        "rank": ["순위", "rank", "등수", "ranking", "top", "랭킹", "서열", "등급"],
    }

    detected = []
    for kw_type, keywords in kw_map.items():
        for c in col_lower:
            for kw in keywords:
                if kw in c:
                    detected.append(kw_type)
                    break

    # 숫자/텍스트 구성 분석
    num_cols = df.select_dtypes(include="number").columns.tolist()
    cat_cols = df.select_dtypes(include="object").columns.tolist()

    # 데이터 규모
    size = "small" if len(df) < 50 else ("medium" if len(df) < 500 else "large")

    # before/after 패턴: "전_XX", "후_XX" 쌍이 있는지
    ba_pairs = []
    for c in col_lower:
        for prefix in ["전_", "후_", "전", "후", "before_", "after_", "old_", "new_"]:
            if c.startswith(prefix) or c == prefix.strip("_"):
                base = c.replace(prefix, "", 1) if c != prefix.strip("_") else ""
                # 짝 찾기
                other_prefix = {"전_": "후_", "후_": "전_", "전": "후", "후": "전",
                                "before_": "after_", "after_": "before_",
                                "old_": "new_", "new_": "old_"}
                if prefix in other_prefix:
                    other = other_prefix[prefix] + base
                    if other in col_lower:
                        ba_pairs.append((col_lower[c], col_lower[other]))

    return {
        "types": detected,
        "num_cols": num_cols,
        "cat_cols": cat_cols,
        "size": size,
        "ba_pairs": ba_pairs,
        "has_date": any(kw in c for kw in ["날짜", "date", "일자", "년도", "year", "연도"]
                        for c in col_lower)
    }

# ================================================================
# 분석 모듈 함수들
# ================================================================
def render_before_after(df, pairs, colors):
    st.markdown("#### 🔄 전후 비교 분석")
    for col1, col2 in pairs:
        if col1 not in df.columns or col2 not in df.columns:
            continue
        s1, s2 = df[col1].dropna(), df[col2].dropna()
        if len(s1) == 0 or len(s2) == 0:
            continue

        change = s2.mean() - s1.mean()
        pct_change = (change / s1.mean() * 100) if s1.mean() != 0 else 0

        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        with col_m1:
            st.markdown(f'<div class="metric-box"><div class="val">{s1.mean():.1f}</div><div class="label">전 ({col1}) 평균</div></div>', unsafe_allow_html=True)
        with col_m2:
            st.markdown(f'<div class="metric-box"><div class="val">{s2.mean():.1f}</div><div class="label">후 ({col2}) 평균</div></div>', unsafe_allow_html=True)
        with col_m3:
            color = "#22c55e" if change > 0 else "#ef4444"
            st.markdown(f'<div class="metric-box"><div class="val" style="color:{color};background:none;-webkit-text-fill-color:{color};">{change:+.1f}</div><div class="label">변화량</div></div>', unsafe_allow_html=True)
        with col_m4:
            color = "#22c55e" if pct_change > 0 else "#ef4444"
            st.markdown(f'<div class="metric-box"><div class="val" style="color:{color};background:none;-webkit-text-fill-color:{color};">{pct_change:+.1f}%</div><div class="label">변화율</div></div>', unsafe_allow_html=True)

        # 전후 비교 차트
        fig = go.Figure()
        fig.add_trace(go.Violin(y=s1, name=f"전 ({col1})", side="negative",
                                 line_color=colors[0], fillcolor=colors[0],
                                 opacity=0.6))
        fig.add_trace(go.Violin(y=s2, name=f"후 ({col2})", side="positive",
                                 line_color=colors[2], fillcolor=colors[2],
                                 opacity=0.6))
        fig.update_layout(template="plotly_white", title=f"📊 {col1} → {col2} 분포 변화",
                          font=dict(family="Noto Sans KR"), showlegend=True,
                          violinmode="overlay", yaxis_title="값",
                          plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)

        # 개별 전후 비교 (데이터프레임)
        with st.expander("📋 개별 전후 데이터 보기"):
            comp = pd.DataFrame({f"전 ({col1})": s1, f"후 ({col2})": s2,
                                 "변화": s2.values - s1.values}).reset_index(drop=True)
            comp["변화율(%)"] = (comp["변화"] / comp[f"전 ({col1})"].replace(0, np.nan) * 100).round(1)
            st.dataframe(comp, use_container_width=True)

    if not pairs:
        st.info("전/후로 의심되는 컬럼 쌍을 찾지 못했습니다. 일반 분석을 이용해주세요.")

def render_distribution(df, num_cols, cat_cols, colors):
    st.markdown("#### 📊 분포 & 구간 분석")
    col = st.selectbox("분석할 컬럼", num_cols, key="dist_col")
    s = df[col].dropna()

    col_d1, col_d2 = st.columns([1, 2])

    with col_d1:
        st.markdown(f"""
        <div class="metric-box" style="margin-bottom:0.5rem;">
            <div style="font-size:0.8rem;color:#666;">기초 통계</div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.3rem;font-size:0.85rem;margin-top:0.3rem;">
                <span>평균 <b>{s.mean():.1f}</b></span>
                <span>중앙 <b>{s.median():.1f}</b></span>
                <span>최소 <b>{s.min():.1f}</b></span>
                <span>최대 <b>{s.max():.1f}</b></span>
                <span>표준편차 <b>{s.std():.1f}</b></span>
                <span>왜도 <b>{s.skew():.2f}</b></span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 구간 분석
        st.markdown("##### 구간 나누기")
        n_bins = st.slider("구간 수", 2, 10, 5, key="dist_bins")
        labels = [f"{s.min() + i*(s.max()-s.min())/n_bins:.0f}~{s.min() + (i+1)*(s.max()-s.min())/n_bins:.0f}"
                  for i in range(n_bins)]
        df_bin = df.copy()
        df_bin["구간"] = pd.cut(df[col], bins=n_bins, labels=labels, include_lowest=True)
        summary = df_bin.groupby("구간", observed=False).agg(
            개수=(col, "count"), 평균=(col, "mean"), 최소=(col, "min"), 최대=(col, "max")
        ).reset_index()
        summary["비율(%)"] = (summary["개수"] / summary["개수"].sum() * 100).round(1)
        summary["평균"] = summary["평균"].round(1)
        st.dataframe(summary, use_container_width=True, hide_index=True)

    with col_d2:
        fig = px.histogram(df, x=col, nbins=n_bins, title=f"📊 {col} 분포",
                           color_discrete_sequence=[colors[0]], template="plotly_white")
        fig.update_traces(marker_line_color="white", marker_line_width=1.2)
        fig.update_layout(font=dict(family="Noto Sans KR"), plot_bgcolor="rgba(0,0,0,0)",
                          bargap=0.05)
        st.plotly_chart(fig, use_container_width=True)

    # --- 내 위치 ---
    st.markdown("##### 🏆 내 위치/값 분석")
    my_val = st.number_input(f"값 입력", value=float(s.mean()), key="my_pos")
    below = (s < my_val).sum() / len(s) * 100
    above = (s > my_val).sum() / len(s) * 100
    rank_n = int((s > my_val).sum()) + 1

    col_r1, col_r2, col_r3 = st.columns(3)
    with col_r1:
        st.markdown(f'<div class="metric-box"><div class="val">{below:.1f}%</div><div class="label">나보다 낮은 값</div></div>', unsafe_allow_html=True)
    with col_r2:
        st.markdown(f'<div class="metric-box"><div class="val">{above:.1f}%</div><div class="label">나보다 높은 값</div></div>', unsafe_allow_html=True)
    with col_r3:
        st.markdown(f'<div class="metric-box"><div class="val">{rank_n}/{len(s)}</div><div class="label">전체 순위</div></div>', unsafe_allow_html=True)

    fig2 = go.Figure()
    fig2.add_trace(go.Histogram(x=s, marker_color=colors[1], marker_line_color="white",
                                 marker_line_width=1, nbinsx=20, opacity=0.7))
    fig2.add_vline(x=my_val, line_dash="dash", line_color=colors[2], line_width=3,
                   annotation_text=f"입력값: {my_val}", annotation_position="top",
                   annotation_font_size=14, annotation_font_color=colors[2])
    fig2.update_layout(template="plotly_white", font=dict(family="Noto Sans KR"),
                       plot_bgcolor="rgba(0,0,0,0)", showlegend=False)
    st.plotly_chart(fig2, use_container_width=True)

def render_trend(df, num_cols, cat_cols, colors):
    st.markdown("#### 📈 추세 분석")
    # 날짜 컬럼 찾기
    date_kws = ["날짜", "date", "일자", "년도", "year", "연도", "년", "월", "month", "분기", "quarter", "일", "day", "기간"]
    date_col = None
    for c in df.columns:
        cl = c.lower()
        if any(kw in cl for kw in date_kws):
            date_col = c
            break
    if date_col is None:
        date_col = st.selectbox("날짜/시간 컬럼 (선택)", ["없음"] + df.columns.tolist())
        if date_col == "없음":
            date_col = None

    if date_col:
        try:
            df_t = df.copy()
            df_t[date_col] = pd.to_datetime(df_t[date_col])
            df_t = df_t.sort_values(date_col)

            y_col = st.selectbox("추세 볼 컬럼", num_cols, key="trend_y")
            group_col = st.selectbox("그룹 구분 (선택)", ["없음"] + cat_cols, key="trend_g")
            group_col = None if group_col == "없음" else group_col

            if group_col:
                fig = px.line(df_t, x=date_col, y=y_col, color=group_col, markers=True,
                              title=f"📈 {y_col} 추세", template="plotly_white",
                              color_discrete_sequence=colors)
            else:
                fig = px.line(df_t, x=date_col, y=y_col, markers=True,
                              title=f"📈 {y_col} 추세", template="plotly_white",
                              color_discrete_sequence=[colors[0]])
            fig.update_layout(font=dict(family="Noto Sans KR"), plot_bgcolor="rgba(0,0,0,0)",
                              hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)
        except:
            st.warning("날짜 변환에 실패했습니다. 컬럼 형식을 확인해주세요.")
    else:
        if len(df) > 1:
            y_col = st.selectbox("추세 볼 컬럼", num_cols, key="trend_y2")
            fig = px.line(df, y=y_col, markers=True, title=f"📈 {y_col} (행순)",
                          template="plotly_white", color_discrete_sequence=[colors[0]])
            fig.update_layout(font=dict(family="Noto Sans KR"), plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("데이터가 충분하지 않습니다.")

def render_composition(df, cat_cols, num_cols, colors):
    st.markdown("#### 🥧 구성비 분석")
    if cat_cols:
        cat = st.selectbox("카테고리 컬럼", cat_cols, key="comp_cat")
        val = st.selectbox("값 컬럼 (생략 시 개수)", ["(개수)"] + num_cols, key="comp_val")

        if val == "(개수)":
            vc = df[cat].value_counts().reset_index()
            vc.columns = [cat, "count"]
            fig = px.pie(vc, names=cat, values="count", title=f"📊 {cat} 구성비",
                         color_discrete_sequence=colors, hole=0.4)
        else:
            gb = df.groupby(cat)[val].sum().reset_index()
            fig = px.pie(gb, names=cat, values=val, title=f"📊 {val} by {cat}",
                         color_discrete_sequence=colors, hole=0.4)
        fig.update_traces(textposition="inside", textinfo="percent+label",
                          marker=dict(line=dict(color="white", width=2)))
        fig.update_layout(font=dict(family="Noto Sans KR"), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("카테고리 컬럼이 없습니다.")

def render_comparison(df, num_cols, cat_cols, colors):
    st.markdown("#### 🔍 그룹별 비교")
    if cat_cols and num_cols:
        cat = st.selectbox("그룹 컬럼", cat_cols, key="comp_cat2")
        val = st.selectbox("비교할 값", num_cols, key="comp_val2")

        fig = px.box(df, x=cat, y=val, color=cat, title=f"📊 {cat}별 {val} 비교",
                     template="plotly_white", color_discrete_sequence=colors,
                     notched=True)
        fig.update_layout(font=dict(family="Noto Sans KR"), plot_bgcolor="rgba(0,0,0,0)",
                          showlegend=False, xaxis_title=cat, yaxis_title=val)
        st.plotly_chart(fig, use_container_width=True)

        # 그룹별 통계표
        stats = df.groupby(cat)[val].agg(["mean", "median", "min", "max", "std", "count"])
        stats = stats.round(1).reset_index()
        st.dataframe(stats, use_container_width=True, hide_index=True)
    else:
        st.info("그룹 비교를 위한 카테고리 컬럼이 필요합니다.")

def render_general_summary(df, num_cols, cat_cols, colors):
    st.markdown("#### 📋 데이터 종합 요약")
    col = st.selectbox("분석 컬럼", num_cols, key="gen_col")
    s = df[col].dropna()

    # Describe
    desc = s.describe()
    col_g1, col_g2, col_g3, col_g4 = st.columns(4)
    with col_g1:
        st.markdown(f'<div class="metric-box"><div class="val">{desc["mean"]:.1f}</div><div class="label">평균</div></div>', unsafe_allow_html=True)
    with col_g2:
        st.markdown(f'<div class="metric-box"><div class="val">{desc["50%"]:.1f}</div><div class="label">중앙값</div></div>', unsafe_allow_html=True)
    with col_g3:
        st.markdown(f'<div class="metric-box"><div class="val">{desc["std"]:.1f}</div><div class="label">표준편차</div></div>', unsafe_allow_html=True)
    with col_g4:
        st.markdown(f'<div class="metric-box"><div class="val">{desc["count"]:.0f}</div><div class="label">데이터 수</div></div>', unsafe_allow_html=True)

    # 히스토그램
    fig = px.histogram(df, x=col, nbins=15, title=f"📊 {col} 분포",
                       color_discrete_sequence=[colors[0]], template="plotly_white")
    fig.update_traces(marker_line_color="white", marker_line_width=1.2)
    fig.update_layout(font=dict(family="Noto Sans KR"), plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)

def render_ranking(df, num_cols, cat_cols, colors):
    st.markdown("#### 🏆 순위 분석")
    col = st.selectbox("순위 기준 컬럼", num_cols, key="rank_col")
    label = st.selectbox("레이블 컬럼 (선택)", ["(인덱스)"] + cat_cols, key="rank_label")
    top_n = st.slider("상위 N개", 3, 30, 10, key="rank_n")

    sorted_df = df.sort_values(col, ascending=False).head(top_n).reset_index(drop=True)
    if label == "(인덱스)":
        sorted_df["label"] = sorted_df.index.astype(str)
    else:
        sorted_df["label"] = sorted_df[label].astype(str)

    fig = px.bar(sorted_df, x="label", y=col,
                 title=f"🏆 {col} Top {top_n}",
                 color=col, color_continuous_scale="purples",
                 template="plotly_white", text_auto=True)
    fig.update_layout(font=dict(family="Noto Sans KR"), plot_bgcolor="rgba(0,0,0,0)",
                      xaxis_title=label if label != "(인덱스)" else "항목",
                      yaxis_title=col, showlegend=False)
    fig.update_traces(marker_line_color="white", marker_line_width=1)
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(sorted_df.drop(columns=["label"]), use_container_width=True, hide_index=True)

# ================================================================
# 메인 로직
# ================================================================
col_upload, col_preview = st.columns([1.2, 2.8])

with col_upload:
    uploaded = st.file_uploader("CSV / Excel", type=["csv", "xlsx", "xls"], label_visibility="collapsed")
    if uploaded:
        try:
            if uploaded.name.endswith(".csv"):
                df = pd.read_csv(uploaded)
            else:
                df = pd.read_excel(uploaded)
            st.session_state.df = df
            st.success(f"✅ {df.shape[0]}행 × {df.shape[1]}열")
        except Exception as e:
            st.error(f"오류: {e}")
    if st.session_state.df is not None and st.button("🔄 새로 업로드"):
        st.session_state.df = None
        st.rerun()

if st.session_state.df is None:
    st.info("👈 CSV 또는 Excel 파일을 업로드해주세요.")
    st.stop()

df = st.session_state.df
info = detect_data_type(df)
num_cols, cat_cols = info["num_cols"], info["cat_cols"]
colors = ["#667eea", "#764ba2", "#a78bfa", "#8b5cf6", "#7c3aed",
          "#06b6d4", "#0891b2", "#22d55e", "#16a34a", "#f97316"]

with col_preview:
    st.markdown(f'<div style="display:flex;gap:0.5rem;flex-wrap:wrap;margin-bottom:0.5rem;">', unsafe_allow_html=True)
    detected_names = {"before_after": "🔄 전후비교", "score": "📝 점수/성적", "sales": "💰 매출/실적",
                      "survey": "📋 설문조사", "time_series": "📈 시계열", "hr": "👥 인사",
                      "ratio": "📊 비율", "rank": "🏆 순위"}
    for t in set(info["types"]):
        if t in detected_names:
            st.markdown(f'<span style="background:#667eea20;padding:0.2rem 0.8rem;border-radius:20px;font-size:0.8rem;">{detected_names[t]}</span>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ================================================================
# TAB: 분석 선택
# ================================================================
tab1, tab2, tab3 = st.tabs(["📋 데이터 개요", "🔬 분석하기", "🎨 그래프 스튜디오"])

with tab1:
    st.markdown('<div class="card"><h3>📋 데이터 미리보기</h3>', unsafe_allow_html=True)
    st.dataframe(df.head(500), use_container_width=True, height=350)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card"><h3>📌 컬럼 정보</h3>', unsafe_allow_html=True)
    c_info = pd.DataFrame({
        "컬럼명": df.columns, "타입": df.dtypes.astype(str).values,
        "널(null)": df.isnull().sum().values,
        "널(%)": (df.isnull().sum() / len(df) * 100).round(1).values,
        "고유값": [df[c].nunique() for c in df.columns]
    })
    st.dataframe(c_info, use_container_width=True, hide_index=True)
    st.markdown('</div>', unsafe_allow_html=True)

with tab2:
    if not num_cols:
        st.warning("숫자 컬럼이 없어 분석할 수 없습니다.")
    else:
        # 분석 모드 선택 (자동 추천 포함)
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown(f'<h3>🔬 분석 모드 선택</h3>', unsafe_allow_html=True)

        detected_set = set(info["types"])
        mode_options = {
            "전후 비교": "before_after" in detected_set or bool(info["ba_pairs"]),
            "분포 & 구간": True,
            "그룹별 비교": len(cat_cols) > 0,
            "순위 분석": True,
            "구성비 분석": len(cat_cols) > 0,
            "추세 분석": info["has_date"],
            "종합 요약": True,
        }

        # 추천 뱃지
        default_idx = 0
        mode_list = list(mode_options.keys())
        if "before_after" in detected_set or info["ba_pairs"]:
            default_idx = 0  # 전후 비교가 감지되면 첫번째

        recommended = [m for m, r in mode_options.items() if r]
        st.markdown(f'<div style="font-size:0.85rem;color:#666;margin-bottom:0.8rem;">💡 추천 분석: <b>{"</b> · <b>".join(recommended[:3])}</b></div>', unsafe_allow_html=True)

        analysis_mode = st.radio("분석 모드", [m for m in mode_list if m],
                                 horizontal=True, label_visibility="collapsed")

        st.markdown('</div>', unsafe_allow_html=True)

        # 각 분석 모드 렌더링
        st.markdown('<div class="card">', unsafe_allow_html=True)
        if analysis_mode == "전후 비교":
            render_before_after(df, info["ba_pairs"], colors)
        elif analysis_mode == "분포 & 구간":
            render_distribution(df, num_cols, cat_cols, colors)
        elif analysis_mode == "그룹별 비교":
            render_comparison(df, num_cols, cat_cols, colors)
        elif analysis_mode == "순위 분석":
            render_ranking(df, num_cols, cat_cols, colors)
        elif analysis_mode == "구성비 분석":
            render_composition(df, cat_cols, num_cols, colors)
        elif analysis_mode == "추세 분석":
            render_trend(df, num_cols, cat_cols, colors)
        elif analysis_mode == "종합 요약":
            render_general_summary(df, num_cols, cat_cols, colors)
        st.markdown('</div>', unsafe_allow_html=True)

with tab3:
    st.markdown('<div class="card"><h3>🎨 그래프 스튜디오</h3>', unsafe_allow_html=True)
    col_s1, col_s2 = st.columns([1, 1.5])

    with col_s1:
        chart_type = st.selectbox("차트 종류", [
            "📊 막대", "📈 라인", "🥧 파이", "🔵 산점도",
            "📦 박스플롯", "🌡️ 히트맵", "📊 누적막대", "📈 면적"
        ])
        chart_key = chart_type.split(" ")[-1]
        x_col = st.selectbox("X축", df.columns.tolist())
        if chart_key not in ["파이", "히트맵"]:
            y_col = st.selectbox("Y축 (수치)", num_cols) if num_cols else st.text_input("Y축", disabled=True)
        else:
            y_col = st.selectbox("값", num_cols) if num_cols else None
        color_col = st.selectbox("색상 구분", ["없음"] + df.columns.tolist())
        color_col = None if color_col == "없음" else color_col
        title_text = st.text_input("그래프 제목", placeholder="자동 생성")
        theme = st.selectbox("테마", ["plotly_white", "plotly_dark", "ggplot2", "seaborn"])
        palette = st.selectbox("컬러 팔레트", ["모던 퍼플", "오션 블루", "선셋 오렌지",
                                              "포레스트 그린", "로즈 핑크"])
        pmap = {
            "모던 퍼플": ["#667eea", "#764ba2", "#a78bfa", "#8b5cf6", "#7c3aed"],
            "오션 블루": ["#06b6d4", "#0891b2", "#22d3ee", "#0e7490", "#38bdf8"],
            "선셋 오렌지": ["#f97316", "#ea580c", "#fdba74", "#d97706", "#fb923c"],
            "포레스트 그린": ["#22c55e", "#16a34a", "#4ade80", "#15803d", "#86efac"],
            "로즈 핑크": ["#ec4899", "#db2777", "#f472b6", "#be185d", "#fbcfe8"],
        }
        pcolors = pmap[palette]

    with col_s2:
        generate = st.button("🎯 생성", type="primary", use_container_width=True)
        if generate:
            try:
                cfgs = {
                    "막대": lambda: px.bar(df, x=x_col, y=y_col, color=color_col,
                                           title=title_text or f"{y_col} by {x_col}",
                                           template=theme, text_auto=True, barmode="group",
                                           color_discrete_sequence=pcolors),
                    "라인": lambda: px.line(df, x=x_col, y=y_col, color=color_col,
                                           title=title_text or f"{y_col} 추세",
                                           template=theme, markers=True,
                                           color_discrete_sequence=pcolors),
                    "파이": lambda: px.pie(df, names=x_col, values=y_col,
                                          title=title_text or f"{y_col} 분포",
                                          color_discrete_sequence=pcolors),
                    "산점도": lambda: px.scatter(df, x=x_col, y=y_col, color=color_col,
                                                title=title_text or f"{x_col} vs {y_col}",
                                                template=theme, color_discrete_sequence=pcolors,
                                                hover_data=df.columns),
                    "박스플롯": lambda: px.box(df, x=x_col if df[x_col].dtype == "object" else None,
                                              y=y_col, color=color_col,
                                              title=title_text or "Box Plot",
                                              template=theme, color_discrete_sequence=pcolors),
                    "히트맵": lambda: px.imshow(df.select_dtypes(include="number").corr(),
                                               text_auto=".2f", aspect="auto",
                                               title=title_text or "Correlation",
                                               color_continuous_scale="Purples", template=theme),
                    "누적막대": lambda: px.bar(df, x=x_col, y=y_col, color=color_col,
                                              title=title_text or f"Stacked {y_col}",
                                              template=theme, barmode="stack", text_auto=True,
                                              color_discrete_sequence=pcolors),
                    "면적": lambda: px.area(df, x=x_col, y=y_col, color=color_col,
                                           title=title_text or f"{y_col} Area",
                                           template=theme, color_discrete_sequence=pcolors),
                }
                if chart_key in cfgs:
                    fig = cfgs[chart_key]()
                    fig.update_layout(font=dict(family="Noto Sans KR", size=13),
                                      title_font=dict(size=18), legend_title_text="",
                                      hovermode="x unified",
                                      margin=dict(l=40, r=40, t=60, b=40),
                                      plot_bgcolor="rgba(0,0,0,0)",
                                      paper_bgcolor="rgba(0,0,0,0)")
                    st.plotly_chart(fig, use_container_width=True)
                    col_dl1, col_dl2 = st.columns(2)
                    with col_dl1:
                        hb = fig.to_html(include_plotlyjs="cdn").encode()
                        st.download_button("🌐 HTML 다운로드", data=hb,
                                           file_name=f"{title_text or 'chart'}.html",
                                           mime="text/html", use_container_width=True)
                    with col_dl2:
                        try:
                            import plotly.io as pio
                            png = pio.to_image(fig, format="png", width=1200, height=700, scale=2)
                            st.download_button("📷 PNG 다운로드", data=png,
                                               file_name=f"{title_text or 'chart'}.png",
                                               mime="image/png", use_container_width=True)
                        except Exception:
                            st.info("PNG 저장은 HTML 다운로드 후 브라우저에서 저장해주세요")
            except Exception as e:
                st.error(f"생성 실패: {e}")
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div style="text-align:center;padding:2rem 0;color:#999;font-size:0.8rem;">HY 인사이트 · 데이터는 서버에 저장되지 않습니다</div>', unsafe_allow_html=True)
