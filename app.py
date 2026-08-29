
import streamlit as st
import json, uuid, re, html as html_lib
from pathlib import Path
from datetime import datetime

DATA_FILE = Path(__file__).with_name("opic_data.json")
TYPE_OPTIONS = ["묘사", "과거 경험", "습관", "비교", "롤플레잉", "14번~15번", "기타"]

def load_data():
    if not DATA_FILE.exists():
        DATA_FILE.write_text("[]", encoding="utf-8")
    try:
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []

def save_data(data):
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def normalize_item(item):
    return {
        "id": item.get("id") or str(uuid.uuid4()),
        "topic": item.get("topic") or "미분류",
        "type": item.get("type") or "기타",
        "question": item.get("question") or "",
        "translation": item.get("translation") or "",
        "main_point": item.get("main_point") or item.get("point") or "",
        "key_expressions": item.get("key_expressions") or [],
        "script": item.get("script") or "",
        "updated_at": item.get("updated_at") or datetime.now().isoformat(timespec="seconds")
    }

def parse_json_loose(text):
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\\s*", "", text)
        text = re.sub(r"\\s*```$", "", text)
    s, e = text.find("{"), text.rfind("}")
    if s >= 0 and e > s:
        text = text[s:e+1]
    return json.loads(text)

def analyze_with_openai(question, script, topic_hint, type_hint, api_key, model):
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    instructions = (
        "You are an OPIc speaking-study coach for a Korean learner targeting IH. "
        "Analyze the supplied OPIc question and English script. "
        "Return ONLY valid JSON with keys: topic, type, translation, main_point, key_expressions. "
        "type must be one of 묘사, 과거 경험, 습관, 비교, 롤플레잉, 14번~15번, 기타. "
        "translation must be natural Korean. "
        "main_point must summarize the actual answer flow in Korean using arrows, 2 to 5 steps. "
        "key_expressions must be an array of 3 to 7 objects with expression, meaning, tip. "
        "Expressions must come directly from the user's script and should favor fillers, transitions, reactions, "
        "and memorable IH-friendly spoken phrases. Respect topic/type hints unless clearly wrong."
    )
    prompt = (
        f"Topic hint: {topic_hint}\\n"
        f"Type hint: {type_hint}\\n\\n"
        f"Question:\\n{question}\\n\\n"
        f"Script:\\n{script}"
    )
    response = client.responses.create(model=model, instructions=instructions, input=prompt)
    return parse_json_loose(response.output_text)

st.set_page_config(page_title="OPIc Study Agent", page_icon="🎙️", layout="wide")

st.markdown("""
<style>
.block-container {padding-top: 1.1rem; padding-bottom: 2rem; max-width: 1700px;}
[data-testid="stSidebar"] {min-width: 260px; max-width: 260px;}
.opic-label {font-size:12px;font-weight:700;color:#6b7280;letter-spacing:.05em;margin-bottom:5px;}
.opic-q {font-size:22px;font-weight:750;line-height:1.5;margin-bottom:12px;}
.opic-translation {font-size:15px;line-height:1.72;color:#111827;background:#f3f4f6;padding:14px;border-radius:10px;border:1px solid #d1d5db;}
.opic-point {font-size:16px;font-weight:650;line-height:1.75;color:#111827;background:#dbeafe;border-left:5px solid #2563eb;padding:15px;border-radius:9px;}
.script-box {font-size:19px;line-height:1.72;white-space:pre-wrap;}
.expr {border:1px solid #374151;border-radius:10px;padding:11px 13px;margin-bottom:9px;background:rgba(255,255,255,.03);}
.expr b {font-size:16px;}
.small-muted {color:#9ca3af;font-size:12px;}
.kick {font-weight:800;background:#fde68a;color:#111827;padding:1px 4px;border-radius:4px;}
.ai-ok {display:inline-block;padding:4px 9px;border-radius:999px;background:#dcfce7;color:#166534;font-size:12px;font-weight:700;}
.ai-off {display:inline-block;padding:4px 9px;border-radius:999px;background:#fee2e2;color:#991b1b;font-size:12px;font-weight:700;}
@media (prefers-color-scheme: dark) {
  .opic-translation {color:#f9fafb;background:#1f2937;border-color:#4b5563;}
  .opic-point {color:#eff6ff;background:#1e3a5f;border-left-color:#60a5fa;}
}
</style>
""", unsafe_allow_html=True)

if "data" not in st.session_state:
    st.session_state.data = [normalize_item(x) for x in load_data()]
if "selected_id" not in st.session_state:
    st.session_state.selected_id = st.session_state.data[0]["id"] if st.session_state.data else None
if "mode" not in st.session_state:
    st.session_state.mode = "home"

data = st.session_state.data

with st.sidebar:
    st.title("🎙️ OPIc Agent")
    st.caption("개인용 로컬 학습 도구")
    st.divider()

    topics = ["전체"] + sorted(set(x["topic"] for x in data))
    topic_filter = st.selectbox("주제", topics)
    type_filter = st.selectbox("유형", ["전체"] + TYPE_OPTIONS)
    keyword = st.text_input("검색", placeholder="질문 / 스크립트 / 표현")

    filtered = []
    for x in data:
        exp_blob = " ".join(
            y.get("expression","") + " " + y.get("meaning","")
            for y in x.get("key_expressions", [])
        )
        blob = " ".join([
            x["topic"], x["type"], x["question"], x["translation"],
            x["main_point"], x["script"], exp_blob
        ]).lower()
        if topic_filter != "전체" and x["topic"] != topic_filter:
            continue
        if type_filter != "전체" and x["type"] != type_filter:
            continue
        if keyword.strip() and keyword.strip().lower() not in blob:
            continue
        filtered.append(x)

    st.caption(f"현재 {len(filtered)}개 / 전체 {len(data)}개")

    if st.button("🏠 메인 화면", use_container_width=True):
        st.session_state.mode = "home"
        st.rerun()

    if st.button("➕ 새 스크립트", use_container_width=True, type="primary"):
        st.session_state.mode = "new"
        st.rerun()
    if st.button("📚 학습 화면", use_container_width=True):
        st.session_state.mode = "study"
        st.rerun()

    st.divider()
    st.markdown("**질문 목록**")
    for x in filtered:
        short = x["question"][:42] + ("…" if len(x["question"]) > 42 else "")
        if st.button(f"{x['type']} · {short}", key=f"q_{x['id']}", use_container_width=True):
            st.session_state.selected_id = x["id"]
            st.session_state.mode = "study"
            st.rerun()

    st.divider()
    with st.expander("⚙️ AI 설정", expanded=False):
        api_key = st.text_input("OpenAI API Key", type="password", help="키는 이 실행 세션에서만 사용하며 데이터 파일에 저장하지 않습니다.")
        model = st.selectbox("Model", ["gpt-5.6-luna", "gpt-5.6-terra", "gpt-5.6-sol"], index=0)
        if api_key:
            st.markdown('<span class="ai-ok">● API Key 입력됨</span>', unsafe_allow_html=True)
            if st.button("AI 연결 테스트", use_container_width=True):
                try:
                    from openai import OpenAI
                    client = OpenAI(api_key=api_key)
                    test = client.responses.create(model=model, input="Reply with exactly: OK")
                    if "OK" in test.output_text:
                        st.success("OpenAI API 연결 성공")
                    else:
                        st.info("API 응답을 받았습니다.")
                except Exception as e:
                    st.error(f"연결 실패: {e}")
        else:
            st.markdown('<span class="ai-off">● API Key 미입력</span>', unsafe_allow_html=True)
        st.caption("AI 기능: 질문 해석 · Main Point · 중요 표현 자동 생성")

    with st.expander("💾 백업 / 가져오기"):
        export_obj = {"version": 1, "scripts": data}
        st.download_button(
            "JSON 백업 다운로드",
            data=json.dumps(export_obj, ensure_ascii=False, indent=2),
            file_name="OPIc_Agent_Backup.json",
            mime="application/json",
            use_container_width=True
        )
        up = st.file_uploader("JSON 가져오기", type=["json"])
        if up is not None:
            try:
                obj = json.load(up)
                arr = obj if isinstance(obj, list) else obj.get("scripts", [])
                if st.button("가져오기 실행", use_container_width=True):
                    existing = {x["id"]: x for x in data}
                    for raw in arr:
                        item = normalize_item(raw)
                        existing[item["id"]] = item
                    st.session_state.data = list(existing.values())
                    save_data(st.session_state.data)
                    st.rerun()
            except Exception:
                st.error("올바른 JSON 파일이 아닙니다.")


if st.session_state.mode == "home":
    st.title("🏠 OPIc Study Agent")
    st.caption("전체 스크립트를 한눈에 보고 원하는 주제로 바로 이동하세요.")

    total_scripts = len(data)
    topic_counts = {}
    type_counts = {}
    for item in data:
        topic_counts[item["topic"]] = topic_counts.get(item["topic"], 0) + 1
        type_counts[item["type"]] = type_counts.get(item["type"], 0) + 1

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("전체 스크립트", total_scripts)
    with m2:
        st.metric("전체 주제", len(topic_counts))
    with m3:
        st.metric("가장 많은 주제", max(topic_counts, key=topic_counts.get) if topic_counts else "-")
    with m4:
        st.metric("가장 많은 유형", max(type_counts, key=type_counts.get) if type_counts else "-")

    st.divider()
    st.subheader("📚 주제별 바로가기")

    if topic_counts:
        topics_sorted = sorted(topic_counts.items(), key=lambda x: (-x[1], x[0]))
        cols = st.columns(4)
        for i, (topic, count) in enumerate(topics_sorted):
            with cols[i % 4]:
                st.markdown(
                    f"""
                    <div style="
                        border:1px solid #374151;
                        border-radius:14px;
                        padding:14px 16px 10px 16px;
                        margin-bottom:6px;
                        min-height:84px;">
                        <div style="font-size:20px;font-weight:800;">{topic}</div>
                        <div style="font-size:13px;color:#9ca3af;margin-top:5px;">스크립트 {count}개</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                if st.button(f"{topic} 열기", key=f"home_topic_{topic}", use_container_width=True):
                    topic_items = [x for x in data if x["topic"] == topic]
                    if topic_items:
                        st.session_state.selected_id = topic_items[0]["id"]
                        st.session_state.home_topic = topic
                        st.session_state.mode = "topic"
                        st.rerun()
    else:
        st.info("아직 등록된 스크립트가 없습니다.")

    st.divider()
    left_home, right_home = st.columns([1.2, 1])

    with left_home:
        st.subheader("🕘 최근 스크립트")
        recent = sorted(data, key=lambda x: x.get("updated_at",""), reverse=True)[:8]
        if recent:
            for item in recent:
                q = item["question"]
                q_short = q[:75] + ("…" if len(q) > 75 else "")
                if st.button(
                    f"{item['topic']} · {item['type']}  |  {q_short}",
                    key=f"recent_{item['id']}",
                    use_container_width=True
                ):
                    st.session_state.selected_id = item["id"]
                    st.session_state.mode = "study"
                    st.rerun()

    with right_home:
        st.subheader("📊 유형별 현황")
        if type_counts:
            for t, count in sorted(type_counts.items(), key=lambda x: (-x[1], x[0])):
                st.write(f"**{t}**  ·  {count}개")
        st.write("")
        if st.button("전체 질문 목록 보기", use_container_width=True):
            st.session_state.mode = "all"
            st.rerun()

elif st.session_state.mode == "topic":
    topic = st.session_state.get("home_topic", "")
    topic_items = [x for x in data if x["topic"] == topic]

    top_a, top_b = st.columns([5,1])
    with top_a:
        st.title(f"📚 {topic}")
        st.caption(f"{topic} 주제의 스크립트 {len(topic_items)}개")
    with top_b:
        if st.button("← 메인", use_container_width=True):
            st.session_state.mode = "home"
            st.rerun()

    if not topic_items:
        st.info("이 주제에는 스크립트가 없습니다.")
    else:
        type_groups = {}
        for item in topic_items:
            type_groups.setdefault(item["type"], []).append(item)

        for t in TYPE_OPTIONS:
            items = type_groups.get(t, [])
            if not items:
                continue
            st.subheader(f"{t} · {len(items)}개")
            for item in items:
                q_short = item["question"][:100] + ("…" if len(item["question"]) > 100 else "")
                c1, c2 = st.columns([5,1])
                with c1:
                    st.markdown(f"**{q_short}**")
                    if item.get("translation"):
                        st.caption(item["translation"])
                with c2:
                    if st.button("열기", key=f"topic_open_{item['id']}", use_container_width=True):
                        st.session_state.selected_id = item["id"]
                        st.session_state.mode = "study"
                        st.rerun()
                st.divider()

elif st.session_state.mode == "all":
    st.title("🗂️ 전체 질문 목록")
    st.caption(f"전체 {len(data)}개 스크립트")

    c_back, c_space = st.columns([1,5])
    with c_back:
        if st.button("← 메인", use_container_width=True):
            st.session_state.mode = "home"
            st.rerun()

    groups = {}
    for item in sorted(data, key=lambda x: (x["topic"], x["type"], x["question"])):
        groups.setdefault(item["topic"], []).append(item)

    for topic, items in groups.items():
        with st.expander(f"{topic} · {len(items)}개", expanded=False):
            for item in items:
                q_short = item["question"][:110] + ("…" if len(item["question"]) > 110 else "")
                c1, c2 = st.columns([5,1])
                with c1:
                    st.markdown(f"**[{item['type']}] {q_short}**")
                    if item.get("translation"):
                        st.caption(item["translation"])
                with c2:
                    if st.button("열기", key=f"all_open_{item['id']}", use_container_width=True):
                        st.session_state.selected_id = item["id"]
                        st.session_state.mode = "study"
                        st.rerun()

if st.session_state.mode == "new":
    st.title("새 OPIc 스크립트")
    st.caption("질문과 스크립트만 넣고 AI 분석을 누르면 질문 해석, Main Point, 중요 표현이 자동 생성됩니다.")

    c1, c2 = st.columns(2)
    with c1:
        new_topic = st.text_input("주제", placeholder="예: 카페")
    with c2:
        new_type = st.selectbox("유형", TYPE_OPTIONS)

    new_question = st.text_area("질문", height=110, placeholder="OPIc question")
    new_script = st.text_area("스크립트", height=360, placeholder="영어 스크립트 전체")

    a, b = st.columns(2)
    with a:
        analyze = st.button("✨ AI로 분석해서 추가", type="primary", use_container_width=True)
    with b:
        manual = st.button("그냥 저장", use_container_width=True)

    if analyze:
        if not new_question.strip() or not new_script.strip():
            st.warning("질문과 스크립트를 입력해 주세요.")
        elif not api_key:
            st.warning("왼쪽 AI 설정에서 OpenAI API Key를 입력해 주세요.")
        else:
            with st.spinner("학습 정보를 분석 중입니다..."):
                try:
                    result = analyze_with_openai(
                        new_question, new_script, new_topic, new_type, api_key, model
                    )
                    item = normalize_item({
                        "id": str(uuid.uuid4()),
                        "topic": result.get("topic") or new_topic or "미분류",
                        "type": result.get("type") or new_type,
                        "question": new_question.strip(),
                        "translation": result.get("translation",""),
                        "main_point": result.get("main_point",""),
                        "key_expressions": result.get("key_expressions",[]),
                        "script": new_script.strip()
                    })
                    st.session_state.data.append(item)
                    save_data(st.session_state.data)
                    st.session_state.selected_id = item["id"]
                    st.session_state.mode = "study"
                    st.rerun()
                except Exception as e:
                    st.error(f"AI 분석에 실패했습니다: {e}")

    if manual:
        item = normalize_item({
            "id": str(uuid.uuid4()),
            "topic": new_topic or "미분류",
            "type": new_type,
            "question": new_question.strip(),
            "script": new_script.strip()
        })
        st.session_state.data.append(item)
        save_data(st.session_state.data)
        st.session_state.selected_id = item["id"]
        st.session_state.mode = "study"
        st.rerun()

else:
    if not data:
        st.info("아직 스크립트가 없습니다. 왼쪽에서 새 스크립트를 추가해 주세요.")
        st.stop()

    selected = next((x for x in data if x["id"] == st.session_state.selected_id), None)
    if not selected:
        selected = filtered[0] if filtered else data[0]
        st.session_state.selected_id = selected["id"]

    top1, top2, top3 = st.columns([5,1,1])
    with top1:
        st.title(f"{selected['topic']} · {selected['type']}")
        st.caption("질문 → 해석 → Main Point → 중요 표현 → Script 순서로 학습하세요.")
    with top2:
        if st.button("🏠 메인", use_container_width=True):
            st.session_state.mode = "home"
            st.rerun()
    with top3:
        if st.button("🗑️ 삭제", use_container_width=True):
            st.session_state.data = [x for x in data if x["id"] != selected["id"]]
            save_data(st.session_state.data)
            st.session_state.selected_id = st.session_state.data[0]["id"] if st.session_state.data else None
            st.rerun()

    left, right = st.columns([0.92, 1.35], gap="large")

    with left:
        st.markdown('<div class="opic-label">QUESTION</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="opic-q">{selected["question"]}</div>', unsafe_allow_html=True)

        st.markdown('<div class="opic-label">질문 해석</div>', unsafe_allow_html=True)
        translation = selected["translation"] or "아직 질문 해석이 없습니다. AI 자동 보완을 실행해 주세요."
        st.markdown(f'<div class="opic-translation">{translation}</div>', unsafe_allow_html=True)

        st.write("")
        st.markdown('<div class="opic-label">MAIN POINT</div>', unsafe_allow_html=True)
        point = selected["main_point"] or "아직 Main Point가 없습니다. AI 자동 보완을 실행해 주세요."
        st.markdown(f'<div class="opic-point">{point}</div>', unsafe_allow_html=True)

        st.write("")
        st.markdown("### ⭐ 중요 표현")
        expressions = selected.get("key_expressions", [])
        if expressions:
            for ex in expressions:
                expr_html = (
                    '<div class="expr"><b>' + ex.get("expression","") + '</b><br>'
                    + ex.get("meaning","")
                    + '<br><span class="small-muted">' + ex.get("tip","")
                    + '</span></div>'
                )
                st.markdown(expr_html, unsafe_allow_html=True)
        else:
            st.info("아직 중요 표현이 없습니다. AI 자동 보완을 사용하면 추출됩니다.")

    with right:
        st.markdown("### 📖 Script")
        safe_script = html_lib.escape(selected["script"])
        for ex in sorted(selected.get("key_expressions", []), key=lambda z: len(z.get("expression","")), reverse=True):
            phrase = ex.get("expression","").strip()
            if phrase:
                escaped_phrase = html_lib.escape(phrase)
                safe_script = safe_script.replace(escaped_phrase, f'<span class="kick">{escaped_phrase}</span>')
        st.markdown(f'<div class="script-box">{safe_script}</div>', unsafe_allow_html=True)

        st.divider()
        st.markdown("#### 🤖 이 스크립트 빠른 작업")

        if st.button("질문 해석 / Main Point / 중요 표현 자동 보완", use_container_width=True):
            if not api_key:
                st.warning("왼쪽 AI 설정에 API Key를 입력해 주세요.")
            else:
                with st.spinner("학습 정보를 보완 중입니다..."):
                    try:
                        result = analyze_with_openai(
                            selected["question"], selected["script"],
                            selected["topic"], selected["type"], api_key, model
                        )
                        selected.update({
                            "topic": result.get("topic") or selected["topic"],
                            "type": result.get("type") or selected["type"],
                            "translation": result.get("translation",""),
                            "main_point": result.get("main_point",""),
                            "key_expressions": result.get("key_expressions",[]),
                            "updated_at": datetime.now().isoformat(timespec="seconds")
                        })
                        save_data(data)
                        st.rerun()
                    except Exception as e:
                        st.error(f"분석 실패: {e}")

        with st.expander("✏️ 직접 수정"):
            e_topic = st.text_input("주제", value=selected["topic"], key=f"topic_{selected['id']}")
            type_index = TYPE_OPTIONS.index(selected["type"]) if selected["type"] in TYPE_OPTIONS else len(TYPE_OPTIONS)-1
            e_type = st.selectbox("유형", TYPE_OPTIONS, index=type_index, key=f"type_{selected['id']}")
            e_q = st.text_area("질문", value=selected["question"], key=f"question_{selected['id']}")
            e_t = st.text_area("질문 해석", value=selected["translation"], key=f"translation_{selected['id']}")
            e_m = st.text_area("Main Point", value=selected["main_point"], key=f"main_{selected['id']}")
            e_s = st.text_area("Script", value=selected["script"], height=300, key=f"script_{selected['id']}")
            if st.button("수정 내용 저장", type="primary", use_container_width=True):
                selected.update({
                    "topic": e_topic,
                    "type": e_type,
                    "question": e_q,
                    "translation": e_t,
                    "main_point": e_m,
                    "script": e_s,
                    "updated_at": datetime.now().isoformat(timespec="seconds")
                })
                save_data(data)
                st.rerun()
