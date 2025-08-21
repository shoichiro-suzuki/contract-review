def load_draft_contracts_api(api, draft_combo, parent=None):
    try:
        draft_combo.clear()
        for item in api.get_draft_contracts():
            partys = item.get("partys", [])
            title = item.get("title", "")
            updated_at = item.get("updated_at", "")
            display = f"{partys}: {title} | {updated_at[:19].replace('T', ' ')}"
            draft_combo.addItem(display, userData=item["id"])
        return True
    except Exception as e:
        draft_combo.clear()
        draft_combo.addItem(f"取得失敗: {str(e)}")
        return False


def reload_draft_contract_api(
    api,
    settings,
    contract_type_combo,
    background_info,
    partys_edit,
    introduction_edit,
    draft_combo,
    display_draft_clauses_func,
    update_approval_status_ui_func,
    parent=None,
):
    try:
        contract_id = draft_combo.currentData()
        if not contract_id:
            QMessageBox.warning(parent, "エラー", "下書きを選択してください")
            return False
        data = api.get_contract_by_id(contract_id)
        if not data:
            QMessageBox.warning(parent, "エラー", "該当データが見つかりません")
            return False
        idx = contract_type_combo.findData(data.get("contract_type_id"))
        if idx >= 0:
            contract_type_combo.setCurrentIndex(idx)
        background_info.setPlainText(data.get("background_info", ""))
        partys = data.get("partys", [])
        if isinstance(partys, list):
            partys_edit.setText(",".join(partys))
        else:
            partys_edit.setText("")
        introduction_edit.setPlainText(data.get("introduction", ""))
        display_draft_clauses_func(
            data.get("clauses", []),
            title=data.get("title", ""),
            introduction=data.get("introduction", ""),
        )
        settings.setValue("contract_master_id", contract_id)
        # approval_statusをUIに反映
        parent._approval_status = data.get("approval_status", "draft")
        update_approval_status_ui_func()
        return True
    except Exception as e:
        QMessageBox.critical(parent, "エラー", f"下書きロードに失敗: {str(e)}")
        return False


from PySide6.QtWidgets import QMessageBox


def load_contract_types_api(api, contract_type_combo, parent=None):
    try:
        contract_type_combo.clear()
        for item in api.get_contract_types():
            contract_type_combo.addItem(item["contract_type"], userData=item["id"])
        return True
    except Exception as e:
        QMessageBox.warning(parent, "エラー", f"契約種別の取得に失敗しました: {str(e)}")
        return False
