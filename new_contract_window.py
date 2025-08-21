from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QLineEdit,
    QTextEdit,
    QComboBox,
    QFileDialog,
    QMessageBox,
    QSizePolicy,
    QScrollArea,
)
from PySide6.QtGui import QMovie
from PySide6.QtCore import QSettings
from api.contract_api import ContractAPI
from azure_.openai_service import AzureOpenAIService
from api.contract_analyze import AnalyzeWorker


class NewContractWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("契約登録・修正")
        self.setGeometry(20, 40, 1500, 750)

        self.api = ContractAPI()
        self.openai_service = AzureOpenAIService()
        self.settings = QSettings("ContractSupportApp", "Session")

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        # ファイルアップロード部分
        upload_layout = QHBoxLayout()
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setReadOnly(True)
        upload_btn = QPushButton("契約ファイル選択")
        upload_btn.clicked.connect(self.upload_file)
        upload_layout.addWidget(self.file_path_edit)
        upload_layout.addWidget(upload_btn)

        # 解析開始ボタン
        self.analyze_btn = QPushButton("解析開始")
        self.analyze_btn.clicked.connect(self.analyze_file)
        upload_layout.addWidget(self.analyze_btn)

        # スピナー（ローディングインジケーター）
        self.spinner_label = QLabel()
        self.spinner_label.setVisible(False)
        self.spinner_movie = QMovie("static/spinner.gif")
        self.spinner_label.setMovie(self.spinner_movie)
        upload_layout.addWidget(self.spinner_label)

        layout.addLayout(upload_layout)
        self.selected_file_path = None  # ファイルパス保持用

        # 契約種別選択
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("契約種別:"))
        self.contract_type_combo = QComboBox()
        self.load_contract_types()
        type_layout.addWidget(self.contract_type_combo)
        layout.addLayout(type_layout)

        # 契約当事者入力欄
        partys_layout = QHBoxLayout()
        partys_layout.addWidget(QLabel("契約当事者（カンマ区切り）:"))
        self.partys_edit = QLineEdit()
        self.partys_edit.setPlaceholderText("例: 甲社,乙社")
        partys_layout.addWidget(self.partys_edit)
        layout.addLayout(partys_layout)

        # 背景情報入力
        layout.addWidget(QLabel("背景情報:"))
        self.background_info = QTextEdit()
        self.background_info.setMaximumHeight(75)
        size_policy = QSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding
        )
        self.background_info.setSizePolicy(size_policy)
        layout.addWidget(self.background_info)

        # 下書き再編集
        draft_layout = QHBoxLayout()
        draft_layout.addWidget(QLabel("ドラフト編集:"))
        self.draft_combo = QComboBox()
        self.load_draft_contracts()
        draft_layout.addWidget(self.draft_combo)
        self.reload_draft_btn = QPushButton("編集する")
        self.reload_draft_btn.clicked.connect(self.reload_draft_contract)
        draft_layout.addWidget(self.reload_draft_btn)
        layout.addLayout(draft_layout)

        # approval_status表示ラベル
        status_layout = QHBoxLayout()
        status_layout.addWidget(QLabel("承認ステータス:"))
        self.approval_status_label = QLabel("")
        status_layout.addWidget(self.approval_status_label)
        layout.addLayout(status_layout)

        # 条文エリア（スクロール可能）
        self.clauses_scroll = QScrollArea()
        self.clauses_scroll.setWidgetResizable(True)
        self.clauses_area = QWidget()
        self.clauses_layout = QVBoxLayout(self.clauses_area)
        self.clauses_area.setLayout(self.clauses_layout)

        # 前文入力欄
        self.intro_label = QLabel("前文:")
        self.introduction_edit = QTextEdit()
        self.introduction_edit.setMaximumHeight(75)
        self.clauses_layout.addWidget(self.intro_label)
        self.clauses_layout.addWidget(self.introduction_edit)

        self.clauses_scroll.setWidget(self.clauses_area)
        layout.addWidget(self.clauses_scroll)

        # ボタン
        button_layout = QHBoxLayout()
        self.save_btn = QPushButton("ナレッジ保存")
        self.save_btn.clicked.connect(self.save_draft)
        self.save_btn.setEnabled(False)
        self.apply_btn = QPushButton("承認申請")
        self.apply_btn.clicked.connect(self.on_apply_btn_clicked)
        self.apply_btn.setEnabled(False)
        self.approve_btn = QPushButton("承認")
        self.approve_btn.clicked.connect(self.on_approve_btn_clicked)
        self.approve_btn.setEnabled(False)
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.apply_btn)
        button_layout.addWidget(self.approve_btn)
        layout.addLayout(button_layout)

    def sync_clause_widgets_to_current_clauses(self):
        """
        現在のウィジェット内容をself._current_clausesへ反映する
        条項No・条文・内容種別・審査観点・アクションプランすべて対象
        """
        clauses = []
        # 条文ウィジェットはタイトル・前文ラベル/欄の後に並ぶ
        for i in range(self.clauses_layout.count()):
            widget = self.clauses_layout.itemAt(i).widget()
            if (
                widget is None
                or widget == self.introduction_edit
                or widget == self.intro_label
                or widget == self.title_edit
            ):
                continue
            # 各clause_widgetから値を取得
            clause_number = widget.findChild(QLineEdit)
            text_edits = widget.findChildren(QTextEdit)
            radio_widget = next(
                (w for w in widget.findChildren(QWidget) if hasattr(w, "button_group")),
                None,
            )
            if not text_edits or not radio_widget:
                continue
            clause_text = text_edits[0].toPlainText()
            # 選択されているラジオボタンからcontents_typeを取得
            checked_button = radio_widget.button_group.checkedButton()
            content_type = checked_button.text() if checked_button else "clauses"
            review_points = text_edits[1].toPlainText() if len(text_edits) > 1 else ""
            action_plan = text_edits[2].toPlainText() if len(text_edits) > 2 else ""
            clauses.append(
                {
                    "clause_number": clause_number.text() if clause_number else "",
                    "clause": clause_text,
                    "contents_type": content_type,
                    "review_points": review_points,
                    "action_plan": action_plan,
                }
            )
        self._current_clauses = clauses

    def load_contract_types(self):
        from contract_ui_helpers import load_contract_types_api

        load_contract_types_api(self.api, self.contract_type_combo, self)

    def load_draft_contracts(self):
        from contract_ui_helpers import load_draft_contracts_api

        load_draft_contracts_api(self.api, self.draft_combo, self)

    def reload_draft_contract(self):
        from contract_ui_helpers import reload_draft_contract_api

        reload_draft_contract_api(
            self.api,
            self.settings,
            self.contract_type_combo,
            self.background_info,
            self.partys_edit,
            self.introduction_edit,
            self.draft_combo,
            self.display_draft_clauses,
            self.update_approval_status_ui,
            self,
        )
        self.save_btn.setEnabled(True)
        self.apply_btn.setEnabled(True)
        self.approve_btn.setEnabled(False)

    def display_draft_clauses(self, clauses, title=None, introduction=None):
        from api.contract_actions import display_draft_clauses_data

        title_text, intro, clauses_out = display_draft_clauses_data(
            clauses, title, introduction
        )
        self.display_clauses(title_text, intro, clauses_out)

    def upload_file(self):
        self.settings.remove("contract_master_id")
        file_path, _ = QFileDialog.getOpenFileName(
            self, "契約書ファイルを選択", "", "Document Files (*.pdf *.docx *.doc)"
        )
        if file_path:
            self.file_path_edit.setText(file_path)
            self.selected_file_path = file_path
        else:
            self.selected_file_path = None

    def analyze_file(self):
        # 解析開始ボタンの処理
        file_path = self.selected_file_path
        if not file_path:
            QMessageBox.warning(self, "エラー", "ファイルを選択してください")
            return
        # ワードファイルの場合は注意文を表示
        if file_path.lower().endswith(".doc") or file_path.lower().endswith(".docx"):
            QMessageBox.information(
                self,
                "注意",
                "ワードファイルを読み込む場合、変更をすべて反映したファイルで解析してください。",
            )
        # 契約当事者と背景情報をクリア
        self.partys_edit.clear()
        self.background_info.clear()

        # スピナー表示・ボタン無効化
        self.spinner_label.setVisible(True)
        self.spinner_movie.start()
        self.analyze_btn.setEnabled(False)

        # ワーカーで非同期実行
        self.worker = AnalyzeWorker(self.api, file_path)
        self.worker.finished.connect(self._on_analyze_finished)
        self.worker.error.connect(self._on_analyze_error)
        self.worker.start()

    def _on_analyze_finished(self, result):
        self.spinner_movie.stop()
        self.spinner_label.setVisible(False)
        self.analyze_btn.setEnabled(True)
        self.display_document_content(result)

    def _on_analyze_error(self, error_msg):
        self.spinner_movie.stop()
        self.spinner_label.setVisible(False)
        self.analyze_btn.setEnabled(True)
        QMessageBox.warning(
            self, "エラー", f"ファイルの解析に失敗しました: {error_msg}"
        )

    def display_document_content(self, content):
        from api.contract_actions import display_document_content_data

        title_text, introduction, clauses, approval_status = (
            display_document_content_data(content)
        )
        self._approval_status = approval_status
        self.update_approval_status_ui()
        self.display_clauses(title_text, introduction, clauses)

    def update_approval_status_ui(self):
        # ステータスラベルとボタン表示を更新
        status_map = {"draft": "下書き", "submitted": "申請中", "approved": "承認済み"}
        label = status_map.get(self._approval_status, self._approval_status)
        self.approval_status_label.setText(label)
        if self._approval_status == "submitted":
            self.apply_btn.setText("承認申請取り下げ")
            self.approve_btn.setEnabled(True)
        else:
            self.apply_btn.setText("承認申請")
            self.approve_btn.setEnabled(False)
        # 保存ボタンの有効/無効制御
        if self._approval_status == "draft":
            self.save_btn.setEnabled(True)
        else:
            self.save_btn.setEnabled(False)

    def on_apply_btn_clicked(self):
        if self._approval_status == "draft":
            self.apply_for_approval()
            self.save_btn.setEnabled(False)
            self.apply_btn.setEnabled(True)
            self.approve_btn.setEnabled(True)
            self.apply_btn.setText("承認申請取り下げ")
        elif self._approval_status == "submitted":
            self.withdraw_approval()
            self.save_btn.setEnabled(True)
            self.apply_btn.setEnabled(True)
            self.approve_btn.setEnabled(False)
            self.apply_btn.setText("承認申請")

    def withdraw_approval(self):
        try:
            contract_id = self.settings.value("contract_master_id", type=str)
            if not contract_id:
                QMessageBox.warning(self, "エラー", "契約情報が保存されていません")
                return
            master_data = self.api.get_contract_by_id(contract_id)
            if not master_data:
                QMessageBox.warning(self, "エラー", "契約情報が見つかりません")
                return
            master_data["approval_status"] = "draft"
            self.api.upsert_contract(master_data)
            self._approval_status = "draft"
            self.update_approval_status_ui()
            QMessageBox.information(self, "成功", "承認申請を取り下げました")
        except Exception as e:
            QMessageBox.critical(
                self, "エラー", f"承認申請取り下げに失敗しました: {str(e)}"
            )

    def display_clauses(self, title, introduction, clauses):
        # 既存の条文表示をクリア
        for i in reversed(range(self.clauses_layout.count())):
            widget = self.clauses_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        # タイトル入力欄
        self.title_edit = QLineEdit()
        self.title_edit.setText(title or "")
        self.clauses_layout.addWidget(QLabel("タイトル:"))
        self.clauses_layout.addWidget(self.title_edit)

        # 前文（introduction）
        self.introduction_edit.setPlainText(introduction or "")
        self.clauses_layout.addWidget(self.intro_label)
        self.clauses_layout.addWidget(self.introduction_edit)

        self._current_clauses = list(clauses)  # 現在の条項リストを保持
        for idx, clause in enumerate(self._current_clauses):
            clause_widget = self.create_clause_widget(clause, idx)
            self.clauses_layout.addWidget(clause_widget)

    def refresh_clauses(self):
        # self._current_clauses から再描画
        title = self.title_edit.text() if hasattr(self, "title_edit") else ""
        introduction = (
            self.introduction_edit.toPlainText()
            if hasattr(self, "introduction_edit")
            else ""
        )
        self.display_clauses(title, introduction, self._current_clauses)

    def create_clause_widget(self, clause, idx):

        from PySide6.QtWidgets import QGridLayout

        clause_widget = QWidget()
        # 各条項ウィジェットの下にスペースを設ける（下マージンのみ）
        clause_widget.setContentsMargins(0, 0, 0, 16)  # 下方向に16pxのスペース
        grid = QGridLayout(clause_widget)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(8)

        # clause_idをウィジェットにセット
        clause_id = clause.get("clause_id")
        if clause_id:
            clause_widget.clause_id = clause_id

        # 1列目: 条項No
        clause_number = QLineEdit()
        clause_number.setMaximumWidth(40)
        clause_number.setText(clause.get("clause_number", ""))
        grid.addWidget(QLabel("条項No"), 0, 0)
        grid.addWidget(clause_number, 1, 0)

        # 2列目: 内容種別（ラジオボタン）
        from PySide6.QtWidgets import QRadioButton, QButtonGroup, QVBoxLayout

        radio_widget = QWidget()
        radio_layout = QVBoxLayout(radio_widget)
        radio_layout.setContentsMargins(0, 0, 0, 0)
        radio_layout.setSpacing(4)
        content_types = ["clauses", "signature_section", "attachments"]
        button_group = QButtonGroup(radio_widget)
        radio_buttons = {}
        for i, ctype in enumerate(content_types):
            rb = QRadioButton(ctype)
            radio_layout.addWidget(rb)
            button_group.addButton(rb, i)
            radio_buttons[ctype] = rb
        selected_type = clause.get("contents_type", "clauses")
        if selected_type in radio_buttons:
            radio_buttons[selected_type].setChecked(True)
        radio_widget.button_group = button_group  # 後でアクセスできるように
        radio_widget.radio_buttons = radio_buttons
        grid.addWidget(QLabel("内容種別"), 0, 1)
        grid.addWidget(radio_widget, 1, 1)

        # 3列目: 条項テキスト（最大幅に）
        clause_text = QTextEdit()
        clause_text.setMinimumHeight(250)
        clause_text.setMinimumWidth(750)
        clause_text.setPlainText(clause.get("clause") or clause.get("text", ""))
        grid.addWidget(QLabel("条項テキスト"), 0, 2)
        # 他の要素の最大高さまで
        grid.addWidget(clause_text, 1, 2, 3, 1)

        # 4列目: 1行目審査観点, 2行目アクションプラン（幅小さめ）
        review_points = QTextEdit()
        review_points.setPlaceholderText("審査観点")
        review_points.setMinimumHeight(50)
        review_points.setMinimumWidth(200)
        review_points.setPlainText(clause.get("review_points", ""))
        grid.addWidget(QLabel("審査観点"), 0, 3)
        grid.addWidget(review_points, 1, 3)

        action_plan = QTextEdit()
        action_plan.setPlaceholderText("アクションプラン")
        action_plan.setMinimumHeight(50)
        action_plan.setMinimumWidth(200)
        action_plan.setPlainText(clause.get("action_plan", ""))
        grid.addWidget(QLabel("アクションプラン"), 2, 3)
        grid.addWidget(action_plan, 3, 3)

        # 5列目: ボタンを縦に並べる
        from PySide6.QtWidgets import QVBoxLayout

        btn_pane = QWidget()
        btn_layout = QVBoxLayout(btn_pane)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(4)

        del_btn = QPushButton("削除")
        del_btn.setStyleSheet("color: red;")
        del_btn.clicked.connect(lambda _, i=idx: self._on_delete_clause(i))
        btn_layout.addWidget(del_btn)

        insert_above_btn = QPushButton("上に条項を挿入")
        insert_above_btn.clicked.connect(
            lambda _, i=idx: self._on_insert_clause(i, above=True)
        )
        btn_layout.addWidget(insert_above_btn)

        insert_below_btn = QPushButton("下に条項を挿入")
        insert_below_btn.clicked.connect(
            lambda _, i=idx: self._on_insert_clause(i, above=False)
        )
        btn_layout.addWidget(insert_below_btn)

        grid.addWidget(btn_pane, 1, 4, 3, 1)

        return clause_widget

    def _on_delete_clause(self, idx):
        reply = QMessageBox.question(
            self, "確認", "この条項を削除しますか？", QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            # まずウィジェット内容をself._current_clausesへ反映
            self.sync_clause_widgets_to_current_clauses()
            if hasattr(self, "_current_clauses") and 0 <= idx < len(
                self._current_clauses
            ):
                del self._current_clauses[idx]
                self.refresh_clauses()

    def _on_insert_clause(self, idx, above=True):
        # まずウィジェット内容をself._current_clausesへ反映
        self.sync_clause_widgets_to_current_clauses()
        # 空の条項を挿入
        empty_clause = {
            "clause_number": "",
            "clause": "",
            "contents_type": "clauses",
            "review_points": "",
            "action_plan": "",
        }
        if hasattr(self, "_current_clauses"):
            insert_idx = idx if above else idx + 1
            self._current_clauses.insert(insert_idx, empty_clause)
            self.refresh_clauses()

    def save_draft(self):
        from api.contract_actions import save_draft_api

        try:
            ok = save_draft_api(
                self.api,
                self.settings,
                self.contract_type_combo,
                self.background_info,
                self.partys_edit,
                self.introduction_edit,
                self.title_edit,
                self.clauses_layout,
                self.intro_label,
                self.introduction_edit,
                self,
            )
            if ok:
                QMessageBox.information(self, "成功", "契約情報を保存しました")
                self.save_btn.setEnabled(True)
                self.apply_btn.setEnabled(True)
                self.approve_btn.setEnabled(False)
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"保存に失敗しました: {str(e)}")
            print(f"Error saving draft: {e}")

    def apply_for_approval(self):
        from api.contract_actions import apply_for_approval_api

        reply = QMessageBox.question(
            self, "確認", "承認を申請します？", QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                ok = apply_for_approval_api(self.api, self.settings, self)
                if ok:
                    self._approval_status = "submitted"
                    self.update_approval_status_ui()
                    self.save_btn.setEnabled(False)
                    self.apply_btn.setEnabled(True)
                    self.approve_btn.setEnabled(True)
                    QMessageBox.information(self, "成功", "承認申請を送信しました")
            except Exception as e:
                QMessageBox.critical(
                    self, "エラー", f"承認申請に失敗しました: {str(e)}"
                )

    def on_approve_btn_clicked(self):
        from api.contract_actions import approve_contract_api, convert_to_vectors_api

        reply = QMessageBox.question(
            self,
            "確認",
            "登録を承認し、同時にベクトル変換を実行しますか？",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            try:
                # 先にベクトル変換を実行
                ok_vector = convert_to_vectors_api(
                    self.api,
                    self.openai_service,
                    self.settings,
                    self.clauses_layout,
                    self.intro_label,
                    self.introduction_edit,
                    self.title_edit,
                    self,
                    self.spinner_label,
                    self.spinner_movie,
                )
                if not ok_vector:
                    QMessageBox.warning(
                        self,
                        "警告",
                        "ベクトル変換に失敗しましたが、承認処理を続行します。",
                    )
                ok = approve_contract_api(self.api, self.settings, self)
                if ok:
                    self._approval_status = "approved"
                    self.update_approval_status_ui()
                    QMessageBox.information(
                        self, "成功", "契約が承認され、ベクトル変換も完了しました"
                    )
                    self.save_btn.setEnabled(False)
                    self.apply_btn.setEnabled(False)
                    self.approve_btn.setEnabled(False)
            except Exception as e:
                if self.spinner_movie and self.spinner_label:
                    self.spinner_movie.stop()
                    self.spinner_label.setVisible(False)
                QMessageBox.critical(
                    self,
                    "エラー",
                    f"承認処理またはベクトル変換に失敗しました: {str(e)}",
                )

    def convert_to_vectors(self):
        from api.contract_actions import convert_to_vectors_api

        try:
            ok = convert_to_vectors_api(
                self.api,
                self.openai_service,
                self.settings,
                self.clauses_layout,
                self.intro_label,
                self.introduction_edit,
                self.title_edit,
                self,
                self.spinner_label,
                self.spinner_movie,
            )
            if ok:
                QMessageBox.information(self, "成功", "ベクトル変換が完了しました")
        except Exception as e:
            if self.spinner_movie and self.spinner_label:
                self.spinner_movie.stop()
                self.spinner_label.setVisible(False)
            QMessageBox.critical(
                self, "エラー", f"ベクトル変換に失敗しました: {str(e)}"
            )
