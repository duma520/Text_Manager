__version__ = "6.41.0"
__build_date__ = "2025-05-14"
__author__ = "杜玛"
__license__ = "MIT"
__copyright__ = "© 2025 杜玛"
__url__ = "https://github.com/duma520"




import sys
import sqlite3
import re
import datetime
import time
import markdown
import os
import math
import glob
from pypinyin import lazy_pinyin
# 布局类
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout
# 控件类
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QLineEdit, 
    QTextEdit, QPushButton, QListWidget, QMessageBox, QComboBox,
    QStatusBar, QTabWidget, QFileDialog, QTreeWidget, QTreeWidgetItem,
    QInputDialog, QAction, QMenu, QScrollArea, QShortcut, QDialog,
    QDialogButtonBox, QCheckBox, QSpinBox, QDateEdit, QGroupBox,
    QListWidgetItem, QToolBar, QFontComboBox, QToolButton, QButtonGroup,
    QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar
)
from PyQt5.QtCore import Qt, QSize, QTimer, QDate, QMimeData
from PyQt5.QtGui import QFont, QIcon, QTextCursor, QKeySequence, QPainter, QColor
from PyQt5.QtChart import QChart, QPieSeries, QChartView


class TextManager(QMainWindow):
    # 类变量 - 集中管理关于信息
    ABOUT = {
        "name": "高级文本管理工具",
        "version": "6.36.0",
        "build_date": "2025-05-14",
        "author": "杜玛",
        "license": "MIT",
        "copyright": "© 2025 杜玛",
        "url": "https://github.com/duma520",
        "description": "一个功能强大的文本管理工具，支持多种格式和高级搜索功能",
        "features": [
            "支持纯文本、Markdown和HTML格式",
            "全文搜索和高级筛选",
            "标签和分类管理",
            "回收站功能",
            "批量操作",
            "文本分析和统计"
        ]
    }

    # 类变量 - 集中管理配置参数
    SIMILAR_TEXT_DISPLAY_COUNT = 0  # 控制显示的相似文章数量，0表示显示全部


    def __init__(self):
        super().__init__()
        title = f"{self.ABOUT['name']} v{self.ABOUT['version']} (Build {self.ABOUT['build_date']})"
        self.setWindowTitle(title)
        self.setWindowIcon(QIcon('icon.ico'))
        
        # 初始化变量
        self.current_view = "normal"  # normal/recycle_bin
        self.current_id = None
        self.db_version = 2  # 当前数据库最新版本
        self.default_format = 2  # 默认使用即见即所得模式
        
        # 初始化数据库和UI
        self.init_db()       # 现在包含版本检查和升级
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

        # 添加全局弹窗样式
        self.setStyleSheet("""
            /* 通用弹窗按钮样式 */
            QMessageBox QPushButton, QDialog QPushButton {
                min-width: 80px;
                padding: 6px 12px;
                border-radius: 4px;
                border: 1px solid #cbd5e1;
                background-color: #e2e8f0;
                color: #1e293b;  /* 深灰色文字 */
            }
            QMessageBox QPushButton:hover, QDialog QPushButton:hover {
                background-color: #cbd5e1;
            }
            /* 确认/提交类按钮 */
            QPushButton[type="submit"], QPushButton[role="accept"] {
                background-color: #10b981;  /* 绿色 */
                color: white;
            }
            /* 取消/关闭类按钮 */
            QPushButton[type="cancel"], QPushButton[role="reject"] {
                background-color: #94a3b8;  /* 灰色 */
                color: white;
            }
            /* 进度条样式 */
            QProgressBar {
                border: 1px solid #cbd5e1;
                border-radius: 4px;
                text-align: center;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #3b82f6;
                border-radius: 3px;
            }            

        """)

        # 备份配置
        self.backup_config = {
            'max_backups': 30,  # 最大备份数量
            'backup_dir': os.path.join(os.path.dirname(__file__), 'backups'),
            'backup_prefix': 'text_manager_backup_'
        }
        
        # 确保备份目录存在
        os.makedirs(self.backup_config['backup_dir'], exist_ok=True)

    def init_db(self):
        """初始化数据库并检查升级"""
        self.conn = sqlite3.connect('text_manager_enhanced.db')
        self.cursor = self.conn.cursor()
        
        # 启用SQLite全文搜索
        self.cursor.execute("PRAGMA journal_mode=WAL")
        
        # 创建版本控制表（如果不存在）
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS db_version (
            version INTEGER PRIMARY KEY,
            update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 获取当前数据库版本
        self.cursor.execute('SELECT version FROM db_version ORDER BY version DESC LIMIT 1')
        current_version = self.cursor.fetchone()
        current_version = current_version[0] if current_version else 0
        
        # 执行必要的升级
        self.upgrade_database(current_version)
        
        # 初始化表结构
        self.init_tables()
        self.init_default_shortcuts()
        self.conn.commit()

    def upgrade_database(self, current_version):
        """执行数据库升级"""
        if current_version < 1:
            # 初始版本创建
            self.init_tables()
            self.cursor.execute('INSERT INTO db_version (version) VALUES (1)')
            print("数据库初始化为版本1")
        
        if current_version < 2:
            # 版本2升级：添加is_html列
            try:
                self.cursor.execute('ALTER TABLE texts ADD COLUMN is_html BOOLEAN DEFAULT 0')
                self.cursor.execute('INSERT INTO db_version (version) VALUES (2)')
                print("数据库升级到版本2：添加HTML支持")
            except sqlite3.OperationalError as e:
                if "duplicate column" not in str(e):
                    raise
        
        # 未来版本升级可以在此继续添加
        # if current_version < 3:
        #     self.upgrade_to_version_3()

    def init_tables(self):
        """初始化所有表结构（不含版本控制）"""
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
            is_html BOOLEAN DEFAULT 0,
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
            name TEXT NOT NULL UNIQUE,
            color TEXT DEFAULT '#FFFFFF'  
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
        """初始化用户界面（功能色区分版）"""
        # 基于功能分色的专业样式表
        self.setStyleSheet("""
            /* ========== 基础样式 ========== */
            QMainWindow {
                background-color: #f8fafc;
            }
            QWidget {
                font-family: 'Segoe UI', 'Microsoft YaHei';
                font-size: 13px;
            }



            /* ========== 功能按钮色彩系统 ========== */
            /* 主操作按钮基础样式 */
            QPushButton {
                min-width: 80px;
                padding: 7px 12px;
                border-radius: 4px;
                font-weight: 500;
                border: none;
                color: white;
            }
            
            /* 1. 新建 - 创造型操作 (活力蓝) */
            QPushButton.new-action {
                background-color: #3b82f6;
                background-image: linear-gradient(to bottom, #3b82f6, #2563eb);
            }
            QPushButton.new-action:hover {
                background-color: #2563eb;
            }
            QPushButton.new-action:pressed {
                background-color: #1d4ed8;
            }
            
            /* 2. 保存 - 关键操作 (安全绿) */
            QPushButton.save-action {
                background-color: #10b981;
                background-image: linear-gradient(to bottom, #10b981, #059669);
            }
            QPushButton.save-action:hover {
                background-color: #059669;
            }
            QPushButton.save-action:pressed {
                background-color: #047857;
            }
            
            /* 3. 删除/危险操作 (警示红) */
            QPushButton.danger-action {
                background-color: #ef4444;
                background-image: linear-gradient(to bottom, #ef4444, #dc2626);
            }
            QPushButton.danger-action:hover {
                background-color: #dc2626;
            }
            QPushButton.danger-action:pressed {
                background-color: #b91c1c;
            }
            
            /* 4. 文本分析 - 分析型操作 (智慧紫) */
            QPushButton.analyze-action {
                background-color: #8b5cf6;
                background-image: linear-gradient(to bottom, #8b5cf6, #7c3aed);
            }
            QPushButton.analyze-action:hover {
                background-color: #7c3aed;
            }
            QPushButton.analyze-action:pressed {
                background-color: #6d28d9;
            }
            
            /* 5. 复制/导出 - 数据操作 (友好橙) */
            QPushButton.data-action {
                background-color: #f97316;
                background-image: linear-gradient(to bottom, #f97316, #ea580c);
            }
            QPushButton.data-action:hover {
                background-color: #ea580c;
            }
            QPushButton.data-action:pressed {
                background-color: #c2410c;
            }
            
            /* 6. 辅助操作 (中性灰) */
            QPushButton.secondary-action {
                background-color: #94a3b8;
                background-image: linear-gradient(to bottom, #94a3b8, #64748b);
                color: #f8fafc;
            }
            QPushButton.secondary-action:hover {
                background-color: #64748b;
            }
            
            /* ========== 按钮状态标识 ========== */
            QPushButton[urgent="true"] {
                animation: pulse 2s infinite;
            }
            @keyframes pulse {
                0% { opacity: 1; }
                50% { opacity: 0.7; }
                100% { opacity: 1; }
            }
            
            /* ========== 图标按钮样式 ========== */
            QPushButton.icon-button {
                min-width: auto;
                padding: 5px;
                border-radius: 3px;
            }
                           
            /* 视图切换按钮 - 特殊状态色 (深紫色) */
            QPushButton.view-toggle-action {
                background-color: #6b46c1;
                background-image: linear-gradient(to bottom, #6b46c1, #553c9a);
                color: white;
            }
            QPushButton.view-toggle-action:hover {
                background-color: #553c9a;
            }
            QPushButton.view-toggle-action:pressed {
                background-color: #44337a;
            }
            /* 批量操作按钮 - 特殊操作色 (深青色) */
            QPushButton.batch-action {
                background-color: #0d9488;
                background-image: linear-gradient(to bottom, #0d9488, #0f766e);
                color: white;
            }
            QPushButton.batch-action:hover {
                background-color: #0f766e;
            }
            QPushButton.batch-action:pressed {
                background-color: #115e59;
            }
            /* 批量操作对话框按钮样式 */
            QDialog QPushButton {
                min-width: 80px;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QDialog QPushButton[type="submit"] {
                background-color: #3b82f6;  /* 蓝色确认按钮 */
                color: white;
            }
            QDialog QPushButton[type="cancel"] {
                background-color: #94a3b8;  /* 灰色取消按钮 */
                color: white;
            }
        """)

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
        
        # 视图切换按钮（使用特殊状态色）
        self.view_toggle_btn = QPushButton("切换到回收站")
        self.view_toggle_btn.setProperty("class", "view-toggle-action")  # 添加专属类名
        self.view_toggle_btn.setCursor(Qt.PointingHandCursor)
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
        self.text_list.itemClicked.connect(self.load_text)
        self.left_layout.addWidget(self.text_list)
        
        # 批量操作按钮（使用特殊操作色）
        self.batch_btn = QPushButton(QIcon.fromTheme('system-run'), "批量操作")
        self.batch_btn.setProperty("class", "batch-action")  # 添加专属类名
        self.batch_btn.setCursor(Qt.PointingHandCursor)
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
        self.save_indicator = QLabel('✅ 已自动保存')
        self.status_bar.addPermanentWidget(self.save_indicator)
        self.save_indicator.setVisible(False)
        
        # 添加阅读进度条
        self.reading_progress = QProgressBar()
        self.reading_progress.setMaximum(100)
        self.reading_progress.setMinimum(0)
        self.reading_progress.setFixedWidth(150)
        self.reading_progress.setFormat("进度: %p%")
        self.reading_progress.setVisible(False)  # 默认隐藏
        self.status_bar.addPermanentWidget(self.reading_progress)

        # 添加阅读进度标签
        self.reading_progress_label = QLabel("0%")
        self.reading_progress_label.setFixedWidth(40)
        self.status_bar.addPermanentWidget(self.reading_progress_label)
        
        # 菜单栏
        self.create_menus()



    def show_text_analysis(self):
        """显示文本分析对话框"""
        if not hasattr(self, 'current_id') or not self.current_id:
            QMessageBox.warning(self, "警告", "请先选择要分析的文本!")
            return
        
        # 获取当前文本格式
        format_index = self.format_combo.currentIndex()
        
        # 根据格式获取内容
        try:
            if format_index == 0:  # 纯文本
                content = self.content_input.toPlainText()
            elif format_index == 1:  # Markdown
                content = self.content_input.toPlainText()
            else:  # HTML
                content = self.wysiwyg_editor.toPlainText() if self.wysiwyg_editor.isVisible() else self.content_input.toPlainText()
            
            if not content.strip():
                QMessageBox.warning(self, "警告", "当前文本内容为空!")
                return
        except Exception as e:
            QMessageBox.warning(self, "错误", f"获取文本内容失败: {str(e)}")
            return

        # 使用主窗口状态栏的进度条
        self.reading_progress.setVisible(True)
        self.reading_progress.setRange(0, 100)
        self.reading_progress.setValue(0)
        self.reading_progress.setFormat("分析进度: %p%")

        dialog = QDialog(self)
        dialog.setWindowTitle("文本分析")
        dialog.resize(800, 600)
        layout = QVBoxLayout()
        
        # 创建选项卡
        tab_widget = QTabWidget()
        
        # 1. 基本统计选项卡
        stats_tab = QWidget()
        stats_layout = QVBoxLayout()
        
        # 添加更多统计信息
        self.stats_info = QTextEdit()
        self.stats_info.setReadOnly(True)
        stats_layout.addWidget(self.stats_info)
        
        # 字数统计图表
        self.stats_chart_view = QChartView()
        stats_layout.addWidget(self.stats_chart_view)
        
        # 关键词提取
        self.keywords_label = QLabel("关键词: ")
        stats_layout.addWidget(self.keywords_label)
        
        # 添加段落统计
        self.paragraph_stats = QLabel("段落统计: ")
        stats_layout.addWidget(self.paragraph_stats)
        
        stats_tab.setLayout(stats_layout)
        tab_widget.addTab(stats_tab, "基本统计")
        
        # 2. 相似文本选项卡 (增强版)
        similar_tab = QWidget()
        similar_layout = QVBoxLayout()
        
        # 相似度分析说明
        similarity_desc = QLabel("基于以下特征计算相似度:")
        similar_layout.addWidget(similarity_desc)
        
        # 相似度特征表格
        self.similarity_table = QTableWidget()
        self.similarity_table.setColumnCount(3)
        self.similarity_table.setHorizontalHeaderLabels(["特征", "权重", "贡献值"])
        self.similarity_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        similar_layout.addWidget(self.similarity_table)
        
        # 相似文本列表 (增强)
        self.similar_texts_list = QListWidget()
        self.similar_texts_list.setStyleSheet("""
            QListWidget::item {
                border-bottom: 1px solid #eee;
                padding: 8px;
            }
            QListWidget::item:hover {
                background: #f5f5f5;
            }
        """)
        self.similar_texts_list.itemClicked.connect(self.show_similarity_detail)
        similar_layout.addWidget(QLabel(f"最相似的{self.SIMILAR_TEXT_DISPLAY_COUNT}篇文本:"))
        similar_layout.addWidget(self.similar_texts_list)
        
        # 相似度详情面板
        self.similarity_detail = QTextEdit()
        self.similarity_detail.setReadOnly(True)
        self.similarity_detail.setFixedHeight(150)
        similar_layout.addWidget(QLabel("相似度分析详情:"))
        similar_layout.addWidget(self.similarity_detail)
        
        similar_tab.setLayout(similar_layout)
        tab_widget.addTab(similar_tab, "相似文本")

        # 3. 文本特征选项卡 (增强版)
        features_tab = QWidget()
        features_layout = QVBoxLayout()
        
        # 特征概览卡片
        features_group = QGroupBox("文本特征概览")
        features_grid = QGridLayout()
        
        # 1. 可读性卡片
        readability_card = QGroupBox("📖 可读性")
        readability_layout = QVBoxLayout()
        self.readability_score = QLabel("正在计算...")
        self.readability_bar = QProgressBar()
        self.readability_bar.setTextVisible(False)
        self.readability_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #ddd;
                border-radius: 3px;
                height: 10px;
            }
            QProgressBar::chunk {
                background: #4CAF50;
            }
        """)
        readability_layout.addWidget(self.readability_score)
        readability_layout.addWidget(self.readability_bar)
        readability_card.setLayout(readability_layout)
        
        # 2. 情感分析卡片
        sentiment_card = QGroupBox("😊 情感倾向")
        sentiment_layout = QVBoxLayout()
        self.sentiment_label = QLabel("正在分析...")
        self.sentiment_graph = QLabel()
        self.sentiment_graph.setFixedHeight(30)
        sentiment_layout.addWidget(self.sentiment_label)
        sentiment_layout.addWidget(self.sentiment_graph)
        sentiment_card.setLayout(sentiment_layout)
        
        # 3. 关键词卡片
        keywords_card = QGroupBox("🔑 关键词云")
        keywords_layout = QVBoxLayout()
        self.keywords_label = QLabel()
        self.keywords_label.setWordWrap(True)
        keywords_layout.addWidget(self.keywords_label)
        keywords_card.setLayout(keywords_layout)
        
        # 4. 风格特征卡片
        style_card = QGroupBox("✍️ 写作风格")
        style_layout = QVBoxLayout()
        self.style_label = QLabel("正在分析...")
        style_layout.addWidget(self.style_label)
        style_card.setLayout(style_layout)
        
        # 添加到网格
        features_grid.addWidget(readability_card, 0, 0)
        features_grid.addWidget(sentiment_card, 0, 1)
        features_grid.addWidget(keywords_card, 1, 0)
        features_grid.addWidget(style_card, 1, 1)
        features_group.setLayout(features_grid)
        features_layout.addWidget(features_group)
        
        # 详细特征表格
        self.features_table = QTableWidget()
        self.features_table.setColumnCount(3)
        self.features_table.setHorizontalHeaderLabels(["特征类型", "特征值", "说明"])
        self.features_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        features_layout.addWidget(self.features_table)
        
        features_tab.setLayout(features_layout)
        tab_widget.addTab(features_tab, "文本特征")

        # 添加选项卡到对话框
        layout.addWidget(tab_widget)
        
        # 添加"正在分析"标签和进度条
        self.analyzing_label = QLabel("正在分析文本，请稍候...")
        self.analyzing_label.setAlignment(Qt.AlignCenter)
        self.analyzing_label.setStyleSheet("font-size: 14px; color: #555;")
        layout.addWidget(self.analyzing_label)
        
        self.analysis_progress = QProgressBar()
        self.analysis_progress.setRange(0, 100)
        self.analysis_progress.setValue(0)
        layout.addWidget(self.analysis_progress)
        
        # 添加分析按钮
        analyze_btn = QPushButton("开始分析")
        analyze_btn.clicked.connect(lambda: self.analyze_text(dialog, content))
        layout.addWidget(analyze_btn)
        
        dialog.setLayout(layout)

        # 创建后立即执行分析
        self.analyze_text(dialog, content)
        
        dialog.exec_()
        
        # 分析完成后恢复进度条原始状态
        self.reading_progress.setFormat("进度: %p%")
        self.reading_progress.setValue(0)


    def analyze_text(self, dialog, content):
        """执行文本分析"""
        print("[DEBUG] 开始文本分析")
    
        # 初始化进度条
        self.reading_progress.setValue(5)
        QApplication.processEvents()  # 强制更新UI
    
        try:
            # 1. 初始化统计信息文本框
            self.stats_info.clear()  # 先清空内容
            print("[DEBUG] 初始化统计信息文本框")
            self.reading_progress.setValue(10)
            QApplication.processEvents()

            # 2. 基本统计
            self.update_basic_stats(content)
            print("[DEBUG] 基本统计信息更新")
            self.reading_progress.setValue(20)
            QApplication.processEvents()
            
            # 3. 关键词提取
            keywords = self.extract_keywords(content)
            self.keywords_label.setText(f"关键词: {', '.join(keywords)}")
            print("[DEBUG] 关键词提取:", keywords)
            self.reading_progress.setValue(35)
            QApplication.processEvents()
            
            # 4. 查找相似文本
            self.find_similar_texts(content)
            self.reading_progress.setValue(50)
            QApplication.processEvents()
            
            # 5. 新增段落统计
            paragraph_count = len([p for p in content.split('\n') if p.strip()])
            self.paragraph_stats.setText(f"段落统计: {paragraph_count}段")
            print("[DEBUG] 段落统计:", paragraph_count)
            self.reading_progress.setValue(60)
            QApplication.processEvents()
            
            # 6. 完整版可读性评分计算 (Flesch Reading Ease + 中文适配)
            # 英文部分计算 (Flesch Reading Ease)
            english_words = re.findall(r'\b[a-zA-Z]+\b', content)
            english_sentences = re.findall(r'[.!?]+', content)
            
            flesch_score = 0
            if english_words and english_sentences:
                avg_words_per_sentence = len(english_words) / len(english_sentences)
                avg_syllables_per_word = sum(len(re.findall(r'[aeiouyAEIOUY]+', word)) for word in english_words) / len(english_words)
                flesch_score = 206.835 - (1.015 * avg_words_per_sentence) - (84.6 * avg_syllables_per_word)
            
            # 中文部分计算 (基于平均句长和词汇难度)
            chinese_chars = re.findall(r'[\u4e00-\u9fff]', content)
            chinese_sentences = re.split(r'[。！？；;]+', content)
            chinese_sentences = [s for s in chinese_sentences if s.strip()]
            
            chinese_score = 0
            if chinese_chars and chinese_sentences:
                avg_chars_per_sentence = len(chinese_chars) / len(chinese_sentences)
                # 中文可读性经验公式 (基于句长和常用词比例)
                common_word_ratio = len(re.findall(r'[的了是在有这我你他我们他们]', content)) / len(chinese_chars)
                chinese_score = 100 - (avg_chars_per_sentence * 0.5) + (common_word_ratio * 20)
            
            # 综合评分 (根据中英文内容比例)
            total_chars = len(content)
            if total_chars > 0:
                english_ratio = len(''.join(english_words)) / total_chars
                chinese_ratio = len(''.join(chinese_chars)) / total_chars
                readability = (flesch_score * english_ratio + chinese_score * chinese_ratio)
                readability = max(0, min(100, readability))  # 限制在0-100范围内
                
                # 评分描述
                if readability >= 90:
                    level = "非常容易"
                    description = (
                        "文本极其易读，适合所有读者，包括小学生。\n"
                        "典型文本：儿童读物、简单对话、基础说明文。\n"
                        "平均句子长度：8个词或更少\n"
                        "平均每词音节数：1.0或更少"
                    )
                elif readability >= 80:
                    level = "容易"
                    description = (
                        "文本非常易读，适合普通大众阅读。\n"
                        "典型文本：流行小说、报纸文章、博客文章。\n"
                        "平均句子长度：8-12个词\n"
                        "平均每词音节数：1.0-1.2"
                    )
                elif readability >= 70:
                    level = "较容易" 
                    description = (
                        "文本比较容易理解，适合13-15岁学生。\n"
                        "典型文本：青少年读物、杂志文章。\n"
                        "平均句子长度：12-15个词\n"
                        "平均每词音节数：1.2-1.4"
                    )
                elif readability >= 60:
                    level = "标准"
                    description = (
                        "文本难度适中，适合高中毕业生阅读。\n"
                        "典型文本：普通报刊、大众非小说类书籍。\n"
                        "平均句子长度：15-17个词\n"
                        "平均每词音节数：1.4-1.6"
                    )
                elif readability >= 50:
                    level = "较难"
                    description = (
                        "文本有一定难度，适合大学生阅读。\n"
                        "典型文本：学术论文、专业杂志、技术文档。\n"
                        "平均句子长度：17-20个词\n"
                        "平均每词音节数：1.6-1.8"
                    )
                elif readability >= 30:
                    level = "困难"
                    description = (
                        "文本难度较高，需要专业知识或高等教育背景。\n"
                        "典型文本：法律文件、学术论文、专业文献。\n"
                        "平均句子长度：20-25个词\n"
                        "平均每词音节数：1.8-2.0"
                    )
                else:
                    level = "非常困难"
                    description = (
                        "文本极其难懂，需要专业领域知识。\n"
                        "典型文本：哲学著作、高级技术规范、古典文学。\n"
                        "平均句子长度：25个词以上\n"
                        "平均每词音节数：2.0以上"
                    )

                
                self.readability_score.setText(
                    f"可读性评分: {readability:.1f}/100 ({level})\n"
                    f"英文部分: {flesch_score:.1f} 中文部分: {chinese_score:.1f}"
                )
            else:
                self.readability_score.setText("可读性评分: 无有效内容")
            
            print(f"[DEBUG] 可读性评分: {readability:.1f} (英文:{flesch_score:.1f} 中文:{chinese_score:.1f})")
            self.reading_progress.setValue(10)
            QApplication.processEvents()
            
            # 7. 完整版情感分析 (支持中英文混合+程度分析)
            # 扩展的情感词典 (包含程度词和否定词处理)
            sentiment_dict = {
                # 中文情感词 (带权重)
                'positive': {
                    '好': 1, '优秀': 2, '成功': 2, '高兴': 1.5, '满意': 1.5,
                    '喜欢': 1, '爱': 2, '开心': 1.5, '幸福': 2, '棒': 1,
                    '完美': 2, '精彩': 1.5, '美丽': 1, '聪明': 1, '强大': 1
                },
                'negative': {
                    '坏': 1, '差': 1, '失败': 2, '伤心': 1.5, '不满': 1.5,
                    '讨厌': 1.5, '恨': 2, '痛苦': 2, '糟糕': 1.5, '愚蠢': 1.5,
                    '难看': 1, '弱': 1, '困难': 1, '麻烦': 1, '失望': 1.5
                },
                # 英文情感词
                'en_positive': {
                    'good': 1, 'excellent': 2, 'success': 2, 'happy': 1.5, 'satisfied': 1.5,
                    'like': 1, 'love': 2, 'joy': 1.5, 'great': 1.5, 'perfect': 2
                },
                'en_negative': {
                    'bad': 1, 'poor': 1, 'fail': 2, 'sad': 1.5, 'angry': 1.5,
                    'hate': 2, 'pain': 2, 'terrible': 1.5, 'stupid': 1.5, 'ugly': 1
                },
                # 程度副词
                'intensifiers': {
                    '非常': 1.5, '特别': 1.5, '极其': 2, '十分': 1.3, '相当': 1.2,
                    '有点': 0.8, '稍微': 0.7, '略微': 0.7, '过于': 1.3,
                    'very': 1.5, 'extremely': 2, 'highly': 1.5, 'quite': 1.2
                },
                # 否定词
                'negators': ['不', '没', '无', '非', '未', '不是', '不要', 'never', 'not', "n't"]
            }

            # 初始化计数器
            positive_score = 0
            negative_score = 0
            sentiment_words = []
            
            # 预处理文本
            sentences = re.split(r'[。！？；;.!?]+', content)
            
            for sentence in sentences:
                if not sentence.strip():
                    continue
                
                # 检查否定词
                has_negator = any(neg in sentence for neg in sentiment_dict['negators'])
                negator_factor = -1 if has_negator else 1
                
                # 检查程度词
                intensifier = 1
                for word, factor in sentiment_dict['intensifiers'].items():
                    if word in sentence:
                        intensifier *= factor
                        break
                
                # 中文情感词分析
                for word, weight in sentiment_dict['positive'].items():
                    if word in sentence:
                        score = weight * intensifier * negator_factor
                        positive_score += max(0, score)
                        negative_score += max(0, -score)
                        sentiment_words.append((word, score))
                
                for word, weight in sentiment_dict['negative'].items():
                    if word in sentence:
                        score = weight * intensifier * negator_factor
                        negative_score += max(0, score)
                        positive_score += max(0, -score)
                        sentiment_words.append((word, score))
                
                # 英文情感词分析
                for word, weight in sentiment_dict['en_positive'].items():
                    if re.search(r'\b' + word + r'\b', sentence, re.IGNORECASE):
                        score = weight * intensifier * negator_factor
                        positive_score += max(0, score)
                        negative_score += max(0, -score)
                        sentiment_words.append((word, score))
                
                for word, weight in sentiment_dict['en_negative'].items():
                    if re.search(r'\b' + word + r'\b', sentence, re.IGNORECASE):
                        score = weight * intensifier * negator_factor
                        negative_score += max(0, score)
                        positive_score += max(0, -score)
                        sentiment_words.append((word, score))
            
            # 计算情感倾向
            total_score = positive_score - negative_score
            abs_total = abs(total_score)
            
            if abs_total < 1:
                sentiment = "中性"
                intensity = "一般"
            else:
                if total_score > 0:
                    sentiment = "积极"
                    intensity = "强烈" if abs_total > 3 else "中等" if abs_total > 1.5 else "轻微"
                else:
                    sentiment = "消极"
                    intensity = "强烈" if abs_total > 3 else "中等" if abs_total > 1.5 else "轻微"
            
            # 生成详细报告
            top_words = sorted(sentiment_words, key=lambda x: abs(x[1]), reverse=True)[:5]
            word_details = "，".join(f"{word}({score:.1f})" for word, score in top_words)
            
            self.sentiment_label.setText(
                f"情感倾向: {sentiment}-{intensity}\n"
                f"正面强度: {positive_score:.1f} 负面强度: {negative_score:.1f}\n"
                f"关键情感词: {word_details}"
            )
            
            print(f"[DEBUG] 情感分析: {sentiment}-{intensity} (正:{positive_score:.1f} 负:{negative_score:.1f})")
            print(f"[DEBUG] 情感词: {top_words}")
            self.reading_progress.setValue(90)
            QApplication.processEvents()

            # 增强版特征分析
            self.analyze_text_features(content)
            self.reading_progress.setValue(100)

            # 更新统计信息文本框 - 使用HTML格式
            stats_html = (
                "<h3>详细统计信息:</h3>"
                "<ul>"
                "<li>总字符数: {}</li>"
                "<li>中文字符: {}</li>"
                "<li>英文单词: {}</li>"
                "<li>数字数量: {}</li>"
                "<li>标点符号: {}</li>"
                "<li>空格数量: {}</li>"
                "<li>换行数量: {}</li>"
                "</ul>"
            ).format(
                len(content),
                len(re.findall(r'[\u4e00-\u9fff]', content)),
                len(re.findall(r'\b[a-zA-Z]+\b', content)),
                len(re.findall(r'\d+', content)),
                len(re.findall(r'[,.!?;:，。！？；：、]', content)),
                content.count(' '),
                content.count('\n')
            )
            self.stats_info.setHtml(stats_html)

            # 分析完成后隐藏"正在分析"标签
            if hasattr(self, 'analyzing_label'):
                self.analyzing_label.setVisible(False)
            
            # 确保所有分析结果可见
            for i in range(3):  # 确保3个选项卡都可见
                dialog.findChild(QTabWidget).setTabVisible(i, True)

            print("[DEBUG] 文本分析完成")
        except Exception as e:
            print("[ERROR] 文本分析失败:", str(e))
            self.reading_progress.setValue(0)
            QMessageBox.critical(dialog, "错误", f"分析失败: {str(e)}")




    def update_basic_stats(self, content):
        """更新基本统计图表"""
        # 计算统计数据
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', content))
        english_words = len(re.findall(r'\b[a-zA-Z]+\b', content))
        numbers = len(re.findall(r'\d+', content))
        punctuation = len(re.findall(r'[,.!?;:，。！？；：、]', content))
        spaces = content.count(' ')
        others = len(content) - chinese_chars - english_words - numbers - punctuation - spaces
        
        # 创建图表
        chart = QChart()
        chart.setTitle("文本统计")
        chart.setAnimationOptions(QChart.SeriesAnimations)
        
        # 创建饼图系列
        series = QPieSeries()
        series.append("中文字符", chinese_chars)
        series.append("英文单词", english_words)
        series.append("数字", numbers)
        series.append("标点符号", punctuation)
        series.append("空格", spaces)
        series.append("其他字符", others)
        
        # 设置切片标签可见
        for slice in series.slices():
            slice.setLabelVisible(True)
            slice.setLabel(f"{slice.label()} ({slice.value()})")
        
        # 添加到图表
        chart.addSeries(series)
        chart.legend().setVisible(True)
        chart.legend().setAlignment(Qt.AlignBottom)
        
        self.stats_chart_view.setChart(chart)
        self.stats_chart_view.setRenderHint(QPainter.Antialiasing)


    def extract_keywords(self, content, top_n=10, with_weight=False):
        """完整版关键词提取(使用jieba分词)
        
        参数:
            content: 要提取关键词的文本内容
            top_n: 返回关键词数量
            with_weight: 是否返回关键词权重
            
        返回:
            关键词列表(带权重时为元组列表)
        """
        try:
            import jieba
            import jieba.analyse
            
            # 初始化jieba (第一次使用时加载词典)
            if not hasattr(jieba, 'dt'):
                jieba.initialize()
            
            # 自定义停用词列表 (可根据需要扩展)
            stop_words = {
                '的', '了', '和', '是', '在', '我', '有', '这', '那', '你', '他', '她', '它',
                '我们', '你们', '他们', '这个', '那个', '要', '也', '都', '会', '可以', '可能',
                '就是', '这样', '这些', '那些', '一些', '一点', '一种', '一样', '一般', '一定',
                '非常', '很多', '什么', '为什么', '怎么', '如何', '因为', '所以', '但是', '虽然',
                '如果', '然后', '而且', '或者', '还是', '不是', '没有', '不要', '不能', '需要',
                '应该', '可能', '可以', '必须', '只是', '真是', '真是', '真是', '真是', '真是'
            }
            
            # 1. 计算TF-IDF (使用jieba的TF-IDF接口)
            keywords = jieba.analyse.extract_tags(
                content,
                topK=top_n*2,  # 先获取更多候选词
                withWeight=True,
                allowPOS=('n', 'vn', 'v', 'a')  # 只保留名词、动名词、动词、形容词
            )
            
            # 2. 过滤停用词和单字词
            filtered_keywords = [
                (word, weight) for word, weight in keywords 
                if word not in stop_words and len(word) > 1
            ][:top_n]
            
            # 3. 计算文档频率 (从数据库获取)
            doc_freq = {}
            total_docs = 0
            self.cursor.execute("SELECT COUNT(*) FROM texts")
            total_docs = self.cursor.fetchone()[0]
            
            if total_docs > 0:
                for word, _ in filtered_keywords:
                    self.cursor.execute(
                        "SELECT COUNT(*) FROM texts WHERE content LIKE ?",
                        (f'%{word}%',)
                    )
                    doc_freq[word] = self.cursor.fetchone()[0]
            
            # 4. 调整权重 (结合全局文档频率)
            final_keywords = []
            for word, weight in filtered_keywords:
                # 计算逆文档频率 (IDF)
                df = doc_freq.get(word, 1)
                idf = math.log((total_docs + 1) / (df + 1)) + 1  # 平滑处理
                
                # 调整后的权重 = TF * IDF
                adjusted_weight = weight * idf
                
                final_keywords.append((word, adjusted_weight))
            
            # 按调整后的权重重新排序
            final_keywords.sort(key=lambda x: x[1], reverse=True)
            
            if with_weight:
                return final_keywords[:top_n]
            else:
                return [word for word, weight in final_keywords[:top_n]]
                
        except ImportError:
            # 回退到简单实现 (如果没有安装jieba)
            QMessageBox.warning(self, "警告", "未安装jieba库，使用简化版关键词提取")
            return self._fallback_extract_keywords(content, top_n)
        except Exception as e:
            print(f"关键词提取错误: {str(e)}")
            return []

    def _fallback_extract_keywords(self, content, top_n):
        """jieba不可用时的回退实现"""
        words = re.findall(r'[\u4e00-\u9fa5]{2,}', content)
        
        # 简单停用词过滤
        stop_words = ['的', '了', '和', '是', '在', '我', '有', '这', '那', '你']
        words = [word for word in words if word not in stop_words]
        
        # 词频统计
        word_counts = {}
        for word in words:
            word_counts[word] = word_counts.get(word, 0) + 1
        
        # 按频率排序
        sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
        
        return [word for word, count in sorted_words[:top_n]]



    def find_similar_texts(self, content):
        """增强版相似文本查找"""
        self.similar_texts_list.clear()
        self.similarity_table.setRowCount(0)
        
        # 获取所有文本
        self.cursor.execute("SELECT id, title, content, category_id FROM texts WHERE id != ?", (self.current_id,))
        texts = self.cursor.fetchall()
        
        # 提取特征
        current_features = self.extract_text_features(content)
        
        # 计算相似度
        similarities = []
        for text_id, title, text, category_id in texts:
            features = self.extract_text_features(text)
            similarity = self.calculate_similarity(current_features, features)
            
            # 获取分类名
            category_name = "未分类"
            if category_id:
                self.cursor.execute("SELECT name FROM categories WHERE id=?", (category_id,))
                res = self.cursor.fetchone()
                if res:
                    category_name = res[0]
            
            similarities.append((text_id, title, category_name, similarity, features))
        
        # 按相似度排序
        similarities.sort(key=lambda x: x[3], reverse=True)
        
        # 显示相似文本（如果SIMILAR_TEXT_DISPLAY_COUNT为0则显示全部）
        display_count = len(similarities) if self.SIMILAR_TEXT_DISPLAY_COUNT == 0 else min(self.SIMILAR_TEXT_DISPLAY_COUNT, len(similarities))
        
        for i, (text_id, title, category, similarity, features) in enumerate(similarities[:display_count]):
            item = QListWidgetItem()
            widget = QWidget()
            layout = QHBoxLayout()
            
            # 相似度进度条
            sim_bar = QProgressBar()
            sim_bar.setValue(int(similarity * 100))
            sim_bar.setFormat(f"{similarity:.1%}")
            sim_bar.setStyleSheet("""
                QProgressBar {
                    text-align: center;
                    min-width: 80px;
                }
            """)
            
            # 文本信息
            label = QLabel(f"{i+1}. {title} [{category}]")
            label.setStyleSheet("font-weight: bold;")
            
            layout.addWidget(sim_bar)
            layout.addWidget(label)
            layout.addStretch()
            widget.setLayout(layout)
            
            item.setSizeHint(widget.sizeHint())
            item.setData(Qt.UserRole, (text_id, features))
            self.similar_texts_list.addItem(item)
            self.similar_texts_list.setItemWidget(item, widget)
        
        # 显示特征权重表
        self.show_feature_weights(current_features)

    def extract_text_features(self, text):
        """提取文本多维特征"""
        features = {
            # 词汇特征
            'word_count': len(re.findall(r'\w+', text)),
            'unique_words': len(set(re.findall(r'\w+', text))),
            'lexical_diversity': len(set(re.findall(r'\w+', text))) / max(1, len(re.findall(r'\w+', text))),
            
            # 中文特征
            'chinese_chars': len(re.findall(r'[\u4e00-\u9fff]', text)),
            'chinese_ratio': len(re.findall(r'[\u4e00-\u9fff]', text)) / max(1, len(text)),
            
            # 英文特征
            'english_words': len(re.findall(r'\b[a-zA-Z]+\b', text)),
            'english_ratio': len(re.findall(r'\b[a-zA-Z]+\b', text)) / max(1, len(re.findall(r'\w+', text))),
            
            # 结构特征
            'avg_sentence_length': len(re.findall(r'\w+', text)) / max(1, len(re.split(r'[。！？.!?]+', text))),
            'paragraph_count': len([p for p in text.split('\n') if p.strip()]),
            
            # 内容特征
            'question_ratio': len(re.findall(r'[？?]', text)) / max(1, len(re.findall(r'[。.！!？?]', text))),
            'exclamation_ratio': len(re.findall(r'[！!]', text)) / max(1, len(re.findall(r'[。.！!？?]', text))),
            
            # 关键词特征
            'keywords': self.extract_keywords(text, top_n=10)
        }
        return features

    def calculate_similarity(self, features1, features2):
        """计算多维特征相似度"""
        # 数值特征相似度
        numeric_sim = 0
        numeric_features = ['word_count', 'unique_words', 'lexical_diversity',
                        'chinese_chars', 'chinese_ratio', 'english_words',
                        'english_ratio', 'avg_sentence_length', 'paragraph_count',
                        'question_ratio', 'exclamation_ratio']
        
        for feat in numeric_features:
            val1 = features1[feat]
            val2 = features2[feat]
            max_val = max(val1, val2) or 1
            numeric_sim += 1 - abs(val1 - val2) / max_val
        
        numeric_sim /= len(numeric_features)
        
        # 关键词相似度
        keywords1 = set(features1['keywords'])
        keywords2 = set(features2['keywords'])
        keyword_sim = len(keywords1 & keywords2) / max(1, len(keywords1 | keywords2))
        
        # 综合相似度
        total_sim = 0.6 * numeric_sim + 0.4 * keyword_sim
        return total_sim

    def show_feature_weights(self, features):
        """显示特征权重表"""
        self.similarity_table.setRowCount(len(features))
        
        for i, (name, value) in enumerate(features.items()):
            if name == 'keywords':
                continue
                
            self.similarity_table.setItem(i, 0, QTableWidgetItem(name))
            
            # 数值型特征
            if isinstance(value, (int, float)):
                self.similarity_table.setItem(i, 1, QTableWidgetItem(f"{value:.2f}"))
                
                # 添加可视化进度条
                progress = QProgressBar()
                max_val = max(1, value * 2, 100) if name in ['word_count', 'chinese_chars'] else 1
                progress.setValue(int(100 * value / max_val))
                progress.setStyleSheet("QProgressBar::chunk { background: #2196F3; }")
                self.similarity_table.setCellWidget(i, 2, progress)
            else:
                self.similarity_table.setItem(i, 1, QTableWidgetItem(str(value)))
                self.similarity_table.setItem(i, 2, QTableWidgetItem("-"))
        
        # 关键词特殊处理
        row = len(features) - 1
        self.similarity_table.setItem(row, 0, QTableWidgetItem("keywords"))
        self.similarity_table.setItem(row, 1, QTableWidgetItem(", ".join(features['keywords'][:5])))
        self.similarity_table.setItem(row, 2, QTableWidgetItem(f"共{len(features['keywords'])}个关键词"))

    def show_similarity_detail(self, item):
        """显示相似文本详情"""
        text_id, features = item.data(Qt.UserRole)
        
        # 获取文本信息
        self.cursor.execute("SELECT title, content FROM texts WHERE id=?", (text_id,))
        title, content = self.cursor.fetchone()
        
        # 生成详情报告
        report = f"📌 相似文本: {title}\n\n"
        report += f"📝 内容摘要: {content[:200]}...\n\n"
        report += "🔍 特征分析:\n"
        
        for name, value in features.items():
            if name == 'keywords':
                report += f" - 关键词: {', '.join(value[:5])} (共{len(value)}个)\n"
            elif isinstance(value, float):
                report += f" - {name}: {value:.2f}\n"
            else:
                report += f" - {name}: {value}\n"
        
        self.similarity_detail.setPlainText(report)

    def analyze_text_features(self, content):
        """增强版文本特征分析"""
        features = self.extract_text_features(content)
        
        # 1. 更新可读性卡片
        readability = min(100, max(0, 100 - (features['avg_sentence_length'] * 0.5)))
        self.readability_score.setText(
            f"可读性评分: {readability:.1f}/100\n"
            f"平均句长: {features['avg_sentence_length']:.1f} 词"
        )
        self.readability_bar.setValue(int(readability))
        
        # 2. 更新情感卡片
        sentiment_html = """
        <div style="background:linear-gradient(to right, 
            #ff4444 0%, #ff9999 {neg}%, 
            #ffffff {neutral}%, 
            #99ff99 {pos}%, #44ff44 100%); 
            height:20px; border-radius:3px;"></div>
        """.format(
            neg=30,  # 负面比例
            neutral=50,  # 中性位置
            pos=70  # 正面比例
        )
        self.sentiment_graph.setText(sentiment_html)
        
        # 3. 更新关键词卡片
        keywords_html = "<div style='line-height:1.8;'>"
        for i, word in enumerate(features['keywords'][:10]):
            size = 12 + i * 2
            color = f"hsl({i*36}, 70%, 50%)"
            keywords_html += f"<span style='font-size:{size}px; color:{color}; margin:0 3px;'>{word}</span>"
        keywords_html += "</div>"
        self.keywords_label.setText(keywords_html)
        
        # 4. 更新风格卡片
        style_text = ""
        if features['question_ratio'] > 0.2:
            style_text += "🔹 提问型风格\n"
        if features['exclamation_ratio'] > 0.15:
            style_text += "🔹 情感强烈型\n"
        if features['lexical_diversity'] > 0.7:
            style_text += "🔹 词汇丰富\n"
        else:
            style_text += "🔹 词汇重复较多\n"
        if features['avg_sentence_length'] > 20:
            style_text += "🔹 长句结构\n"
        elif features['avg_sentence_length'] < 10:
            style_text += "🔹 短句结构\n"
        
        self.style_label.setText(style_text)
        
        # 5. 更新特征表格
        self.features_table.setRowCount(len(features))
        for i, (name, value) in enumerate(features.items()):
            self.features_table.setItem(i, 0, QTableWidgetItem(name))
            
            if name == 'keywords':
                self.features_table.setItem(i, 1, QTableWidgetItem(", ".join(value[:5])))
                self.features_table.setItem(i, 2, QTableWidgetItem(f"共{len(value)}个关键词"))
            elif isinstance(value, float):
                self.features_table.setItem(i, 1, QTableWidgetItem(f"{value:.2f}"))
                
                # 添加说明
                if name == 'lexical_diversity':
                    desc = ">0.7表示词汇丰富，<0.5表示重复较多"
                elif name == 'avg_sentence_length':
                    desc = "10-20为适中，>20偏长，<10偏短"
                else:
                    desc = ""
                self.features_table.setItem(i, 2, QTableWidgetItem(desc))
            else:
                self.features_table.setItem(i, 1, QTableWidgetItem(str(value)))
                self.features_table.setItem(i, 2, QTableWidgetItem(""))


    def update_reading_progress(self):
        """更新阅读进度"""
        if not hasattr(self, 'current_id') or not self.current_id:
            return
        
        # 获取当前编辑器内容
        if hasattr(self, 'wysiwyg_editor') and self.wysiwyg_editor.isVisible():
            content = self.wysiwyg_editor.toPlainText()
            cursor = self.wysiwyg_editor.textCursor()
        elif hasattr(self, 'content_input'):
            content = self.content_input.toPlainText()
            cursor = self.content_input.textCursor()
        else:
            return
        
        # 计算进度
        position = cursor.position()
        total = len(content)
        
        if total > 0:
            progress = int((position / total) * 100)
            if hasattr(self, 'reading_progress'):
                self.reading_progress.setValue(progress)
            if hasattr(self, 'reading_progress_label'):
                self.reading_progress_label.setText(f"{progress}%")



    def create_edit_tab(self):
        """创建编辑选项卡（完整功能色区分版）"""
        self.edit_tab = QWidget()
        self.edit_layout = QVBoxLayout()
        self.edit_tab.setLayout(self.edit_layout)
        
        # 标题输入框（带聚焦效果）
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText('输入标题...')
        self.title_input.setStyleSheet("""
            QLineEdit {
                font-size: 14px;
                padding: 8px;
                border: 1px solid #cbd5e1;
                border-radius: 4px;
            }
            QLineEdit:focus {
                border: 1px solid #3b82f6;
                background-color: #f8fafc;
            }
        """)
        self.edit_layout.addWidget(self.title_input)
        
        # 分类选择框
        self.category_combo = QComboBox()
        self.category_combo.addItem('未分类', 0)
        self.edit_layout.addWidget(self.category_combo)
        
        # 标签输入框
        self.tag_edit = QLineEdit()
        self.tag_edit.setPlaceholderText('输入标签，用逗号分隔')
        self.edit_layout.addWidget(self.tag_edit)
        
        # 格式选择
        self.format_combo = QComboBox()
        self.format_combo.addItem('纯文本')
        self.format_combo.addItem('Markdown')
        self.format_combo.addItem('即见即所得')
        self.format_combo.setCurrentIndex(self.default_format)
        self.format_combo.currentIndexChanged.connect(self.toggle_edit_mode)
        self.edit_layout.addWidget(self.format_combo)
        
        # 文本编辑区
        self.content_input = QTextEdit()
        self.content_input.setStyleSheet("""
            QTextEdit {
                border: 1px solid #cbd5e1;
                border-radius: 4px;
                padding: 8px;
                font-family: 'Consolas', 'Microsoft YaHei', monospace;
            }
        """)
        self.content_input.textChanged.connect(self.update_word_count)
        self.edit_layout.addWidget(self.content_input)
        
        # WYSIWYG编辑器（初始隐藏）
        self.wysiwyg_editor = QTextEdit()
        self.wysiwyg_editor.setAcceptRichText(True)
        self.wysiwyg_editor.setVisible(False)
        self.wysiwyg_editor.setStyleSheet("""
            QTextEdit {
                border: 1px solid #cbd5e1;
                border-radius: 4px;
                padding: 8px;
                background-color: white;
            }
        """)
        self.edit_layout.addWidget(self.wysiwyg_editor)
        
        # 操作按钮区域 ======================================
        btn_layout = QHBoxLayout()
        
        # 新建按钮（活力蓝）
        self.btn_new = QPushButton(QIcon.fromTheme('document-new'), '新建')
        self.btn_new.setProperty("class", "new-action")
        self.btn_new.setCursor(Qt.PointingHandCursor)
        self.btn_new.clicked.connect(self.new_text)
        btn_layout.addWidget(self.btn_new)
        
        # 保存按钮（安全绿）
        self.btn_save = QPushButton(QIcon.fromTheme('document-save'), '保存')
        self.btn_save.setProperty("class", "save-action")
        self.btn_save.setCursor(Qt.PointingHandCursor)
        self.btn_save.clicked.connect(self.save_text)
        btn_layout.addWidget(self.btn_save)
        
        # 删除按钮（警示红）
        self.btn_delete = QPushButton(QIcon.fromTheme('edit-delete'), '删除')
        self.btn_delete.setProperty("class", "danger-action")
        self.btn_delete.setCursor(Qt.PointingHandCursor)
        self.btn_delete.clicked.connect(self.delete_text)
        btn_layout.addWidget(self.btn_delete)
        
        # 恢复按钮（中性灰）
        self.btn_restore = QPushButton('从回收站恢复')
        self.btn_restore.setProperty("class", "secondary-action")
        self.btn_restore.setCursor(Qt.PointingHandCursor)
        self.btn_restore.clicked.connect(self.restore_from_recycle_bin)
        self.btn_restore.setVisible(False)
        btn_layout.addWidget(self.btn_restore)
        
        # 文本分析按钮（智慧紫）
        self.stats_btn = QPushButton(QIcon.fromTheme('office-chart-bar'), '文本分析')
        self.stats_btn.setProperty("class", "analyze-action")
        self.stats_btn.setCursor(Qt.PointingHandCursor)
        self.stats_btn.clicked.connect(self.show_text_analysis)
        btn_layout.addWidget(self.stats_btn)
        
        # 复制按钮下拉菜单（友好橙）
        self.copy_menu = QMenu(self)
        copy_actions = [
            ("复制全文(含格式)", lambda: self.copy_text(with_format=True, selection_only=False)),
            ("复制全文(无格式)", lambda: self.copy_text(with_format=False, selection_only=False)),
            ("复制选定(含格式)", lambda: self.copy_text(with_format=True, selection_only=True)),
            ("复制选定(无格式)", lambda: self.copy_text(with_format=False, selection_only=True))
        ]
        for text, handler in copy_actions:
            action = QAction(text, self)
            action.triggered.connect(handler)
            self.copy_menu.addAction(action)
        
        self.copy_btn = QPushButton(QIcon.fromTheme('edit-copy'), '复制 ▼')
        self.copy_btn.setProperty("class", "data-action")
        self.copy_btn.setCursor(Qt.PointingHandCursor)
        self.copy_btn.setMenu(self.copy_menu)
        btn_layout.addWidget(self.copy_btn)
        
        self.edit_layout.addLayout(btn_layout)
        self.right_panel.addTab(self.edit_tab, "编辑")
        
        # 连接文本光标变化信号
        self.content_input.cursorPositionChanged.connect(self.update_reading_progress)
        self.wysiwyg_editor.cursorPositionChanged.connect(self.update_reading_progress)


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
            self.view_toggle_btn.setStyleSheet("""
                background-color: #9f7aea;  /* 切换后变为浅紫色 */
                color: white;
            """)
            self.btn_restore.setVisible(True)
            self.btn_delete.setText("永久删除")
        else:
            self.current_view = "normal"
            self.view_toggle_btn.setText("切换到回收站")
            self.view_toggle_btn.setStyleSheet("""
                background-color: #6b46c1;  /* 恢复默认深紫色 */
                color: white;
            """)
            self.btn_restore.setVisible(False)
            self.btn_delete.setText("删除")
        
        self.load_text_list()

    def show_batch_operations(self):
        """显示批量操作对话框（优化按钮文字颜色）"""
        dialog = QDialog(self)
        dialog.setWindowTitle("批量操作")
        # 添加对话框样式表
        dialog.setStyleSheet("""
            QDialog {
                background-color: #f8fafc;
            }
            QPushButton {
                min-width: 80px;
                padding: 6px 12px;
                border-radius: 4px;
                border: 1px solid #cbd5e1;
                background-color: #e2e8f0;
                color: #1e293b;  /* 深灰色文字 */
            }
            QPushButton:hover {
                background-color: #cbd5e1;
            }
            QPushButton:pressed {
                background-color: #94a3b8;
            }
            QGroupBox {
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 15px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px;
                color: #475569;
                font-weight: bold;
            }
        """)
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
        
        # 修改按钮样式（示例：导出目录按钮）
        self.export_dir_btn = QPushButton("选择导出目录")
        self.export_dir_btn.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;  /* 蓝色 */
                color: white;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
        """)
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
            print(self, "错误", f"导出失败: {str(e)}")
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
        """加载搜索历史（使用与文件列表相同的配色方案）"""
        self.search_history_combo.clear()
        self.cursor.execute(
            "SELECT rowid, query FROM search_history ORDER BY search_time DESC LIMIT 10"
        )
        history = self.cursor.fetchall()
        
        for rowid, query in history:
            # 使用与文件列表相同的颜色生成方法
            bg_color, text_color = self.generate_harmonious_color(rowid, saturation=0.4, value=0.92)
            
            # 添加历史项并设置颜色
            self.search_history_combo.addItem(query)
            index = self.search_history_combo.count() - 1
            self.search_history_combo.setItemData(index, bg_color, Qt.BackgroundRole)
            self.search_history_combo.setItemData(index, text_color, Qt.TextColorRole)



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
        """加载回收站列表（使用与文件列表相同的配色方案）"""
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
            
            # 使用与文件列表相同的颜色生成方法
            bg_color, text_color = self.generate_harmonious_color(original_id, saturation=0.4, value=0.92)
            item.setBackground(bg_color)
            item.setForeground(text_color)
            
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
        """保存文本（完整支持三种格式）"""
        title = self.title_input.text().strip()
        if not title:
            QMessageBox.warning(self, '警告', '标题不能为空!')
            return
            
        category_id = self.category_combo.currentData()
        format_index = self.format_combo.currentIndex()
        is_markdown = (format_index == 1)
        is_html = (format_index == 2)
        
        # 获取标签
        tags = [tag.strip() for tag in self.tag_edit.text().split(',') if tag.strip()]

        # 根据当前活动编辑器获取内容
        if self.wysiwyg_editor.isVisible():
            content = self.wysiwyg_editor.toHtml() if is_html else self.wysiwyg_editor.toPlainText()
        else:
            content = self.content_input.toPlainText()
        
        # 计算字数（使用纯文本计算）
        plain_text = self.wysiwyg_editor.toPlainText() if is_html else content
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', plain_text))
        english_words = len(re.findall(r'\b[a-zA-Z]+\b', plain_text))
        word_count = len(plain_text)
        
        try:
            if hasattr(self, 'current_id') and self.current_id is not None:
                # 更新现有文本
                text_id = self.current_id
                self.cursor.execute('''
                UPDATE texts 
                SET title=?, content=?, category_id=?, is_markdown=?, is_html=?,
                    update_time=CURRENT_TIMESTAMP, word_count=?, 
                    chinese_count=?, english_count=?
                WHERE id=?
                ''', (title, content, category_id, is_markdown, is_html,
                    word_count, chinese_chars, english_words,
                    text_id))
            else:
                # 插入新文本
                self.cursor.execute('''
                INSERT INTO texts (title, content, category_id, is_markdown, is_html,
                                word_count, chinese_count, english_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (title, content, category_id, is_markdown, is_html,
                    word_count, chinese_chars, english_words))
                text_id = self.cursor.lastrowid
                self.current_id = text_id
            
            # 更新FTS索引（使用纯文本内容）
            self.update_fts_index(text_id, title, plain_text)
            
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
            print(self, '错误', f'保存失败: {str(e)}')
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
        """加载文本（完整支持三种格式）"""
        text_id = item.data(Qt.UserRole)
        
        if self.current_view == "recycle_bin":
            # 加载回收站内容（始终作为纯文本处理）
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
            self.wysiwyg_editor.setPlainText(content)
            self.category_combo.setCurrentIndex(0)
            self.tag_edit.clear()
            self.format_combo.setCurrentIndex(0)  # 强制设为纯文本模式
            self.toggle_edit_mode()
            return
        
        # 正常加载文本
        self.cursor.execute('''
        SELECT t.title, t.content, t.category_id, t.is_markdown, t.is_html,
            group_concat(tg.name, ', ') as tags
        FROM texts t
        LEFT JOIN text_tags tt ON t.id = tt.text_id
        LEFT JOIN tags tg ON tt.tag_id = tg.id
        WHERE t.id = ?
        GROUP BY t.id
        ''', (text_id,))
        
        result = self.cursor.fetchone()
        if not result:
            return
            
        title, content, category_id, is_markdown, is_html, tags = result
        
        self.current_id = text_id
        self.title_input.setText(title)
        
        # 统一设置分类和标签
        index = self.category_combo.findData(category_id)
        if index >= 0:
            self.category_combo.setCurrentIndex(index)
        self.tag_edit.setText(tags if tags else '')
        
        # 根据格式设置内容
        if is_markdown:
            self.format_combo.setCurrentIndex(1)  # Markdown模式
            self.content_input.setPlainText(content)
            self.wysiwyg_editor.setPlainText(content)
            self.update_preview()
        elif is_html:
            self.format_combo.setCurrentIndex(2)  # HTML模式
            self.wysiwyg_editor.setHtml(self.clean_html(content))
            self.content_input.setPlainText(self.html_to_plain(content))
        else:
            self.format_combo.setCurrentIndex(0)  # 纯文本模式
            self.content_input.setPlainText(content)
            self.wysiwyg_editor.setPlainText(content)
        
        # 确保编辑器状态正确
        self.toggle_edit_mode()
        # 强制更新一次编辑器内容
        if is_html:
            self.wysiwyg_editor.setHtml(self.clean_html(content))
        else:
            self.content_input.setPlainText(content)
        
        self.update_word_count()




    def toggle_markdown(self):
        """切换Markdown预览状态"""
        if self.format_combo.currentIndex() == 1:  # Markdown模式
            self.update_preview()
            self.right_panel.setTabVisible(1, True)  # 显示预览标签页
        else:
            self.right_panel.setTabVisible(1, False)  # 隐藏预览标签页


    def toggle_edit_mode(self):
        """切换编辑模式"""
        mode = self.format_combo.currentIndex()
        
        # 保存当前内容
        if mode == 0:  # 切换到纯文本
            # 从当前活动编辑器获取内容
            if self.wysiwyg_editor.isVisible():
                current_content = self.wysiwyg_editor.toPlainText()
            else:
                current_content = self.content_input.toPlainText()
                
            self.content_input.setPlainText(current_content)
            self.wysiwyg_editor.setPlainText(current_content)
            
        elif mode == 1:  # 切换到Markdown
            # 从当前活动编辑器获取内容
            if self.wysiwyg_editor.isVisible():
                current_content = self.wysiwyg_editor.toPlainText()
            else:
                current_content = self.content_input.toPlainText()
                
            self.content_input.setPlainText(current_content)
            self.wysiwyg_editor.setPlainText(current_content)
            self.update_preview()
            
        else:  # 切换到即见即所得
            # 获取当前内容
            if self.format_combo.currentIndex() == 1:  # 之前是Markdown
                current_content = markdown.markdown(self.content_input.toPlainText())
            else:  # 之前是纯文本
                if self.content_input.isVisible():
                    current_content = self.content_input.toPlainText()
                else:
                    current_content = self.wysiwyg_editor.toPlainText()
                
                # 将纯文本转换为HTML，保留换行等基本格式
                current_content = current_content.replace('\n', '<br>')
            
            # 清理HTML，移除自动添加的样式
            current_content = self.clean_html(current_content)
            self.wysiwyg_editor.setHtml(current_content)
        
        # 切换可见性
        self.content_input.setVisible(mode != 2)
        self.wysiwyg_editor.setVisible(mode == 2)
        self.right_panel.setTabVisible(1, mode == 1)  # 只有Markdown模式显示预览


    def clean_html(self, html):
        """清理HTML内容，移除不需要的样式和标签"""
        # 移除自动添加的white-space样式
        html = html.replace('p, li { white-space: pre-wrap; }', '')
        # 移除空的style标签
        html = re.sub(r'<style[^>]*>\s*</style>', '', html)
        # 移除class属性
        html = re.sub(r' class="[^"]*"', '', html)
        # 移除span标签但保留内容
        html = re.sub(r'<span[^>]*>([^<]*)</span>', r'\1', html)
        # 移除空的div标签
        html = re.sub(r'<div[^>]*>\s*</div>', '', html)
        return html






    def update_preview(self):
        """更新Markdown预览"""
        if self.format_combo.currentIndex() == 1:  # 只在Markdown模式下更新
            content = self.content_input.toPlainText()
            html = markdown.markdown(content)
            self.preview_label.setText(html)

    def load_categories(self):
        """加载分类数据（使用与文件列表相同的配色方案）"""
        self.category_tree.clear()
        self.cursor.execute("SELECT id, name, parent_id FROM categories ORDER BY parent_id, name")
        categories = self.cursor.fetchall()
        
        # 构建树形结构
        categories_dict = {}
        for cat_id, name, parent_id in categories:
            item = QTreeWidgetItem([name])
            item.setData(0, Qt.UserRole, cat_id)
            
            # 使用与文件列表相同的颜色生成方法
            bg_color, text_color = self.generate_harmonious_color(cat_id, saturation=0.4, value=0.92)
            item.setBackground(0, bg_color)
            item.setForeground(0, text_color)
            
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
            # 设置下拉项颜色（与文件列表相同）
            index = self.category_combo.count() - 1
            bg_color, text_color = self.generate_harmonious_color(cat_id, saturation=0.4, value=0.92)
            self.category_combo.setItemData(index, bg_color, Qt.BackgroundRole)
            self.category_combo.setItemData(index, text_color, Qt.TextColorRole)






    def load_tags(self):
        """加载标签数据（使用与文件列表相同的配色方案）"""
        self.tag_cloud.clear()
        self.cursor.execute("SELECT id, name FROM tags ORDER BY name")
        tags = self.cursor.fetchall()
        
        for tag_id, name in tags:
            # 使用与文件列表相同的颜色生成方法
            bg_color, text_color = self.generate_harmonious_color(tag_id, saturation=0.4, value=0.92)
            
            # 添加标签项并设置颜色
            self.tag_cloud.addItem(name)
            index = self.tag_cloud.count() - 1
            self.tag_cloud.setItemData(index, bg_color, Qt.BackgroundRole)
            self.tag_cloud.setItemData(index, text_color, Qt.TextColorRole)




    def load_text_list(self, category_id=None, tag_name=None, search_query=None):
        """加载文本列表（使用和谐颜色方案）"""
        if self.current_view == "recycle_bin":
            self.load_recycle_bin_list(search_query)
            return
        
        query = '''
        SELECT t.id, t.title, c.name, t.category_id
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
        for text_id, title, category_name, category_id in texts:
            item = QListWidgetItem(f"{title} [{category_name or '未分类'}] (ID: {text_id})")
            item.setData(Qt.UserRole, text_id)
            
            # 生成颜色（基于分类ID，如果没有分类则使用文本ID）
            color_id = category_id if category_id else text_id
            bg_color, text_color = self.generate_harmonious_color(color_id, saturation=0.4, value=0.92)
            
            item.setBackground(bg_color)
            item.setForeground(text_color)
            
            self.text_list.addItem(item)

    def filter_by_category(self, item):
        """按分类筛选文本 - 修改为显示选中分类+未分类的内容"""
        category_id = item.data(0, Qt.UserRole)
        
        # 获取所有未分类的文本
        query = '''
        SELECT t.id, t.title, c.name 
        FROM texts t
        LEFT JOIN categories c ON t.category_id = c.id
        WHERE t.category_id = 0 OR t.category_id = ?
        ORDER BY t.update_time DESC
        '''
        
        self.cursor.execute(query, (category_id,))
        texts = self.cursor.fetchall()
        
        self.text_list.clear()
        for text_id, title, category_name in texts:
            item = QListWidgetItem(f"{title} [{category_name or '未分类'}] (ID: {text_id})")
            item.setData(Qt.UserRole, text_id)
            self.text_list.addItem(item)


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
        self.save_indicator.setText('✅ ' + datetime.datetime.now().strftime('%H:%M:%S 已保存'))
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

        # 添加阅读进度快捷键
        self.shortcut_progress = QShortcut(QKeySequence("Ctrl+G"), self)
        self.shortcut_progress.activated.connect(self.show_reading_progress)
        

        self.shortcut_copy = QShortcut(QKeySequence("Ctrl+Shift+C"), self)
        self.shortcut_copy.activated.connect(self.copy_without_background)
    
        # 连接文本光标变化信号
        self.content_input.cursorPositionChanged.connect(self.update_reading_progress)

    def show_reading_progress(self):
        """显示阅读进度提示"""
        self.update_reading_progress()
        self.status_bar.showMessage(f"当前阅读进度: {self.reading_progress.value()}%", 2000)

    def manage_tags(self):
        """标签管理对话框(支持颜色编码)"""
        dialog = QDialog(self)
        dialog.setWindowTitle("标签管理")
        dialog.setStyleSheet("""
            QPushButton {
                background-color: #e2e8f0;
                color: #1e293b;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #cbd5e1;
            }
        """)
        dialog.resize(600, 400)
        
        layout = QVBoxLayout()
        
        # 标签列表
        self.tag_list = QListWidget()
        self.load_tag_list()
        layout.addWidget(self.tag_list)
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        
        color_btn = QPushButton("设置颜色")
        color_btn.clicked.connect(self.set_tag_color)
        btn_layout.addWidget(color_btn)
        
        delete_btn = QPushButton("删除未使用标签")
        delete_btn.clicked.connect(self.clean_unused_tags)
        btn_layout.addWidget(delete_btn)
        
        layout.addLayout(btn_layout)
        
        # 确定按钮
        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(dialog.accept)
        layout.addWidget(ok_btn)
        
        dialog.setLayout(layout)
        dialog.exec_()

    def load_tag_list(self):
        """加载标签列表(带使用计数)"""
        self.tag_list.clear()
        
        self.cursor.execute('''
        SELECT t.id, t.name, COUNT(tt.text_id) as usage_count
        FROM tags t
        LEFT JOIN text_tags tt ON t.id = tt.tag_id
        GROUP BY t.id
        ORDER BY t.name
        ''')
        
        for tag_id, name, count in self.cursor.fetchall():
            item = QListWidgetItem(f"{name} (使用: {count}次)")
            item.setData(Qt.UserRole, tag_id)
            self.tag_list.addItem(item)

    def set_tag_color(self):
        """设置标签颜色"""
        item = self.tag_list.currentItem()
        if not item:
            QMessageBox.warning(self, "警告", "请先选择标签!")
            return
        
        tag_id = item.data(Qt.UserRole)
        color = QColorDialog.getColor(Qt.white, self, "选择标签颜色")
        
        if color.isValid():
            # 保存颜色到数据库(需要添加color字段到tags表)
            try:
                self.cursor.execute(
                    "UPDATE tags SET color = ? WHERE id = ?",
                    (color.name(), tag_id)
                )
                self.conn.commit()
                
                # 更新显示
                item.setBackground(color)
                self.show_status_message("标签颜色已设置", 2000)
            except Exception as e:
                QMessageBox.critical(self, "错误", f"设置颜色失败: {str(e)}")

    def clean_unused_tags(self):
        """清理未使用标签"""
        reply = QMessageBox.question(
            self, "确认清理",
            "确定要删除所有未使用的标签吗?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                self.cursor.execute('''
                DELETE FROM tags 
                WHERE id NOT IN (SELECT DISTINCT tag_id FROM text_tags)
                ''')
                deleted_count = self.cursor.rowcount
                self.conn.commit()
                
                self.load_tag_list()
                self.load_tags()  # 刷新主界面标签云
                self.show_status_message(f"已删除{deleted_count}个未使用标签", 3000)
            except Exception as e:
                QMessageBox.critical(self, "错误", f"清理失败: {str(e)}")

    def auto_tag_text(self):
        """自动为当前文本添加标签(基于关键词)"""
        if not hasattr(self, 'current_id') or not self.current_id:
            QMessageBox.warning(self, "警告", "请先选择文本!")
            return
        
        content = self.content_input.toPlainText()
        keywords = self.extract_keywords(content, top_n=3)
        
        if not keywords:
            QMessageBox.information(self, "提示", "未提取到有效关键词")
            return
        
        # 获取现有标签
        current_tags = self.tag_edit.text().split(',')
        current_tags = [tag.strip() for tag in current_tags if tag.strip()]
        
        # 添加新标签
        new_tags = current_tags + keywords
        self.tag_edit.setText(', '.join(set(new_tags)))  # 去重
        
        self.show_status_message(f"已自动添加标签: {', '.join(keywords)}", 3000)

    def optimize_database(self):
        """优化数据库"""
        try:
            start_time = time.time()
            
            # 执行优化命令
            self.cursor.execute("VACUUM")
            self.cursor.execute("ANALYZE")
            
            elapsed = time.time() - start_time
            self.show_status_message(f"数据库优化完成, 耗时{elapsed:.2f}秒", 5000)
        except Exception as e:
            print(self, "错误", f"优化失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"优化失败: {str(e)}")

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
        dialog = QDialog(self)
        dialog.setWindowTitle("分类管理")
        dialog.resize(600, 500)
        
        layout = QVBoxLayout()
        
        # 分类树
        self.manage_category_tree = QTreeWidget()
        self.manage_category_tree.setHeaderLabels(["分类名称", "颜色"])
        self.manage_category_tree.setColumnCount(2)
        self.manage_category_tree.setDragDropMode(QTreeWidget.InternalMove)
        self.manage_category_tree.setSelectionMode(QTreeWidget.SingleSelection)
        self.manage_category_tree.itemDoubleClicked.connect(self.edit_category_item)
        self.manage_category_tree.itemChanged.connect(self.handle_category_item_changed)
        
        # 加载分类数据
        self.load_manage_categories()
        layout.addWidget(self.manage_category_tree)
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        
        add_btn = QPushButton("添加分类")
        add_btn.clicked.connect(self.add_category_dialog)
        btn_layout.addWidget(add_btn)
        
        edit_btn = QPushButton("编辑分类")
        edit_btn.clicked.connect(lambda: self.edit_category_item(self.manage_category_tree.currentItem()))
        btn_layout.addWidget(edit_btn)
        
        delete_btn = QPushButton("删除分类")
        delete_btn.clicked.connect(self.delete_category)
        btn_layout.addWidget(delete_btn)
        
        color_btn = QPushButton("设置颜色")
        color_btn.clicked.connect(self.set_category_color)
        btn_layout.addWidget(color_btn)
        
        layout.addLayout(btn_layout)
        
        # 确定按钮
        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(dialog.accept)
        layout.addWidget(ok_btn)
        
        dialog.setLayout(layout)
        dialog.exec_()
        
        # 对话框关闭后刷新分类显示
        self.load_categories()

    def load_manage_categories(self):
        """加载分类数据到管理对话框"""
        self.manage_category_tree.clear()
        
        # 获取所有分类数据
        self.cursor.execute("SELECT id, name, parent_id, color FROM categories ORDER BY parent_id, name")
        categories = self.cursor.fetchall()
        
        # 构建树形结构
        categories_dict = {}
        for cat_id, name, parent_id, color in categories:
            item = QTreeWidgetItem([name, color or '自动生成'])
            item.setData(0, Qt.UserRole, cat_id)
            item.setData(1, Qt.UserRole, color)
            
            # 设置颜色显示
            if color and color != '#FFFFFF':
                item.setBackground(1, QColor(color))
            else:
                # 显示自动生成的颜色
                auto_color = self.generate_category_color(cat_id)
                item.setBackground(1, QColor(auto_color))
                item.setText(1, auto_color)
            
            categories_dict[cat_id] = item
            
            if parent_id == 0:
                self.manage_category_tree.addTopLevelItem(item)
            else:
                parent_item = categories_dict.get(parent_id)
                if parent_item:
                    parent_item.addChild(item)
        
        # 展开所有节点
        self.manage_category_tree.expandAll()


    def add_category_dialog(self):
        """添加分类对话框"""
        name, ok = QInputDialog.getText(
            self, '添加分类', '请输入分类名称:',
            QLineEdit.Normal, ''
        )
        
        if ok and name:
            # 获取选中的父分类
            parent_item = self.manage_category_tree.currentItem()
            parent_id = 0
            if parent_item:
                parent_id = parent_item.data(0, Qt.UserRole)
            
            try:
                self.cursor.execute(
                    "INSERT INTO categories (name, parent_id) VALUES (?, ?)",
                    (name, parent_id)
                )
                self.conn.commit()
                
                # 重新加载分类
                self.load_manage_categories()
                self.show_status_message(f'分类"{name}"已添加!', 2000)
            except sqlite3.IntegrityError:
                QMessageBox.warning(self, '警告', '分类名称已存在!')

    def edit_category_item(self, item):
        """编辑分类项"""
        if not item:
            return
            
        old_name = item.text(0)
        cat_id = item.data(0, Qt.UserRole)
        
        new_name, ok = QInputDialog.getText(
            self, '编辑分类', '请输入新的分类名称:',
            QLineEdit.Normal, old_name
        )
        
        if ok and new_name and new_name != old_name:
            try:
                self.cursor.execute(
                    "UPDATE categories SET name = ? WHERE id = ?",
                    (new_name, cat_id)
                )
                self.conn.commit()
                item.setText(0, new_name)
                self.show_status_message('分类名称已更新!', 2000)
            except sqlite3.IntegrityError:
                QMessageBox.warning(self, '警告', '分类名称已存在!')

    def delete_category(self):
        """删除分类"""
        item = self.manage_category_tree.currentItem()
        if not item:
            QMessageBox.warning(self, '警告', '请先选择要删除的分类!')
            return
            
        cat_id = item.data(0, Qt.UserRole)
        cat_name = item.text(0)
        
        # 检查是否有子分类
        self.cursor.execute("SELECT COUNT(*) FROM categories WHERE parent_id = ?", (cat_id,))
        child_count = self.cursor.fetchone()[0]
        
        # 检查分类下是否有文本
        self.cursor.execute("SELECT COUNT(*) FROM texts WHERE category_id = ?", (cat_id,))
        text_count = self.cursor.fetchone()[0]
        
        if child_count > 0 or text_count > 0:
            reply = QMessageBox.question(
                self, '确认删除',
                f'分类"{cat_name}"包含{child_count}个子分类和{text_count}个文本，删除后这些内容将变为未分类。确定删除吗?',
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
        
        try:
            # 更新子分类的parent_id为0
            self.cursor.execute(
                "UPDATE categories SET parent_id = 0 WHERE parent_id = ?",
                (cat_id,)
            )
            
            # 更新文本的分类为未分类
            self.cursor.execute(
                "UPDATE texts SET category_id = 0 WHERE category_id = ?",
                (cat_id,)
            )
            
            # 删除分类
            self.cursor.execute(
                "DELETE FROM categories WHERE id = ?",
                (cat_id,)
            )
            
            self.conn.commit()
            
            # 从树中移除
            (item.parent() or self.manage_category_tree.invisibleRootItem()).removeChild(item)
            
            self.show_status_message(f'分类"{cat_name}"已删除!', 2000)
        except Exception as e:
            QMessageBox.critical(self, '错误', f'删除失败: {str(e)}')

    def set_category_color(self):
        """设置分类颜色"""
        item = self.manage_category_tree.currentItem()
        if not item:
            QMessageBox.warning(self, '警告', '请先选择要设置颜色的分类!')
            return
            
        cat_id = item.data(0, Qt.UserRole)
        current_color = item.data(1, Qt.UserRole) or '#FFFFFF'
        
        color = QColorDialog.getColor(QColor(current_color), self, "选择分类颜色")
        if color.isValid():
            hex_color = color.name()
            
            try:
                self.cursor.execute(
                    "UPDATE categories SET color = ? WHERE id = ?",
                    (hex_color, cat_id)
                )
                self.conn.commit()
                
                item.setData(1, Qt.UserRole, hex_color)
                item.setText(1, hex_color)
                item.setBackground(1, color)
                
                # 更新主界面显示
                self.load_categories()

                self.show_status_message('分类颜色已设置!', 2000)
            except Exception as e:
                QMessageBox.critical(self, '错误', f'设置颜色失败: {str(e)}')

    def handle_category_item_changed(self, item, column):
        """处理分类项拖拽排序后的更新"""
        if column != 0:  # 只处理名称列的变化
            return
            
        # 防止递归调用
        self.manage_category_tree.itemChanged.disconnect(self.handle_category_item_changed)
        
        cat_id = item.data(0, Qt.UserRole)
        parent_item = item.parent()
        parent_id = parent_item.data(0, Qt.UserRole) if parent_item else 0
        
        try:
            self.cursor.execute(
                "UPDATE categories SET parent_id = ? WHERE id = ?",
                (parent_id, cat_id)
            )
            self.conn.commit()
        except Exception as e:
            QMessageBox.critical(self, '错误', f'更新分类结构失败: {str(e)}')
            self.load_manage_categories()  # 出错时重新加载
        
        # 重新连接信号
        self.manage_category_tree.itemChanged.connect(self.handle_category_item_changed)

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
        
        auto_tag_action = QAction('自动添加标签', self)
        auto_tag_action.triggered.connect(self.auto_tag_text)
        tools_menu.addAction(auto_tag_action)
        
        optimize_db_action = QAction('优化数据库', self)
        optimize_db_action.triggered.connect(self.optimize_database)
        tools_menu.addAction(optimize_db_action)
        
        manage_tags_action = QAction('管理标签', self)
        manage_tags_action.triggered.connect(self.manage_tags)
        tools_menu.addAction(manage_tags_action)

        # 帮助菜单
        help_menu = menubar.addMenu('帮助')
        about_action = QAction('关于', self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)

    def copy_without_background(self):
        """复制文本时不带背景色"""
        clipboard = QApplication.clipboard()
        cursor = self.content_input.textCursor()
        
        if not cursor.hasSelection():
            QMessageBox.information(self, "提示", "请先选择要复制的文本")
            return
        
        # 获取纯文本
        text = cursor.selectedText()
        
        # 获取HTML格式（如果有）
        html = ""
        if cursor.selection().toHtml():
            html = cursor.selection().toHtml()
            # 移除背景色样式
            html = re.sub(r'background-color:[^;"]*;?', '', html)
            html = re.sub(r'<span style="[^"]*">\s*</span>', '', html)  # 移除空样式
        
        # 创建MIME数据
        mime_data = QMimeData()
        mime_data.setText(text)
        
        if html:
            mime_data.setHtml(html)
        
        # 设置剪贴板内容
        clipboard.setMimeData(mime_data)
        self.show_status_message("已复制文本（无格式）", 2000)


    def create_wysiwyg_tab(self):
        """创建即见即所得编辑选项卡"""
        self.wysiwyg_tab = QWidget()
        self.wysiwyg_layout = QVBoxLayout()
        self.wysiwyg_tab.setLayout(self.wysiwyg_layout)
        
        # 使用QTextEdit并启用富文本编辑
        self.wysiwyg_editor = QTextEdit()
        self.wysiwyg_editor.setAcceptRichText(True)
        self.wysiwyg_editor.setHtml("<p>在这里输入内容...</p>")
        self.wysiwyg_editor.setStyleSheet("""
            QTextEdit {
                background-color: white;
                border: 1px solid #ccc;
                padding: 10px;
            }
        """)
        self.wysiwyg_layout.addWidget(self.wysiwyg_editor)
        
        # 添加格式工具栏
        toolbar = QToolBar()
        
        # 字体选择
        self.font_combo = QFontComboBox()
        toolbar.addWidget(self.font_combo)
        
        # 字号选择
        self.font_size = QComboBox()
        self.font_size.addItems(["8", "9", "10", "11", "12", "14", "16", "18", "20", "22", "24"])
        toolbar.addWidget(self.font_size)
        
        # 加粗/斜体/下划线按钮
        self.bold_btn = QToolButton()
        self.bold_btn.setIcon(QIcon.fromTheme("format-text-bold"))
        self.bold_btn.setCheckable(True)
        
        self.italic_btn = QToolButton()
        self.italic_btn.setIcon(QIcon.fromTheme("format-text-italic"))
        self.italic_btn.setCheckable(True)
        
        self.underline_btn = QToolButton()
        self.underline_btn.setIcon(QIcon.fromTheme("format-text-underline"))
        self.underline_btn.setCheckable(True)
        
        toolbar.addWidget(self.bold_btn)
        toolbar.addWidget(self.italic_btn)
        toolbar.addWidget(self.underline_btn)
        
        # 对齐方式
        self.align_left = QToolButton()
        self.align_left.setIcon(QIcon.fromTheme("format-justify-left"))
        self.align_left.setCheckable(True)
        
        self.align_center = QToolButton()
        self.align_center.setIcon(QIcon.fromTheme("format-justify-center"))
        self.align_center.setCheckable(True)
        
        self.align_right = QToolButton()
        self.align_right.setIcon(QIcon.fromTheme("format-justify-right"))
        self.align_right.setCheckable(True)
        
        align_group = QButtonGroup()
        align_group.addButton(self.align_left)
        align_group.addButton(self.align_center)
        align_group.addButton(self.align_right)
        
        toolbar.addWidget(self.align_left)
        toolbar.addWidget(self.align_center)
        toolbar.addWidget(self.align_right)
        
        # 连接信号
        self.font_combo.currentFontChanged.connect(self.set_editor_font)
        self.font_size.currentTextChanged.connect(self.set_editor_font_size)
        self.bold_btn.toggled.connect(self.set_bold)
        self.italic_btn.toggled.connect(self.set_italic)
        self.underline_btn.toggled.connect(self.set_underline)
        self.align_left.toggled.connect(lambda: self.set_alignment(Qt.AlignLeft))
        self.align_center.toggled.connect(lambda: self.set_alignment(Qt.AlignCenter))
        self.align_right.toggled.connect(lambda: self.set_alignment(Qt.AlignRight))
        
        self.wysiwyg_layout.addWidget(toolbar)
        self.right_panel.addTab(self.wysiwyg_tab, "富文本编辑")


    def set_editor_font(self, font):
        """设置编辑器字体"""
        self.wysiwyg_editor.setCurrentFont(font)

    def set_editor_font_size(self, size):
        """设置编辑器字号"""
        self.wysiwyg_editor.setFontPointSize(float(size))

    def set_bold(self, checked):
        """设置加粗"""
        self.wysiwyg_editor.setFontWeight(QFont.Bold if checked else QFont.Normal)

    def set_italic(self, checked):
        """设置斜体"""
        self.wysiwyg_editor.setFontItalic(checked)

    def set_underline(self, checked):
        """设置下划线"""
        self.wysiwyg_editor.setFontUnderline(checked)

    def set_alignment(self, alignment):
        """设置对齐方式"""
        self.wysiwyg_editor.setAlignment(alignment)

    def html_to_plain(self, html):
        """将HTML转换为纯文本（简化版）"""
        # 移除HTML标签
        text = re.sub(r'<[^>]+>', '', html)
        # 替换HTML实体
        text = text.replace('&nbsp;', ' ').replace('&lt;', '<').replace('&gt;', '>')
        return text.strip()

    def copy_text(self, with_format=True, selection_only=False):
        """复制文本内容到剪贴板
        
        Args:
            with_format (bool): 是否保留格式
            selection_only (bool): 是否只复制选中的内容
        """
        clipboard = QApplication.clipboard()
        
        # 确定使用哪个编辑器
        editor = self.wysiwyg_editor if self.wysiwyg_editor.isVisible() else self.content_input
        
        # 获取文本和HTML内容
        if selection_only:
            cursor = editor.textCursor()
            if not cursor.hasSelection():
                QMessageBox.information(self, "提示", "请先选择要复制的文本")
                return
            
            text = cursor.selectedText()
            html = cursor.selection().toHtml() if with_format else ""
        else:
            text = editor.toPlainText()
            html = editor.toHtml() if with_format else ""
        
        # 创建MIME数据
        mime_data = QMimeData()
        mime_data.setText(text)
        
        if html and with_format:
            # 清理HTML格式（移除不需要的样式）
            html = self.clean_html(html)
            mime_data.setHtml(html)
        
        # 设置剪贴板内容
        clipboard.setMimeData(mime_data)
        
        # 显示操作反馈
        mode = "选定" if selection_only else "全文"
        format_type = "含格式" if with_format else "无格式"
        self.show_status_message(f"已复制{format_type}{mode}内容", 2000)

    def generate_category_color(self, category_id):
        """为分类生成和谐且文字清晰的颜色
        
        参数:
            category_id: 分类ID，用于确定颜色序列中的位置
        
        返回:
            QColor对象
        """
        # 黄金比例常数
        golden_ratio = 0.618033988749895
        
        # 使用ID乘以黄金比例，然后取小数部分作为色相
        hue = (category_id * golden_ratio) % 1.0
        
        # 调整饱和度和亮度参数，确保颜色既不太刺眼也不太暗淡
        saturation = 0.6  # 中等饱和度
        value = 0.9       # 高亮度
        
        # 创建颜色对象
        color = QColor()
        color.setHsvF(hue, saturation, value)
        
        # 计算颜色的亮度 (YIQ公式)
        brightness = 0.299 * color.redF() + 0.587 * color.greenF() + 0.114 * color.blueF()
        
        # 如果颜色太亮(接近白色)，降低亮度
        if brightness > 0.85:
            value = 0.7
            color.setHsvF(hue, saturation, value)
        
        # 如果颜色太暗(接近黑色)，提高亮度
        elif brightness < 0.3:
            value = 0.8
            color.setHsvF(hue, saturation, value)
        
        return color


    def generate_color(self, item_id, saturation=0.7, value=0.95):
        """使用黄金分割比例生成无限颜色
        
        参数:
            item_id: 项目ID，用于确定颜色序列中的位置
            saturation: 饱和度 (0-1)
            value: 亮度 (0-1)
        
        返回:
            QColor对象
        """
        # 黄金比例常数
        golden_ratio = 0.618033988749895
        
        # 使用ID乘以黄金比例，然后取小数部分
        hue = (item_id * golden_ratio) % 1.0
        
        # 将色相转换为QColor
        color = QColor()
        color.setHsvF(hue, saturation, value)
        return color

    def generate_harmonious_color(self, item_id, saturation=0.6, value=0.9):
        """增强版和谐颜色生成"""
        # 使用斐波那契散列确保更好的颜色分布
        def fib_hash(n):
            phi = (1 + 5**0.5) / 2
            return (n * phi) % 1.0
        
        hue = fib_hash(item_id)
        
        # 动态调整饱和度基于ID的奇偶性
        saturation = saturation + (0.1 if item_id % 2 else -0.05)
        saturation = max(0.3, min(0.9, saturation))
        
        # 创建颜色对象
        bg_color = QColor()
        bg_color.setHsvF(hue, saturation, value)
        
        # 使用感知亮度公式
        brightness = (0.2126 * bg_color.redF() + 
                    0.7152 * bg_color.greenF() + 
                    0.0722 * bg_color.blueF())
        
        # 自动对比度文字颜色（考虑色盲友好）
        text_color = QColor(Qt.black) if brightness > 0.45 else QColor(Qt.white)
        
        return (bg_color, text_color)

    def perform_auto_backup(self):
        """执行智能备份，包含循环清理"""
        try:
            # 1. 创建新备份
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = os.path.join(
                self.backup_config['backup_dir'],
                f"{self.backup_config['backup_prefix']}{timestamp}.db"
            )
            
            # 使用WAL模式确保备份一致性
            self.cursor.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            
            # 执行备份
            backup_conn = sqlite3.connect(backup_file)
            with backup_conn:
                self.conn.backup(backup_conn)
            backup_conn.close()
            
            # 2. 清理旧备份
            self.cleanup_old_backups()
            
            self.show_status_message(f"数据库备份完成: {backup_file}", 3000)
            return True
        except Exception as e:
            print(f"备份失败: {str(e)}")
            return False

    def cleanup_old_backups(self):
        """清理超出数量的旧备份"""
        try:
            # 获取所有备份文件（按时间排序）
            backups = sorted(
                glob.glob(os.path.join(
                    self.backup_config['backup_dir'],
                    f"{self.backup_config['backup_prefix']}*.db"
                )),
                key=os.path.getmtime
            )
            
            # 删除超出数量的旧备份
            while len(backups) > self.backup_config['max_backups']:
                oldest_backup = backups.pop(0)
                try:
                    os.remove(oldest_backup)
                    print(f"已清理旧备份: {oldest_backup}")
                except Exception as e:
                    print(f"清理备份失败: {oldest_backup} - {str(e)}")
        except Exception as e:
            print(f"备份清理出错: {str(e)}")


    def clear_search(self):
        """清除搜索条件"""
        self.search_input.clear()
        self.advanced_search_group.setChecked(False)
        self.load_text_list()

    def show_about_dialog(self):
        """显示关于对话框"""
        about_text = f"""
        <h2>{self.ABOUT['name']}</h2>
        <p>版本: {self.ABOUT['version']} (Build {self.ABOUT['build_date']})</p>
        <p>{self.ABOUT['description']}</p>
        
        <h3>主要功能:</h3>
        <ul>
            {"".join(f"<li>{feature}</li>" for feature in self.ABOUT['features'])}
        </ul>
        
        <p>作者: {self.ABOUT['author']}<br>
        许可证: {self.ABOUT['license']}<br>
        {self.ABOUT['copyright']}</p>
        
        <p>项目主页: <a href="{self.ABOUT['url']}">{self.ABOUT['url']}</a></p>
        """
        
        msg = QMessageBox(self)
        msg.setWindowTitle("关于")
        msg.setTextFormat(Qt.RichText)
        msg.setText(about_text)
        msg.setIconPixmap(QIcon('icon.ico').pixmap(64, 64))
        msg.exec_()


    def closeEvent(self, event):
        """关闭时执行智能备份"""
        self.perform_auto_backup()  # 使用新的备份方法
        
        # 原有清理逻辑
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