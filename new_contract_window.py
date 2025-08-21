import streamlit as st
from api.contract_api import ContractAPI
from azure_.openai_service import AzureOpenAIService

st.title("契約登録・修正")

api = ContractAPI()
openai_service = AzureOpenAIService()

# --- state initialization --------------------------------------------------
if "contract_id" not in st.session_state:
    st.session_state["contract_id"] = None
if "contract_type" not in st.session_state:
    st.session_state["contract_type"] = ""
if "partys" not in st.session_state:
    st.session_state["partys"] = ""
if "background_info" not in st.session_state:
    st.session_state["background_info"] = ""
if "title" not in st.session_state:
    st.session_state["title"] = ""
if "introduction" not in st.session_state:
    st.session_state["introduction"] = ""
if "clauses" not in st.session_state:
    st.session_state["clauses"] = []
if "approval_status" not in st.session_state:
    st.session_state["approval_status"] = "draft"

# --- file upload -----------------------------------------------------------
uploaded = st.file_uploader("契約ファイル選択")
if st.button("解析開始", disabled=uploaded is None):
    st.info("解析処理は未実装です。")

# --- contract type ---------------------------------------------------------
try:
    contract_types = api.get_contract_types()
    type_map = {
        t.get("contract_type", ""): t.get("id")
        for t in contract_types
        if isinstance(t, dict) and t.get("contract_type")
    }
    if not type_map:
        raise ValueError("no contract types")
except Exception:
    type_map = {"汎用": None}

current_type = st.selectbox(
    "契約種別", list(type_map.keys()), key="contract_type"
)

# --- basic information -----------------------------------------------------
st.text_input(
    "契約当事者（カンマ区切り）",
    key="partys",
    placeholder="例: 甲社,乙社",
)
st.text_area("背景情報", height=75, key="background_info")
st.text_input("タイトル", key="title")
st.text_area("前文", height=75, key="introduction")

# --- draft reload ----------------------------------------------------------
try:
    drafts = api.get_draft_contracts()
except Exception:
    drafts = []

draft_map = {
    f"{','.join(d.get('partys', []))}: {d.get('title', '')}": d for d in drafts
}
selected_draft = st.selectbox("ドラフト編集", ["新規"] + list(draft_map.keys()))
if st.button("編集する") and selected_draft != "新規":
    data = draft_map[selected_draft]
    st.session_state.update(
        {
            "contract_id": data.get("id"),
            "contract_type": data.get("contract_type", st.session_state["contract_type"]),
            "partys": ",".join(data.get("partys", [])),
            "background_info": data.get("background_info", ""),
            "title": data.get("title", ""),
            "introduction": data.get("introduction", ""),
            "clauses": data.get("clauses", []),
            "approval_status": data.get("approval_status", "draft"),
        }
    )
    st.experimental_rerun()

# --- approval status -------------------------------------------------------
st.write(f"承認ステータス: {st.session_state['approval_status']}")

# --- clauses ---------------------------------------------------------------
st.subheader("条文")
if st.button("条項追加"):
    st.session_state["clauses"].append(
        {
            "clause_number": "",
            "clause": "",
            "contents_type": "clauses",
            "review_points": "",
            "action_plan": "",
        }
    )

for idx, clause in enumerate(st.session_state["clauses"]):
    st.text_input(
        f"条項番号 {idx + 1}",
        value=clause.get("clause_number", ""),
        key=f"clause_number_{idx}",
    )
    st.text_area(
        f"条文 {idx + 1}", clause.get("clause", ""), key=f"clause_{idx}"
    )
    st.text_area(
        f"審査観点 {idx + 1}",
        clause.get("review_points", ""),
        key=f"review_{idx}",
    )
    st.text_area(
        f"アクションプラン {idx + 1}",
        clause.get("action_plan", ""),
        key=f"action_{idx}",
    )
    st.divider()


def collect_clauses():
    clauses = []
    for idx in range(len(st.session_state["clauses"])):
        clauses.append(
            {
                "clause_number": st.session_state.get(f"clause_number_{idx}", ""),
                "clause": st.session_state.get(f"clause_{idx}", ""),
                "contents_type": "clauses",
                "review_points": st.session_state.get(f"review_{idx}", ""),
                "action_plan": st.session_state.get(f"action_{idx}", ""),
            }
        )
    return clauses


# --- action buttons -------------------------------------------------------
col1, col2, col3 = st.columns(3)
with col1:
    save_clicked = st.button("ナレッジ保存")
with col2:
    apply_clicked = st.button(
        "承認申請", disabled=st.session_state["approval_status"] not in ("draft", "submitted")
    )
with col3:
    approve_clicked = st.button(
        "承認", disabled=st.session_state["approval_status"] != "submitted"
    )

if save_clicked:
    data = {
        "id": st.session_state.get("contract_id"),
        "contract_type": st.session_state["contract_type"],
        "background_info": st.session_state["background_info"],
        "partys": [p.strip() for p in st.session_state["partys"].split(",") if p.strip()],
        "introduction": st.session_state["introduction"],
        "title": st.session_state["title"],
        "clauses": collect_clauses(),
        "approval_status": st.session_state.get("approval_status", "draft"),
        "record_status": "latest",
    }
    try:
        saved = api.upsert_contract(data)
        st.session_state["contract_id"] = saved.get("id", st.session_state["contract_id"])
        st.session_state["approval_status"] = saved.get(
            "approval_status", st.session_state["approval_status"]
        )
        st.success("保存しました")
    except Exception as e:
        st.error(f"保存に失敗しました: {e}")

if apply_clicked and st.session_state.get("contract_id"):
    try:
        contract = api.get_contract_by_id(st.session_state["contract_id"])
        status = contract.get("approval_status")
        contract["approval_status"] = (
            "submitted" if status == "draft" else "draft"
        )
        saved = api.upsert_contract(contract)
        st.session_state["approval_status"] = saved.get("approval_status", status)
        st.success("承認申請を更新しました")
    except Exception as e:
        st.error(f"更新に失敗しました: {e}")

if approve_clicked and st.session_state.get("contract_id"):
    try:
        contract = api.get_contract_by_id(st.session_state["contract_id"])
        contract["approval_status"] = "approved"
        saved = api.upsert_contract(contract)
        st.session_state["approval_status"] = saved.get("approval_status", "approved")
        st.success("承認しました")
    except Exception as e:
        st.error(f"承認に失敗しました: {e}")
