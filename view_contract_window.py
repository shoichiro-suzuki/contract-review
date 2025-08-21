from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QComboBox,
    QTextEdit,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QScrollArea,
    QMessageBox,
)
from PySide6.QtCore import Qt
from PySide6.QtCore import QSettings
from api.contract_api import ContractAPI


class ViewContractWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("契約閲覧")
        self.setGeometry(20, 40, 1500, 750)

        # API初期化
        self.api = ContractAPI()
        self.settings = QSettings("ContractSupportApp", "Session")

        # メインウィジェットとレイアウトの設定（QSplitterを使用）
        from PySide6.QtWidgets import QSplitter

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        splitter = QSplitter(Qt.Horizontal, main_widget)
        splitter.setChildrenCollapsible(False)

        # 左側：契約一覧エリア
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
                raise ValueError("契約種別が取得できません")
        except Exception:
            type_names = []
            QMessageBox.warning(self, "警告", "契約種別の取得に失敗しました")

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
        search_layout.addWidget(self.search_btn)

        filter_layout.addLayout(search_layout)
        left_layout.addWidget(filter_widget)

        # 契約リスト
        self.contract_table = QTableWidget()
        self.contract_table.setColumnCount(3)
        self.contract_table.setHorizontalHeaderLabels(
            [
                "契約種別",
                "タイトル",
                "契約当事者",
            ]
        )
        # 列幅をユーザーが可変できるように
        from PySide6.QtWidgets import QHeaderView

        header = self.contract_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        # 初期幅を指定
        self.contract_table.setColumnWidth(0, 80)
        self.contract_table.setColumnWidth(1, 120)
        self.contract_table.setColumnWidth(2, 200)
        self.contract_table.cellClicked.connect(self.load_contract)
        left_layout.addWidget(self.contract_table)

        splitter.addWidget(left_widget)

        # 右側：閲覧エリア
        right_widget = QScrollArea()
        right_widget.setWidgetResizable(True)
        view_widget = QWidget()
        view_layout = QVBoxLayout(view_widget)

        # 契約種別
        edit_contract_layout = QHBoxLayout()
        edit_contract_layout.addWidget(QLabel("契約種別:"))
        self.edit_contract_type = QComboBox()
        self.edit_contract_type.addItems(type_names)
        edit_contract_layout.addWidget(self.edit_contract_type)
        view_layout.addLayout(edit_contract_layout)

        # 契約当事者
        view_layout.addWidget(QLabel("契約当事者:"))
        self.partys_edit = QLineEdit()
        self.partys_edit.setPlaceholderText("例: 甲社,乙社")
        view_layout.addWidget(self.partys_edit)

        # 背景情報
        view_layout.addWidget(QLabel("背景情報:"))
        self.background_info = QTextEdit()
        self.background_info.setMaximumHeight(75)
        view_layout.addWidget(self.background_info)

        # タイトル
        view_layout.addWidget(QLabel("タイトル:"))
        self.title_edit = QLineEdit()
        view_layout.addWidget(self.title_edit)

        # 前文
        view_layout.addWidget(QLabel("前文:"))
        self.introduction_edit = QTextEdit()
        self.introduction_edit.setMaximumHeight(75)
        view_layout.addWidget(self.introduction_edit)

        # 条項エリア（スクロール可能）
        self.clauses_scroll = QScrollArea()
        self.clauses_scroll.setWidgetResizable(True)
        self.clauses_area = QWidget()
        self.clauses_layout = QVBoxLayout(self.clauses_area)
        self.clauses_scroll.setWidget(self.clauses_area)
        view_layout.addWidget(self.clauses_scroll)

        right_widget.setWidget(view_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([500, 1000])  # 初期幅（必要に応じて調整）

        # ボタン群（「ドラフトに戻す」のみ）
        button_layout = QHBoxLayout()
        self.save_btn = QPushButton("ドラフトに戻す")
        self.save_btn.clicked.connect(self.save_draft)
        button_layout.addWidget(self.save_btn)
        view_layout.addLayout(button_layout)

        # splitterをmain_widgetのレイアウトに追加
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(splitter)

        # 初期データ読み込み
        self.load_contract_list()

    def update_button_status(self):
        """契約が選択されている場合のみボタン有効化"""
        contract_id = self.settings.value("contract_master_id", type=str)
        if not contract_id:
            self.save_btn.setEnabled(False)
            return
        contract = self.api.get_contract_by_id(contract_id)
        if not contract:
            self.save_btn.setEnabled(False)
            return
        self.save_btn.setEnabled(True)

    def display_clauses(self, clauses):
        """
        条項リストをclauses_layoutに表示（new_contract_window.pyの方式に準拠）
        条文・審査観点・アクションプランを個別ウィジェットで表示
        """
        # 既存のウィジェットをクリア
        while self.clauses_layout.count():
            item = self.clauses_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        self._current_clauses = list(clauses) if clauses else []
        for idx, clause in enumerate(self._current_clauses):
            clause_widget = self.create_clause_widget(clause, idx)
            self.clauses_layout.addWidget(clause_widget)
        self.clauses_layout.addStretch()

    def create_clause_widget(self, clause, idx):
        from PySide6.QtWidgets import (
            QGridLayout,
            QRadioButton,
            QButtonGroup,
            QVBoxLayout,
        )

        clause_widget = QWidget()
        clause_widget.setContentsMargins(0, 0, 0, 16)
        grid = QGridLayout(clause_widget)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(8)

        # 条項No
        clause_number = QLineEdit()
        clause_number.setMaximumWidth(40)
        clause_number.setText(clause.get("clause_number", ""))
        grid.addWidget(QLabel("条項No"), 0, 0)
        grid.addWidget(clause_number, 1, 0)

        # 条項テキスト
        clause_text = QTextEdit()
        clause_text.setMinimumHeight(250)
        clause_text.setMinimumWidth(500)
        clause_text.setPlainText(clause.get("clause") or clause.get("text", ""))
        grid.addWidget(QLabel("条項テキスト"), 0, 2)
        grid.addWidget(clause_text, 1, 2, 3, 1)

        # 審査観点
        review_points = QTextEdit()
        review_points.setPlaceholderText("審査観点")
        review_points.setMinimumHeight(50)
        review_points.setMinimumWidth(200)
        review_points.setPlainText(clause.get("review_points", ""))
        grid.addWidget(QLabel("審査観点"), 0, 3)
        grid.addWidget(review_points, 1, 3)

        # アクションプラン
        action_plan = QTextEdit()
        action_plan.setPlaceholderText("アクションプラン")
        action_plan.setMinimumHeight(50)
        action_plan.setMinimumWidth(200)
        action_plan.setPlainText(clause.get("action_plan", ""))
        grid.addWidget(QLabel("アクションプラン"), 2, 3)
        grid.addWidget(action_plan, 3, 3)

        return clause_widget

    def load_contract_list(self):
        """契約一覧を取得してテーブルに表示"""
        try:
            self.contract_table.setRowCount(0)
            contracts = self.api.get_approved_contracts()
            filter_type = self.contract_type_combo.currentText()
            if filter_type != "すべて":
                contracts = [
                    c for c in contracts if c.get("contract_type") == filter_type
                ]
            search_text = self.search_edit.text().strip()
            if search_text:
                contracts = [
                    c
                    for c in contracts
                    if search_text.lower() in c.get("title", "").lower()
                    or search_text.lower() in ",".join(c.get("partys", [])).lower()
                ]
            # 契約種別IDと名称のマッピングを取得
            try:
                contract_types = self.api.get_contract_types()
                contract_type_map = {
                    str(t.get("id")): t.get("contract_type", "")
                    for t in contract_types
                    if isinstance(t, dict) and "id" in t
                }
            except Exception:
                contract_type_map = {}

            for contract in contracts:
                row = self.contract_table.rowCount()
                self.contract_table.insertRow(row)
                # contract_type_idから名称を取得
                contract_type_id = str(contract.get("contract_type_id", ""))
                contract_type_name = contract_type_map.get(contract_type_id, "")
                contract_type_item = QTableWidgetItem(contract_type_name)
                contract_type_item.setData(
                    Qt.UserRole, contract.get("id")
                )  # ここでIDをセット
                self.contract_table.setItem(row, 0, contract_type_item)
                title = QTableWidgetItem(contract.get("title", ""))
                self.contract_table.setItem(row, 1, title)
                partys = QTableWidgetItem(",".join(contract.get("partys", [])))
                self.contract_table.setItem(row, 2, partys)
        except Exception as e:
            QMessageBox.critical(
                self, "エラー", f"契約一覧の取得に失敗しました: {str(e)}"
            )

    def save_draft(self):
        """確認後、approval_statusをdraftにして保存"""
        contract_id = self.settings.value("contract_master_id", type=str)
        if not contract_id:
            QMessageBox.warning(self, "エラー", "契約情報が保存されていません")
            return
        contract = self.api.get_contract_by_id(contract_id)
        if not contract:
            QMessageBox.warning(self, "エラー", "契約情報が見つかりません")
            return
        reply = QMessageBox.question(
            self,
            "確認",
            "この契約をドラフトに戻しますか？",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.No:
            return
        try:
            contract["approval_status"] = "draft"
            self.api.upsert_contract(contract)
            QMessageBox.information(
                self, "成功", "契約情報をドラフトに戻しました（ステータス:ドラフト）"
            )
            self.load_contract_list()
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"保存に失敗しました: {str(e)}")

    # revise_contractは廃止

    def load_contract(self, row, col):
        """選択された契約の詳細を表示"""
        try:
            contract_id = self.contract_table.item(row, 0).data(Qt.UserRole)
            contract = self.api.get_contract_by_id(contract_id)
            if not contract:
                QMessageBox.warning(
                    self,
                    "エラー",
                    "契約情報が見つかりません：リストからデータが取得できません",
                )
                return

            # 編集エリア
            idx = self.edit_contract_type.findText(contract.get("contract_type", ""))
            if idx >= 0:
                self.edit_contract_type.setCurrentIndex(idx)
            self.partys_edit.setText(",".join(contract.get("partys", [])))
            self.background_info.setPlainText(contract.get("background_info", ""))
            self.title_edit.setText(contract.get("title", ""))
            self.introduction_edit.setPlainText(contract.get("introduction", ""))
            # 条項エリア
            self.display_clauses(contract.get("clauses", []))
            # 保存用にIDを保持
            self.settings.setValue("contract_master_id", contract_id)
            # ボタンの有効/無効を設定
            self.update_button_status()
        except Exception as e:
            print(f"Error loading contract: {str(e)}")
            QMessageBox.critical(
                self, "エラー", f"契約情報の読み込みに失敗しました: {str(e)}"
            )
