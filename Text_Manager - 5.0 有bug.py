import sys
import sqlite3
import re
import datetime
import markdown
import os
from pypinyin import lazy_pinyin
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QTextEdit, QPushButton, QListWidget,
    QMessageBox, QComboBox, QStatusBar, QTabWidget, QFileDialog,
    QTreeWidget, QTreeWidgetItem, QInputDialog, QAction, QMenu, QScrollArea,
    QShortcut, QDialog, QDialogButtonBox, QFormLayout, QCheckBox, QSpinBox,
    QDateEdit, QGroupBox, QRadioButton, QListWidgetItem, QAbstractItemView
)
from PyQt5.QtCore import Qt, QSize, QTimer, QDate
from PyQt5.QtGui import QFont, QIcon, QTextCursor, QKeySequence, QColor


class TextManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('高级文本管理工具 v3.5')
        self.setWindowIcon(QIcon('icon.png'))
        
        # 初始化数据库和UI
        self.init_db()
        self.init_ui()
        self.init_shortcuts()
        
        # 加载初始数据
        self.load_categories()
        self.load_tags()
        self.load_text_list()
        self.load_search_history()
        
        # 自动保存定时器
        self.auto_save_timer = QTimer()
        self.auto_save_timer.timeout.connect(self.auto_save)
        self.auto_save_timer.start(30000)  # 30秒自动保存
        
        # 回收站数据
        self.recycle_bin_enabled = True
        self.current_view = "normal"  # normal/recycle_bin
        self.current_id = None

    def init_db(self):
        """初始化数据库结构（增强版）"""
        self.conn = sqlite3.connect('text_manager_enhanced.db')
        self.cursor = self.conn.cursor()
        
        # 启用SQLite全文搜索
        self.cursor.execute("PRAGMA journal_mode=WAL")
        
        # 核心表（增强）
        self.cursor.executescript('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            parent_id INTEGER DEFAULT 0,
            color TEXT DEFAULT '#FFFFFF'
        );
        
        CREATE TABLE IF NOT EXISTS texts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT,
            category_id INTEGER DEFAULT 0,
            is_markdown BOOLEAN DEFAULT 0,
            create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            word_count INTEGER DEFAULT 0,
            chinese_count INTEGER DEFAULT 0,
            english_count INTEGER DEFAULT 0,
            FOREIGN KEY (category_id) REFERENCES categories(id)
        );
        
        CREATE TABLE IF NOT EXISTS texts_fts (
            id INTEGER PRIMARY KEY,
            title TEXT,
            content TEXT
        );
        
        CREATE VIRTUAL TABLE IF NOT EXISTS texts_fts USING fts5(
            title, content, 
            tokenize="porter unicode61"
        );
        
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        );
        
        CREATE TABLE IF NOT EXISTS text_tags (
            text_id INTEGER NOT NULL,
            tag_id INTEGER NOT NULL,
            PRIMARY KEY (text_id, tag_id),
            FOREIGN KEY (text_id) REFERENCES texts(id),
            FOREIGN KEY (tag_id) REFERENCES tags(id)
        );
        
        CREATE TABLE IF NOT EXISTS templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            content TEXT NOT NULL
        );
        
        CREATE TABLE IF NOT EXISTS search_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT NOT NULL,
            search_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS recycle_bin (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            content TEXT,
            deleted_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS shortcuts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL UNIQUE,
            shortcut TEXT NOT NULL
        );
        ''')
        
        # 初始化默认快捷键
        self.init_default_shortcuts()
        self.conn.commit()

    def init_default_shortcuts(self):
        """初始化默认快捷键"""
        default_shortcuts = [
            ('save', 'Ctrl+S'),
            ('new', 'Ctrl+N'),
            ('delete', 'Del'),
            ('search', 'Ctrl+F'),
            ('toggle_preview', 'Ctrl+P'),
            ('toggle_view', 'Ctrl+Shift+R')
        ]
        
        for action, shortcut in default_shortcuts:
            self.cursor.execute(
                "INSERT OR IGNORE INTO shortcuts (action, shortcut) VALUES (?, ?)",
                (action, shortcut)
            )

    def init_ui(self):
        """初始化用户界面（增强版）"""
        self.resize(1200, 800)
        self.setMinimumSize(QSize(900, 600))
        
        # 主布局
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        self.main_layout = QHBoxLayout()
        self.main_widget.setLayout(self.main_layout)
        
        # 左侧面板 (分类树+文本列表)
        self.left_panel = QWidget()
        self.left_layout = QVBoxLayout()
        self.left_panel.setLayout(self.left_layout)
        
        # 视图切换按钮
        self.view_toggle_btn = QPushButton("切换到回收站" if self.current_view == "normal" else "切换到正常视图")
        self.view_toggle_btn.clicked.connect(self.toggle_view)
        self.left_layout.addWidget(self.view_toggle_btn)
        
        # 分类树
        self.category_tree = QTreeWidget()
        self.category_tree.setHeaderLabel('分类')
        self.category_tree.itemClicked.connect(self.filter_by_category)
        self.left_layout.addWidget(self.category_tree)
        
        # 高级搜索组
        self.advanced_search_group = QGroupBox("高级搜索")
        self.advanced_search_layout = QVBoxLayout()
        
        # 日期范围搜索
        self.date_search_layout = QHBoxLayout()
        self.date_from = QDateEdit()
        self.date_from.setDate(QDate.currentDate().addMonths(-1))
        self.date_to = QDateEdit()
        self.date_to.setDate(QDate.currentDate())
        self.date_search_layout.addWidget(QLabel("从:"))
        self.date_search_layout.addWidget(self.date_from)
        self.date_search_layout.addWidget(QLabel("到:"))
        self.date_search_layout.addWidget(self.date_to)
        self.advanced_search_layout.addLayout(self.date_search_layout)
        
        # 字数范围
        self.word_count_layout = QHBoxLayout()
        self.word_count_min = QSpinBox()
        self.word_count_min.setRange(0, 99999)
        self.word_count_max = QSpinBox()
        self.word_count_max.setRange(0, 99999)
        self.word_count_max.setValue(99999)
        self.word_count_layout.addWidget(QLabel("字数:"))
        self.word_count_layout.addWidget(self.word_count_min)
        self.word_count_layout.addWidget(QLabel("-"))
        self.word_count_layout.addWidget(self.word_count_max)
        self.advanced_search_layout.addLayout(self.word_count_layout)
        
        # 搜索模式
        self.search_mode = QComboBox()
        self.search_mode.addItems(["普通搜索", "全文检索"])
        self.advanced_search_layout.addWidget(self.search_mode)
        
        self.advanced_search_group.setLayout(self.advanced_search_layout)
        self.advanced_search_group.setCheckable(True)
        self.advanced_search_group.setChecked(False)
        self.left_layout.addWidget(self.advanced_search_group)
        
        # 标签云
        self.tag_cloud = QComboBox()
        self.tag_cloud.setEditable(True)
        self.tag_cloud.setPlaceholderText("选择或输入标签...")
        self.tag_cloud.currentTextChanged.connect(self.filter_by_tag)
        self.left_layout.addWidget(QLabel('标签筛选:'))
        self.left_layout.addWidget(self.tag_cloud)
        
        # 搜索历史
        self.search_history_combo = QComboBox()
        self.search_history_combo.setPlaceholderText("搜索历史...")
        self.search_history_combo.currentTextChanged.connect(self.apply_search_history)
        self.left_layout.addWidget(QLabel('搜索历史:'))
        self.left_layout.addWidget(self.search_history_combo)
        
        # 搜索区域
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText('搜索标题/内容/拼音首字母...')
        self.search_input.textChanged.connect(self.search_texts)
        self.left_layout.addWidget(self.search_input)
        
        # 文本列表
        self.text_list = QListWidget()
        self.text_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.text_list.itemClicked.connect(self.load_text)
        self.left_layout.addWidget(self.text_list)
        
        # 批量操作按钮
        self.batch_btn = QPushButton("批量操作")
        self.batch_btn.clicked.connect(self.show_batch_operations)
        self.left_layout.addWidget(self.batch_btn)
        
        # 右侧面板 (编辑区)
        self.right_panel = QTabWidget()
        self.main_layout.addWidget(self.left_panel, 3)
        self.main_layout.addWidget(self.right_panel, 7)
        
        # 创建编辑选项卡
        self.create_edit_tab()
        self.create_preview_tab()
        
        # 状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # 字数统计
        self.word_count_label = QLabel('字数: 0 (中:0 英:0)')
        self.reading_time_label = QLabel('阅读时间: 0分钟')
        self.status_bar.addPermanentWidget(self.word_count_label)
        self.status_bar.addPermanentWidget(self.reading_time_label)
        
        # 自动保存指示器
        self.save_indicator = QLabel('🟢 已自动保存')
        self.status_bar.addPermanentWidget(self.save_indicator)
        self.save_indicator.setVisible(False)
        
        # 菜单栏
        self.create_menus()

    def create_edit_tab(self):
        """创建编辑选项卡（增强版）"""
        self.edit_tab = QWidget()
        self.edit_layout = QVBoxLayout()
        self.edit_tab.setLayout(self.edit_layout)
        
        # 标题和分类
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText('标题')
        self.edit_layout.addWidget(self.title_input)
        
        # 分类选择
        self.category_combo = QComboBox()
        self.category_combo.addItem('未分类', 0)
        self.edit_layout.addWidget(self.category_combo)
        
        # 标签编辑
        self.tag_edit = QLineEdit()
        self.tag_edit.setPlaceholderText('输入标签，用逗号分隔')
        self.edit_layout.addWidget(self.tag_edit)
        
        # 格式选择
        self.format_combo = QComboBox()
        self.format_combo.addItem('纯文本')
        self.format_combo.addItem('Markdown')
        self.format_combo.currentIndexChanged.connect(self.toggle_markdown)
        self.edit_layout.addWidget(self.format_combo)
        
        # 文本编辑区
        self.content_input = QTextEdit()
        self.content_input.textChanged.connect(self.update_word_count)
        self.edit_layout.addWidget(self.content_input)
        
        # 操作按钮
        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton('保存')
        self.btn_save.clicked.connect(self.save_text)
        self.btn_new = QPushButton('新建')
        self.btn_new.clicked.connect(self.new_text)
        self.btn_delete = QPushButton('删除')
        self.btn_delete.clicked.connect(self.delete_text)
        self.btn_restore = QPushButton('从回收站恢复')
        self.btn_restore.clicked.connect(self.restore_from_recycle_bin)
        self.btn_restore.setVisible(False)
        
        btn_layout.addWidget(self.btn_new)
        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_delete)
        btn_layout.addWidget(self.btn_restore)
        self.edit_layout.addLayout(btn_layout)
        
        self.right_panel.addTab(self.edit_tab, "编辑")

    def create_preview_tab(self):
        """创建Markdown预览选项卡"""
        self.preview_tab = QWidget()
        self.preview_layout = QVBoxLayout()
        self.preview_tab.setLayout(self.preview_layout)
        
        self.preview_label = QLabel()
        self.preview_label.setWordWrap(True)
        self.preview_label.setOpenExternalLinks(True)
        
        scroll = QScrollArea()
        scroll.setWidget(self.preview_label)
        scroll.setWidgetResizable(True)
        self.preview_layout.addWidget(scroll)
        
        self.right_panel.addTab(self.preview_tab, "预览")

    def toggle_view(self):
        """切换正常视图和回收站视图"""
        if self.current_view == "normal":
            self.current_view = "recycle_bin"
            self.view_toggle_btn.setText("切换到正常视图")
            self.btn_restore.setVisible(True)
            self.btn_delete.setText("永久删除")
        else:
            self.current_view = "normal"
            self.view_toggle_btn.setText("切换到回收站")
            self.btn_restore.setVisible(False)
            self.btn_delete.setText("删除")
        
        self.load_text_list()

    def show_batch_operations(self):
        """显示批量操作对话框"""
        dialog = QDialog(self)
        dialog.setWindowTitle("批量操作")
        layout = QVBoxLayout()
        
        # 批量修改分类
        category_group = QGroupBox("批量修改分类")
        category_layout = QVBoxLayout()
        self.batch_category_combo = QComboBox()
        self.batch_category_combo.addItem('未分类', 0)
        self.cursor.execute("SELECT id, name FROM categories ORDER BY name")
        for cat_id, name in self.cursor.fetchall():
            self.batch_category_combo.addItem(name, cat_id)
        
        category_layout.addWidget(self.batch_category_combo)
        btn_apply_category = QPushButton("应用分类")
        btn_apply_category.clicked.connect(lambda: self.batch_update_category(dialog))
        category_layout.addWidget(btn_apply_category)
        category_group.setLayout(category_layout)
        layout.addWidget(category_group)
        
        # 批量添加标签
        tag_group = QGroupBox("批量添加标签")
        tag_layout = QVBoxLayout()
        self.batch_tag_input = QLineEdit()
        self.batch_tag_input.setPlaceholderText("输入要添加的标签，用逗号分隔")
        tag_layout.addWidget(self.batch_tag_input)
        btn_apply_tags = QPushButton("添加标签")
        btn_apply_tags.clicked.connect(lambda: self.batch_add_tags(dialog))
        tag_layout.addWidget(btn_apply_tags)
        tag_group.setLayout(tag_layout)
        layout.addWidget(tag_group)
        
        # 批量导出
        export_group = QGroupBox("批量导出")
        export_layout = QVBoxLayout()
        self.export_format_combo = QComboBox()
        self.export_format_combo.addItems(["Markdown (.md)", "纯文本 (.txt)", "HTML (.html)"])
        export_layout.addWidget(self.export_format_combo)
        
        self.export_dir_btn = QPushButton("选择导出目录")
        self.export_dir_btn.clicked.connect(self.select_export_directory)
        export_layout.addWidget(self.export_dir_btn)
        
        self.export_dir_label = QLabel("未选择目录")
        export_layout.addWidget(self.export_dir_label)
        
        btn_export = QPushButton("导出选中项")
        btn_export.clicked.connect(lambda: self.batch_export(dialog))
        export_layout.addWidget(btn_export)
        export_group.setLayout(export_layout)
        layout.addWidget(export_group)
        
        # 关闭按钮
        btn_close = QPushButton("关闭")
        btn_close.clicked.connect(dialog.close)
        layout.addWidget(btn_close)
        
        dialog.setLayout(layout)
        dialog.exec_()

    def select_export_directory(self):
        """选择导出目录"""
        dir_path = QFileDialog.getExistingDirectory(self, "选择导出目录")
        if dir_path:
            self.export_dir_label.setText(dir_path)

    def batch_export(self, dialog):
        """批量导出选中文本"""
        selected_items = self.text_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "请先选择要导出的文本!")
            return
            
        export_dir = self.export_dir_label.text()
        if not export_dir or export_dir == "未选择目录":
            QMessageBox.warning(self, "警告", "请先选择导出目录!")
            return
            
        export_format = self.export_format_combo.currentText()
        text_ids = [item.data(Qt.UserRole) for item in selected_items]
        
        try:
            for text_id in text_ids:
                if self.current_view == "recycle_bin":
                    self.cursor.execute(
                        "SELECT title, content FROM recycle_bin WHERE id = ?",
                        (text_id,)
                    )
                else:
                    self.cursor.execute(
                        "SELECT title, content, is_markdown FROM texts WHERE id = ?",
                        (text_id,)
                    )
                
                result = self.cursor.fetchone()
                if not result:
                    continue
                    
                if self.current_view == "recycle_bin":
                    title, content = result
                    is_markdown = False
                else:
                    title, content, is_markdown = result
                
                # 确定文件扩展名
                if export_format == "Markdown (.md)":
                    ext = ".md"
                elif export_format == "HTML (.html)":
                    ext = ".html"
                    if is_markdown:
                        content = markdown.markdown(content)
                else:
                    ext = ".txt"
                
                # 清理文件名
                clean_title = re.sub(r'[\\/*?:"<>|]', "", title)
                file_path = os.path.join(export_dir, f"{clean_title}{ext}")
                
                # 处理重复文件名
                counter = 1
                while os.path.exists(file_path):
                    file_path = os.path.join(export_dir, f"{clean_title}_{counter}{ext}")
                    counter += 1
                
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
            
            dialog.close()
            QMessageBox.information(self, "完成", f"已成功导出{len(text_ids)}个文件到:\n{export_dir}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")

    def batch_update_category(self, dialog):
        """批量更新分类"""
        selected_items = self.text_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "请先选择要操作的文本!")
            return
            
        category_id = self.batch_category_combo.currentData()
        text_ids = [item.data(Qt.UserRole) for item in selected_items]
        
        try:
            for text_id in text_ids:
                self.cursor.execute(
                    "UPDATE texts SET category_id = ? WHERE id = ?",
                    (category_id, text_id)
                )
            
            self.conn.commit()
            self.load_text_list()
            dialog.close()
            self.show_status_message(f"已批量更新{len(text_ids)}个文本的分类", 3000)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"批量更新失败: {str(e)}")

    def batch_add_tags(self, dialog):
        """批量添加标签"""
        selected_items = self.text_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "请先选择要操作的文本!")
            return
            
        new_tags = [tag.strip() for tag in self.batch_tag_input.text().split(",") if tag.strip()]
        if not new_tags:
            QMessageBox.warning(self, "警告", "请输入有效的标签!")
            return
            
        text_ids = [item.data(Qt.UserRole) for item in selected_items]
        
        try:
            for text_id in text_ids:
                for tag_name in new_tags:
                    # 查找或创建标签
                    self.cursor.execute("SELECT id FROM tags WHERE name=?", (tag_name,))
                    tag_id = self.cursor.fetchone()
                    
                    if not tag_id:
                        self.cursor.execute("INSERT INTO tags (name) VALUES (?)", (tag_name,))
                        tag_id = self.cursor.lastrowid
                    else:
                        tag_id = tag_id[0]
                    
                    # 检查是否已存在关联
                    self.cursor.execute(
                        "SELECT 1 FROM text_tags WHERE text_id=? AND tag_id=?",
                        (text_id, tag_id)
                    )
                    if not self.cursor.fetchone():
                        self.cursor.execute(
                            "INSERT INTO text_tags (text_id, tag_id) VALUES (?, ?)",
                            (text_id, tag_id)
                        )
            
            self.conn.commit()
            self.load_text_list()
            self.load_tags()
            dialog.close()
            self.show_status_message(f"已批量添加标签到{len(text_ids)}个文本", 3000)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"批量添加标签失败: {str(e)}")

    def load_search_history(self):
        """加载搜索历史"""
        self.search_history_combo.clear()
        self.cursor.execute(
            "SELECT query FROM search_history ORDER BY search_time DESC LIMIT 10"
        )
        history = [item[0] for item in self.cursor.fetchall()]
        self.search_history_combo.addItems(history)

    def apply_search_history(self, query):
        """应用搜索历史"""
        if query:
            self.search_input.setText(query)
            self.search_texts()

    def save_search_history(self, query):
        """保存搜索历史"""
        if query.strip():
            self.cursor.execute(
                "INSERT INTO search_history (query) VALUES (?)",
                (query,)
            )
            self.conn.commit()
            self.load_search_history()

    def search_texts(self):
        """增强版搜索功能"""
        search_query = self.search_input.text().strip()
        
        if search_query:
            self.save_search_history(search_query)
        
        if self.advanced_search_group.isChecked():
            # 高级搜索模式
            self.advanced_search(search_query)
        else:
            # 普通搜索模式
            self.normal_search(search_query)

    def normal_search(self, search_query=None):
        """普通搜索模式"""
        if self.current_view == "recycle_bin":
            self.load_recycle_bin_list(search_query)
            return
        
        query = '''
        SELECT t.id, t.title, c.name 
        FROM texts t
        LEFT JOIN categories c ON t.category_id = c.id
        WHERE 1=1
        '''
        params = []
        
        if search_query:
            pinyin_query = self.get_pinyin_query(search_query)
            if self.search_mode.currentText() == "全文检索":
                # 使用FTS全文搜索
                fts_query = f'''
                AND t.id IN (
                    SELECT rowid FROM texts_fts
                    WHERE texts_fts MATCH ?
                )
                '''
                query += fts_query
                params.append(search_query)
            else:
                # 普通搜索
                query += '''
                AND (t.title LIKE ? OR t.content LIKE ? 
                     OR t.title LIKE ? OR t.content LIKE ?)
                '''
                params.extend([
                    f'%{search_query}%', f'%{search_query}%',
                    f'%{pinyin_query}%', f'%{pinyin_query}%'
                ])
        
        query += ' ORDER BY t.update_time DESC'
        
        self.cursor.execute(query, params)
        texts = self.cursor.fetchall()
        
        self.text_list.clear()
        for text_id, title, category_name in texts:
            item = QListWidgetItem(f"{title} [{category_name or '未分类'}] (ID: {text_id})")
            item.setData(Qt.UserRole, text_id)
            self.text_list.addItem(item)

    def advanced_search(self, search_query=None):
        """高级搜索模式"""
        if self.current_view == "recycle_bin":
            self.load_recycle_bin_list(search_query)
            return
        
        query = '''
        SELECT t.id, t.title, c.name, t.create_time, t.update_time, t.word_count
        FROM texts t
        LEFT JOIN categories c ON t.category_id = c.id
        WHERE 1=1
        '''
        params = []
        
        # 日期范围
        date_from = self.date_from.date().toString("yyyy-MM-dd")
        date_to = self.date_to.date().addDays(1).toString("yyyy-MM-dd")  # 包含当天
        query += " AND t.update_time BETWEEN ? AND ?"
        params.extend([date_from, date_to])
        
        # 字数范围
        word_min = self.word_count_min.value()
        word_max = self.word_count_max.value()
        if word_max > 0:
            query += " AND t.word_count BETWEEN ? AND ?"
            params.extend([word_min, word_max])
        
        # 搜索查询
        if search_query:
            if self.search_mode.currentText() == "全文检索":
                # 使用FTS全文搜索
                fts_query = f'''
                AND t.id IN (
                    SELECT rowid FROM texts_fts
                    WHERE texts_fts MATCH ?
                )
                '''
                query += fts_query
                params.append(search_query)
            else:
                # 普通搜索
                pinyin_query = self.get_pinyin_query(search_query)
                query += '''
                AND (t.title LIKE ? OR t.content LIKE ? 
                     OR t.title LIKE ? OR t.content LIKE ?)
                '''
                params.extend([
                    f'%{search_query}%', f'%{search_query}%',
                    f'%{pinyin_query}%', f'%{pinyin_query}%'
                ])
        
        query += ' ORDER BY t.update_time DESC'
        
        self.cursor.execute(query, params)
        texts = self.cursor.fetchall()
        
        self.text_list.clear()
        for text_id, title, category_name, create_time, update_time, word_count in texts:
            item_text = f"{title} [{category_name or '未分类'}] (ID: {text_id})\n"
            item_text += f"字数: {word_count} | 创建: {create_time} | 更新: {update_time}"
            
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, text_id)
            self.text_list.addItem(item)

    def load_recycle_bin_list(self, search_query=None):
        """加载回收站列表"""
        query = "SELECT id, original_id, title, deleted_time FROM recycle_bin WHERE 1=1"
        params = []
        
        if search_query:
            query += " AND title LIKE ?"
            params.append(f'%{search_query}%')
        
        query += " ORDER BY deleted_time DESC"
        
        self.cursor.execute(query, params)
        items = self.cursor.fetchall()
        
        self.text_list.clear()
        for item_id, original_id, title, deleted_time in items:
            item = QListWidgetItem(f"{title} (原ID: {original_id}, 删除于: {deleted_time})")
            item.setData(Qt.UserRole, item_id)
            self.text_list.addItem(item)

    def restore_from_recycle_bin(self):
        """从回收站恢复文本"""
        selected_items = self.text_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "请先选择要恢复的文本!")
            return
            
        item_id = selected_items[0].data(Qt.UserRole)
        
        # 获取回收站内容
        self.cursor.execute(
            "SELECT original_id, title, content FROM recycle_bin WHERE id = ?",
            (item_id,)
        )
        result = self.cursor.fetchone()
        
        if not result:
            QMessageBox.warning(self, "警告", "找不到要恢复的文本!")
            return
            
        original_id, title, content = result
        
        try:
            # 检查原始文本是否还存在
            self.cursor.execute("SELECT 1 FROM texts WHERE id = ?", (original_id,))
            if self.cursor.fetchone():
                # 如果存在，则创建新记录
                self.cursor.execute(
                    "INSERT INTO texts (title, content) VALUES (?, ?)",
                    (title, content)
                )
            else:
                # 如果不存在，则恢复原始记录
                self.cursor.execute(
                    "INSERT INTO texts (id, title, content) VALUES (?, ?, ?)",
                    (original_id, title, content)
                )
            
            # 从回收站删除
            self.cursor.execute("DELETE FROM recycle_bin WHERE id = ?", (item_id,))
            self.conn.commit()
            
            self.load_text_list()
            self.show_status_message("文本已从回收站恢复", 2000)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"恢复失败: {str(e)}")

    def update_word_count(self):
        """增强版字数统计"""
        content = self.content_input.toPlainText()
        
        # 中文统计
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', content))
        
        # 英文单词统计
        english_words = len(re.findall(r'\b[a-zA-Z]+\b', content))
        
        # 总字数
        total = len(content)  # 简单统计总字符数
        
        # 阅读时间估算 (中文300字/分钟，英文200词/分钟)
        reading_time = max(1, round((chinese_chars / 300) + (english_words / 200)))
        
        # 更新UI
        self.word_count_label.setText(f'字数: {total} (中:{chinese_chars} 英:{english_words})')
        self.reading_time_label.setText(f'阅读时间: ~{reading_time}分钟')
        
        # 如果是Markdown模式，更新预览
        if self.format_combo.currentIndex() == 1:
            self.update_preview()

    def delete_text(self):
        """增强版删除功能（支持回收站）"""
        if not hasattr(self, 'current_id') or self.current_id is None:
            QMessageBox.warning(self, '警告', '没有选中任何文本!')
            return
        
        if self.current_view == "recycle_bin":
            # 永久删除
            reply = QMessageBox.question(
                self, '确认永久删除', 
                '确定要永久删除这个文本吗? 此操作不可撤销!', 
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                try:
                    self.cursor.execute(
                        "DELETE FROM recycle_bin WHERE id = ?", 
                        (self.current_id,)
                    )
                    self.conn.commit()
                    self.load_text_list()
                    self.show_status_message('已永久删除!', 2000)
                    self.new_text()
                except Exception as e:
                    QMessageBox.critical(self, '错误', f'删除失败: {str(e)}')
            return
        
        # 普通删除（移动到回收站）
        reply = QMessageBox.question(
            self, '确认删除', 
            '确定要删除这个文本吗?', 
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                # 获取文本内容
                self.cursor.execute(
                    "SELECT title, content FROM texts WHERE id = ?", 
                    (self.current_id,)
                )
                title, content = self.cursor.fetchone()
                
                # 添加到回收站
                self.cursor.execute(
                    "INSERT INTO recycle_bin (original_id, title, content) VALUES (?, ?, ?)",
                    (self.current_id, title, content)
                )
                
                # 删除原文本
                self.cursor.execute(
                    "DELETE FROM texts WHERE id = ?", 
                    (self.current_id,)
                )
                self.cursor.execute(
                    "DELETE FROM text_tags WHERE text_id = ?", 
                    (self.current_id,)
                )
                
                self.conn.commit()
                self.new_text()
                self.load_text_list()
                self.show_status_message('文本已移至回收站!', 2000)
            except Exception as e:
                QMessageBox.critical(self, '错误', f'删除失败: {str(e)}')

    def save_text(self):
        """保存文本（增强字数统计）"""
        title = self.title_input.text().strip()
        content = self.content_input.toPlainText().strip()
        category_id = self.category_combo.currentData()
        is_markdown = self.format_combo.currentIndex() == 1
        tags = [tag.strip() for tag in self.tag_edit.text().split(',') if tag.strip()]
        
        if not title:
            QMessageBox.warning(self, '警告', '标题不能为空!')
            return
        
        # 计算字数
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', content))
        english_words = len(re.findall(r'\b[a-zA-Z]+\b', content))
        word_count = len(content)
        
        try:
            if hasattr(self, 'current_id') and self.current_id is not None:
                # 更新现有文本
                self.cursor.execute('''
                UPDATE texts 
                SET title=?, content=?, category_id=?, is_markdown=?, 
                    update_time=CURRENT_TIMESTAMP, word_count=?, 
                    chinese_count=?, english_count=?
                WHERE id=?
                ''', (title, content, category_id, is_markdown, 
                     word_count, chinese_chars, english_words, 
                     self.current_id))
                text_id = self.current_id
            else:
                # 插入新文本
                self.cursor.execute('''
                INSERT INTO texts (title, content, category_id, is_markdown, 
                                 word_count, chinese_count, english_count)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (title, content, category_id, is_markdown, 
                     word_count, chinese_chars, english_words))
                text_id = self.cursor.lastrowid
                self.current_id = text_id
            
            # 更新FTS索引
            self.update_fts_index(text_id, title, content)
            
            # 更新标签
            self.cursor.execute('DELETE FROM text_tags WHERE text_id=?', (text_id,))
            
            for tag_name in tags:
                # 查找或创建标签
                self.cursor.execute('SELECT id FROM tags WHERE name=?', (tag_name,))
                tag_id = self.cursor.fetchone()
                
                if not tag_id:
                    self.cursor.execute('INSERT INTO tags (name) VALUES (?)', (tag_name,))
                    tag_id = self.cursor.lastrowid
                else:
                    tag_id = tag_id[0]
                
                # 关联文本和标签
                self.cursor.execute('INSERT INTO text_tags (text_id, tag_id) VALUES (?, ?)', 
                                   (text_id, tag_id))
            
            self.conn.commit()
            
            # 更新UI
            self.load_text_list()
            self.load_tags()
            self.show_status_message('保存成功!', 2000)
            
            # 显示自动保存指示器
            self.show_auto_save_indicator()
            
        except Exception as e:
            QMessageBox.critical(self, '错误', f'保存失败: {str(e)}')

    def update_fts_index(self, text_id, title, content):
        """更新全文搜索索引"""
        # 删除旧索引（如果存在）
        self.cursor.execute(
            "DELETE FROM texts_fts WHERE rowid = ?",
            (text_id,)
        )
        
        # 插入新索引
        self.cursor.execute(
            "INSERT INTO texts_fts (rowid, title, content) VALUES (?, ?, ?)",
            (text_id, title, content)
        )

    def load_text(self, item):
        """加载选中的文本内容"""
        text_id = item.data(Qt.UserRole)
        
        if self.current_view == "recycle_bin":
            # 加载回收站内容
            self.cursor.execute(
                "SELECT title, content FROM recycle_bin WHERE id = ?",
                (text_id,)
            )
            result = self.cursor.fetchone()
            
            if not result:
                return
                
            title, content = result
            
            self.current_id = text_id
            self.title_input.setText(title)
            self.content_input.setPlainText(content)
            self.category_combo.setCurrentIndex(0)
            self.tag_edit.clear()
            self.format_combo.setCurrentIndex(0)
            return
        
        # 正常加载文本
        self.cursor.execute('''
        SELECT t.title, t.content, t.category_id, t.is_markdown, 
               group_concat(tg.name, ', ') as tags,
               t.word_count, t.chinese_count, t.english_count
        FROM texts t
        LEFT JOIN text_tags tt ON t.id = tt.text_id
        LEFT JOIN tags tg ON tt.tag_id = tg.id
        WHERE t.id = ?
        GROUP BY t.id
        ''', (text_id,))
        
        result = self.cursor.fetchone()
        if not result:
            return
            
        title, content, category_id, is_markdown, tags, word_count, chinese_count, english_count = result
        
        self.current_id = text_id
        self.title_input.setText(title)
        self.content_input.setPlainText(content)
        
        # 设置分类
        index = self.category_combo.findData(category_id)
        if index >= 0:
            self.category_combo.setCurrentIndex(index)
        
        # 设置标签
        self.tag_edit.setText(tags if tags else '')
        
        # 设置格式
        self.format_combo.setCurrentIndex(1 if is_markdown else 0)
        self.toggle_markdown()
        
        # 更新字数统计
        self.word_count_label.setText(f'字数: {word_count} (中:{chinese_count} 英:{english_count})')
        reading_time = max(1, round((chinese_count / 300) + (english_count / 200)))
        self.reading_time_label.setText(f'阅读时间: ~{reading_time}分钟')

    def toggle_markdown(self):
        """切换Markdown模式"""
        if self.format_combo.currentIndex() == 1:  # Markdown模式
            self.update_preview()
        else:
            self.preview_label.clear()

    def update_preview(self):
        """更新Markdown预览"""
        if self.format_combo.currentIndex() == 1:  # 只在Markdown模式下更新
            content = self.content_input.toPlainText()
            html = markdown.markdown(content)
            self.preview_label.setText(html)

    def load_categories(self):
        """加载分类数据"""
        self.category_tree.clear()
        self.cursor.execute("SELECT id, name, parent_id FROM categories ORDER BY parent_id, name")
        categories = self.cursor.fetchall()
        
        # 构建树形结构
        categories_dict = {}
        for cat_id, name, parent_id in categories:
            item = QTreeWidgetItem([name])
            item.setData(0, Qt.UserRole, cat_id)
            categories_dict[cat_id] = item
            
            if parent_id == 0:
                self.category_tree.addTopLevelItem(item)
            else:
                parent_item = categories_dict.get(parent_id)
                if parent_item:
                    parent_item.addChild(item)
        
        # 更新分类下拉框
        self.category_combo.clear()
        self.category_combo.addItem('未分类', 0)
        for cat_id, name, _ in categories:
            self.category_combo.addItem(name, cat_id)

    def load_tags(self):
        """加载标签数据"""
        self.tag_cloud.clear()
        self.cursor.execute("SELECT name FROM tags ORDER BY name")
        tags = [tag[0] for tag in self.cursor.fetchall()]
        self.tag_cloud.addItems(tags)

    def load_text_list(self, category_id=None, tag_name=None, search_query=None):
        """加载文本列表"""
        if self.current_view == "recycle_bin":
            self.load_recycle_bin_list(search_query)
            return
        
        query = '''
        SELECT t.id, t.title, c.name 
        FROM texts t
        LEFT JOIN categories c ON t.category_id = c.id
        WHERE 1=1
        '''
        params = []
        
        # 分类筛选
        if category_id:
            query += ' AND t.category_id = ?'
            params.append(category_id)
        
        # 标签筛选
        if tag_name:
            query += '''
            AND t.id IN (
                SELECT text_id FROM text_tags tt
                JOIN tags tg ON tt.tag_id = tg.id
                WHERE tg.name = ?
            )
            '''
            params.append(tag_name)
        
        # 搜索查询
        if search_query:
            pinyin_query = self.get_pinyin_query(search_query)
            query += '''
            AND (t.title LIKE ? OR t.content LIKE ? 
                 OR t.title LIKE ? OR t.content LIKE ?)
            '''
            params.extend([
                f'%{search_query}%', f'%{search_query}%',
                f'%{pinyin_query}%', f'%{pinyin_query}%'
            ])
        
        query += ' ORDER BY t.update_time DESC'
        
        self.cursor.execute(query, params)
        texts = self.cursor.fetchall()
        
        self.text_list.clear()
        for text_id, title, category_name in texts:
            item = QListWidgetItem(f"{title} [{category_name or '未分类'}] (ID: {text_id})")
            item.setData(Qt.UserRole, text_id)
            self.text_list.addItem(item)

    def filter_by_category(self, item):
        """按分类筛选文本"""
        category_id = item.data(0, Qt.UserRole)
        self.load_text_list(category_id=category_id)

    def filter_by_tag(self, tag_name):
        """按标签筛选文本"""
        if tag_name:
            self.load_text_list(tag_name=tag_name)

    def get_pinyin_query(self, text):
        """将中文转换为拼音首字母查询字符串"""
        result = []
        for char in text:
            if '\u4e00' <= char <= '\u9fff':  # 中文字符
                pinyin = lazy_pinyin(char)
                if pinyin:
                    result.append(pinyin[0][0].lower())
            else:
                result.append(char)
        return ''.join(result)

    def new_text(self):
        """新建文本"""
        self.current_id = None
        self.title_input.clear()
        self.content_input.clear()
        self.tag_edit.clear()
        self.category_combo.setCurrentIndex(0)
        self.format_combo.setCurrentIndex(0)
        self.title_input.setFocus()

    def show_auto_save_indicator(self):
        """显示自动保存指示器"""
        self.save_indicator.setText('🟢 ' + datetime.datetime.now().strftime('%H:%M:%S 已保存'))
        self.save_indicator.setVisible(True)
        QTimer.singleShot(3000, lambda: self.save_indicator.setVisible(False))

    def auto_save(self):
        """自动保存当前文本"""
        if hasattr(self, 'current_id') and self.title_input.text().strip():
            self.save_text()

    def show_status_message(self, message, timeout=0):
        """在状态栏显示临时消息"""
        self.status_bar.showMessage(message, timeout)

    def init_shortcuts(self):
        """初始化快捷键（从数据库加载）"""
        # 清除现有快捷键
        if hasattr(self, 'shortcut_save'):
            self.shortcut_save.deleteLater()
        if hasattr(self, 'shortcut_new'):
            self.shortcut_new.deleteLater()
        if hasattr(self, 'shortcut_delete'):
            self.shortcut_delete.deleteLater()
        if hasattr(self, 'shortcut_search'):
            self.shortcut_search.deleteLater()
        if hasattr(self, 'shortcut_preview'):
            self.shortcut_preview.deleteLater()
        if hasattr(self, 'shortcut_toggle_view'):
            self.shortcut_toggle_view.deleteLater()
        
        # 从数据库加载快捷键
        self.cursor.execute("SELECT action, shortcut FROM shortcuts")
        shortcuts = {action: shortcut for action, shortcut in self.cursor.fetchall()}
        
        # 设置快捷键
        self.shortcut_save = QShortcut(QKeySequence(shortcuts.get('save', 'Ctrl+S')), self)
        self.shortcut_save.activated.connect(self.save_text)
        
        self.shortcut_new = QShortcut(QKeySequence(shortcuts.get('new', 'Ctrl+N')), self)
        self.shortcut_new.activated.connect(self.new_text)
        
        self.shortcut_delete = QShortcut(QKeySequence(shortcuts.get('delete', 'Del')), self)
        self.shortcut_delete.activated.connect(self.delete_text)
        
        self.shortcut_search = QShortcut(QKeySequence(shortcuts.get('search', 'Ctrl+F')), self)
        self.shortcut_search.activated.connect(lambda: self.search_input.setFocus())
        
        self.shortcut_preview = QShortcut(QKeySequence(shortcuts.get('toggle_preview', 'Ctrl+P')), self)
        self.shortcut_preview.activated.connect(lambda: self.right_panel.setCurrentIndex(1))
        
        self.shortcut_toggle_view = QShortcut(QKeySequence(shortcuts.get('toggle_view', 'Ctrl+Shift+R')), self)
        self.shortcut_toggle_view.activated.connect(self.toggle_view)

    def configure_shortcuts(self):
        """配置快捷键对话框"""
        dialog = QDialog(self)
        dialog.setWindowTitle("快捷键设置")
        layout = QFormLayout()
        
        # 从数据库加载当前快捷键
        self.cursor.execute("SELECT action, shortcut FROM shortcuts")
        current_shortcuts = {action: shortcut for action, shortcut in self.cursor.fetchall()}
        
        # 保存快捷键输入框
        self.save_shortcut_edit = QLineEdit(current_shortcuts.get('save', 'Ctrl+S'))
        layout.addRow("保存文本:", self.save_shortcut_edit)
        
        # 新建快捷键输入框
        self.new_shortcut_edit = QLineEdit(current_shortcuts.get('new', 'Ctrl+N'))
        layout.addRow("新建文本:", self.new_shortcut_edit)
        
        # 删除快捷键输入框
        self.delete_shortcut_edit = QLineEdit(current_shortcuts.get('delete', 'Del'))
        layout.addRow("删除文本:", self.delete_shortcut_edit)
        
        # 搜索快捷键输入框
        self.search_shortcut_edit = QLineEdit(current_shortcuts.get('search', 'Ctrl+F'))
        layout.addRow("搜索文本:", self.search_shortcut_edit)
        
        # 预览快捷键输入框
        self.preview_shortcut_edit = QLineEdit(current_shortcuts.get('toggle_preview', 'Ctrl+P'))
        layout.addRow("切换预览:", self.preview_shortcut_edit)
        
        # 切换视图快捷键输入框
        self.toggle_view_shortcut_edit = QLineEdit(current_shortcuts.get('toggle_view', 'Ctrl+Shift+R'))
        layout.addRow("切换回收站:", self.toggle_view_shortcut_edit)
        
        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(lambda: self.save_shortcuts(dialog))
        button_box.rejected.connect(dialog.reject)
        layout.addRow(button_box)
        
        dialog.setLayout(layout)
        dialog.exec_()

    def save_shortcuts(self, dialog):
        """保存快捷键设置"""
        shortcuts = [
            ('save', self.save_shortcut_edit.text()),
            ('new', self.new_shortcut_edit.text()),
            ('delete', self.delete_shortcut_edit.text()),
            ('search', self.search_shortcut_edit.text()),
            ('toggle_preview', self.preview_shortcut_edit.text()),
            ('toggle_view', self.toggle_view_shortcut_edit.text())
        ]
        
        try:
            for action, shortcut in shortcuts:
                self.cursor.execute(
                    "UPDATE shortcuts SET shortcut = ? WHERE action = ?",
                    (shortcut, action)
                )
            
            self.conn.commit()
            self.init_shortcuts()  # 重新初始化快捷键
            dialog.close()
            self.show_status_message("快捷键设置已保存", 2000)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存快捷键失败: {str(e)}")

    def import_text(self):
        """导入文本文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, '选择文本文件', '',
            '文本文件 (*.txt *.md);;所有文件 (*.*)'
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 使用文件名作为标题
                title = os.path.splitext(os.path.basename(file_path))[0]
                self.title_input.setText(title)
                self.content_input.setPlainText(content)
                
                # 根据扩展名设置格式
                if file_path.lower().endswith('.md'):
                    self.format_combo.setCurrentIndex(1)
                
                self.show_status_message(f'已导入: {title}', 2000)
            except Exception as e:
                QMessageBox.critical(self, '错误', f'导入失败: {str(e)}')

    def export_text(self):
        """导出当前文本"""
        if not hasattr(self, 'current_id') or not self.title_input.text():
            QMessageBox.warning(self, '警告', '没有可导出的内容!')
            return
            
        default_name = self.title_input.text()
        if self.format_combo.currentIndex() == 1:  # Markdown
            default_name += '.md'
        else:
            default_name += '.txt'
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, '导出文件', default_name,
            'Markdown文件 (*.md);;文本文件 (*.txt);;HTML文件 (*.html);;所有文件 (*.*)'
        )
        
        if file_path:
            try:
                content = self.content_input.toPlainText()
                
                # 如果是HTML导出且是Markdown内容
                if file_path.lower().endswith('.html') and self.format_combo.currentIndex() == 1:
                    content = markdown.markdown(content)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.show_status_message(f'已导出到: {file_path}', 3000)
            except Exception as e:
                QMessageBox.critical(self, '错误', f'导出失败: {str(e)}')

    def batch_export(self):
        """批量导出（通过批量操作对话框实现）"""
        self.show_batch_operations()

    def insert_template(self):
        """插入模板"""
        self.cursor.execute('SELECT name FROM templates ORDER BY name')
        templates = [t[0] for t in self.cursor.fetchall()]
        
        if not templates:
            QMessageBox.information(self, '提示', '没有可用模板')
            return
            
        template_name, ok = QInputDialog.getItem(
            self, '选择模板', '模板列表:', 
            templates, 0, False
        )
        
        if ok and template_name:
            self.cursor.execute(
                'SELECT content FROM templates WHERE name=?',
                (template_name,)
            )
            content = self.cursor.fetchone()[0]
            self.content_input.insertPlainText(content)
            self.show_status_message(f'已插入模板: {template_name}', 2000)

    def add_category(self):
        """添加新分类"""
        name, ok = QInputDialog.getText(
            self, '新建分类', '输入分类名称:',
            QLineEdit.Normal, ''
        )
        
        if ok and name:
            try:
                self.cursor.execute(
                    'INSERT INTO categories (name) VALUES (?)',
                    (name,)
                )
                self.conn.commit()
                self.load_categories()
                self.show_status_message(f'分类"{name}"已添加!', 2000)
            except sqlite3.IntegrityError:
                QMessageBox.warning(self, '警告', '分类名称已存在!')

    def manage_categories(self):
        """管理分类对话框"""
        # 实现分类管理界面 (可扩展)
        QMessageBox.information(self, '提示', '分类管理功能将在后续版本实现')

    def create_menus(self):
        """创建菜单栏（增强版）"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu('文件')
        
        import_action = QAction('导入文本', self)
        import_action.triggered.connect(self.import_text)
        file_menu.addAction(import_action)
        
        export_action = QAction('导出当前文本', self)
        export_action.triggered.connect(self.export_text)
        file_menu.addAction(export_action)
        
        batch_export_action = QAction('批量导出', self)
        batch_export_action.triggered.connect(self.batch_export)
        file_menu.addAction(batch_export_action)
        
        file_menu.addSeparator()
        
        recycle_bin_action = QAction('回收站', self)
        recycle_bin_action.triggered.connect(self.toggle_view)
        file_menu.addAction(recycle_bin_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('退出', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 编辑菜单
        edit_menu = menubar.addMenu('编辑')
        
        template_action = QAction('插入模板', self)
        template_action.triggered.connect(self.insert_template)
        edit_menu.addAction(template_action)
        
        shortcuts_action = QAction('快捷键设置', self)
        shortcuts_action.triggered.connect(self.configure_shortcuts)
        edit_menu.addAction(shortcuts_action)
        
        # 搜索菜单
        search_menu = menubar.addMenu('搜索')
        
        advanced_search_action = QAction('高级搜索', self)
        advanced_search_action.setCheckable(True)
        advanced_search_action.setChecked(False)
        advanced_search_action.triggered.connect(
            lambda: self.advanced_search_group.setChecked(not self.advanced_search_group.isChecked())
        )
        search_menu.addAction(advanced_search_action)
        
        clear_search_action = QAction('清除搜索条件', self)
        clear_search_action.triggered.connect(self.clear_search)
        search_menu.addAction(clear_search_action)
        
        # 分类菜单
        category_menu = menubar.addMenu('分类')
        
        new_category_action = QAction('新建分类', self)
        new_category_action.triggered.connect(self.add_category)
        category_menu.addAction(new_category_action)
        
        manage_categories_action = QAction('管理分类', self)
        manage_categories_action.triggered.connect(self.manage_categories)
        category_menu.addAction(manage_categories_action)
        
        # 工具菜单
        tools_menu = menubar.addMenu('工具')
        
        batch_action = QAction('批量操作', self)
        batch_action.triggered.connect(self.show_batch_operations)
        tools_menu.addAction(batch_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu('帮助')
        about_action = QAction('关于', self)
        help_menu.addAction(about_action)

    def clear_search(self):
        """清除搜索条件"""
        self.search_input.clear()
        self.advanced_search_group.setChecked(False)
        self.load_text_list()

    def closeEvent(self, event):
        """关闭窗口时执行清理"""
        self.auto_save_timer.stop()
        self.conn.close()
        event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # 设置全局字体
    font = QFont('Microsoft YaHei', 10)
    app.setFont(font)
    
    window = TextManager()
    window.show()
    sys.exit(app.exec_())