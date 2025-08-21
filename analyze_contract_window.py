import streamlit as st
from api.contract_api import ContractAPI

st.title("契約審査")

api = ContractAPI()

# --- state initialization --------------------------------------------------
if "exam_contract_type" not in st.session_state:
    st.session_state["exam_contract_type"] = ""
if "exam_partys" not in st.session_state:
    st.session_state["exam_partys"] = ""
if "exam_background" not in st.session_state:
    st.session_state["exam_background"] = ""
if "exam_title" not in st.session_state:
    st.session_state["exam_title"] = ""
if "exam_intro" not in st.session_state:
    st.session_state["exam_intro"] = ""
if "exam_clauses" not in st.session_state:
    st.session_state["exam_clauses"] = []

# --- file upload -----------------------------------------------------------
uploaded = st.file_uploader("契約ファイル選択")
if st.button("解析開始", disabled=uploaded is None):
    st.info("解析処理は未実装です。")

# --- contract type ---------------------------------------------------------
try:
    contract_types = api.get_contract_types()
    type_names = [
        t.get("contract_type")
        for t in contract_types
        if isinstance(t, dict) and t.get("contract_type")
    ]
    if not type_names:
        raise ValueError
except Exception:
    type_names = ["汎用"]

st.selectbox(
    "契約種別", type_names, key="exam_contract_type"
)

# --- basic info ------------------------------------------------------------
st.text_input(
    "契約当事者（カンマ区切り）",
    key="exam_partys",
    placeholder="例: 甲社,乙社",
)
st.text_area("背景情報", height=75, key="exam_background")
st.text_input("タイトル", key="exam_title")
st.text_area("前文", height=75, key="exam_intro")

# --- clauses ---------------------------------------------------------------
st.subheader("条文")
if st.button("条項追加"):
    st.session_state["exam_clauses"].append(
        {
            "clause_number": "",
            "clause": "",
            "review_points": "",
            "action_plan": "",
        }
    )

for idx, clause in enumerate(st.session_state["exam_clauses"]):
    st.text_input(
        f"条項番号 {idx + 1}", clause.get("clause_number", ""), key=f"exam_clause_number_{idx}"
    )
    st.text_area(
        f"条文 {idx + 1}", clause.get("clause", ""), key=f"exam_clause_{idx}"
    )
    st.text_area(
        f"審査結果 {idx + 1}", clause.get("review_points", ""), key=f"exam_review_{idx}"
    )
    st.text_area(
        f"アクションプラン {idx + 1}", clause.get("action_plan", ""), key=f"exam_action_{idx}"
    )
    st.divider()


def collect_exam_clauses():
    data = []
    for idx in range(len(st.session_state["exam_clauses"])):
        data.append(
            {
                "clause_number": st.session_state.get(f"exam_clause_number_{idx}", ""),
                "clause": st.session_state.get(f"exam_clause_{idx}", ""),
                "review_points": st.session_state.get(f"exam_review_{idx}", ""),
                "action_plan": st.session_state.get(f"exam_action_{idx}", ""),
            }
        )
    return data


col1, col2 = st.columns(2)
with col1:
    save_clicked = st.button("一時保存")
with col2:
    exam_clicked = st.button("審査開始")

if save_clicked:
    data = {
        "contract_type": st.session_state["exam_contract_type"],
        "background_info": st.session_state["exam_background"],
        "partys": [p.strip() for p in st.session_state["exam_partys"].split(",") if p.strip()],
        "introduction": st.session_state["exam_intro"],
        "title": st.session_state["exam_title"],
        "clauses": collect_exam_clauses(),
        "approval_status": "draft",
        "record_status": "latest",
    }
    try:
        api.upsert_contract(data)
        st.success("保存しました")
    except Exception as e:
        st.error(f"保存に失敗しました: {e}")

if exam_clicked:
    st.subheader("審査結果")
    for clause in collect_exam_clauses():
        st.markdown(f"#### 条項{clause.get('clause_number','')}")
        try:
            sims = api.search_similar_clauses(clause.get("clause", ""))
            for s in sims:
                st.write(f"- {s.get('clause', '')}")
        except Exception as e:
            st.error(f"検索に失敗しました: {e}")
