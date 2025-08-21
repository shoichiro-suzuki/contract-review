from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QTextEdit,
    QComboBox,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QScrollArea,
    QMessageBox,
    QSpinBox,
    QSplitter,
    QHeaderView,
)
from PySide6.QtCore import Qt
from api.knowledge_api import KnowledgeAPI
import uuid


class KnowledgeWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ナレッジ登録・改訂")
        self.setGeometry(20, 40, 1500, 750)

        # API初期化
        self.api = KnowledgeAPI()

        # メインウィジェットとQSplitterの設定
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        splitter = QSplitter(Qt.Horizontal)
        main_layout = QVBoxLayout(main_widget)
        main_layout.addWidget(splitter)

        # 左側：ナレッジ一覧エリア
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        # フィルター機能
        filter_widget = QWidget()
        filter_layout = QVBoxLayout(filter_widget)

        # 契約種別フィルター
        contract_type_layout = QHBoxLayout()
        contract_type_layout.addWidget(QLabel("契約種別:"))
        self.contract_type_combo = QComboBox()
        # get_contract_typesで取得しセット
        try:
            contract_types = self.api.get_contract_types()
            type_names = [
                t["contract_type"]
                for t in contract_types
                if isinstance(t, dict) and "contract_type" in t
            ]
            if not type_names:
                type_names = ["汎用", "秘密保持", "業務委託", "共同開発", "共同出願"]
        except Exception:
            type_names = ["汎用", "秘密保持", "業務委託", "共同開発", "共同出願"]
        self.contract_type_combo.addItem("すべて")
        self.contract_type_combo.addItems(type_names)
        contract_type_layout.addWidget(self.contract_type_combo)
        filter_layout.addLayout(contract_type_layout)

        # テキスト検索
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("検索:"))
        self.search_edit = QLineEdit()
        search_layout.addWidget(self.search_edit)
        self.search_btn = QPushButton("検索")
        self.search_btn.clicked.connect(self.search_knowledge)
        search_layout.addWidget(self.search_btn)

        # 新規追加ボタン
        self.new_btn = QPushButton("新規追加")
        self.new_btn.clicked.connect(self.create_new_knowledge)
        search_layout.addWidget(self.new_btn)

        filter_layout.addLayout(search_layout)
        left_layout.addWidget(filter_widget)

        # ナレッジリスト
        self.knowledge_table = QTableWidget()
        self.knowledge_table.setColumnCount(8)
        self.knowledge_table.setHorizontalHeaderLabels(
            [
                "No",
                "Ver",
                "最新",
                "承認",
                "契約種別",
                "タイトル",
                "審査観点",
                "対応策",
            ]
        )
        header = self.knowledge_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        # 各列の初期幅を指定
        self.knowledge_table.setColumnWidth(0, 40)  # No
        self.knowledge_table.setColumnWidth(1, 40)  # Ver
        self.knowledge_table.setColumnWidth(2, 40)  # 最新
        self.knowledge_table.setColumnWidth(3, 40)  # 承認
        self.knowledge_table.setColumnWidth(4, 80)  # 契約種別
        self.knowledge_table.setColumnWidth(5, 150)  # タイトル
        self.knowledge_table.setColumnWidth(6, 150)  # 審査観点
        self.knowledge_table.setColumnWidth(7, 150)  # 対応策
        self.knowledge_table.cellClicked.connect(self.load_knowledge)
        left_layout.addWidget(self.knowledge_table)

        splitter.addWidget(left_widget)

        # 右側：編集エリア
        right_widget = QScrollArea()
        right_widget.setWidgetResizable(True)
        edit_widget = QWidget()
        edit_layout = QVBoxLayout(edit_widget)

        # ナレッジ番号・バージョン（IDは非表示で裏で保持）
        id_version_layout = QHBoxLayout()
        id_version_layout.addWidget(QLabel("ナレッジ番号:"))
        self.knowledge_number_label = QLabel()
        id_version_layout.addWidget(self.knowledge_number_label)
        # IDは非表示で保持
        self.knowledge_id_label = QLabel()
        self.knowledge_id_label.setVisible(False)
        id_version_layout.addWidget(QLabel("バージョン:"))
        self.version_spin = QSpinBox()
        self.version_spin.setReadOnly(True)
        self.version_spin.setButtonSymbols(QSpinBox.NoButtons)
        id_version_layout.addWidget(self.version_spin)

        # record_status, approval_status 表示
        self.record_status_label = QLabel()
        id_version_layout.addWidget(QLabel("record_status:"))
        id_version_layout.addWidget(self.record_status_label)
        self.approval_status_label = QLabel()
        id_version_layout.addWidget(QLabel("approval_status:"))
        id_version_layout.addWidget(self.approval_status_label)
        edit_layout.addLayout(id_version_layout)

        # 契約種別
        edit_contract_layout = QHBoxLayout()
        edit_contract_layout.addWidget(QLabel("契約種別:"))
        self.edit_contract_type = QComboBox()
        # get_contract_typesで取得しセット
        try:
            contract_types = self.api.get_contract_types()
            # contract_typesは辞書のリスト想定、"contract_type"キーのみを使用
            type_names = [
                t["contract_type"]
                for t in contract_types
                if isinstance(t, dict) and "contract_type" in t
            ]
            if not type_names:
                type_names = ["汎用", "秘密保持", "業務委託", "共同開発", "共同出願"]
        except Exception:
            type_names = ["汎用", "秘密保持", "業務委託", "共同開発", "共同出願"]
        self.edit_contract_type.addItems(type_names)
        edit_contract_layout.addWidget(self.edit_contract_type)
        edit_layout.addLayout(edit_contract_layout)

        # タイトル
        edit_layout.addWidget(QLabel("タイトル:"))
        self.title_edit = QTextEdit()
        self.title_edit.setMaximumHeight(50)
        edit_layout.addWidget(self.title_edit)

        # 審査観点
        edit_layout.addWidget(QLabel("審査観点:"))
        self.review_points_edit = QTextEdit()
        edit_layout.addWidget(self.review_points_edit)

        # 対応策
        edit_layout.addWidget(QLabel("対応策:"))
        self.action_edit = QTextEdit()
        edit_layout.addWidget(self.action_edit)

        # 条項サンプル
        edit_layout.addWidget(QLabel("条項サンプル:"))
        self.clause_edit = QTextEdit()
        edit_layout.addWidget(self.clause_edit)

        # ボタン群
        button_layout = QHBoxLayout()

        # 改訂ボタン
        self.revise_btn = QPushButton("改訂")
        self.revise_btn.clicked.connect(self.revise_knowledge)
        button_layout.addWidget(self.revise_btn)

        self.save_btn = QPushButton("保存")
        self.save_btn.clicked.connect(self.save_draft)
        button_layout.addWidget(self.save_btn)

        self.apply_btn = QPushButton("承認申請")
        self.apply_btn.clicked.connect(self.apply_for_approval)
        button_layout.addWidget(self.apply_btn)

        self.approve_btn = QPushButton("承認")
        self.approve_btn.clicked.connect(self.approve_knowledge)
        button_layout.addWidget(self.approve_btn)

        edit_layout.addLayout(button_layout)

        right_widget.setWidget(edit_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([900, 600])  # 初期幅（必要に応じて調整）

        # 初期データ読み込み
        self.load_knowledge_list()

    def load_knowledge_list(self):
        """ナレッジ一覧を読み込む（supersededは除外）"""
        contract_type = (
            None
            if self.contract_type_combo.currentText() == "すべて"
            else self.contract_type_combo.currentText()
        )
        search_text = self.search_edit.text() if self.search_edit.text() else None

        knowledge_list = self.api.get_knowledge_list(contract_type, search_text)
        # record_statusがsupersededのものは除外
        filtered_list = [
            k
            for k in knowledge_list
            if k.get("record_status", "latest") != "superseded"
        ]
        # knowledge_numberで昇順ソート
        sorted_list = sorted(
            filtered_list,
            key=lambda x: (
                x.get("knowledge_number")
                if x.get("knowledge_number") is not None
                else float("inf")
            ),
        )

        self.knowledge_table.setRowCount(len(sorted_list))
        for i, knowledge in enumerate(sorted_list):
            self.knowledge_table.setItem(
                i, 0, QTableWidgetItem(str(knowledge.get("knowledge_number", "")))
            )
            self.knowledge_table.setItem(
                i, 1, QTableWidgetItem(str(knowledge.get("version", "")))
            )
            self.knowledge_table.setItem(
                i, 2, QTableWidgetItem(knowledge.get("record_status", ""))
            )
            self.knowledge_table.setItem(
                i, 3, QTableWidgetItem(knowledge.get("approval_status", ""))
            )
            self.knowledge_table.setItem(
                i, 4, QTableWidgetItem(knowledge.get("contract_type", ""))
            )
            self.knowledge_table.setItem(
                i, 5, QTableWidgetItem(knowledge.get("knowledge_title", ""))
            )
            self.knowledge_table.setItem(
                i, 6, QTableWidgetItem(knowledge.get("review_points", ""))
            )
            self.knowledge_table.setItem(
                i, 7, QTableWidgetItem(knowledge.get("action_plan", ""))
            )

        self.knowledge_table.resizeColumnsToContents()

    def search_knowledge(self):
        """検索を実行"""
        self.load_knowledge_list()

    def load_knowledge(self, row, col):
        """選択したナレッジの詳細を読み込む"""
        # ナレッジ番号とバージョンからidを特定して詳細取得
        knowledge_number = self.knowledge_table.item(row, 0).text()
        version = self.knowledge_table.item(row, 1).text()
        contract_type = (
            None
            if self.contract_type_combo.currentText() == "すべて"
            else self.contract_type_combo.currentText()
        )
        search_text = self.search_edit.text() if self.search_edit.text() else None
        knowledge_list = self.api.get_knowledge_list(contract_type, search_text)
        knowledge = next(
            (
                k
                for k in knowledge_list
                if str(k.get("knowledge_number", "")) == knowledge_number
                and str(k.get("version", "")) == version
            ),
            None,
        )
        if knowledge:
            self.knowledge_number_label.setText(
                str(knowledge.get("knowledge_number", ""))
            )
            self.knowledge_id_label.setText(knowledge.get("id", ""))
            self.version_spin.setValue(knowledge.get("version", ""))
            self.edit_contract_type.setCurrentText(knowledge.get("contract_type", ""))
            self.title_edit.setText(knowledge.get("knowledge_title", ""))
            self.review_points_edit.setText(knowledge.get("review_points", ""))
            self.action_edit.setText(knowledge.get("action_plan", ""))
            self.clause_edit.setText(knowledge.get("clause_sample", ""))

            # record_status, approval_status 表示
            self.record_status_label.setText(knowledge.get("record_status", "latest"))
            self.approval_status_label.setText(
                knowledge.get("approval_status", "draft")
            )

            # 承認ボタンの制御
            approval_status = knowledge.get("approval_status", "draft")
            self.approve_btn.setEnabled(approval_status == "submitted")
            if approval_status == "submitted":
                self.apply_btn.setText("承認申請取り下げ")
                self.apply_btn.setEnabled(True)
            elif approval_status == "approved":
                self.apply_btn.setText("承認申請")
                self.apply_btn.setEnabled(False)
            else:
                self.apply_btn.setText("承認申請")
                self.apply_btn.setEnabled(True)
            # 改訂ボタンの制御
            self.revise_btn.setEnabled(approval_status == "approved")
            # ドラフト保存ボタンの制御
            self.save_btn.setEnabled(approval_status == "draft")

    def get_current_knowledge_data(self):
        """現在の編集内容をデータとして取得"""
        return {
            "id": self.knowledge_id_label.text() or str(uuid.uuid4()),
            "knowledge_number": (
                int(self.knowledge_number_label.text())
                if self.knowledge_number_label.text()
                else None
            ),
            "version": self.version_spin.value(),
            "contract_type": self.edit_contract_type.currentText(),
            "knowledge_title": self.title_edit.toPlainText(),
            "review_points": self.review_points_edit.toPlainText(),
            "action_plan": self.action_edit.toPlainText(),
            "clause_sample": self.clause_edit.toPlainText(),
            "record_status": self.record_status_label.text() or "latest",
            "approval_status": self.approval_status_label.text() or "draft",
        }

    def save_draft(self):
        """ドラフトとして保存"""
        try:
            knowledge_data = self.get_current_knowledge_data()
            # approval_statusがdraft以外なら保存不可
            if knowledge_data.get("approval_status", "draft") != "draft":
                QMessageBox.warning(self, "保存不可", "ドラフト状態のみ保存できます。")
                return
            self.api.save_knowledge_draft(knowledge_data)
            QMessageBox.information(
                self, "保存完了", "ナレッジをドラフトとして保存しました。"
            )
            self.load_knowledge_list()

            # ボタン設定
            self.revise_btn.setEnabled(False)
            self.save_btn.setEnabled(True)
            self.apply_btn.setEnabled(True)
            self.approve_btn.setEnabled(False)

        except Exception as e:
            QMessageBox.critical(
                self, "エラー", f"保存中にエラーが発生しました: {str(e)}"
            )

    def revise_knowledge(self):
        """改訂処理: approved状態のナレッジを改訂し新バージョンを作成（versionもUIも更新）"""
        try:
            # 現在のデータ取得
            knowledge_data = self.get_current_knowledge_data()
            if knowledge_data.get("approval_status") != "approved":
                QMessageBox.warning(self, "改訂不可", "承認済みのみ改訂できます。")
                return
            # 既存レコードをsupersededに
            old_id = knowledge_data["id"]
            old_data = self.api.get_knowledge_by_id(old_id)
            if old_data:
                old_data["record_status"] = "superseded"
                self.api.save_knowledge_draft(old_data)
            # 新レコード作成
            new_data = dict(old_data) if old_data else dict(knowledge_data)
            new_data["id"] = str(uuid.uuid4())
            # versionを正しくインクリメント
            new_version = (
                (old_data["version"] + 1) if old_data and "version" in old_data else 1
            )
            new_data["version"] = new_version
            new_data["record_status"] = "latest"
            new_data["approval_status"] = "draft"
            # 編集欄の内容で上書き
            new_data["contract_type"] = self.edit_contract_type.currentText()
            new_data["knowledge_title"] = self.title_edit.toPlainText()
            new_data["review_points"] = self.review_points_edit.toPlainText()
            new_data["action_plan"] = self.action_edit.toPlainText()
            new_data["clause_sample"] = self.clause_edit.toPlainText()
            self.api.save_knowledge_draft(new_data)
            QMessageBox.information(
                self, "改訂完了", "新しいバージョンで改訂しました。"
            )
            self.load_knowledge_list()
            # 新バージョンのデータをUIに反映
            self.knowledge_number_label.setText(
                str(new_data.get("knowledge_number", ""))
            )
            self.knowledge_id_label.setText(new_data["id"])
            self.version_spin.setValue(new_data["version"])
            self.edit_contract_type.setCurrentText(new_data.get("contract_type", ""))
            self.title_edit.setText(new_data.get("knowledge_title", ""))
            self.review_points_edit.setText(new_data.get("review_points", ""))
            self.action_edit.setText(new_data.get("action_plan", ""))
            self.clause_edit.setText(new_data.get("clause_sample", ""))
            self.record_status_label.setText(new_data["record_status"])
            self.approval_status_label.setText(new_data["approval_status"])
            # ボタンの状態を設定
            self.revise_btn.setEnabled(False)
            self.save_btn.setEnabled(True)
            self.apply_btn.setEnabled(False)
            self.approve_btn.setEnabled(False)

        except Exception as e:
            QMessageBox.critical(self, "エラー", f"改訂処理でエラー: {str(e)}")

    def apply_for_approval(self):
        """承認申請または取り下げ（UIも即時更新・確認ダイアログあり）"""
        try:
            knowledge_id = self.knowledge_id_label.text()
            approval_status = self.approval_status_label.text()
            if not knowledge_id:
                return
            if approval_status == "draft":
                reply = QMessageBox.question(
                    self,
                    "承認申請の確認",
                    "このナレッジの承認申請を行いますか？",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No,
                )
                if reply != QMessageBox.Yes:
                    return
                self.api.update_approval_status(knowledge_id, "submitted")
                self.approval_status_label.setText("submitted")

                # ボタン設定
                self.revise_btn.setEnabled(False)
                self.save_btn.setEnabled(False)
                self.apply_btn.setEnabled(True)
                self.approve_btn.setEnabled(True)
                self.apply_btn.setText("承認申請取り下げ")

                QMessageBox.information(self, "申請完了", "承認申請を行いました。")
            elif approval_status == "submitted":
                reply = QMessageBox.question(
                    self,
                    "申請取り下げの確認",
                    "このナレッジの承認申請を取り下げますか？",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No,
                )
                if reply != QMessageBox.Yes:
                    return
                self.api.update_approval_status(knowledge_id, "draft")
                self.approval_status_label.setText("draft")
                # ボタン設定
                self.revise_btn.setEnabled(False)
                self.save_btn.setEnabled(True)
                self.apply_btn.setEnabled(True)
                self.approve_btn.setEnabled(False)
                self.apply_btn.setText("承認申請")

                QMessageBox.information(
                    self, "取り下げ完了", "承認申請を取り下げました。"
                )
            self.load_knowledge_list()
        except Exception as e:
            QMessageBox.critical(
                self, "エラー", f"承認申請中にエラーが発生しました: {str(e)}"
            )

    def approve_knowledge(self):
        """承認する前に確認ダイアログを表示し、承認処理とベクトル変換保存も同時に実行"""
        try:
            reply = QMessageBox.question(
                self,
                "承認確認",
                "本当にこのナレッジを承認しますか？\n承認後は内容の編集ができません。",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return
            knowledge_id = self.knowledge_id_label.text()
            if knowledge_id:
                # まず承認状態を更新
                self.api.update_approval_status(knowledge_id, "approved")
                self.approval_status_label.setText("approved")
                # ベクトル変換して保存も実行
                try:
                    knowledge_data = self.get_current_knowledge_data()
                    self.api.save_knowledge_with_vectors(knowledge_data)
                except Exception as ve:
                    QMessageBox.warning(
                        self,
                        "ベクトル保存エラー",
                        f"ベクトル変換保存時にエラー: {str(ve)}",
                    )
                # ボタンの状態を更新
                self.revise_btn.setEnabled(True)
                self.save_btn.setEnabled(False)
                self.apply_btn.setEnabled(False)
                self.approve_btn.setEnabled(False)

                QMessageBox.information(
                    self, "承認完了", "ナレッジを承認し、ベクトル変換保存も行いました。"
                )
                self.load_knowledge_list()
        except Exception as e:
            QMessageBox.critical(
                self, "エラー", f"承認中にエラーが発生しました: {str(e)}"
            )

    def create_new_knowledge(self):
        """新規ナレッジの作成"""
        # 編集エリアをクリア
        self.knowledge_id_label.clear()
        self.version_spin.setValue(1)
        self.edit_contract_type.setCurrentIndex(0)
        self.title_edit.clear()
        self.review_points_edit.clear()
        self.action_edit.clear()
        self.clause_edit.clear()

        # 新しいknowledge_numberをAPIから取得
        try:
            max_number = self.api.get_max_knowledge_number()
            new_number = max_number + 1 if max_number is not None else 1
        except Exception:
            new_number = 1
        self.knowledge_number_label.setText(str(new_number))

        # ボタンの状態を設定
        self.revise_btn.setEnabled(False)
        self.save_btn.setEnabled(True)
        self.apply_btn.setEnabled(False)
        self.approve_btn.setEnabled(False)

        self.record_status_label.setText("latest")
        self.approval_status_label.setText("draft")

        # フォーカスをタイトル入力欄に設定
        self.title_edit.setFocus()
