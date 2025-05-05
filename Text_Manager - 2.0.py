import sys
import sqlite3
import os
import re
import datetime
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QTextEdit, QPushButton, QListWidget,
    QMessageBox, QComboBox, QStatusBar, QInputDialog, QAction,
    QShortcut, QFileDialog, QTreeWidget, QTreeWidgetItem
, QMenu)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QIcon, QKeySequence


class TextManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('高效文本管理工具')
        self.setWindowIcon(QIcon('icon.png'))
        
        # 初始化数据库
        self.init_db()
        
        # 设置主窗口
        self.setup_ui()
        
        # 初始化快捷键
        self.setup_shortcuts()
        
        # 初始化自动保存
        self.setup_auto_save()
        
        # 加载数据
        self.load_templates()
        self.load_text_list()
        
        # 当前编辑状态
        self.unsaved_changes = False

    def init_db(self):
        """初始化数据库结构"""
        self.conn = sqlite3.connect('efficient_text_manager.db')
        self.cursor = self.conn.cursor()
        
        # 创建文本表
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS texts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT,
            create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 创建模板表
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            content TEXT NOT NULL,
            shortcut TEXT,
            last_used TIMESTAMP
        )
        ''')
        
        self.conn.commit()

    def setup_ui(self):
        """设置用户界面"""
        self.resize(1000, 700)
        self.setMinimumSize(800, 500)
        
        # 主部件和布局
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        
        # 左侧面板 (30%宽度)
        left_panel = QWidget()
        left_panel.setMinimumWidth(250)
        left_layout = QVBoxLayout(left_panel)
        
        # 文本列表
        self.text_list = QListWidget()
        self.text_list.itemClicked.connect(self.load_text)
        left_layout.addWidget(self.text_list)
        
        # 右侧面板 (70%宽度)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # 标题输入
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("输入标题...")
        self.title_input.textChanged.connect(self.mark_unsaved)
        right_layout.addWidget(self.title_input)
        
        # 内容编辑
        self.content_input = QTextEdit()
        self.content_input.setPlaceholderText("输入内容...")
        self.content_input.textChanged.connect(self.mark_unsaved)
        right_layout.addWidget(self.content_input)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        self.new_btn = QPushButton("新建 (Ctrl+N)")
        self.new_btn.clicked.connect(self.new_text)
        button_layout.addWidget(self.new_btn)
        
        self.save_btn = QPushButton("保存 (Ctrl+S)")
        self.save_btn.clicked.connect(self.save_text)
        button_layout.addWidget(self.save_btn)
        
        self.delete_btn = QPushButton("删除 (Del)")
        self.delete_btn.clicked.connect(self.delete_text)
        button_layout.addWidget(self.delete_btn)
        
        self.template_btn = QPushButton("模板 (Ctrl+T)")
        self.template_btn.clicked.connect(self.show_template_menu)
        button_layout.addWidget(self.template_btn)
        
        right_layout.addLayout(button_layout)
        
        # 状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # 状态标签
        self.status_label = QLabel("就绪")
        self.status_bar.addWidget(self.status_label)
        
        # 自动保存指示器
        self.auto_save_label = QLabel("自动保存: 开启")
        self.status_bar.addPermanentWidget(self.auto_save_label)
        
        # 字数统计
        self.word_count_label = QLabel("字数: 0")
        self.status_bar.addPermanentWidget(self.word_count_label)
        
        # 添加左右面板到主布局
        main_layout.addWidget(left_panel, 3)
        main_layout.addWidget(right_panel, 7)
        
        # 创建菜单
        self.create_menus()

    def create_menus(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件")
        
        new_action = QAction("新建", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.new_text)
        file_menu.addAction(new_action)
        
        save_action = QAction("保存", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_text)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        import_action = QAction("导入文本...", self)
        import_action.triggered.connect(self.import_text)
        file_menu.addAction(import_action)
        
        export_action = QAction("导出当前文本...", self)
        export_action.triggered.connect(self.export_text)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 模板菜单
        template_menu = menubar.addMenu("模板")
        
        manage_templates_action = QAction("管理模板...", self)
        manage_templates_action.triggered.connect(self.manage_templates)
        template_menu.addAction(manage_templates_action)
        
        template_menu.addSeparator()
        
        # 动态模板菜单项将在 load_templates() 中添加
        
        # 设置菜单
        settings_menu = menubar.addMenu("设置")
        
        auto_save_action = QAction("自动保存设置...", self)
        auto_save_action.triggered.connect(self.configure_auto_save)
        settings_menu.addAction(auto_save_action)

    def setup_shortcuts(self):
        """设置快捷键"""
        # 保存快捷键
        self.shortcut_save = QShortcut(QKeySequence("Ctrl+S"), self)
        self.shortcut_save.activated.connect(self.save_text)
        
        # 新建快捷键
        self.shortcut_new = QShortcut(QKeySequence("Ctrl+N"), self)
        self.shortcut_new.activated.connect(self.new_text)
        
        # 删除快捷键
        self.shortcut_delete = QShortcut(QKeySequence("Delete"), self)
        self.shortcut_delete.activated.connect(self.delete_text)
        
        # 模板快捷键
        self.shortcut_template = QShortcut(QKeySequence("Ctrl+T"), self)
        self.shortcut_template.activated.connect(self.show_template_menu)
        
        # 搜索快捷键
        self.shortcut_search = QShortcut(QKeySequence("Ctrl+F"), self)
        self.shortcut_search.activated.connect(self.focus_search)

    def setup_auto_save(self):
        """设置自动保存"""
        self.auto_save_timer = QTimer()
        self.auto_save_timer.timeout.connect(self.auto_save)
        self.auto_save_interval = 30000  # 30秒
        self.auto_save_enabled = True
        self.auto_save_timer.start(self.auto_save_interval)

    def load_text_list(self, search_query=None):
        """加载文本列表"""
        self.text_list.clear()
        
        if search_query:
            query = "SELECT id, title FROM texts WHERE title LIKE ? OR content LIKE ? ORDER BY update_time DESC"
            params = (f"%{search_query}%", f"%{search_query}%")
        else:
            query = "SELECT id, title FROM texts ORDER BY update_time DESC"
            params = ()
        
        self.cursor.execute(query, params)
        texts = self.cursor.fetchall()
        
        for text_id, title in texts:
            self.text_list.addItem(f"{title} (ID: {text_id})")

    def load_text(self, item):
        """加载选中的文本"""
        if self.unsaved_changes:
            reply = QMessageBox.question(
                self, "未保存的更改",
                "当前文本有未保存的更改，是否保存？",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                QMessageBox.Save
            )
            
            if reply == QMessageBox.Save:
                self.save_text()
            elif reply == QMessageBox.Cancel:
                return
        
        text_id = int(item.text().split("(ID: ")[1].rstrip(")"))
        
        self.cursor.execute("SELECT title, content FROM texts WHERE id = ?", (text_id,))
        result = self.cursor.fetchone()
        
        if result:
            title, content = result
            self.current_id = text_id
            self.title_input.setText(title)
            self.content_input.setPlainText(content)
            self.unsaved_changes = False
            self.update_status(f"已加载: {title}")

    def save_text(self):
        """保存当前文本"""
        title = self.title_input.text().strip()
        content = self.content_input.toPlainText()
        
        if not title:
            QMessageBox.warning(self, "警告", "标题不能为空！")
            return
        
        try:
            if hasattr(self, "current_id"):
                # 更新现有文本
                self.cursor.execute(
                    "UPDATE texts SET title = ?, content = ?, update_time = CURRENT_TIMESTAMP WHERE id = ?",
                    (title, content, self.current_id)
                )
            else:
                # 插入新文本
                self.cursor.execute(
                    "INSERT INTO texts (title, content) VALUES (?, ?)",
                    (title, content)
                )
                self.current_id = self.cursor.lastrowid
            
            self.conn.commit()
            self.unsaved_changes = False
            self.load_text_list()
            self.update_status(f"已保存: {title}")
            
            # 更新自动保存指示器
            self.auto_save_label.setText(f"自动保存: {datetime.datetime.now().strftime('%H:%M:%S')}")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存失败: {str(e)}")

    def new_text(self):
        """新建文本"""
        if self.unsaved_changes:
            reply = QMessageBox.question(
                self, "未保存的更改",
                "当前文本有未保存的更改，是否保存？",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                QMessageBox.Save
            )
            
            if reply == QMessageBox.Save:
                self.save_text()
            elif reply == QMessageBox.Cancel:
                return
        
        self.current_id = None
        self.title_input.clear()
        self.content_input.clear()
        self.unsaved_changes = False
        self.title_input.setFocus()
        self.update_status("新建文档")

    def delete_text(self):
        """删除当前文本"""
        if not hasattr(self, "current_id"):
            QMessageBox.warning(self, "警告", "没有选中任何文本！")
            return
        
        reply = QMessageBox.question(
            self, "确认删除",
            "确定要删除这个文本吗？此操作不可恢复！",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.cursor.execute("DELETE FROM texts WHERE id = ?", (self.current_id,))
            self.conn.commit()
            self.new_text()
            self.load_text_list()
            self.update_status("文本已删除")

    def auto_save(self):
        """自动保存当前文本"""
        if self.auto_save_enabled and self.unsaved_changes and self.title_input.text().strip():
            self.save_text()

    def load_templates(self):
        """加载模板列表"""
        self.cursor.execute("SELECT name, shortcut FROM templates ORDER BY name")
        templates = self.cursor.fetchall()
        
        # 清除现有模板菜单项
        template_menu = self.menuBar().findChild(QMenu, "模板")
        if template_menu:
            for action in template_menu.actions()[2:]:  # 跳过前两个固定项
                template_menu.removeAction(action)
        
        # 添加快捷键
        self.template_shortcuts = []
        
        for name, shortcut in templates:
            # 添加到菜单
            action = QAction(name, self)
            if shortcut:
                action.setShortcut(shortcut)
            action.triggered.connect(lambda _, n=name: self.insert_template(n))
            template_menu.addAction(action)
            
            # 注册快捷键
            if shortcut:
                shortcut = QShortcut(QKeySequence(shortcut), self)
                shortcut.activated.connect(lambda n=name: self.insert_template(n))
                self.template_shortcuts.append(shortcut)

    def show_template_menu(self):
        """显示模板菜单"""
        template_menu = self.menuBar().findChild(QMenu, "模板")
        if template_menu:
            template_menu.exec_(self.mapToGlobal(self.template_btn.pos() + self.template_btn.rect().bottomLeft()))

    def insert_template(self, template_name):
        """插入模板内容"""
        self.cursor.execute("SELECT content FROM templates WHERE name = ?", (template_name,))
        result = self.cursor.fetchone()
        
        if result:
            template_content = result[0]
            self.content_input.insertPlainText(template_content)
            self.mark_unsaved()
            
            # 更新最后使用时间
            self.cursor.execute(
                "UPDATE templates SET last_used = CURRENT_TIMESTAMP WHERE name = ?",
                (template_name,)
            )
            self.conn.commit()
            
            self.update_status(f"已插入模板: {template_name}")

    def manage_templates(self):
        """管理模板对话框"""
        from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QListWidget, QLineEdit

        class TemplateManager(QDialog):
            def __init__(self, parent=None):
                super().__init__(parent)
                self.parent = parent
                self.setWindowTitle("管理模板")
                self.setModal(True)
                self.resize(600, 400)
                
                layout = QVBoxLayout(self)
                
                # 模板列表
                self.template_list = QListWidget()
                self.load_templates()
                self.template_list.itemClicked.connect(self.load_template_details)
                layout.addWidget(self.template_list)
                
                # 模板详情表单
                form_layout = QFormLayout()
                
                self.name_input = QLineEdit()
                form_layout.addRow("模板名称:", self.name_input)
                
                self.shortcut_input = QLineEdit()
                self.shortcut_input.setPlaceholderText("例如: Ctrl+Shift+T")
                form_layout.addRow("快捷键:", self.shortcut_input)
                
                self.content_input = QTextEdit()
                self.content_input.setMinimumHeight(150)
                form_layout.addRow("模板内容:", self.content_input)
                
                layout.addLayout(form_layout)
                
                # 按钮
                button_box = QDialogButtonBox()
                self.add_btn = button_box.addButton("添加", QDialogButtonBox.ActionRole)
                self.update_btn = button_box.addButton("更新", QDialogButtonBox.ActionRole)
                self.delete_btn = button_box.addButton("删除", QDialogButtonBox.ActionRole)
                button_box.addButton(QDialogButtonBox.Close)
                
                self.add_btn.clicked.connect(self.add_template)
                self.update_btn.clicked.connect(self.update_template)
                self.delete_btn.clicked.connect(self.delete_template)
                button_box.rejected.connect(self.reject)
                
                layout.addWidget(button_box)
            
            def load_templates(self):
                self.template_list.clear()
                self.parent.cursor.execute("SELECT name FROM templates ORDER BY name")
                templates = [t[0] for t in self.parent.cursor.fetchall()]
                self.template_list.addItems(templates)
            
            def load_template_details(self, item):
                template_name = item.text()
                self.parent.cursor.execute(
                    "SELECT name, shortcut, content FROM templates WHERE name = ?",
                    (template_name,)
                )
                result = self.parent.cursor.fetchone()
                
                if result:
                    name, shortcut, content = result
                    self.name_input.setText(name)
                    self.shortcut_input.setText(shortcut if shortcut else "")
                    self.content_input.setPlainText(content)
            
            def add_template(self):
                name = self.name_input.text().strip()
                shortcut = self.shortcut_input.text().strip()
                content = self.content_input.toPlainText().strip()
                
                if not name:
                    QMessageBox.warning(self, "警告", "模板名称不能为空！")
                    return
                
                if not content:
                    QMessageBox.warning(self, "警告", "模板内容不能为空！")
                    return
                
                try:
                    self.parent.cursor.execute(
                        "INSERT INTO templates (name, shortcut, content) VALUES (?, ?, ?)",
                        (name, shortcut if shortcut else None, content)
                    )
                    self.parent.conn.commit()
                    self.load_templates()
                    self.parent.load_templates()  # 刷新主窗口模板列表
                    QMessageBox.information(self, "成功", "模板已添加！")
                except sqlite3.IntegrityError:
                    QMessageBox.warning(self, "警告", "模板名称已存在！")
            
            def update_template(self):
                if not self.template_list.currentItem():
                    return
                
                old_name = self.template_list.currentItem().text()
                new_name = self.name_input.text().strip()
                shortcut = self.shortcut_input.text().strip()
                content = self.content_input.toPlainText().strip()
                
                if not new_name:
                    QMessageBox.warning(self, "警告", "模板名称不能为空！")
                    return
                
                if not content:
                    QMessageBox.warning(self, "警告", "模板内容不能为空！")
                    return
                
                try:
                    self.parent.cursor.execute(
                        "UPDATE templates SET name = ?, shortcut = ?, content = ? WHERE name = ?",
                        (new_name, shortcut if shortcut else None, content, old_name)
                    )
                    self.parent.conn.commit()
                    self.load_templates()
                    self.parent.load_templates()  # 刷新主窗口模板列表
                    QMessageBox.information(self, "成功", "模板已更新！")
                except sqlite3.IntegrityError:
                    QMessageBox.warning(self, "警告", "模板名称已存在！")
            
            def delete_template(self):
                if not self.template_list.currentItem():
                    return
                
                template_name = self.template_list.currentItem().text()
                
                reply = QMessageBox.question(
                    self, "确认删除",
                    f"确定要删除模板 '{template_name}' 吗？",
                    QMessageBox.Yes | QDialogButtonBox.No,
                    QDialogButtonBox.No
                )
                
                if reply == QMessageBox.Yes:
                    self.parent.cursor.execute(
                        "DELETE FROM templates WHERE name = ?",
                        (template_name,)
                    )
                    self.parent.conn.commit()
                    self.load_templates()
                    self.parent.load_templates()  # 刷新主窗口模板列表
                    self.name_input.clear()
                    self.shortcut_input.clear()
                    self.content_input.clear()
                    QMessageBox.information(self, "成功", "模板已删除！")

        dialog = TemplateManager(self)
        dialog.exec_()

    def configure_auto_save(self):
        """配置自动保存设置"""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QCheckBox, QSpinBox, QDialogButtonBox

        class AutoSaveDialog(QDialog):
            def __init__(self, parent=None):
                super().__init__(parent)
                self.parent = parent
                self.setWindowTitle("自动保存设置")
                self.setModal(True)
                
                layout = QVBoxLayout(self)
                
                # 启用自动保存
                self.enable_check = QCheckBox("启用自动保存")
                self.enable_check.setChecked(self.parent.auto_save_enabled)
                layout.addWidget(self.enable_check)
                
                # 保存间隔
                self.interval_spin = QSpinBox()
                self.interval_spin.setRange(10, 600)  # 10秒到10分钟
                self.interval_spin.setValue(self.parent.auto_save_interval // 1000)
                self.interval_spin.setSuffix(" 秒")
                layout.addWidget(QLabel("自动保存间隔:"))
                layout.addWidget(self.interval_spin)
                
                # 按钮
                button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
                button_box.accepted.connect(self.accept)
                button_box.rejected.connect(self.reject)
                layout.addWidget(button_box)
            
            def accept(self):
                self.parent.auto_save_enabled = self.enable_check.isChecked()
                self.parent.auto_save_interval = self.interval_spin.value() * 1000
                self.parent.auto_save_timer.setInterval(self.parent.auto_save_interval)
                
                if self.parent.auto_save_enabled:
                    self.parent.auto_save_label.setText("自动保存: 开启")
                else:
                    self.parent.auto_save_label.setText("自动保存: 关闭")
                
                super().accept()

        dialog = AutoSaveDialog(self)
        dialog.exec_()

    def import_text(self):
        """导入文本文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择文本文件", "",
            "文本文件 (*.txt);;所有文件 (*.*)"
        )
        
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                # 使用文件名作为标题
                title = os.path.splitext(os.path.basename(file_path))[0]
                self.title_input.setText(title)
                self.content_input.setPlainText(content)
                self.mark_unsaved()
                self.update_status(f"已导入: {title}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导入失败: {str(e)}")

    def export_text(self):
        """导出当前文本"""
        if not self.title_input.text().strip() or not self.content_input.toPlainText().strip():
            QMessageBox.warning(self, "警告", "没有内容可导出！")
            return
        
        default_name = self.title_input.text().strip() + ".txt"
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出文本", default_name,
            "文本文件 (*.txt);;所有文件 (*.*)"
        )
        
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(self.content_input.toPlainText())
                self.update_status(f"已导出到: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")

    def mark_unsaved(self):
        """标记有未保存的更改"""
        self.unsaved_changes = True
        self.update_status("有未保存的更改")

    def update_status(self, message):
        """更新状态栏消息"""
        self.status_label.setText(message)
        
        # 更新字数统计
        content = self.content_input.toPlainText()
        word_count = len(content)  # 简单统计字符数
        self.word_count_label.setText(f"字数: {word_count}")

    def focus_search(self):
        """聚焦到搜索框"""
        pass  # 在这个版本中未实现搜索框

    def closeEvent(self, event):
        """关闭窗口时检查未保存的更改"""
        if self.unsaved_changes:
            reply = QMessageBox.question(
                self, "未保存的更改",
                "当前文本有未保存的更改，是否保存？",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                QMessageBox.Save
            )
            
            if reply == QMessageBox.Save:
                self.save_text()
            elif reply == QMessageBox.Cancel:
                event.ignore()
                return
        
        # 停止自动保存定时器
        self.auto_save_timer.stop()
        
        # 关闭数据库连接
        self.conn.close()
        
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置全局字体
    font = QFont("Microsoft YaHei", 10)
    app.setFont(font)
    
    window = TextManager()
    window.show()
    sys.exit(app.exec_())