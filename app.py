import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json
import re
import uuid

st.set_page_config(page_title="여행 플래너", layout="wide")

# --- init session state ---
KEYS = ["trips", "current_trip", "page", "amadeus_ok", "gmap_ok"]
for k in KEYS:
    if k not in st.session_state:
        st.session_state[k] = None if k != "trips" else []

# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.title("✈️ 여행 플래너")

    with st.expander("🔑 API 설정", expanded=not st.session_state.amadeus_ok):
        amd_key = st.text_input("Amadeus Client ID", type="password",
                                help="https://developer.amadeus.com → Register → My Apps")
        amd_secret = st.text_input("Amadeus Client Secret", type="password")
        gmap_key = st.text_input("Google Maps API Key", type="password",
                                 help="https://console.cloud.google.com → API 및 서비스 → 사용자 인증 정보")

        if st.button("API 연결 테스트"):
            ok = False
            try:
                from amadeus import Client, ResponseError
                c = Client(client_id=amd_key, client_secret=amd_secret)
                r = c.reference_data.locations.get(subtype="AIRPORT", keyword="ICN")
                if r.data:
                    st.success("Amadeus 연결 성공!")
                    st.session_state.amadeus_ok = True
                    ok = True
            except Exception as e:
                st.error(f"Amadeus 실패: {e}")
                st.session_state.amadeus_ok = False

            if gmap_key:
                import requests
                url = "https://maps.googleapis.com/maps/api/distancematrix/json"
                params = {"origins": "Seoul", "destinations": "Busan",
                          "key": gmap_key}
                r2 = requests.get(url, params=params)
                if r2.status_code == 200 and r2.json().get("status") == "OK":
                    st.success("Google Maps 연결 성공!")
                    st.session_state.gmap_ok = True
                else:
                    st.warning("Google Maps 연결 실패 (키 확인)")
                    st.session_state.gmap_ok = False

            if ok and gmap_key:
                st.session_state.amd_key = amd_key
                st.session_state.amd_secret = amd_secret
                st.session_state.gmap_key = gmap_key

    st.divider()
    st.markdown("### 📁 내 여행")

    for i, t in enumerate(st.session_state.trips):
        if st.button(f"{t['name']} ({t['dates']})", key=f"trip_{i}", use_container_width=True):
            st.session_state.current_trip = i
            st.session_state.page = "일정보기"

    if st.button("➕ 새 여행", use_container_width=True):
        st.session_state.current_trip = None
        st.session_state.page = "새여행"

# ============================================================
# PAGE: API 키 준비 안내
# ============================================================
if not st.session_state.amadeus_ok or not st.session_state.gmap_ok:
    st.markdown("## 🔑 API 키 준비 안내")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### ✈️ Amadeus API")
        st.markdown("""
        1. [Amadeus for Developers](https://developer.amadeus.com) 접속
        2. **Register** → 무료 가입
        3. 로그인 후 **My Apps** → **Create New App**
        4. **API Key**와 **API Secret** 복사
        """)
        st.info("무료 티어: 월 2,000건 요청 가능")

    with col2:
        st.markdown("### 🗺️ Google Maps API")
        st.markdown("""
        1. [Google Cloud Console](https://console.cloud.google.com) 접속
        2. **새 프로젝트 생성**
        3. **API 및 서비스** → **라이브러리**
        4. **Distance Matrix API** 검색 → 사용 설정
        5. **사용자 인증 정보** → **API 키 만들기**
        """)
        st.info("무료 티어: 월 $200 크레딧 (개인 사용 충분)")
        st.markdown("⚠️ **API 키 제한 설정** (필수)")
        st.markdown("API 키 → HTTP 리퍼러 제한에 `*.streamlit.app` 추가")

    st.warning("왼쪽 사이드바에서 API 키를 입력하고 '연결 테스트'를 눌러주세요.")
    st.stop()

# ============================================================
# PAGE: 새 여행 만들기
# ============================================================
if st.session_state.page == "새여행" or st.session_state.current_trip is None:
    st.markdown("## 🧳 새 여행 만들기")

    with st.form("new_trip"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("여행 이름", placeholder="예: 2025 여름 도쿄 여행")
            origin = st.text_input("출발 도시", placeholder="예: 서울")
            dest = st.text_input("도착 도시 (공항코드)", placeholder="예: TYO (도쿄)")
        with col2:
            dep_date = st.date_input("출발일", min_value=datetime.today())
            ret_date = st.date_input("도착일 (돌아오는 날)")
            persons = st.number_input("인원", min_value=1, value=1)

        submitted = st.form_submit_button("여행 생성", type="primary", use_container_width=True)

    if submitted:
        st.session_state.trips.append({
            "id": str(uuid.uuid4())[:8],
            "name": name,
            "origin": origin,
            "dest": dest,
            "dep_date": str(dep_date),
            "ret_date": str(ret_date),
            "persons": persons,
            "flights": [],
            "schedule": {},
            "hotel": ""
        })
        st.session_state.current_trip = len(st.session_state.trips) - 1
        st.success("여행이 생성되었습니다! 항공권을 검색해보세요.")
        st.session_state.page = "일정보기"
        st.rerun()

    st.stop()

# ============================================================
# PAGE: 일정보기 / 관리
# ============================================================
trip = st.session_state.trips[st.session_state.current_trip]
dep = datetime.strptime(trip["dep_date"], "%Y-%m-%d")
ret = datetime.strptime(trip["ret_date"], "%Y-%m-%d")

# Tab navigation
tab1, tab2, tab3, tab4 = st.tabs(["✈️ 항공권 검색", "🗓️ 일정 생성", "📋 내 일정보기", "⚙️ 설정"])

# ============================================================
# TAB 1: 항공권 검색
# ============================================================
with tab1:
    st.markdown(f"### ✈️ {trip['origin']} → {trip['dest']} 항공권 검색")

    with st.form("flight_search"):
        col1, col2, col3 = st.columns(3)
        with col1:
            f_origin = st.text_input("출발지 (공항코드)", trip.get("origin", "").upper())
        with col2:
            f_dest = st.text_input("도착지 (공항코드)", trip.get("dest", "").upper())
        with col3:
            f_date = st.date_input("출발일", dep)
        search = st.form_submit_button("🔍 항공권 검색", type="primary", use_container_width=True)

    if search:
        with st.spinner("항공권 검색 중..."):
            try:
                from amadeus import Client, ResponseError
                amadeus = Client(client_id=st.session_state.amd_key,
                                 client_secret=st.session_state.amd_secret)
                resp = amadeus.shopping.flight_offers_search.get(
                    originLocationCode=f_origin,
                    destinationLocationCode=f_dest,
                    departureDate=f_date.strftime("%Y-%m-%d"),
                    adults=trip["persons"],
                    max=10
                )
                flights = resp.data
                if not flights:
                    st.warning("검색 결과가 없습니다.")
                else:
                    rows = []
                    for f in flights:
                        first_seg = f["itineraries"][0]["segments"][0]
                        last_seg = f["itineraries"][0]["segments"][-1]
                        price = f["price"]["grandTotal"]
                        currency = f["price"]["currency"]
                        dep_time = first_seg["departure"]["at"]
                        arr_time = last_seg["arrival"]["at"]
                        airline = first_seg["carrierCode"]
                        flight_num = first_seg["number"]
                        duration = f["itineraries"][0]["duration"]

                        rows.append({
                            "선택": False,
                            "항공사": airline,
                            "편명": flight_num,
                            "출발": dep_time,
                            "도착": arr_time,
                            "소요시간": duration,
                            "가격": f"{price} {currency}",
                            "경유": len(f["itineraries"][0]["segments"]) - 1,
                            "_raw": json.dumps(f)
                        })

                    df = pd.DataFrame(rows)
                    st.dataframe(df.drop(columns=["_raw"]), use_container_width=True, hide_index=True)

                    st.markdown("#### 항공권 선택")
                    sel_idx = st.number_input("선택할 항공권 번호", min_value=0, max_value=len(rows)-1, value=0)
                    if st.button("이 항공권 선택", type="primary"):
                        trip["flights"] = rows[sel_idx]
                        trip["flights_raw"] = rows[sel_idx]["_raw"]
                        st.success(f"{rows[sel_idx]['항공사']} {rows[sel_idx]['편명']} 선택 완료!")
                        st.rerun()

            except Exception as e:
                st.error(f"검색 실패: {e}")

    if trip.get("flights"):
        st.markdown("---")
        f = trip["flights"]
        st.info(f"✅ 선택된 항공편: **{f['항공사']} {f['편명']}** | {f['출발']} → {f['도착']} | {f['가격']}")

# ============================================================
# TAB 2: 일정 생성
# ============================================================
with tab2:
    st.markdown("### 🗓️ 스마트 일정 생성")

    if not trip.get("flights"):
        st.warning("먼저 '항공권 검색' 탭에서 항공편을 선택해주세요.")
    else:
        f = trip["flights"]
        dep_dt = datetime.fromisoformat(f["출발"].replace("Z", ""))
        arr_dt = datetime.fromisoformat(f["도착"].replace("Z", ""))

        st.markdown(f"**선택된 항공편:** {f['항공사']} {f['편명']}")

        with st.form("schedule_form"):
            col1, col2 = st.columns(2)
            with col1:
                from_where = st.text_input("출발지 주소 (ex: 서울 강남구 역삼동)",
                                           placeholder="집 or 호텔 주소")
                hotel = st.text_input("숙소/목적지 주소", placeholder="도착 후 갈 곳")
            with col2:
                airport_arrival = st.number_input("공항 도착(분 전)", min_value=60, max_value=180, value=120,
                                                  help="출발 몇 분 전에 공항에 도착할지")
                buffer = st.number_input("여유 시간(분)", min_value=0, max_value=120, value=30)

            st.markdown("#### 이동 수단")
            transport = st.selectbox("공항까지 이동 수단", ["대중교통", "자가용", "택시", "리무진", "기타"])

            generate = st.form_submit_button("🚀 일정 자동 생성", type="primary", use_container_width=True)

        if generate and from_where:
            with st.spinner("Google Maps에서 이동 시간 계산 중..."):
                try:
                    import requests
                    gkey = st.session_state.gmap_key

                    # --- 편도: 출발지 → 출발 공항 ---
                    dep_airport_code = trip["dest"]  # Actually need origin airport code
                    origin_airport = trip["origin"]
                    url_dep = "https://maps.googleapis.com/maps/api/distancematrix/json"
                    params_dep = {
                        "origins": from_where,
                        "destinations": f"{origin_airport} Airport",
                        "key": gkey,
                        "language": "ko",
                        "departure_time": "now"
                    }
                    r_dep = requests.get(url_dep, params=params_dep)
                    dep_data = r_dep.json()

                    travel_time_min = 60
                    travel_dist = ""
                    if dep_data["status"] == "OK" and dep_data["rows"][0]["elements"][0]["status"] == "OK":
                        elem = dep_data["rows"][0]["elements"][0]
                        travel_time_min = elem["duration_in_traffic"]["value"] // 60 if "duration_in_traffic" in elem else elem["duration"]["value"] // 60
                        travel_dist = elem["distance"]["text"]

                    # --- 귀도: 도착 공항 → 숙소 ---
                    dest_airport = trip["dest"]
                    url_arr = "https://maps.googleapis.com/maps/api/distancematrix/json"
                    params_arr = {
                        "origins": f"{dest_airport} Airport",
                        "destinations": hotel if hotel else f"{trip['dest']} City Center",
                        "key": gkey,
                        "language": "ko"
                    }
                    r_arr = requests.get(url_arr, params=params_arr)
                    arr_data = r_arr.json()

                    arr_travel_min = 60
                    arr_dist = ""
                    if arr_data["status"] == "OK" and arr_data["rows"][0]["elements"][0]["status"] == "OK":
                        elem = arr_data["rows"][0]["elements"][0]
                        arr_travel_min = elem["duration"]["value"] // 60
                        arr_dist = elem["distance"]["text"]

                    # --- 일정 생성 ---
                    leave_home = dep_dt - timedelta(minutes=travel_time_min + airport_arrival + buffer)
                    arrive_airport = dep_dt - timedelta(minutes=airport_arrival)
                    board_start = dep_dt - timedelta(minutes=40)
                    arrive_dest = arr_dt + timedelta(minutes=arr_travel_min + 30)  # +30 immigration

                    schedule = []

                    # Day -1 items (departure day prep)
                    schedule.append({
                        "day": dep.strftime("%Y-%m-%d"),
                        "time": leave_home.strftime("%H:%M"),
                        "activity": f"🏠 집 출발 (→ {origin_airport} Airport)",
                        "note": f"{transport} · 약 {travel_time_min}분 소요 ({travel_dist})"
                    })
                    schedule.append({
                        "day": dep.strftime("%Y-%m-%d"),
                        "time": arrive_airport.strftime("%H:%M"),
                        "activity": f"🛫 {origin_airport} Airport 도착 (출발 {airport_arrival}분 전)",
                        "note": "체크인 · 수하물 위탁 · 보안 검색"
                    })
                    schedule.append({
                        "day": dep.strftime("%Y-%m-%d"),
                        "time": board_start.strftime("%H:%M"),
                        "activity": f"✈️ 탑승 시작 (편명: {f['편명']})",
                        "note": f"탑승구 확인"
                    })
                    schedule.append({
                        "day": dep.strftime("%Y-%m-%d"),
                        "time": dep_dt.strftime("%H:%M"),
                        "activity": f"✈️ 출발",
                        "note": f"{f['항공사']} {f['편명']}"
                    })
                    schedule.append({
                        "day": dep.strftime("%Y-%m-%d"),
                        "time": arr_dt.strftime("%H:%M"),
                        "activity": f"🛬 {trip['dest']} Airport 도착",
                        "note": "입국 심사 · 수하물 수취"
                    })
                    schedule.append({
                        "day": dep.strftime("%Y-%m-%d"),
                        "time": arrive_dest.strftime("%H:%M"),
                        "activity": f"🏨 숙소/목적지 도착" if hotel else "🏙️ 도시 도착",
                        "note": f"약 {arr_travel_min}분 소요 ({arr_dist})" if arr_dist else ""
                    })

                    trip["schedule"] = {dep.strftime("%Y-%m-%d"): schedule}
                    trip["hotel"] = hotel
                    trip["transport_info"] = {
                        "from_where": from_where,
                        "travel_time_min": travel_time_min,
                        "travel_dist": travel_dist,
                        "arr_travel_min": arr_travel_min,
                        "arr_dist": arr_dist
                    }
                    st.success("일정이 자동 생성되었습니다! '내 일정보기' 탭에서 확인하세요.")
                    st.rerun()

                except Exception as e:
                    st.error(f"일정 생성 실패: {e}")

        elif not from_where and generate:
            st.warning("출발지 주소를 입력해주세요.")

    # Show existing generated schedule preview
    if trip.get("schedule"):
        st.markdown("---")
        st.markdown("#### 📋 현재 저장된 일정")
        for day, items in trip["schedule"].items():
            with st.container(border=True):
                st.markdown(f"**{day}**")
                for item in items:
                    st.markdown(f"- **{item['time']}** | {item['activity']}")

# ============================================================
# TAB 3: 내 일정보기
# ============================================================
with tab3:
    st.markdown(f"### 📋 {trip['name']} 일정")

    if not trip.get("schedule"):
        st.info("아직 일정이 없습니다. '일정 생성' 탭에서 만들어주세요.")
    else:
        col_left, col_right = st.columns([2, 1])

        with col_left:
            for day in sorted(trip["schedule"].keys()):
                items = trip["schedule"][day]
                with st.container(border=True):
                    st.markdown(f"#### 📅 {day}")
                    for idx, item in enumerate(items):
                        col_t, col_a, col_del = st.columns([1.5, 4, 0.5])
                        with col_t:
                            st.markdown(f"**{item['time']}**")
                        with col_a:
                            st.markdown(f"{item['activity']}")
                            if item.get("note"):
                                st.caption(item["note"])
                        with col_del:
                            if st.button("✕", key=f"del_{day}_{idx}"):
                                trip["schedule"][day].pop(idx)
                                st.rerun()

                    # Add item to this day
                    with st.expander("+ 항목 추가"):
                        new_time = st.text_input("시간", value="09:00", key=f"nt_{day}")
                        new_act = st.text_input("내용", key=f"na_{day}")
                        new_note = st.text_input("메모", key=f"nn_{day}")
                        if st.button("추가", key=f"add_{day}"):
                            trip["schedule"][day].append({
                                "time": new_time,
                                "activity": new_act,
                                "note": new_note
                            })
                            st.rerun()

        with col_right:
            st.markdown("#### 📌 요약")
            st.markdown(f"**여행:** {trip['name']}")
            st.markdown(f"**기간:** {trip['dep_date']} ~ {trip['ret_date']}")
            st.markdown(f"**인원:** {trip['persons']}명")

            if trip.get("flights"):
                f = trip["flights"]
                st.markdown(f"**항공:** {f['항공사']} {f['편명']}")
                st.markdown(f"**출발:** {f['출발']}")
                st.markdown(f"**도착:** {f['도착']}")

            if trip.get("hotel"):
                st.markdown(f"**숙소:** {trip['hotel']}")

            if trip.get("transport_info"):
                ti = trip["transport_info"]
                st.markdown(f"**공항 이동:** 약 {ti['travel_time_min']}분")

            st.divider()
            st.markdown("##### 📤 내보내기")
            if st.button("📋 일정 복사"):
                lines = [f"🗓️ {trip['name']}"]
                for day in sorted(trip["schedule"].keys()):
                    lines.append(f"\n📅 {day}")
                    for item in trip["schedule"][day]:
                        lines.append(f"  {item['time']} - {item['activity']}")
                        if item.get("note"):
                            lines.append(f"    💬 {item['note']}")
                text = "\n".join(lines)
                st.code(text, language="text")
                st.info("위 텍스트를 복사해 사용하세요!")

# ============================================================
# TAB 4: 설정
# ============================================================
with tab4:
    st.markdown("### ⚙️ 여행 설정")

    with st.form("edit_trip"):
        col1, col2 = st.columns(2)
        with col1:
            new_name = st.text_input("여행 이름", trip["name"])
            new_origin = st.text_input("출발지", trip.get("origin", ""))
        with col2:
            new_dest = st.text_input("목적지", trip.get("dest", ""))
            new_persons = st.number_input("인원", min_value=1, value=trip.get("persons", 1))
        save = st.form_submit_button("저장", use_container_width=True)

    if save:
        trip["name"] = new_name
        trip["origin"] = new_origin
        trip["dest"] = new_dest
        trip["persons"] = new_persons
        st.success("저장되었습니다!")

    st.divider()
    st.markdown("##### 🗑️ 여행 삭제")
    if st.button("이 여행 삭제", type="secondary", use_container_width=True):
        st.session_state.trips.pop(st.session_state.current_trip)
        st.session_state.current_trip = None
        st.session_state.page = "새여행"
        st.rerun()

    st.divider()
    st.markdown("##### 💾 데이터 관리")
    if st.button("📥 모든 데이터 내보내기"):
        st.download_button(
            label="JSON 다운로드",
            data=json.dumps(st.session_state.trips, ensure_ascii=False, indent=2),
            file_name="travel_data.json",
            mime="application/json"
        )

    uploaded = st.file_uploader("📤 JSON 불러오기", type="json")
    if uploaded:
        try:
            data = json.load(uploaded)
            st.session_state.trips = data
            st.success("불러오기 완료!")
            st.rerun()
        except:
            st.error("파일 형식을 확인해주세요.")
