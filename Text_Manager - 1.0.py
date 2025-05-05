import os
import sys
import sqlite3
import re
from pypinyin import lazy_pinyin
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QTextEdit, QPushButton, QListWidget,
                             QMessageBox, QComboBox, QStatusBar)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFont, QIcon


class TextManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('文本管理工具')
        self.setWindowIcon(QIcon('icon.ico'))  # 请准备一个icon.png文件或删除这行
        
        # 初始化数据库
        self.init_db()
        
        # 设置主窗口大小和最小尺寸
        self.resize(800, 600)
        self.setMinimumSize(QSize(600, 400))
        
        # 创建主部件和布局
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        self.main_layout = QHBoxLayout()
        self.main_widget.setLayout(self.main_layout)
        
        # 左侧面板 - 文本列表和搜索
        self.left_panel = QWidget()
        self.left_layout = QVBoxLayout()
        self.left_panel.setLayout(self.left_layout)
        
        # 搜索区域
        self.search_label = QLabel('搜索:')
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText('输入标题或内容(支持拼音首字母)')
        self.search_input.textChanged.connect(self.search_texts)
        self.search_mode = QComboBox()
        self.search_mode.addItems(['模糊搜索', '精确搜索'])
        
        search_top_layout = QHBoxLayout()
        search_top_layout.addWidget(self.search_label)
        search_top_layout.addWidget(self.search_mode)
        
        self.left_layout.addLayout(search_top_layout)
        self.left_layout.addWidget(self.search_input)
        
        # 文本列表
        self.text_list = QListWidget()
        self.text_list.itemClicked.connect(self.load_text)
        self.left_layout.addWidget(self.text_list)
        
        # 右侧面板 - 文本编辑和操作
        self.right_panel = QWidget()
        self.right_layout = QVBoxLayout()
        self.right_panel.setLayout(self.right_layout)
        
        # 标题区域
        self.title_label = QLabel('标题:')
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText('输入文本标题')
        self.right_layout.addWidget(self.title_label)
        self.right_layout.addWidget(self.title_input)
        
        # 文本编辑区域
        self.content_label = QLabel('内容:')
        self.content_input = QTextEdit()
        self.content_input.setPlaceholderText('输入文本内容')
        self.content_input.textChanged.connect(self.update_word_count)
        self.right_layout.addWidget(self.content_label)
        self.right_layout.addWidget(self.content_input)
        
        # 操作按钮
        self.btn_save = QPushButton('保存')
        self.btn_save.clicked.connect(self.save_text)
        self.btn_new = QPushButton('新建')
        self.btn_new.clicked.connect(self.new_text)
        self.btn_delete = QPushButton('删除')
        self.btn_delete.clicked.connect(self.delete_text)
        
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.btn_new)
        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_delete)
        self.right_layout.addLayout(btn_layout)
        
        # 状态栏 - 显示字数统计
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.word_count_label = QLabel('字数: 0')
        self.status_bar.addPermanentWidget(self.word_count_label)
        
        # 将左右面板添加到主布局
        self.main_layout.addWidget(self.left_panel, 1)
        self.main_layout.addWidget(self.right_panel, 2)
        
        # 加载所有文本到列表
        self.load_text_list()
        
        # 设置字体
        self.set_font()
    
    def set_font(self):
        """设置统一的字体"""
        font = QFont('Microsoft YaHei', 10)  # 使用微软雅黑字体
        self.setFont(font)
        self.status_bar.setFont(font)
    
    def init_db(self):
        """初始化数据库"""
        self.conn = sqlite3.connect('text_manager.db')
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
        self.conn.commit()
    
    def load_text_list(self, search_query=None):
        """加载文本列表"""
        self.text_list.clear()
        
        if search_query:
            # 如果是搜索查询，使用模糊匹配
            query = '''
            SELECT id, title FROM texts 
            WHERE title LIKE ? OR content LIKE ? OR title LIKE ? OR content LIKE ?
            ORDER BY update_time DESC
            '''
            pinyin_query = self.get_pinyin_query(search_query)
            params = (f'%{search_query}%', f'%{search_query}%', 
                      f'%{pinyin_query}%', f'%{pinyin_query}%')
            
            if self.search_mode.currentText() == '精确搜索':
                query = '''
                SELECT id, title FROM texts 
                WHERE title = ? OR content = ? OR title = ? OR content = ?
                ORDER BY update_time DESC
                '''
                params = (search_query, search_query, pinyin_query, pinyin_query)
        else:
            # 加载所有文本
            query = 'SELECT id, title FROM texts ORDER BY update_time DESC'
            params = ()
        
        self.cursor.execute(query, params)
        texts = self.cursor.fetchall()
        
        for text_id, title in texts:
            self.text_list.addItem(f"{title} (ID: {text_id})")
    
    def load_text(self, item):
        """加载选中的文本内容"""
        # 从列表项中提取ID
        text_id = int(item.text().split('(ID: ')[1].rstrip(')'))
        
        self.cursor.execute('SELECT title, content FROM texts WHERE id = ?', (text_id,))
        title, content = self.cursor.fetchone()
        
        self.current_id = text_id
        self.title_input.setText(title)
        self.content_input.setPlainText(content)
    
    def save_text(self):
        """保存文本"""
        title = self.title_input.text().strip()
        content = self.content_input.toPlainText().strip()
        
        if not title:
            QMessageBox.warning(self, '警告', '标题不能为空!')
            return
        
        if hasattr(self, 'current_id'):
            # 更新现有文本
            self.cursor.execute('''
            UPDATE texts SET title = ?, content = ?, update_time = CURRENT_TIMESTAMP
            WHERE id = ?
            ''', (title, content, self.current_id))
        else:
            # 插入新文本
            self.cursor.execute('''
            INSERT INTO texts (title, content) VALUES (?, ?)
            ''', (title, content))
            self.current_id = self.cursor.lastrowid
        
        self.conn.commit()
        self.load_text_list()
        QMessageBox.information(self, '成功', '文本已保存!')
    
    def new_text(self):
        """新建文本"""
        self.current_id = None
        self.title_input.clear()
        self.content_input.clear()
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
            self.cursor.execute('DELETE FROM texts WHERE id = ?', (self.current_id,))
            self.conn.commit()
            self.new_text()
            self.load_text_list()
            QMessageBox.information(self, '成功', '文本已删除!')
    
    def search_texts(self):
        """搜索文本"""
        search_query = self.search_input.text().strip()
        self.load_text_list(search_query if search_query else None)
    
    def update_word_count(self):
        """更新字数统计"""
        content = self.content_input.toPlainText()
        # 简单的字数统计：中文字符和单词
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', content))
        english_words = len(re.findall(r'\b[a-zA-Z]+\b', content))
        total = chinese_chars + english_words
        self.word_count_label.setText(f'字数: {total}')
    
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
    
    def closeEvent(self, event):
        """关闭窗口时关闭数据库连接"""
        self.conn.close()
        event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    manager = TextManager()
    manager.show()
    sys.exit(app.exec_())