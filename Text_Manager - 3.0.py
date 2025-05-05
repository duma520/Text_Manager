import sys
import sqlite3
import re
import datetime
import markdown
from pypinyin import lazy_pinyin
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QTextEdit, QPushButton, QListWidget,
                             QMessageBox, QComboBox, QStatusBar, QTabWidget, QFileDialog,
                             QTreeWidget, QTreeWidgetItem, QInputDialog, QAction, QMenu)
from PyQt5.QtCore import Qt, QSize, QTimer
from PyQt5.QtGui import QFont, QIcon, QTextCursor, QKeySequence


class TextManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('高级文本管理工具')
        self.setWindowIcon(QIcon('icon.png'))
        
        # 初始化数据库和UI
        self.init_db()
        self.init_ui()
        self.init_shortcuts()
        
        # 加载初始数据
        self.load_categories()
        self.load_text_list()
        
        # 自动保存定时器
        self.auto_save_timer = QTimer()
        self.auto_save_timer.timeout.connect(self.auto_save)
        self.auto_save_timer.start(30000)  # 30秒自动保存
        
    def init_db(self):
        """初始化数据库结构"""
        self.conn = sqlite3.connect('text_manager_enhanced.db')
        self.cursor = self.conn.cursor()
        
        # 核心表
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
            FOREIGN KEY (category_id) REFERENCES categories(id)
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
        ''')
        self.conn.commit()
        
    def init_ui(self):
        """初始化用户界面"""
        self.resize(1000, 700)
        self.setMinimumSize(QSize(800, 500))
        
        # 主布局
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        self.main_layout = QHBoxLayout()
        self.main_widget.setLayout(self.main_layout)
        
        # 左侧面板 (分类树+文本列表)
        self.left_panel = QWidget()
        self.left_layout = QVBoxLayout()
        self.left_panel.setLayout(self.left_layout)
        
        # 分类树
        self.category_tree = QTreeWidget()
        self.category_tree.setHeaderLabel('分类')
        self.category_tree.itemClicked.connect(self.filter_by_category)
        self.left_layout.addWidget(self.category_tree)
        
        # 标签云
        self.tag_cloud = QComboBox()
        self.tag_cloud.setEditable(True)
        self.tag_cloud.setPlaceholderText("选择或输入标签...")
        self.tag_cloud.currentTextChanged.connect(self.filter_by_tag)
        self.left_layout.addWidget(QLabel('标签筛选:'))
        self.left_layout.addWidget(self.tag_cloud)
        
        # 搜索区域
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText('搜索标题/内容/拼音首字母...')
        self.search_input.textChanged.connect(self.search_texts)
        self.left_layout.addWidget(self.search_input)
        
        # 文本列表
        self.text_list = QListWidget()
        self.text_list.itemClicked.connect(self.load_text)
        self.left_layout.addWidget(self.text_list)
        
        # 右侧面板 (编辑区)
        self.right_panel = QTabWidget()
        self.main_layout.addWidget(self.left_panel, 2)
        self.main_layout.addWidget(self.right_panel, 3)
        
        # 创建编辑选项卡
        self.create_edit_tab()
        self.create_preview_tab()
        
        # 状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # 字数统计
        self.word_count_label = QLabel('字数: 0')
        self.status_bar.addPermanentWidget(self.word_count_label)
        
        # 自动保存指示器
        self.save_indicator = QLabel('🟢 已自动保存')
        self.status_bar.addPermanentWidget(self.save_indicator)
        self.save_indicator.setVisible(False)
        
        # 菜单栏
        self.create_menus()
        
    def create_edit_tab(self):
        """创建编辑选项卡"""
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
        
        btn_layout.addWidget(self.btn_new)
        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_delete)
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
        
    def create_menus(self):
        """创建菜单栏"""
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
        
        exit_action = QAction('退出', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 编辑菜单
        edit_menu = menubar.addMenu('编辑')
        
        template_action = QAction('插入模板', self)
        template_action.triggered.connect(self.insert_template)
        edit_menu.addAction(template_action)
        
        # 分类菜单
        category_menu = menubar.addMenu('分类')
        
        new_category_action = QAction('新建分类', self)
        new_category_action.triggered.connect(self.add_category)
        category_menu.addAction(new_category_action)
        
        manage_categories_action = QAction('管理分类', self)
        manage_categories_action.triggered.connect(self.manage_categories)
        category_menu.addAction(manage_categories_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu('帮助')
        about_action = QAction('关于', self)
        help_menu.addAction(about_action)
        
    def init_shortcuts(self):
        """初始化快捷键"""
        # 保存快捷键
        self.shortcut_save = QShortcut(QKeySequence("Ctrl+S"), self)
        self.shortcut_save.activated.connect(self.save_text)
        
        # 新建快捷键
        self.shortcut_new = QShortcut(QKeySequence("Ctrl+N"), self)
        self.shortcut_new.activated.connect(self.new_text)
        
        # 搜索快捷键
        self.shortcut_search = QShortcut(QKeySequence("Ctrl+F"), self)
        self.shortcut_search.activated.connect(lambda: self.search_input.setFocus())
        
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
        
        # 加载标签
        self.load_tags()
        
    def load_tags(self):
        """加载标签数据"""
        self.tag_cloud.clear()
        self.cursor.execute("SELECT name FROM tags ORDER BY name")
        tags = [tag[0] for tag in self.cursor.fetchall()]
        self.tag_cloud.addItems(tags)
        
    def load_text_list(self, category_id=None, tag_name=None, search_query=None):
        """加载文本列表"""
        self.text_list.clear()
        
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
        
        for text_id, title, category_name in texts:
            item = QListWidgetItem(f"{title} [{category_name or '未分类'}] (ID: {text_id})")
            item.setData(Qt.UserRole, text_id)
            self.text_list.addItem(item)
    
    def load_text(self, item):
        """加载选中的文本内容"""
        text_id = item.data(Qt.UserRole)
        
        self.cursor.execute('''
        SELECT t.title, t.content, t.category_id, t.is_markdown, 
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
            
        title, content, category_id, is_markdown, tags = result
        
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
        
    def save_text(self):
        """保存文本"""
        title = self.title_input.text().strip()
        content = self.content_input.toPlainText().strip()
        category_id = self.category_combo.currentData()
        is_markdown = self.format_combo.currentIndex() == 1
        tags = [tag.strip() for tag in self.tag_edit.text().split(',') if tag.strip()]
        
        if not title:
            QMessageBox.warning(self, '警告', '标题不能为空!')
            return
        
        try:
            if hasattr(self, 'current_id'):
                # 更新现有文本
                self.cursor.execute('''
                UPDATE texts 
                SET title=?, content=?, category_id=?, is_markdown=?, update_time=CURRENT_TIMESTAMP
                WHERE id=?
                ''', (title, content, category_id, is_markdown, self.current_id))
                text_id = self.current_id
            else:
                # 插入新文本
                self.cursor.execute('''
                INSERT INTO texts (title, content, category_id, is_markdown)
                VALUES (?, ?, ?, ?)
                ''', (title, content, category_id, is_markdown))
                text_id = self.cursor.lastrowid
                self.current_id = text_id
            
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
    
    def auto_save(self):
        """自动保存当前文本"""
        if hasattr(self, 'current_id') and self.title_input.text().strip():
            self.save_text()
    
    def show_auto_save_indicator(self):
        """显示自动保存指示器"""
        self.save_indicator.setText('🟢 ' + datetime.datetime.now().strftime('%H:%M:%S 已保存'))
        self.save_indicator.setVisible(True)
        QTimer.singleShot(3000, lambda: self.save_indicator.setVisible(False))
    
    def new_text(self):
        """新建文本"""
        self.current_id = None
        self.title_input.clear()
        self.content_input.clear()
        self.tag_edit.clear()
        self.category_combo.setCurrentIndex(0)
        self.format_combo.setCurrentIndex(0)
        self.title_input.setFocus()
    
    def delete_text(self):
        """删除当前文本"""
        if not hasattr(self, 'current_id'):
            QMessageBox.warning(self, '警告', '没有选中任何文本!')
            return
        
        reply = QMessageBox.question(
            self, '确认', '确定要删除这个文本吗?', 
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.cursor.execute('DELETE FROM texts WHERE id=?', (self.current_id,))
            self.cursor.execute('DELETE FROM text_tags WHERE text_id=?', (self.current_id,))
            self.conn.commit()
            self.new_text()
            self.load_text_list()
            self.show_status_message('删除成功!', 2000)
    
    def search_texts(self):
        """搜索文本"""
        search_query = self.search_input.text().strip()
        self.load_text_list(search_query=search_query if search_query else None)
    
    def filter_by_category(self, item):
        """按分类筛选文本"""
        category_id = item.data(0, Qt.UserRole)
        self.load_text_list(category_id=category_id)
    
    def filter_by_tag(self, tag_name):
        """按标签筛选文本"""
        if tag_name:
            self.load_text_list(tag_name=tag_name)
    
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
    
    def update_word_count(self):
        """更新字数统计"""
        content = self.content_input.toPlainText()
        # 中文按字符统计，英文按单词统计
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', content))
        english_words = len(re.findall(r'\b[a-zA-Z]+\b', content))
        total = chinese_chars + english_words
        self.word_count_label.setText(f'字数: {total}')
        
        # 如果是Markdown模式，更新预览
        if self.format_combo.currentIndex() == 1:
            self.update_preview()
    
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
            'Markdown文件 (*.md);;文本文件 (*.txt);;所有文件 (*.*)'
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.content_input.toPlainText())
                self.show_status_message(f'已导出到: {file_path}', 3000)
            except Exception as e:
                QMessageBox.critical(self, '错误', f'导出失败: {str(e)}')
    
    def batch_export(self):
        """批量导出"""
        # 实现批量导出功能 (可扩展)
        QMessageBox.information(self, '提示', '批量导出功能将在后续版本实现')
    
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
    
    def show_status_message(self, message, timeout=0):
        """在状态栏显示临时消息"""
        self.status_bar.showMessage(message, timeout)
    
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