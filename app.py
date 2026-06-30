import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO
import base64

st.set_page_config(page_title="데이터 시각화 대시보드", layout="wide")
st.title("📊 데이터 시각화 대시보드")
st.markdown("CSV 또는 Excel 파일을 업로드하고 예쁜 그래프를 만들어보세요.")

# ---------- Session ----------
if "df" not in st.session_state:
    st.session_state.df = None
if "chart_history" not in st.session_state:
    st.session_state.chart_history = []

# ---------- File Upload ----------
col_upload, col_preview = st.columns([1, 2])

with col_upload:
    uploaded = st.file_uploader("파일 업로드 (CSV / Excel)", type=["csv", "xlsx", "xls"])
    if uploaded:
        try:
            if uploaded.name.endswith(".csv"):
                df = pd.read_csv(uploaded)
            else:
                df = pd.read_excel(uploaded)
            st.session_state.df = df
            st.success(f"불러오기 완료! ({df.shape[0]}행 x {df.shape[1]}열)")
        except Exception as e:
            st.error(f"파일 읽기 실패: {e}")

with col_preview:
    if st.session_state.df is not None:
        df = st.session_state.df
        with st.expander("📋 데이터 미리보기", expanded=True):
            st.dataframe(df.head(100), use_container_width=True, height=250)
        with st.expander("📊 컬럼 정보"):
            info = pd.DataFrame({
                "컬럼명": df.columns,
                "데이터타입": df.dtypes.values,
                "널(null)": df.isnull().sum().values,
                "고유값": [df[c].nunique() for c in df.columns]
            })
            st.dataframe(info, use_container_width=True, hide_index=True)

# ---------- Chart Create ----------
if st.session_state.df is not None:
    df = st.session_state.df
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    all_cols = df.columns.tolist()
    cat_cols = [c for c in all_cols if c not in numeric_cols]

    st.divider()
    st.markdown("## 🎨 그래프 생성")

    with st.container(border=True):
        col1, col2, col3 = st.columns(3)

        with col1:
            chart_type = st.selectbox("차트 종류", [
                "📊 막대 그래프", "📈 라인 그래프", "🥧 파이 차트",
                "🔵 산점도", "📦 박스 플롯", "🌡️ 히트맵",
                "📊 누적 막대", "📈 면적 그래프", "🎯 버블 차트"
            ])

        with col2:
            if "파이" in chart_type or "히트맵" in chart_type:
                x_col = st.selectbox("레이블 (카테고리)", all_cols)
            else:
                x_col = st.selectbox("X축", all_cols)

            if "박스" in chart_type:
                y_col = st.multiselect("Y축 (수치)", numeric_cols, default=numeric_cols[:min(3, len(numeric_cols))])
            else:
                y_col = st.selectbox("Y축 (수치)", numeric_cols) if numeric_cols else st.text_input("Y축", disabled=True)

        with col3:
            color_col = st.selectbox("색상 구분 (선택)", ["없음"] + all_cols)
            color_col = None if color_col == "없음" else color_col

            if "버블" in chart_type:
                size_col = st.selectbox("크기 (수치)", numeric_cols) if numeric_cols else None
            else:
                size_col = None

    col_style1, col_style2, col_style3 = st.columns(3)
    with col_style1:
        chart_title = st.text_input("그래프 제목", value="", placeholder="자동 생성")
    with col_style2:
        color_theme = st.selectbox("색상 테마", [
            "plasma", "viridis", "magma", "inferno", "turbo",
            "Blues", "Reds", "Greens", "Portland", "Rainbow",
            "Jet", "Hot", "Electric"
        ])
    with col_style3:
        template = st.selectbox("스타일 템플릿", [
            "plotly_dark", "plotly_white", "ggplot2", "seaborn",
            "simple_white", "presentation", "xgridoff", "gridon"
        ])

    # ---------- Generate ----------
    if st.button("🎯 그래프 생성", type="primary", use_container_width=True):
        fig = None
        ct = chart_type.split(" ")[-1]

        try:
            if "막대" in chart_type:
                fig = px.bar(df, x=x_col, y=y_col, color=color_col,
                             title=chart_title or f"{y_col} by {x_col}",
                             color_continuous_scale=color_theme, template=template,
                             barmode="group", text_auto=True)

            elif "라인" in chart_type:
                fig = px.line(df, x=x_col, y=y_col, color=color_col,
                              title=chart_title or f"{y_col} Trend",
                              color_continuous_scale=color_theme, template=template,
                              markers=True)

            elif "파이" in chart_type:
                fig = px.pie(df, names=x_col, values=y_col,
                             title=chart_title or f"{y_col} Distribution",
                             color_discrete_sequence=px.colors.sequential.__dict__[color_theme.upper()] if hasattr(px.colors.sequential, color_theme.upper()) else None)

            elif "산점" in chart_type:
                fig = px.scatter(df, x=x_col, y=y_col, color=color_col, size=size_col,
                                 title=chart_title or f"{x_col} vs {y_col}",
                                 color_continuous_scale=color_theme, template=template,
                                 hover_data=df.columns)

            elif "박스" in chart_type:
                fig = px.box(df, x=x_col if df[x_col].dtype == "object" else None,
                             y=y_col, color=color_col,
                             title=chart_title or "Box Plot",
                             color_continuous_scale=color_theme, template=template)

            elif "히트맵" in chart_type:
                corr = df.select_dtypes(include="number").corr()
                fig = px.imshow(corr, text_auto=".2f", aspect="auto",
                                title=chart_title or "Correlation Heatmap",
                                color_continuous_scale=color_theme, template=template)

            elif "누적" in chart_type:
                fig = px.bar(df, x=x_col, y=y_col, color=color_col,
                             title=chart_title or f"Stacked {y_col}",
                             color_continuous_scale=color_theme, template=template,
                             barmode="stack", text_auto=True)

            elif "면적" in chart_type:
                fig = px.area(df, x=x_col, y=y_col, color=color_col,
                              title=chart_title or f"{y_col} Area",
                              color_continuous_scale=color_theme, template=template)

            elif "버블" in chart_type:
                fig = px.scatter(df, x=x_col, y=y_col, size=size_col, color=color_col,
                                 title=chart_title or "Bubble Chart",
                                 color_continuous_scale=color_theme, template=template,
                                 size_max=60, hover_data=df.columns)

            if fig:
                fig.update_layout(
                    title_font_size=20,
                    legend_title_text="",
                    hovermode="x unified",
                    margin=dict(l=40, r=40, t=60, b=40)
                )
                st.session_state.current_fig = fig
                st.session_state.current_title = chart_title or ""
                st.success("그래프 생성 완료!")

        except Exception as e:
            st.error(f"그래프 생성 실패: {e}")

    # ---------- Display & Export ----------
    if st.session_state.get("current_fig") is not None:
        fig = st.session_state.current_fig
        st.plotly_chart(fig, use_container_width=True)

        col_exp1, col_exp2, col_exp3 = st.columns(3)

        with col_exp1:
            img_bytes = fig.to_image(format="png", width=1200, height=700, scale=2)
            st.download_button(
                label="📷 PNG 이미지 다운로드",
                data=img_bytes,
                file_name=f"chart_{st.session_state.current_title or 'graph'}.png",
                mime="image/png",
                use_container_width=True
            )

        with col_exp2:
            html_bytes = fig.to_html(include_plotlyjs="cdn").encode()
            st.download_button(
                label="🌐 HTML 다운로드 (인터랙티브)",
                data=html_bytes,
                file_name=f"chart_{st.session_state.current_title or 'graph'}.html",
                mime="text/html",
                use_container_width=True
            )

        with col_exp3:
            csv_data = df.to_csv(index=False).encode()
            st.download_button(
                label="📄 CSV 다운로드 (원본 데이터)",
                data=csv_data,
                file_name="data.csv",
                mime="text/csv",
                use_container_width=True
            )

        if st.button("📋 내보낸 그래프 저장하기"):
            st.session_state.chart_history.append({
                "title": st.session_state.current_title,
                "fig": fig
            })
            st.success("저장 완료!")

    # ---------- Chart History ----------
    if st.session_state.chart_history:
        st.divider()
        st.markdown("### 📂 저장된 그래프")
        for i, c in enumerate(st.session_state.chart_history):
            with st.expander(f"📊 {c['title'] or 'Graph'} #{i+1}"):
                st.plotly_chart(c["fig"], use_container_width=True)
                buf = c["fig"].to_image(format="png", width=1200, height=700, scale=2)
                st.download_button(
                    label="📷 다운로드",
                    data=buf,
                    file_name=f"chart_{i}.png",
                    mime="image/png",
                    key=f"history_dl_{i}"
                )

else:
    st.info("👈 CSV 또는 Excel 파일을 업로드해주세요.")

st.divider()
st.caption("데이터는 서버에 저장되지 않으며, 세션 내에서만 처리됩니다.")
