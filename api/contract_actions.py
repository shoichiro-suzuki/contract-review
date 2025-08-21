from PySide6.QtWidgets import QMessageBox
import uuid
from datetime import datetime, timedelta, timezone


def save_draft_api(
    api,
    settings,
    contract_type_combo,
    background_info_edit,
    partys_edit,
    introduction_edit,
    title_edit,
    clauses_layout,
    intro_label,
    introduction_edit_widget,
    parent=None,
):
    # JSTタイムゾーンを定義
    JST = timezone(timedelta(hours=9))
    now_jst = datetime.now(JST)
    contract_type_id = contract_type_combo.currentData()
    background_info = background_info_edit.toPlainText()
    partys_text = partys_edit.text().strip()
    partys = [p.strip() for p in partys_text.split(",") if p.strip()]
    introduction = introduction_edit.toPlainText()
    if not contract_type_id or not partys or not background_info.strip():
        raise ValueError("契約種別、契約当事者および背景情報は必須です")
    master_id = settings.value("contract_master_id", type=str)
    if not master_id:
        master_id = str(uuid.uuid4())
    existing = api.get_contract_by_id(master_id)
    clauses = []
    for i in range(clauses_layout.count()):
        clause_widget = clauses_layout.itemAt(i).widget()
        if (
            clause_widget is None
            or clause_widget == introduction_edit_widget
            or clause_widget == intro_label
        ):
            continue
        from PySide6.QtWidgets import QTextEdit, QLineEdit, QWidget

        text_edits = clause_widget.findChildren(QTextEdit)
        radio_widget = next(
            (
                w
                for w in clause_widget.findChildren(QWidget)
                if hasattr(w, "button_group")
            ),
            None,
        )
        if not text_edits or not radio_widget:
            continue
        clause_number = clause_widget.findChild(QLineEdit)
        clause_text = text_edits[0].toPlainText()
        checked_button = radio_widget.button_group.checkedButton()
        content_type = checked_button.text() if checked_button else "clauses"
        review_points = text_edits[1].toPlainText() if len(text_edits) > 1 else ""
        action_plan = text_edits[2].toPlainText() if len(text_edits) > 2 else ""
        if (review_points and not action_plan) or (action_plan and not review_points):
            QMessageBox.warning(
                parent,
                "入力エラー",
                "審査観点とアクションプランは両方入力する必要があります。どちらか一方のみの入力はできません。",
            )
            return False
        if not clause_text.strip():
            continue
        clause_id = getattr(clause_widget, "clause_id", None)
        if not clause_id:
            clause_id = str(uuid.uuid4())
        clause_widget.clause_id = clause_id
        clause_obj = {
            "clause_id": clause_id,
            "clause_number": clause_number.text(),
            "clause": clause_text,
            "contents_type": content_type,
            "review_points": review_points,
            "action_plan": action_plan,
            "created_at": (
                existing["clauses"][i]["created_at"]
                if existing
                and "clauses" in existing
                and len(existing["clauses"]) > i
                and "created_at" in existing["clauses"][i]
                else now_jst.isoformat()
            ),
            "updated_at": now_jst.isoformat(),
        }
        clauses.append(clause_obj)
    master_data = {
        "id": master_id,
        "contract_type_id": contract_type_id,
        "partys": partys,
        "title": title_edit.text().strip(),
        "background_info": background_info,
        "introduction": introduction,
        "approval_status": "draft",
        "record_status": "latest",
        "created_at": (
            existing["created_at"]
            if existing and "created_at" in existing
            else now_jst.isoformat()
        ),
        "updated_at": now_jst.isoformat(),
        "clauses": clauses,
    }
    settings.setValue("contract_master_id", master_id)
    api.upsert_contract(master_data)
    return True


def apply_for_approval_api(api, settings, parent=None):
    contract_id = settings.value("contract_master_id", type=str)
    if not contract_id:
        QMessageBox.warning(parent, "エラー", "契約情報が保存されていません")
        return False
    master_data = api.get_contract_by_id(contract_id)
    if not master_data:
        QMessageBox.warning(parent, "エラー", "契約情報が見つかりません")
        return False
    master_data["approval_status"] = "submitted"
    api.upsert_contract(master_data)
    return True


def approve_contract_api(api, settings, parent=None):
    contract_id = settings.value("contract_master_id", type=str)
    if not contract_id:
        QMessageBox.warning(parent, "エラー", "契約情報が保存されていません")
        return False
    master_data = api.get_contract_by_id(contract_id)
    if not master_data:
        QMessageBox.warning(parent, "エラー", "契約情報が見つかりません")
        return False
    master_data["approval_status"] = "approved"
    api.upsert_contract(master_data)
    return True


def convert_to_vectors_api(
    api,
    openai_service,
    settings,
    clauses_layout,
    intro_label,
    introduction_edit,
    title_edit,
    parent=None,
    spinner_label=None,
    spinner_movie=None,
):
    # まず現在の内容を保存
    ok = save_draft_api(
        api,
        settings,
        parent.contract_type_combo,
        parent.background_info,
        parent.partys_edit,
        parent.introduction_edit,
        parent.title_edit,
        parent.clauses_layout,
        parent.intro_label,
        parent.introduction_edit,
        parent,
    )
    if not ok:
        return False
    # スピナー表示
    if spinner_label and spinner_movie:
        spinner_label.setVisible(True)
        spinner_movie.start()
    QApplication = None
    try:
        from PySide6.QtWidgets import QApplication as _QApp

        QApplication = _QApp.instance()
    except Exception:
        pass
    if QApplication:
        QApplication.processEvents()
    contract_id = settings.value("contract_master_id", type=str)
    if not contract_id:
        raise ValueError("契約情報が保存されていません")
    from PySide6.QtWidgets import QTextEdit, QWidget

    for i in range(clauses_layout.count()):
        clause_widget = clauses_layout.itemAt(i).widget()
        if (
            clause_widget is None
            or clause_widget == introduction_edit
            or clause_widget == intro_label
            or clause_widget == title_edit
        ):
            continue
        clause_id = getattr(clause_widget, "clause_id", None)
        if not clause_id:
            continue
        text_edits = clause_widget.findChildren(QTextEdit)
        if not text_edits or len(text_edits) < 3:
            continue
        clause_text = text_edits[0].toPlainText()
        review_points = text_edits[1].toPlainText()
        action_plan = text_edits[2].toPlainText()
        if not review_points and not action_plan:
            continue
        clause_vector = (
            openai_service.get_emb_3_small(clause_text) if clause_text else None
        )
        review_points_vector = (
            openai_service.get_emb_3_small(review_points)
            if review_points
            else None
        )
        action_vector = (
            openai_service.get_emb_3_small(action_plan) if action_plan else None
        )
        clause_entry = {
            "id": clause_id,
            "contract_id": contract_id,
            "clause": clause_text,
            "review_points": review_points,
            "action_plan": action_plan,
            "clause_vector": clause_vector,
            "review_points_vector": review_points_vector,
            "action_plan_vector": action_vector,
        }
        api.upsert_clause_entry(clause_entry)
    if spinner_movie and spinner_label:
        spinner_movie.stop()
        spinner_label.setVisible(False)
    return True


def display_draft_clauses_data(clauses, title=None, introduction=None):
    """
    ドラフトデータ用の整形と共通描画呼び出し用データを返す
    """
    title_text = title.replace("　", "") if title else ""
    # ドラフトは"clause"キーが主、なければ"text"を見る
    for c in clauses:
        if "clause" not in c and "text" in c:
            c["clause"] = c["text"]
    return title_text, introduction, clauses


def display_document_content_data(content):
    """
    ファイルアップロード時のデータ整形と共通描画呼び出し用データを返す
    """
    title_text = content["title"].replace("　", "") if content.get("title") else ""
    introduction = content.get("introduction", "")
    clauses = content.get("clauses", [])
    # ファイルは"text"キーが主、なければ"clause"を見る
    for c in clauses:
        if "text" not in c and "clause" in c:
            c["text"] = c["clause"]
    # signature_sectionを追加
    if content.get("signature_section"):
        clauses.append(
            {
                "clause_number": "-",
                "clause": content["signature_section"],
                "contents_type": "signature_section",
                "review_points": "",
                "action_plan": "",
            }
        )
    # attachmentsがリストなら分割して追加、文字列ならそのまま
    attachments = content.get("attachments")
    if attachments:
        if isinstance(attachments, list):
            for att in attachments:
                clauses.append(
                    {
                        "clause_number": "-",
                        "clause": att,
                        "contents_type": "attachments",
                        "review_points": "",
                        "action_plan": "",
                    }
                )
        else:
            clauses.append(
                {
                    "clause_number": "-",
                    "clause": attachments,
                    "contents_type": "attachments",
                    "review_points": "",
                    "action_plan": "",
                }
            )
    approval_status = content.get("approval_status", "draft")
    return title_text, introduction, clauses, approval_status


# 以下は契約審査用のアクション
def save_temp_api(
    api,
    settings,
    contract_type_combo,
    background_info_edit,
    partys_edit,
    introduction_edit,
    title_edit,
    clauses_layout,
    intro_label,
    introduction_edit_widget,
    parent=None,
):
    # JSTタイムゾーンを定義
    JST = timezone(timedelta(hours=9))
    now_jst = datetime.now(JST)
    contract_type_id = contract_type_combo.currentData()
    background_info = background_info_edit.toPlainText()
    partys_text = partys_edit.text().strip()
    partys = [p.strip() for p in partys_text.split(",") if p.strip()]
    introduction = introduction_edit.toPlainText()
    if not contract_type_id or not partys or not background_info.strip():
        raise ValueError("契約種別、契約当事者および背景情報は必須です")
    master_id = settings.value("contract_master_id", type=str)
    if not master_id:
        master_id = str(uuid.uuid4())
    existing = api.get_contract_by_id(master_id)
    clauses = []
    for i in range(clauses_layout.count()):
        clause_widget = clauses_layout.itemAt(i).widget()
        if (
            clause_widget is None
            or clause_widget == introduction_edit_widget
            or clause_widget == intro_label
        ):
            continue
        from PySide6.QtWidgets import QTextEdit, QLineEdit, QWidget

        text_edits = clause_widget.findChildren(QTextEdit)
        radio_widget = next(
            (
                w
                for w in clause_widget.findChildren(QWidget)
                if hasattr(w, "button_group")
            ),
            None,
        )
        if not text_edits or not radio_widget:
            continue
        clause_number = clause_widget.findChild(QLineEdit)
        clause_text = text_edits[0].toPlainText()
        checked_button = radio_widget.button_group.checkedButton()
        content_type = checked_button.text() if checked_button else "clauses"
        review_points = text_edits[1].toPlainText() if len(text_edits) > 1 else ""
        action_plan = text_edits[2].toPlainText() if len(text_edits) > 2 else ""
        if (review_points and not action_plan) or (action_plan and not review_points):
            QMessageBox.warning(
                parent,
                "入力エラー",
                "審査観点とアクションプランは両方入力する必要があります。どちらか一方のみの入力はできません。",
            )
            return False
        if not clause_text.strip():
            continue
        clause_id = getattr(clause_widget, "clause_id", None)
        if not clause_id:
            clause_id = str(uuid.uuid4())
        clause_widget.clause_id = clause_id
        clause_obj = {
            "clause_id": clause_id,
            "clause_number": clause_number.text(),
            "clause": clause_text,
            "contents_type": content_type,
            "review_points": review_points,
            "action_plan": action_plan,
            "created_at": (
                existing["clauses"][i]["created_at"]
                if existing
                and "clauses" in existing
                and len(existing["clauses"]) > i
                and "created_at" in existing["clauses"][i]
                else now_jst.isoformat()
            ),
            "updated_at": now_jst.isoformat(),
        }
        clauses.append(clause_obj)
    master_data = {
        "id": master_id,
        "contract_type_id": contract_type_id,
        "partys": partys,
        "title": title_edit.text().strip(),
        "background_info": background_info,
        "introduction": introduction,
        "approval_status": "temp",
        "record_status": "latest",
        "created_at": (
            existing["created_at"]
            if existing and "created_at" in existing
            else now_jst.isoformat()
        ),
        "updated_at": now_jst.isoformat(),
        "clauses": clauses,
    }
    settings.setValue("contract_master_id", master_id)
    api.upsert_contract(master_data)
    return True

