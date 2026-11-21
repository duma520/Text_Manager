import sys
import sqlite3
import re
import datetime
import time
import os
import math
import shutil
import json

# 布局类
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout
# 控件类
from PySide6.QtWidgets import (
                                QApplication, QMainWindow, QWidget, QLabel, QLineEdit, 
                                QTextEdit, QPushButton, QListWidget, QMessageBox, QComboBox,
                                QStatusBar, QTabWidget, QFileDialog, QTreeWidget, QTreeWidgetItem,
                                QInputDialog, QMenu, QScrollArea, QDialog,
                                QDialogButtonBox, QCheckBox, QSpinBox, QDateEdit, QGroupBox,
                                QListWidgetItem, QToolBar, QFontComboBox, QToolButton, QButtonGroup,
                                QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar, QTextBrowser,
                                QFrame, QSplitter, QPlainTextEdit, QColorDialog
                            )
from PySide6.QtCore import Qt, QSize, QTimer, QDate, QMimeData, QEvent, QEventLoop, QThread, Signal
from PySide6.QtGui import QFont, QIcon, QTextCursor, QKeySequence, QPainter, QColor, QAction, QShortcut

# 重量级模块改为延迟导入，加快程序启动速度
# markdown    → 在 ProjectInfo.markdown_to_html / update_preview / batch_export / export_text 中按需导入
# pypinyin    → 在 get_pinyin_query 中按需导入
# QtChart     → 在 update_basic_stats 中按需导入
# glob        → 在 backup/cleanup 方法中按需导入
# traceback   → 在异常处理中按需导入
# jieba       → 在 extract_keywords 中按需导入（已有）



class ProjectInfo:
    """项目信息元数据（集中管理所有项目相关信息）"""
    VERSION = "8.2.0"
    BUILD_DATE = "2026-08-20"
    # BUILD_DATE = datetime.now().strftime("%Y-%m-%d")  # 修改为动态获取当前日期
    AUTHOR = "杜玛"
    LICENSE = "MIT"
    COPYRIGHT = "© 永久 杜玛"
    URL = "https://github.com/duma520"
    MAINTAINER_EMAIL = "不提供"
    NAME = "高级文本管理工具"
    DESCRIPTION = "高级文本管理工具，支持多种格式和高级搜索功能"
    VERSION_HISTORY = {
        "6.46.0": "增加复制预览内容",
        "6.55.0": "增加自动备份功能",
        "6.60.0": "修复纯文本/粘贴时丢弃富文本格式",
        "6.61.0": "优化启动速度（延迟导入重量级模块）",
        "7.1.0": "从 PyQt5 升级到 PySide6",
        "7.3.0": "多线程改造：文本分析/批量操作/备份等改用后台线程，避免UI卡顿",
        "7.4.0": "增加设置功能，支持自定义自动保存时间间隔",
        "7.5.0": "增加列表排序方式设置；移除自定义样式改用默认风格；扩大自动保存间隔范围",
        "7.6.0": "增加多套界面风格选择（默认/马卡龙/莫兰迪/中国传统色系）",
        "8.0.0": "升级到 8.0 版本",
        "8.1.0": "设置改为实时自动保存+持久保存（原子写入），避免设置丢失",
        "8.2.0": "增加窗口几何/最大化状态记忆（closeEvent 保存，启动恢复）"
    }
    HELP_TEXT = """
使用说明:


"""



    @classmethod
    def get_metadata(cls) -> dict:
        """获取主要元数据字典"""
        return {
            'version': cls.VERSION,
            'author': cls.AUTHOR,
            'license': cls.LICENSE,
            'url': cls.URL
        }



    @classmethod
    def get_header(cls) -> str:
        """生成标准化的项目头信息"""
        return f"{cls.NAME} {cls.VERSION} | {cls.LICENSE} License | {cls.URL}"

    @classmethod
    def get_about_info(cls):
        """获取ABOUT信息字典"""
        return {
            "name": cls.NAME,
            "version": cls.VERSION,
            "build_date": cls.BUILD_DATE,
            "author": cls.AUTHOR,
            "license": cls.LICENSE,
            "copyright": cls.COPYRIGHT,
            "url": cls.URL,
            "description": cls.DESCRIPTION,
            "features": [
                "支持纯文本、Markdown和HTML格式",
                "全文搜索和高级筛选",
                "标签和分类管理",
                "回收站功能",
                "批量操作",
                "文本分析和统计"
            ]
        }

    @staticmethod
    def strip_markdown(text):
        """去除Markdown格式符号"""
        # 去除标题符号
        text = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE)
        # 去除粗体、斜体等格式符号
        text = re.sub(r'\*{1,2}(.*?)\*{1,2}', r'\1', text)
        text = re.sub(r'_{1,2}(.*?)_{1,2}', r'\1', text)
        # 去除代码块和行内代码
        text = re.sub(r'`{3}.*?`{3}', '', text, flags=re.DOTALL)
        text = re.sub(r'`(.*?)`', r'\1', text)
        # 去除链接和图片标记
        text = re.sub(r'!?\[(.*?)\]\(.*?\)', r'\1', text)
        # 去除列表符号
        text = re.sub(r'^[\*\+-]\s+', '', text, flags=re.MULTILINE)
        # 去除引用符号
        text = re.sub(r'^>\s*', '', text, flags=re.MULTILINE)
        return text.strip()

    @staticmethod
    def html_to_plain(html):
        """将HTML转换为纯文本（完整实现）"""
        # 移除HTML标签
        text = re.sub(r'<[^>]+>', '', html)
        # 替换HTML实体
        text = text.replace('&nbsp;', ' ').replace('&lt;', '<').replace('&gt;', '>')
        # 合并多余的空格和换行
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    @staticmethod
    def wysiwyg_to_plain(wysiwyg_content):
        """将即见即所得内容转为纯文本"""
        return ProjectInfo.html_to_plain(wysiwyg_content)
    @staticmethod
    def plain_to_html(plain_text):
        """将纯文本转为基本HTML"""
        # 保留换行符，用<br>替换
        html = plain_text.replace('\n', '<br>')
        return f"<div>{html}</div>"
    @staticmethod
    def markdown_to_html(markdown_text):
        """将Markdown转为HTML"""
        import markdown
        return markdown.markdown(markdown_text)




# 马卡龙色系定义
class MacaronColors_12:
    # 粉色系
    SAKURA_PINK = QColor('#FFB7CE')  # 樱花粉
    ROSE_PINK = QColor('#FF9AA2')    # 玫瑰粉
    # 蓝色系
    SKY_BLUE = QColor('#A2E1F6')     # 天空蓝
    LILAC_MIST = QColor('#E6E6FA')   # 淡丁香
    # 绿色系
    MINT_GREEN = QColor('#B5EAD7')   # 薄荷绿
    APPLE_GREEN = QColor('#D4F1C7')  # 苹果绿
    # 黄色/橙色系
    LEMON_YELLOW = QColor('#FFEAA5') # 柠檬黄
    BUTTER_CREAM = QColor('#FFF8B8') # 奶油黄
    PEACH_ORANGE = QColor('#FFDAC1') # 蜜桃橙
    # 紫色系
    LAVENDER = QColor('#C7CEEA')     # 薰衣草紫
    TARO_PURPLE = QColor('#D8BFD8')  # 香芋紫
    # 中性色
    CARAMEL_CREAM = QColor('#F0E6DD') # 焦糖奶霜

# ============================================================
# 后台工作线程类 (多线程改造，避免UI卡顿)
# ============================================================

class AnalysisWorker(QThread):
    """文本分析后台工作线程"""
    progress = Signal(int, str)          # 进度百分比, 状态描述
    stats_ready = Signal(dict)           # 基本统计数据
    keywords_ready = Signal(list)        # 关键词列表
    similar_ready = Signal(list)         # 相似文本列表 [(text_id, title, category, similarity, features), ...]
    feature_weights_ready = Signal(dict) # 当前文本特征权重
    readability_ready = Signal(dict)     # 可读性分析结果
    sentiment_ready = Signal(dict)       # 情感分析结果
    features_ready = Signal(dict)        # 文本特征
    finished = Signal()                  # 分析完成
    error = Signal(str)                  # 错误信息

    def __init__(self, content, current_id, db_path):
        super().__init__()
        self.content = content
        self.current_id = current_id
        self.db_path = db_path

    def run(self):
        try:
            # 为工作线程创建独立的数据库连接
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 1. 基本统计 (5%-20%)
            self.progress.emit(5, "正在计算基本统计...")
            stats = self._calc_basic_stats(self.content)
            self.progress.emit(20, "基本统计完成")
            self.stats_ready.emit(stats)

            # 2. 关键词提取 (20%-35%)
            self.progress.emit(20, "正在提取关键词...")
            keywords = self._extract_keywords(cursor, self.content)
            self.progress.emit(35, "关键词提取完成")
            self.keywords_ready.emit(keywords)

            # 3. 相似文本查找 (35%-50%)
            self.progress.emit(35, "正在查找相似文本...")
            similar_texts = self._find_similar_texts(cursor)
            self.progress.emit(50, "相似文本查找完成")
            self.similar_ready.emit(similar_texts)

            # 4. 段落统计 (50%-55%)
            self.progress.emit(50, "正在统计段落...")
            paragraph_count = len([p for p in self.content.split('\n') if p.strip()])

            # 5. 可读性分析 (55%-75%)
            self.progress.emit(55, "正在分析可读性...")
            readability = self._calc_readability(self.content)
            readability['paragraph_count'] = paragraph_count
            self.progress.emit(75, "可读性分析完成")
            self.readability_ready.emit(readability)

            # 6. 情感分析 (75%-90%)
            self.progress.emit(75, "正在分析情感倾向...")
            sentiment = self._calc_sentiment(self.content)
            self.progress.emit(90, "情感分析完成")
            self.sentiment_ready.emit(sentiment)

            # 7. 文本特征分析 (90%-100%)
            self.progress.emit(90, "正在提取文本特征...")
            features = self._extract_text_features(cursor, self.content)
            self.feature_weights_ready.emit(features)
            self.features_ready.emit(features)
            self.progress.emit(100, "分析完成")

            conn.close()
            self.finished.emit()

        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))

    def _calc_basic_stats(self, content):
        """计算基本统计数据"""
        return {
            'total_chars': len(content),
            'chinese_chars': len(re.findall(r'[\u4e00-\u9fff]', content)),
            'english_words': len(re.findall(r'\b[a-zA-Z]+\b', content)),
            'numbers': len(re.findall(r'\d+', content)),
            'punctuation': len(re.findall(r'[,.!?;:，。！？；：、]', content)),
            'spaces': content.count(' '),
            'newlines': content.count('\n'),
        }

    def _extract_keywords(self, cursor, content, top_n=10):
        """在后台线程中提取关键词（使用独立数据库连接）"""
        try:
            import jieba
            import jieba.analyse

            if not hasattr(jieba, 'dt'):
                jieba.initialize()

            stop_words = {
                '的', '了', '和', '是', '在', '我', '有', '这', '那', '你', '他', '她', '它',
                '我们', '你们', '他们', '这个', '那个', '要', '也', '都', '会', '可以', '可能',
                '就是', '这样', '这些', '那些', '一些', '一点', '一种', '一样', '一般', '一定',
                '非常', '很多', '什么', '为什么', '怎么', '如何', '因为', '所以', '但是', '虽然',
                '如果', '然后', '而且', '或者', '还是', '不是', '没有', '不要', '不能', '需要',
                '应该', '可能', '可以', '必须', '只是', '真是',
            }

            keywords = jieba.analyse.extract_tags(
                content, topK=top_n * 2, withWeight=True,
                allowPOS=('n', 'vn', 'v', 'a')
            )

            filtered_keywords = [
                (word, weight) for word, weight in keywords
                if word not in stop_words and len(word) > 1
            ][:top_n]

            # 计算文档频率 (IDF)
            cursor.execute("SELECT COUNT(*) FROM texts")
            total_docs = cursor.fetchone()[0]

            doc_freq = {}
            if total_docs > 0:
                for word, _ in filtered_keywords:
                    cursor.execute(
                        "SELECT COUNT(*) FROM texts WHERE content LIKE ?",
                        (f'%{word}%',)
                    )
                    doc_freq[word] = cursor.fetchone()[0]

            final_keywords = []
            for word, weight in filtered_keywords:
                df = doc_freq.get(word, 1)
                idf = math.log((total_docs + 1) / (df + 1)) + 1
                adjusted_weight = weight * idf
                final_keywords.append((word, adjusted_weight))

            final_keywords.sort(key=lambda x: x[1], reverse=True)
            return [word for word, _ in final_keywords[:top_n]]

        except ImportError:
            # 回退到简单实现
            words = re.findall(r'[\u4e00-\u9fa5]{2,}', content)
            stop_words = ['的', '了', '和', '是', '在', '我', '有', '这', '那', '你']
            words = [w for w in words if w not in stop_words]
            word_counts = {}
            for w in words:
                word_counts[w] = word_counts.get(w, 0) + 1
            sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
            return [w for w, _ in sorted_words[:top_n]]
        except Exception:
            return []

    def _find_similar_texts(self, cursor):
        """在后台线程中查找相似文本"""
        results = []
        cursor.execute("SELECT id, title, content, category_id FROM texts WHERE id != ?", (self.current_id,))
        texts = cursor.fetchall()

        current_features = self._extract_text_features(cursor, self.content)

        for text_id, title, text, category_id in texts:
            features = self._extract_text_features(cursor, text)
            similarity = self._calculate_similarity(current_features, features)

            category_name = "未分类"
            if category_id:
                cursor.execute("SELECT name FROM categories WHERE id=?", (category_id,))
                res = cursor.fetchone()
                if res:
                    category_name = res[0]

            results.append((text_id, title, category_name, similarity, features))

        results.sort(key=lambda x: x[3], reverse=True)
        return results

    def _extract_text_features(self, cursor, text):
        """提取文本多维特征"""
        keywords = self._extract_keywords(cursor, text, top_n=10)

        return {
            'word_count': len(re.findall(r'\w+', text)),
            'unique_words': len(set(re.findall(r'\w+', text))),
            'lexical_diversity': len(set(re.findall(r'\w+', text))) / max(1, len(re.findall(r'\w+', text))),
            'chinese_chars': len(re.findall(r'[\u4e00-\u9fff]', text)),
            'chinese_ratio': len(re.findall(r'[\u4e00-\u9fff]', text)) / max(1, len(text)),
            'english_words': len(re.findall(r'\b[a-zA-Z]+\b', text)),
            'english_ratio': len(re.findall(r'\b[a-zA-Z]+\b', text)) / max(1, len(re.findall(r'\w+', text))),
            'avg_sentence_length': len(re.findall(r'\w+', text)) / max(1, len(re.split(r'[。！？.!?]+', text))),
            'paragraph_count': len([p for p in text.split('\n') if p.strip()]),
            'question_ratio': len(re.findall(r'[？?]', text)) / max(1, len(re.findall(r'[。.！!？?]', text))),
            'exclamation_ratio': len(re.findall(r'[！!]', text)) / max(1, len(re.findall(r'[。.！!？?]', text))),
            'keywords': keywords,
        }

    def _calculate_similarity(self, features1, features2):
        """计算多维特征相似度"""
        numeric_features = ['word_count', 'unique_words', 'lexical_diversity',
                        'chinese_chars', 'chinese_ratio', 'english_words',
                        'english_ratio', 'avg_sentence_length', 'paragraph_count',
                        'question_ratio', 'exclamation_ratio']

        numeric_sim = 0
        for feat in numeric_features:
            val1 = features1[feat]
            val2 = features2[feat]
            max_val = max(val1, val2) or 1
            numeric_sim += 1 - abs(val1 - val2) / max_val
        numeric_sim /= len(numeric_features)

        keywords1 = set(features1['keywords'])
        keywords2 = set(features2['keywords'])
        keyword_sim = len(keywords1 & keywords2) / max(1, len(keywords1 | keywords2))

        return 0.6 * numeric_sim + 0.4 * keyword_sim

    def _calc_readability(self, content):
        """计算可读性评分"""
        english_words = re.findall(r'\b[a-zA-Z]+\b', content)
        english_sentences = re.findall(r'[.!?]+', content)

        flesch_score = 0
        if english_words and english_sentences:
            avg_words_per_sentence = len(english_words) / len(english_sentences)
            avg_syllables_per_word = sum(len(re.findall(r'[aeiouyAEIOUY]+', word)) for word in english_words) / len(english_words)
            flesch_score = 206.835 - (1.015 * avg_words_per_sentence) - (84.6 * avg_syllables_per_word)

        chinese_chars = re.findall(r'[\u4e00-\u9fff]', content)
        chinese_sentences = re.split(r'[。！？；;]+', content)
        chinese_sentences = [s for s in chinese_sentences if s.strip()]

        chinese_score = 0
        if chinese_chars and chinese_sentences:
            avg_chars_per_sentence = len(chinese_chars) / len(chinese_sentences)
            common_word_ratio = len(re.findall(r'[的了是在有这我你他我们他们]', content)) / len(chinese_chars)
            chinese_score = 100 - (avg_chars_per_sentence * 0.5) + (common_word_ratio * 20)

        total_chars = len(content)
        if total_chars > 0:
            english_ratio = len(''.join(english_words)) / total_chars
            chinese_ratio = len(''.join(chinese_chars)) / total_chars
            readability = (flesch_score * english_ratio + chinese_score * chinese_ratio)
            readability = max(0, min(100, readability))
        else:
            readability = 0

        if readability >= 90:
            level = "非常容易"
            description = "文本极其易读，适合所有读者。"
        elif readability >= 80:
            level = "容易"
            description = "文本非常易读，适合普通大众阅读。"
        elif readability >= 70:
            level = "较容易"
            description = "文本比较容易理解，适合13-15岁学生。"
        elif readability >= 60:
            level = "标准"
            description = "文本难度适中，适合高中毕业生阅读。"
        elif readability >= 50:
            level = "较难"
            description = "文本有一定难度，适合大学生阅读。"
        elif readability >= 30:
            level = "困难"
            description = "文本难度较高，需要专业知识。"
        else:
            level = "非常困难"
            description = "文本极其难懂，需要专业领域知识。"

        return {
            'score': readability,
            'flesch_score': flesch_score,
            'chinese_score': chinese_score,
            'level': level,
            'description': description,
            'paragraph_count': 0,  # 由调用者填充
        }

    def _calc_sentiment(self, content):
        """计算情感倾向"""
        sentiment_dict = {
            'positive': {
                '好': 1, '优秀': 2, '成功': 2, '高兴': 1.5, '满意': 1.5,
                '喜欢': 1, '爱': 2, '开心': 1.5, '幸福': 2, '棒': 1,
                '完美': 2, '精彩': 1.5, '美丽': 1, '聪明': 1, '强大': 1,
            },
            'negative': {
                '坏': 1, '差': 1, '失败': 2, '伤心': 1.5, '不满': 1.5,
                '讨厌': 1.5, '恨': 2, '痛苦': 2, '糟糕': 1.5, '愚蠢': 1.5,
                '难看': 1, '弱': 1, '困难': 1, '麻烦': 1, '失望': 1.5,
            },
            'en_positive': {
                'good': 1, 'great': 2, 'excellent': 2, 'happy': 1.5, 'love': 2,
                'wonderful': 2, 'fantastic': 2, 'beautiful': 1, 'amazing': 2,
            },
            'en_negative': {
                'bad': 1, 'terrible': 2, 'awful': 2, 'sad': 1.5, 'hate': 2,
                'poor': 1, 'horrible': 2, 'ugly': 1, 'stupid': 1.5,
            },
            'negators': ['不', '没', '无', '非', '别', '未', '否'],
            'intensifiers': {
                '非常': 1.5, '很': 1.3, '特别': 1.5, '极其': 2, '十分': 1.5,
                '太': 1.5, '相当': 1.3, '挺': 1.2,
            },
        }

        positive_score = 0
        negative_score = 0
        sentiment_words = []

        sentences = re.split(r'[。！？；;.!?]+', content)

        for sentence in sentences:
            if not sentence.strip():
                continue

            has_negator = any(neg in sentence for neg in sentiment_dict['negators'])
            negator_factor = -1 if has_negator else 1

            intensifier = 1
            for word, factor in sentiment_dict['intensifiers'].items():
                if word in sentence:
                    intensifier *= factor
                    break

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

        top_words = sorted(sentiment_words, key=lambda x: abs(x[1]), reverse=True)[:5]
        word_details = "，".join(f"{word}({score:.1f})" for word, score in top_words)

        return {
            'sentiment': sentiment,
            'intensity': intensity,
            'positive_score': positive_score,
            'negative_score': negative_score,
            'word_details': word_details,
            'top_words': top_words,
        }


class BatchExportWorker(QThread):
    """批量导出后台工作线程"""
    progress = Signal(int, str)       # 进度百分比, 状态描述
    finished = Signal(int, str)       # 成功导出数量, 导出目录
    error = Signal(str)

    def __init__(self, text_ids, export_dir, export_format, db_path, current_view):
        super().__init__()
        self.text_ids = text_ids
        self.export_dir = export_dir
        self.export_format = export_format
        self.db_path = db_path
        self.current_view = current_view

    def run(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            total = len(self.text_ids)

            for i, text_id in enumerate(self.text_ids):
                self.progress.emit(int((i / total) * 100), f"正在导出 {i+1}/{total}...")

                if self.current_view == "recycle_bin":
                    cursor.execute("SELECT title, content FROM recycle_bin WHERE id = ?", (text_id,))
                else:
                    cursor.execute("SELECT title, content, is_markdown FROM texts WHERE id = ?", (text_id,))

                result = cursor.fetchone()
                if not result:
                    continue

                if self.current_view == "recycle_bin":
                    title, content = result
                    is_markdown = False
                else:
                    title, content, is_markdown = result

                if self.export_format == "Markdown (.md)":
                    ext = ".md"
                elif self.export_format == "HTML (.html)":
                    ext = ".html"
                    if is_markdown:
                        import markdown
                        content = markdown.markdown(content)
                else:
                    ext = ".txt"

                clean_title = re.sub(r'[\\/*?:"<>|]', "", title)
                file_path = os.path.join(self.export_dir, f"{clean_title}{ext}")

                counter = 1
                while os.path.exists(file_path):
                    file_path = os.path.join(self.export_dir, f"{clean_title}_{counter}{ext}")
                    counter += 1

                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)

            conn.close()
            self.progress.emit(100, "导出完成!")
            self.finished.emit(total, self.export_dir)

        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))


class BackupWorker(QThread):
    """数据库备份后台工作线程"""
    finished = Signal(str)       # 备份文件路径
    error = Signal(str)

    def __init__(self, db_path, backup_dir, backup_prefix, max_backups):
        super().__init__()
        self.db_path = db_path
        self.backup_dir = backup_dir
        self.backup_prefix = backup_prefix
        self.max_backups = max_backups

    def run(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("PRAGMA wal_checkpoint(TRUNCATE)")

            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = os.path.join(
                self.backup_dir,
                f"{self.backup_prefix}{timestamp}.db"
            )

            backup_conn = sqlite3.connect(backup_file)
            with backup_conn:
                conn.backup(backup_conn)
            backup_conn.close()

            # 清理旧备份
            import glob
            backups = sorted(
                glob.glob(os.path.join(self.backup_dir, f"{self.backup_prefix}*.db")),
                key=os.path.getmtime,
                reverse=True
            )
            while len(backups) > self.max_backups:
                oldest = backups.pop()
                try:
                    os.remove(oldest)
                except Exception:
                    pass

            conn.close()
            self.finished.emit(backup_file)

        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))


class DatabaseOptimizeWorker(QThread):
    """数据库优化后台工作线程"""
    finished = Signal(float)     # 耗时(秒)
    error = Signal(str)

    def __init__(self, db_path):
        super().__init__()
        self.db_path = db_path

    def run(self):
        try:
            start_time = time.time()
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("VACUUM")
            cursor.execute("ANALYZE")
            conn.close()
            elapsed = time.time() - start_time
            self.finished.emit(elapsed)
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))


class BatchOperationWorker(QThread):
    """批量操作（分类/标签）后台工作线程"""
    finished = Signal(int, str)   # 操作数量, 操作类型描述
    error = Signal(str)

    def __init__(self, db_path, text_ids, operation_type, **kwargs):
        super().__init__()
        self.db_path = db_path
        self.text_ids = text_ids
        self.operation_type = operation_type  # 'update_category' or 'add_tags'
        self.kwargs = kwargs

    def run(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            if self.operation_type == 'update_category':
                category_id = self.kwargs.get('category_id', 0)
                for text_id in self.text_ids:
                    cursor.execute(
                        "UPDATE texts SET category_id = ? WHERE id = ?",
                        (category_id, text_id)
                    )
                conn.commit()
                conn.close()
                self.finished.emit(len(self.text_ids), "分类更新")

            elif self.operation_type == 'add_tags':
                new_tags = self.kwargs.get('new_tags', [])
                for text_id in self.text_ids:
                    for tag_name in new_tags:
                        cursor.execute("SELECT id FROM tags WHERE name=?", (tag_name,))
                        tag_id = cursor.fetchone()
                        if not tag_id:
                            cursor.execute("INSERT INTO tags (name) VALUES (?)", (tag_name,))
                            tag_id = cursor.lastrowid
                        else:
                            tag_id = tag_id[0]

                        cursor.execute(
                            "SELECT 1 FROM text_tags WHERE text_id=? AND tag_id=?",
                            (text_id, tag_id)
                        )
                        if not cursor.fetchone():
                            cursor.execute(
                                "INSERT INTO text_tags (text_id, tag_id) VALUES (?, ?)",
                                (text_id, tag_id)
                            )
                conn.commit()
                conn.close()
                self.finished.emit(len(self.text_ids), "标签添加")

        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))


class TextManager(QMainWindow):
    # 类变量 - 集中管理关于信息
    ABOUT = ProjectInfo.get_about_info()

    # 类变量 - 集中管理配置参数
    SIMILAR_TEXT_DISPLAY_COUNT = 0  # 控制显示的相似文章数量，0表示显示全部


    def __init__(self):
        super().__init__()
        # title = f"{self.ABOUT['name']} v{self.ABOUT['version']} (Build {self.ABOUT['build_date']})"
        self.setWindowTitle(f"{ProjectInfo.NAME} {ProjectInfo.VERSION} (Build: {ProjectInfo.BUILD_DATE})")
        # self.setWindowTitle(title)
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

        # 安装事件过滤器（添加在这里↓↓↓）
        self.btn_new.installEventFilter(self)

        # 加载设置（必须在 load_text_list 之前，因为 load_text_list 依赖 settings 中的排序设置）
        self.settings = self.load_settings()

        # 恢复窗口几何与最大化状态（设置实时自动保存约定）
        self._restore_window_geometry()

        # 应用界面主题
        self.apply_theme()

        # 加载初始数据
        self.load_categories()
        self.load_tags()
        self.load_text_list()
        self.load_search_history()
        
        # 自动保存定时器（使用用户配置的时间间隔，默认30秒）
        self.auto_save_timer = QTimer()
        self.auto_save_timer.timeout.connect(self.auto_save)
        auto_save_interval = self.settings.get('auto_save_interval', 30) * 1000
        self.auto_save_timer.start(auto_save_interval)

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

        
        if current_version < 2:
            # 版本2升级：添加is_html列
            try:
                self.cursor.execute('ALTER TABLE texts ADD COLUMN is_html BOOLEAN DEFAULT 0')
                self.cursor.execute('INSERT INTO db_version (version) VALUES (2)')

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

        self.MACARON_COLORS = [
            # ======================
            # 标准马卡龙16色
            # ======================

            # 粉色系（4色）
            QColor(255, 183, 206),  # #FFB7CE 经典樱花粉
            QColor(255, 209, 220),  # #FFD1DC 泡泡糖粉
            QColor(255, 215, 225),  # #FFD7E1 草莓奶霜
            QColor(255, 227, 227),  # #FFE3E3 浅珊瑚粉

            # 蓝色系（3色）
            QColor(162, 225, 246),  # #A2E1F6 天空蓝
            QColor(200, 255, 240),  # #C8FFF0 冰蓝
            QColor(214, 232, 255),  # #D6E8FF 淡 powder 蓝

            # 绿色系（3色）
            QColor(181, 234, 215),  # #B5EAD7 薄荷绿
            QColor(210, 255, 210),  # #D2FFD2 苹果绿
            QColor(220, 245, 220),  # #DCF5DC 嫩绿

            # 黄色/橙色系（3色）
            QColor(255, 234, 165),  # #FFEAA5 柠檬黄
            QColor(255, 240, 200),  # #FFF0C8 奶油黄
            QColor(255, 218, 193),  # #FFDAC1 蜜桃橙

            # 紫色系（2色）
            QColor(199, 206, 234),  # #C7CEEA 薰衣草紫
            QColor(216, 191, 216),  # #D8BFD8 香芋紫

            # 中性色（1色）
            QColor(240, 230, 221),  # #F0E6DD 焦糖奶霜
        ]

        """初始化用户界面"""

        self.resize(1200, 800)
        self.setMinimumSize(QSize(900, 600))

        
        if hasattr(self, 'btn_new'):
            self.btn_new.setStyleSheet("background: red;")  # 强制设置醒目颜色

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
        self.view_toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
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
        self.batch_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.batch_btn.clicked.connect(self.show_batch_operations)
        self.left_layout.addWidget(self.batch_btn)

        
        # 右侧面板 (编辑区)
        self.right_panel = QTabWidget()
        self.main_layout.addWidget(self.left_panel, 3)
        self.main_layout.addWidget(self.right_panel, 7)
        
        # 创建编辑选项卡
        self.create_edit_tab()
        
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

        # 确保按钮可见且可点击
        self.btn_new.raise_()  # 确保按钮在最上层

        # 调试






    def show_text_analysis(self):
        """显示文本分析对话框（使用后台线程，避免UI卡顿）"""
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
        dialog.setStyleSheet('')  # 使用默认风格
        dialog.resize(800, 600)
        layout = QVBoxLayout()
        
        # 创建选项卡
        tab_widget = QTabWidget()
        
        # 1. 基本统计选项卡
        stats_tab = QWidget()
        stats_layout = QVBoxLayout()
        
        self.stats_info = QTextEdit()
        self.stats_info.setReadOnly(True)
        stats_layout.addWidget(self.stats_info)
        
        from PySide6.QtCharts import QChartView
        self.stats_chart_view = QChartView()
        stats_layout.addWidget(self.stats_chart_view)
        
        self.keywords_label = QLabel("关键词: 正在分析...")
        stats_layout.addWidget(self.keywords_label)
        
        self.paragraph_stats = QLabel("段落统计: 正在分析...")
        stats_layout.addWidget(self.paragraph_stats)
        
        stats_tab.setLayout(stats_layout)
        tab_widget.addTab(stats_tab, "基本统计")
        
        # 2. 相似文本选项卡
        similar_tab = QWidget()
        similar_layout = QVBoxLayout()
        
        similarity_desc = QLabel("基于以下特征计算相似度:")
        similar_layout.addWidget(similarity_desc)
        
        self.similarity_table = QTableWidget()
        self.similarity_table.setColumnCount(3)
        self.similarity_table.setHorizontalHeaderLabels(["特征", "权重", "贡献值"])
        self.similarity_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        similar_layout.addWidget(self.similarity_table)
        
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
        similar_layout.addWidget(QLabel(f"最相似文本:"))
        similar_layout.addWidget(self.similar_texts_list)
        
        self.similarity_detail = QTextEdit()
        self.similarity_detail.setReadOnly(True)
        self.similarity_detail.setFixedHeight(150)
        similar_layout.addWidget(QLabel("相似度分析详情:"))
        similar_layout.addWidget(self.similarity_detail)
        
        similar_tab.setLayout(similar_layout)
        tab_widget.addTab(similar_tab, "相似文本")

        # 3. 文本特征选项卡
        features_tab = QWidget()
        features_layout = QVBoxLayout()
        
        features_group = QGroupBox("文本特征概览")
        features_grid = QGridLayout()
        
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
        
        sentiment_card = QGroupBox("😊 情感倾向")
        sentiment_layout = QVBoxLayout()
        self.sentiment_label = QLabel("正在分析...")
        self.sentiment_graph = QLabel()
        self.sentiment_graph.setFixedHeight(30)
        sentiment_layout.addWidget(self.sentiment_label)
        sentiment_layout.addWidget(self.sentiment_graph)
        sentiment_card.setLayout(sentiment_layout)
        
        keywords_card = QGroupBox("🔑 关键词云")
        keywords_layout = QVBoxLayout()
        self.keywords_card_label = QLabel()
        self.keywords_card_label.setWordWrap(True)
        keywords_layout.addWidget(self.keywords_card_label)
        keywords_card.setLayout(keywords_layout)
        
        style_card = QGroupBox("✍️ 写作风格")
        style_layout = QVBoxLayout()
        self.style_label = QLabel("正在分析...")
        style_layout.addWidget(self.style_label)
        style_card.setLayout(style_layout)
        
        features_grid.addWidget(readability_card, 0, 0)
        features_grid.addWidget(sentiment_card, 0, 1)
        features_grid.addWidget(keywords_card, 1, 0)
        features_grid.addWidget(style_card, 1, 1)
        features_group.setLayout(features_grid)
        features_layout.addWidget(features_group)
        
        self.features_table = QTableWidget()
        self.features_table.setColumnCount(3)
        self.features_table.setHorizontalHeaderLabels(["特征类型", "特征值", "说明"])
        self.features_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        features_layout.addWidget(self.features_table)
        
        features_tab.setLayout(features_layout)
        tab_widget.addTab(features_tab, "文本特征")

        layout.addWidget(tab_widget)
        
        # 进度指示
        self.analyzing_label = QLabel("正在分析文本，请稍候...")
        self.analyzing_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.analyzing_label.setStyleSheet("font-size: 14px; color: #555;")
        layout.addWidget(self.analyzing_label)
        
        self.analysis_progress = QProgressBar()
        self.analysis_progress.setRange(0, 100)
        self.analysis_progress.setValue(0)
        layout.addWidget(self.analysis_progress)
        
        dialog.setLayout(layout)

        # ---- 启动后台分析线程 ----
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'text_manager_enhanced.db')
        self.analysis_worker = AnalysisWorker(content, self.current_id, db_path)
        
        # 存储相似文本数据以备show_similarity_detail使用
        self._similar_texts_data = {}
        
        self.analysis_worker.progress.connect(
            lambda pct, msg: self._on_analysis_progress(dialog, pct, msg)
        )
        self.analysis_worker.stats_ready.connect(
            lambda stats: self._on_stats_ready(content, stats)
        )
        self.analysis_worker.keywords_ready.connect(
            lambda kw: self._on_keywords_ready(kw)
        )
        self.analysis_worker.similar_ready.connect(
            lambda sim: self._on_similar_ready(sim)
        )
        self.analysis_worker.feature_weights_ready.connect(
            lambda fw: self._on_feature_weights_ready(fw)
        )
        self.analysis_worker.readability_ready.connect(
            lambda r: self._on_readability_ready(r)
        )
        self.analysis_worker.sentiment_ready.connect(
            lambda s: self._on_sentiment_ready(s)
        )
        self.analysis_worker.features_ready.connect(
            lambda f: self._on_features_ready(f)
        )
        self.analysis_worker.finished.connect(
            lambda: self._on_analysis_finished(dialog)
        )
        self.analysis_worker.error.connect(
            lambda err: self._on_analysis_error(dialog, err)
        )
        
        self.analysis_worker.start()
        dialog.exec()
        
        # 清理
        self.reading_progress.setFormat("进度: %p%")
        self.reading_progress.setValue(0)

    # ---- 分析回调方法（在主线程中更新UI） ----
    
    def _on_analysis_progress(self, dialog, pct, msg):
        """更新分析进度"""
        self.reading_progress.setValue(pct)
        self.analysis_progress.setValue(pct)
        self.analyzing_label.setText(f"正在分析文本: {msg}")

    def _on_stats_ready(self, content, stats):
        """基本统计完成，更新图表"""
        self.stats_info.setHtml(
            "<h3>详细统计信息:</h3>"
            "<ul>"
            f"<li>总字符数: {stats['total_chars']}</li>"
            f"<li>中文字符: {stats['chinese_chars']}</li>"
            f"<li>英文单词: {stats['english_words']}</li>"
            f"<li>数字数量: {stats['numbers']}</li>"
            f"<li>标点符号: {stats['punctuation']}</li>"
            f"<li>空格数量: {stats['spaces']}</li>"
            f"<li>换行数量: {stats['newlines']}</li>"
            "</ul>"
        )
        
        # 更新图表
        from PySide6.QtCharts import QChart, QPieSeries
        chart = QChart()
        chart.setTitle("文本统计")
        chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        
        series = QPieSeries()
        others = stats['total_chars'] - stats['chinese_chars'] - stats['english_words'] - stats['numbers'] - stats['punctuation'] - stats['spaces']
        series.append("中文字符", stats['chinese_chars'])
        series.append("英文单词", stats['english_words'])
        series.append("数字", stats['numbers'])
        series.append("标点符号", stats['punctuation'])
        series.append("空格", stats['spaces'])
        series.append("其他字符", max(0, others))
        
        for s in series.slices():
            s.setLabelVisible(True)
            s.setLabel(f"{s.label()} ({s.value()})")
        
        chart.addSeries(series)
        chart.legend().setVisible(True)
        chart.legend().setAlignment(Qt.AlignmentFlag.AlignBottom)
        
        self.stats_chart_view.setChart(chart)
        self.stats_chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)

    def _on_keywords_ready(self, keywords):
        """关键词提取完成"""
        self.keywords_label.setText(f"关键词: {', '.join(keywords)}")
        # 更新关键词云卡片
        if hasattr(self, 'keywords_card_label') and keywords:
            html = "<div style='line-height:1.8;'>"
            for i, word in enumerate(keywords[:10]):
                size = 12 + i * 2
                color = f"hsl({i*36}, 70%, 50%)"
                html += f"<span style='font-size:{size}px; color:{color}; margin:0 3px;'>{word}</span>"
            html += "</div>"
            self.keywords_card_label.setText(html)

    def _on_similar_ready(self, similar_texts):
        """相似文本查找完成"""
        self.similar_texts_list.clear()
        self.similarity_table.setRowCount(0)
        self._similar_texts_data = {}
        
        display_count = len(similar_texts) if self.SIMILAR_TEXT_DISPLAY_COUNT == 0 else min(self.SIMILAR_TEXT_DISPLAY_COUNT, len(similar_texts))
        
        for i, (text_id, title, category, similarity, features) in enumerate(similar_texts[:display_count]):
            item = QListWidgetItem()
            widget = QWidget()
            h_layout = QHBoxLayout()
            
            sim_bar = QProgressBar()
            sim_bar.setValue(int(similarity * 100))
            sim_bar.setFormat(f"{similarity:.1%}")
            sim_bar.setStyleSheet("QProgressBar { text-align: center; min-width: 80px; }")
            
            label = QLabel(f"{i+1}. {title} [{category}]")
            label.setStyleSheet("font-weight: bold;")
            
            h_layout.addWidget(sim_bar)
            h_layout.addWidget(label)
            h_layout.addStretch()
            widget.setLayout(h_layout)
            
            item.setSizeHint(widget.sizeHint())
            item.setData(Qt.ItemDataRole.UserRole, text_id)
            self.similar_texts_list.addItem(item)
            self.similar_texts_list.setItemWidget(item, widget)
            self._similar_texts_data[text_id] = features

    def _on_feature_weights_ready(self, features):
        """特征权重完成"""
        self.show_feature_weights(features)

    def _on_readability_ready(self, readability):
        """可读性分析完成"""
        self.readability_score.setText(
            f"可读性评分: {readability['score']:.1f}/100 ({readability['level']})\n"
            f"英文部分: {readability['flesch_score']:.1f} 中文部分: {readability['chinese_score']:.1f}"
        )
        self.readability_bar.setValue(int(readability['score']))
        self.paragraph_stats.setText(f"段落统计: {readability['paragraph_count']}段")

    def _on_sentiment_ready(self, sentiment):
        """情感分析完成"""
        self.sentiment_label.setText(
            f"情感倾向: {sentiment['sentiment']}-{sentiment['intensity']}\n"
            f"正面强度: {sentiment['positive_score']:.1f} 负面强度: {sentiment['negative_score']:.1f}\n"
            f"关键情感词: {sentiment['word_details']}"
        )
        # 情感可视化
        total = sentiment['positive_score'] + sentiment['negative_score'] or 1
        pos_pct = int(sentiment['positive_score'] / total * 100)
        neg_pct = int(sentiment['negative_score'] / total * 100)
        sentiment_html = (
            f"<div style='background:linear-gradient(to right, "
            f"#ff4444 0%, #ff9999 {neg_pct}%, "
            f"#ffffff {neg_pct}%, #ffffff {pos_pct}%, "
            f"#99ff99 {pos_pct}%, #44ff44 100%); "
            f"height:20px; border-radius:3px;'></div>"
        )
        self.sentiment_graph.setText(sentiment_html)

    def _on_features_ready(self, features):
        """文本特征分析完成"""
        # 更新风格标签
        avg_sent_len = features.get('avg_sentence_length', 0)
        lexical_div = features.get('lexical_diversity', 0)
        if avg_sent_len < 10:
            style_desc = "简洁风格 - 短句为主，表达直接"
        elif avg_sent_len < 20:
            style_desc = "中等风格 - 句式均衡，表达流畅"
        else:
            style_desc = "复杂风格 - 长句较多，表达详细"
        if lexical_div > 0.7:
            style_desc += "，词汇丰富"
        self.style_label.setText(style_desc)
        
        # 更新特征表格
        self.features_table.setRowCount(len(features))
        for i, (name, value) in enumerate(features.items()):
            if name == 'keywords':
                continue
            self.features_table.setItem(i, 0, QTableWidgetItem(name))
            if isinstance(value, float):
                self.features_table.setItem(i, 1, QTableWidgetItem(f"{value:.2f}"))
            else:
                self.features_table.setItem(i, 1, QTableWidgetItem(str(value)))
            desc = ""
            if name == 'lexical_diversity':
                desc = "词汇多样性(0-1)，越高词汇越丰富"
            elif name == 'avg_sentence_length':
                desc = "平均句长(词数)"
            elif name == 'chinese_ratio':
                desc = "中文占比"
            elif name == 'english_ratio':
                desc = "英文占比"
            self.features_table.setItem(i, 2, QTableWidgetItem(desc))

    def _on_analysis_finished(self, dialog):
        """分析完成"""
        self.analyzing_label.setText("✅ 分析完成!")
        self.analyzing_label.setStyleSheet("font-size: 14px; color: #10b981;")
        self.analysis_progress.setValue(100)

    def _on_analysis_error(self, dialog, err_msg):
        """分析出错"""
        self.analyzing_label.setText(f"❌ 分析失败: {err_msg}")
        self.analyzing_label.setStyleSheet("font-size: 14px; color: #ef4444;")
        QMessageBox.critical(dialog, "错误", f"分析失败: {err_msg}")


    def analyze_text(self, dialog, content):
        """执行文本分析"""
    
        # 初始化进度条
        self.reading_progress.setValue(5)
        QApplication.processEvents()  # 强制更新UI
    
        try:
            # 1. 初始化统计信息文本框
            self.stats_info.clear()  # 先清空内容
            self.reading_progress.setValue(10)
            QApplication.processEvents()

            # 2. 基本统计
            self.update_basic_stats(content)
            self.reading_progress.setValue(20)
            QApplication.processEvents()
            
            # 3. 关键词提取
            keywords = self.extract_keywords(content)
            self.keywords_label.setText(f"关键词: {', '.join(keywords)}")
            self.reading_progress.setValue(35)
            QApplication.processEvents()
            
            # 4. 查找相似文本
            self.find_similar_texts(content)
            self.reading_progress.setValue(50)
            QApplication.processEvents()
            
            # 5. 新增段落统计
            paragraph_count = len([p for p in content.split('\n') if p.strip()])
            self.paragraph_stats.setText(f"段落统计: {paragraph_count}段")
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
        from PySide6.QtCharts import QChart, QPieSeries
        chart = QChart()
        chart.setTitle("文本统计")
        chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        
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
        chart.legend().setAlignment(Qt.AlignmentFlag.AlignBottom)
        
        self.stats_chart_view.setChart(chart)
        self.stats_chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)


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
            item.setData(Qt.ItemDataRole.UserRole, (text_id, features))
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
        """显示相似文本详情（从后台线程分析结果中获取）"""
        text_id = item.data(Qt.ItemDataRole.UserRole)
        
        # 从缓存的特征数据中获取
        features = self._similar_texts_data.get(text_id, {})
        
        # 获取文本信息
        self.cursor.execute("SELECT title, content FROM texts WHERE id=?", (text_id,))
        result = self.cursor.fetchone()
        if not result:
            return
        title, content = result
        
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
        try:
            # 调试信息 - 开始创建编辑选项卡
            
            # 检查主布局是否存在
            if not hasattr(self, 'right_panel'):
                print("[ERROR] right_panel 未初始化")
                raise AttributeError("right_panel 未初始化")
            
            # 创建编辑选项卡
            self.edit_tab = QWidget()
            self.edit_layout = QVBoxLayout()
            self.edit_tab.setLayout(self.edit_layout)
        
            # 调试信息 - 基本框架创建完成
            
            # 标题输入框（带聚焦效果）
            self.title_input = QLineEdit()
            if not self.title_input:
                print("[ERROR] 无法创建 title_input")
                raise RuntimeError("无法创建标题输入框")
                
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
            # print("[DEBUG] 标题输入框创建并添加完成")
            
            # 分类选择框
            self.category_combo = QComboBox()
            self.category_combo.addItem('未分类', 0)
            self.edit_layout.addWidget(self.category_combo)
            # print("[DEBUG] 分类选择框创建并添加完成")
            
            # 标签输入框
            self.tag_edit = QLineEdit()
            self.tag_edit.setPlaceholderText('输入标签，用逗号分隔')
            self.edit_layout.addWidget(self.tag_edit)
            # print("[DEBUG] 标签输入框创建并添加完成")
            
            # 格式选择
            self.format_combo = QComboBox()
            self.format_combo.addItem('纯文本')
            self.format_combo.addItem('Markdown')
            self.format_combo.addItem('即见即所得')
            self.format_combo.setCurrentIndex(self.default_format)
            self.format_combo.currentIndexChanged.connect(self.toggle_edit_mode)
            self.edit_layout.addWidget(self.format_combo)
            # print(f"[DEBUG] 格式选择框创建并添加完成，默认索引: {self.default_format}")
            
            # 文本编辑区（默认不接受富文本，纯文本模式粘贴时丢弃格式）
            self.content_input = QTextEdit()
            if not self.content_input:
                print("[ERROR] 无法创建 content_input")
                raise RuntimeError("无法创建内容编辑器")
                
            self.content_input.setAcceptRichText(False)  # 默认纯文本模式，粘贴时不带格式
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
            if not self.btn_new:
                print("[ERROR] 无法创建 btn_new")
                raise RuntimeError("无法创建新建按钮")
                
            self.btn_new.setProperty("class", "new-action")
            self.btn_new.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_layout.addWidget(self.btn_new)
            
            # 添加按钮调试信息
            
            # 修改连接方式，确保连接成功
            def safe_new_text():
                try:
                    self.new_text()
                except Exception as e:
                    print(f"[ERROR] 调用new_text失败: {str(e)}")
                    QMessageBox.critical(self, "错误", f"新建文本失败: {str(e)}")
            
            self.btn_new.clicked.connect(safe_new_text)
            
            # 保存按钮（安全绿）
            self.btn_save = QPushButton(QIcon.fromTheme('document-save'), '保存')
            self.btn_save.setProperty("class", "save-action")
            self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_save.clicked.connect(self.save_text)
            btn_layout.addWidget(self.btn_save)
            
            # 删除按钮（警示红）
            self.btn_delete = QPushButton(QIcon.fromTheme('edit-delete'), '删除')
            self.btn_delete.setProperty("class", "danger-action")
            self.btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_delete.clicked.connect(self.delete_text)
            btn_layout.addWidget(self.btn_delete)
            
            # 恢复按钮（中性灰）
            self.btn_restore = QPushButton('从回收站恢复')
            self.btn_restore.setProperty("class", "secondary-action")
            self.btn_restore.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_restore.clicked.connect(self.restore_from_recycle_bin)
            self.btn_restore.setVisible(False)
            btn_layout.addWidget(self.btn_restore)
            
            # 文本分析按钮（智慧紫）
            self.stats_btn = QPushButton(QIcon.fromTheme('office-chart-bar'), '文本分析')
            self.stats_btn.setProperty("class", "analyze-action")
            self.stats_btn.setCursor(Qt.CursorShape.PointingHandCursor)
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
            self.copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.copy_btn.setMenu(self.copy_menu)
            btn_layout.addWidget(self.copy_btn)
            
            self.edit_layout.addLayout(btn_layout)
            self.right_panel.addTab(self.edit_tab, "编辑")
            # print("[DEBUG] 编辑选项卡添加完成")

            # 然后创建预览标签
            self.create_preview_tab()
            
            # 连接文本光标变化信号
            self.content_input.cursorPositionChanged.connect(self.update_reading_progress)
            self.wysiwyg_editor.cursorPositionChanged.connect(self.update_reading_progress)
            # print("[DEBUG] 光标变化信号连接完成")
            
            # print("[DEBUG] === 编辑选项卡创建完成 ===")
            
        except Exception as e:
            print(f"[CRITICAL] 创建编辑选项卡时发生错误: {str(e)}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "严重错误", f"无法创建编辑界面: {str(e)}")
            raise  # 重新抛出异常，让上层处理



    def create_preview_tab(self):
        """创建Markdown预览选项卡"""
        # 添加预览内容存储变量
        self.preview_html_content = ""
        self.preview_plain_content = ""
        self.preview_tab = QWidget()
        self.preview_layout = QVBoxLayout()
        self.preview_tab.setLayout(self.preview_layout)

        # 添加复制按钮区域
        copy_btn_layout = QHBoxLayout()

        # 复制纯文本按钮 - 复制预览内容的纯TEXT文本版本
        self.btn_copy_plain = QPushButton("复制纯文本内容") 
        self.btn_copy_plain.setProperty("class", "data-action") 
        self.btn_copy_plain.clicked.connect(self.copy_preview_plain_text)
        self.btn_copy_plain.setToolTip("复制预览内容的纯文本版本（无格式）")
        copy_btn_layout.addWidget(self.btn_copy_plain)

        # 复制HTML内容按钮
        #self.btn_copy_html = QPushButton("复制HTML文本") 
        #self.btn_copy_html.setProperty("class", "data-action") 
        #self.btn_copy_html.clicked.connect(self.copy_preview_content)
        #self.btn_copy_html.setToolTip("复制预览内容（保留格式）")
        #copy_btn_layout.addWidget(self.btn_copy_html)

        self.preview_layout.addLayout(copy_btn_layout)
        
        # 使用QTextBrowser代替原来的QLabel
        self.preview_browser = QTextBrowser()
        self.preview_browser.setOpenExternalLinks(True)
        self.preview_browser.setStyleSheet("""
            QTextBrowser {
                background-color: white;
                border: none;
                padding: 5px;
                margin: 0px;
            }
        """)
        
        scroll = QScrollArea()
        scroll.setWidget(self.preview_browser)
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
        dialog.setStyleSheet('')  # 使用默认风格
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
        dialog.exec()

    def select_export_directory(self):
        """选择导出目录"""
        dir_path = QFileDialog.getExistingDirectory(self, "选择导出目录")
        if dir_path:
            self.export_dir_label.setText(dir_path)

    def batch_export(self, dialog):
        """批量导出选中文本（使用后台线程，避免UI卡顿）"""
        selected_items = self.text_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "请先选择要导出的文本!")
            return
            
        export_dir = self.export_dir_label.text()
        if not export_dir or export_dir == "未选择目录":
            QMessageBox.warning(self, "警告", "请先选择导出目录!")
            return
            
        export_format = self.export_format_combo.currentText()
        text_ids = [item.data(Qt.ItemDataRole.UserRole) for item in selected_items]
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'text_manager_enhanced.db')
        
        # 禁用对话框按钮防止重复操作
        dialog.setEnabled(False)
        self.show_status_message("正在后台导出...", 0)
        
        self.export_worker = BatchExportWorker(text_ids, export_dir, export_format, db_path, self.current_view)
        self.export_worker.progress.connect(
            lambda pct, msg: self.show_status_message(f"导出进度: {pct}% - {msg}", 0)
        )
        self.export_worker.finished.connect(
            lambda count, d: self._on_batch_export_finished(dialog, count, d)
        )
        self.export_worker.error.connect(
            lambda err: self._on_batch_export_error(dialog, err)
        )
        self.export_worker.start()

    def _on_batch_export_finished(self, dialog, count, export_dir):
        """批量导出完成"""
        dialog.setEnabled(True)
        dialog.close()
        QMessageBox.information(self, "完成", f"已成功导出{count}个文件到:\n{export_dir}")
        self.show_status_message(f"导出完成: {count}个文件", 3000)

    def _on_batch_export_error(self, dialog, err_msg):
        """批量导出出错"""
        dialog.setEnabled(True)
        QMessageBox.critical(self, "错误", f"导出失败: {err_msg}")

    def batch_update_category(self, dialog):
        """批量更新分类（使用后台线程）"""
        selected_items = self.text_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "请先选择要操作的文本!")
            return
            
        category_id = self.batch_category_combo.currentData()
        text_ids = [item.data(Qt.ItemDataRole.UserRole) for item in selected_items]
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'text_manager_enhanced.db')
        
        dialog.setEnabled(False)
        self.show_status_message("正在后台更新分类...", 0)
        
        self.batch_worker = BatchOperationWorker(db_path, text_ids, 'update_category', category_id=category_id)
        self.batch_worker.finished.connect(
            lambda count, op_type: self._on_batch_operation_finished(dialog, count)
        )
        self.batch_worker.error.connect(
            lambda err: self._on_batch_operation_error(dialog, err)
        )
        self.batch_worker.start()

    def batch_add_tags(self, dialog):
        """批量添加标签（使用后台线程）"""
        selected_items = self.text_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "请先选择要操作的文本!")
            return
            
        new_tags = [tag.strip() for tag in self.batch_tag_input.text().split(",") if tag.strip()]
        if not new_tags:
            QMessageBox.warning(self, "警告", "请输入有效的标签!")
            return
            
        text_ids = [item.data(Qt.ItemDataRole.UserRole) for item in selected_items]
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'text_manager_enhanced.db')
        
        dialog.setEnabled(False)
        self.show_status_message("正在后台添加标签...", 0)
        
        self.batch_worker = BatchOperationWorker(db_path, text_ids, 'add_tags', new_tags=new_tags)
        self.batch_worker.finished.connect(
            lambda count, op_type: self._on_batch_tags_finished(dialog, count)
        )
        self.batch_worker.error.connect(
            lambda err: self._on_batch_operation_error(dialog, err)
        )
        self.batch_worker.start()

    def _on_batch_operation_finished(self, dialog, count):
        """批量操作完成（分类/标签）"""
        dialog.setEnabled(True)
        self.conn.commit()
        self.load_text_list()
        dialog.close()
        self.show_status_message(f"已批量更新{count}个文本的分类", 3000)

    def _on_batch_tags_finished(self, dialog, count):
        """批量添加标签完成"""
        dialog.setEnabled(True)
        self.conn.commit()
        self.load_text_list()
        self.load_tags()
        dialog.close()
        self.show_status_message(f"已批量添加标签到{count}个文本", 3000)

    def _on_batch_operation_error(self, dialog, err_msg):
        """批量操作出错"""
        dialog.setEnabled(True)
        QMessageBox.critical(self, "错误", f"批量操作失败: {err_msg}")

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
            self.search_history_combo.setItemData(index, bg_color, Qt.ItemDataRole.BackgroundRole)
            self.search_history_combo.setItemData(index, text_color, Qt.ItemDataRole.ForegroundRole)



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
        
        query += ' ' + self.get_sort_clause()
        
        self.cursor.execute(query, params)
        texts = self.cursor.fetchall()
        
        self.text_list.clear()
        for text_id, title, category_name in texts:
            item = QListWidgetItem(f"{title} [{category_name or '未分类'}] (ID: {text_id})")
            item.setData(Qt.ItemDataRole.UserRole, text_id)
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
        
        query += ' ' + self.get_sort_clause()
        
        self.cursor.execute(query, params)
        texts = self.cursor.fetchall()
        
        self.text_list.clear()
        for text_id, title, category_name, create_time, update_time, word_count in texts:
            item_text = f"{title} [{category_name or '未分类'}] (ID: {text_id})\n"
            item_text += f"字数: {word_count} | 创建: {create_time} | 更新: {update_time}"
            
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, text_id)
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
            item.setData(Qt.ItemDataRole.UserRole, item_id)
            
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
            
        item_id = selected_items[0].data(Qt.ItemDataRole.UserRole)
        
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

            # 保存成功后创建自动备份
            self.create_backup("auto")
            self.cleanup_old_backups()

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
        text_id = item.data(Qt.ItemDataRole.UserRole)
        
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
            
            # 纯文本模式：粘贴时丢弃所有格式
            self.content_input.setAcceptRichText(False)
            
            # 更新预览
            self.update_preview()
            
        elif mode == 1:  # 切换到Markdown
            # 从当前活动编辑器获取内容
            if self.wysiwyg_editor.isVisible():
                current_content = self.wysiwyg_editor.toPlainText()
            else:
                current_content = self.content_input.toPlainText()
                
            self.content_input.setPlainText(current_content)
            self.wysiwyg_editor.setPlainText(current_content)
            
            # Markdown模式：粘贴时丢弃所有格式
            self.content_input.setAcceptRichText(False)
            self.update_preview()
            
        else:  # 切换到即见即所得
            # 获取当前内容
            if self.content_input.isVisible():
                current_content = self.content_input.toPlainText()
            else:
                current_content = self.wysiwyg_editor.toPlainText()
            
            # 将纯文本转换为HTML，保留换行等基本格式
            current_content = current_content.replace('\n', '<br>')
            current_content = self.clean_html(current_content)
            self.wysiwyg_editor.setHtml(current_content)
            
            # 即见即所得模式：允许富文本粘贴
            self.wysiwyg_editor.setAcceptRichText(True)
            
            # 更新预览
            self.update_preview()
        
        # 切换可见性
        self.content_input.setVisible(mode != 2)
        self.wysiwyg_editor.setVisible(mode == 2)
        self.right_panel.setTabVisible(1, True)  # 始终显示预览标签页



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
        """更新预览内容（支持所有格式）"""
        # 获取当前内容
        format_index = self.format_combo.currentIndex()
        current_content = self.get_current_content(as_plain_text=(format_index != 2))
        
        # 根据当前格式转换内容
        if format_index == 0:  # 纯文本模式
            html_content = ProjectInfo.plain_to_html(current_content)
            plain_content = current_content
        elif format_index == 1:  # Markdown模式
            html_content = ProjectInfo.markdown_to_html(current_content)
            plain_content = current_content
        else:  # HTML模式
            html_content = self.clean_html(current_content)
            plain_content = ProjectInfo.html_to_plain(current_content)
        
        # 更新预览显示 - 使用更严格的HTML处理
        # 添加基本样式以确保一致的显示
        styled_html = f"""
        <html>
        <head>
        <style>
            body {{
                margin: 0;
                padding: 5px;
                font-family: Arial, sans-serif;
                font-size: 14px;
                line-height: 1.5;
            }}
            p, h1, h2, h3, h4, h5, h6 {{
                margin-top: 0;
                margin-bottom: 0.5em;
            }}
            pre, code {{
                background-color: #f5f5f5;
                padding: 2px 4px;
                border-radius: 3px;
            }}
        </style>
        </head>
        <body>
        {html_content}
        </body>
        </html>
        """
        
        self.preview_browser.setHtml(styled_html)
        self.preview_html_content = styled_html
        self.preview_plain_content = plain_content





    def load_categories(self):
        """加载分类数据（使用与文件列表相同的配色方案）"""
        self.category_tree.clear()
        self.cursor.execute("SELECT id, name, parent_id FROM categories ORDER BY parent_id, name")
        categories = self.cursor.fetchall()
        
        # 构建树形结构
        categories_dict = {}
        for cat_id, name, parent_id in categories:
            item = QTreeWidgetItem([name])
            item.setData(0, Qt.ItemDataRole.UserRole, cat_id)
            
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
            self.category_combo.setItemData(index, bg_color, Qt.ItemDataRole.BackgroundRole)
            self.category_combo.setItemData(index, text_color, Qt.ItemDataRole.ForegroundRole)






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
            self.tag_cloud.setItemData(index, bg_color, Qt.ItemDataRole.BackgroundRole)
            self.tag_cloud.setItemData(index, text_color, Qt.ItemDataRole.ForegroundRole)




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
        
        query += ' ' + self.get_sort_clause()
        
        self.cursor.execute(query, params)
        texts = self.cursor.fetchall()
        
        self.text_list.clear()
        for text_id, title, category_name, category_id in texts:
            item = QListWidgetItem(f"{title} [{category_name or '未分类'}] (ID: {text_id})")
            item.setData(Qt.ItemDataRole.UserRole, text_id)
            
            # 生成颜色（基于分类ID，如果没有分类则使用文本ID）
            color_id = category_id if category_id else text_id
            bg_color, text_color = self.generate_harmonious_color(color_id, saturation=0.4, value=0.92)
            
            item.setBackground(bg_color)
            item.setForeground(text_color)
            
            self.text_list.addItem(item)

    def filter_by_category(self, item):
        """按分类筛选文本 - 修改为显示选中分类+未分类的内容"""
        category_id = item.data(0, Qt.ItemDataRole.UserRole)
        
        # 获取所有未分类的文本
        query = '''
        SELECT t.id, t.title, c.name 
        FROM texts t
        LEFT JOIN categories c ON t.category_id = c.id
        WHERE t.category_id = 0 OR t.category_id = ?
        '''
        query += ' ' + self.get_sort_clause()
        
        self.cursor.execute(query, (category_id,))
        texts = self.cursor.fetchall()
        
        self.text_list.clear()
        for text_id, title, category_name in texts:
            item = QListWidgetItem(f"{title} [{category_name or '未分类'}] (ID: {text_id})")
            item.setData(Qt.ItemDataRole.UserRole, text_id)
            self.text_list.addItem(item)


    def filter_by_tag(self, tag_name):
        """按标签筛选文本"""
        if tag_name:
            self.load_text_list(tag_name=tag_name)

    def get_pinyin_query(self, text):
        """将中文转换为拼音首字母查询字符串"""
        from pypinyin import lazy_pinyin
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

        # 调试标题输入框
        self.title_input.clear()

        # 调试内容编辑器
        self.content_input.setPlainText("")

        # 调试富文本编辑器
        self.wysiwyg_editor.setHtml("")
        self.wysiwyg_editor.document().clear()

        # 调试标签和分类
        self.tag_edit.clear()
        
        self.category_combo.setCurrentIndex(0)

        # 调试格式选择
        self.format_combo.setCurrentIndex(self.default_format)

        # 调试编辑器切换
        self.toggle_edit_mode()

        # 调试焦点设置
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
        dialog.setStyleSheet('')  # 使用默认风格
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
        dialog.exec()

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
            item.setData(Qt.ItemDataRole.UserRole, tag_id)
            self.tag_list.addItem(item)

    def set_tag_color(self):
        """设置标签颜色"""
        item = self.tag_list.currentItem()
        if not item:
            QMessageBox.warning(self, "警告", "请先选择标签!")
            return
        
        tag_id = item.data(Qt.ItemDataRole.UserRole)
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
        """优化数据库（使用后台线程，避免UI卡顿）"""
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'text_manager_enhanced.db')
        self.show_status_message("正在后台优化数据库...", 0)
        
        self.optimize_worker = DatabaseOptimizeWorker(db_path)
        self.optimize_worker.finished.connect(
            lambda elapsed: self.show_status_message(f"数据库优化完成, 耗时{elapsed:.2f}秒", 5000)
        )
        self.optimize_worker.error.connect(
            lambda err: QMessageBox.critical(self, "错误", f"优化失败: {err}")
        )
        self.optimize_worker.start()

    def configure_shortcuts(self):
        """配置快捷键对话框"""
        dialog = QDialog(self)
        dialog.setWindowTitle("快捷键设置")
        dialog.setStyleSheet('')  # 使用默认风格
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
        dialog.exec()

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
                    import markdown
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
        dialog.setStyleSheet('')  # 使用默认风格
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
        dialog.exec()
        
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
            item.setData(0, Qt.ItemDataRole.UserRole, cat_id)
            item.setData(1, Qt.ItemDataRole.UserRole, color)
            
            # 设置颜色显示
            if color and color != '#FFFFFF':
                item.setBackground(1, QColor(color))
            else:
                # 显示自动生成的颜色
                auto_color = self.generate_category_color(cat_id)
                item.setBackground(1, QColor(auto_color))
                item.setText(1, auto_color.name())
            
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
                parent_id = parent_item.data(0, Qt.ItemDataRole.UserRole)
            
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
        cat_id = item.data(0, Qt.ItemDataRole.UserRole)
        
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
            
        cat_id = item.data(0, Qt.ItemDataRole.UserRole)
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
            
        cat_id = item.data(0, Qt.ItemDataRole.UserRole)
        current_color = item.data(1, Qt.ItemDataRole.UserRole) or '#FFFFFF'
        
        color = QColorDialog.getColor(QColor(current_color), self, "选择分类颜色")
        if color.isValid():
            hex_color = color.name()
            
            try:
                self.cursor.execute(
                    "UPDATE categories SET color = ? WHERE id = ?",
                    (hex_color, cat_id)
                )
                self.conn.commit()
                
                item.setData(1, Qt.ItemDataRole.UserRole, hex_color)
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
        
        cat_id = item.data(0, Qt.ItemDataRole.UserRole)
        parent_item = item.parent()
        parent_id = parent_item.data(0, Qt.ItemDataRole.UserRole) if parent_item else 0
        
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

        backup_action = QAction('数据库备份', self)
        backup_action.triggered.connect(self.show_backup_manager)
        file_menu.addAction(backup_action)

        file_menu.addSeparator()
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

        tools_menu.addSeparator()

        settings_action = QAction('设置', self)
        settings_action.triggered.connect(self.show_settings_dialog)
        tools_menu.addAction(settings_action)

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
        self.align_left.toggled.connect(lambda: self.set_alignment(Qt.AlignmentFlag.AlignLeft))
        self.align_center.toggled.connect(lambda: self.set_alignment(Qt.AlignmentFlag.AlignCenter))
        self.align_right.toggled.connect(lambda: self.set_alignment(Qt.AlignmentFlag.AlignRight))
        
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
        self.wysiwyg_editor.setFontWeight(QFont.Weight.Bold if checked else QFont.Weight.Normal)

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

    def generate_harmonious_color(self, item_id, saturation=0.4, value=0.92):
        """使用马卡龙色系生成颜色"""
        # 使用ID选择马卡龙色系中的颜色
        color_index = item_id % len(self.MACARON_COLORS)
        bg_color = self.MACARON_COLORS[color_index]
        
        # 计算颜色的亮度 (YIQ公式)
        brightness = (0.299 * bg_color.redF() + 
                    0.587 * bg_color.greenF() + 
                    0.114 * bg_color.blueF())
        
        # 自动对比度文字颜色
        text_color = QColor(Qt.black) if brightness > 0.6 else QColor(Qt.white)
        
        return (bg_color, text_color)


    def perform_auto_backup(self):
        """执行智能备份（使用后台线程）"""
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'text_manager_enhanced.db')
        
        self.backup_worker = BackupWorker(
            db_path,
            self.backup_config['backup_dir'],
            self.backup_config['backup_prefix'],
            self.backup_config['max_backups']
        )
        self.backup_worker.finished.connect(
            lambda backup_file: self.show_status_message(f"数据库备份完成: {backup_file}", 3000)
        )
        self.backup_worker.error.connect(
            lambda err: print(f"备份失败: {err}")
        )
        self.backup_worker.start()
        return True

    def clear_search(self):
        """清除搜索条件"""
        self.search_input.clear()
        self.advanced_search_group.setChecked(False)
        self.load_text_list()

    # ==================== 设置功能 ====================

    def get_settings_path(self):
        """获取设置文件路径（保存在程序当前目录下的 settings 子目录）"""
        settings_dir = os.path.join(os.path.dirname(__file__), 'settings')
        os.makedirs(settings_dir, exist_ok=True)
        return os.path.join(settings_dir, 'app_settings.json')

    def load_settings(self) -> dict:
        """从JSON文件加载设置，如果文件不存在则返回默认设置"""
        default_settings = {
            'auto_save_interval': 30,  # 默认30秒
            'sort_mode': 'update_time_desc',  # 默认按日期排序（最新在前）
            'theme': 'macaron',  # 默认马卡龙色系
            'window_geometry': '',  # 窗口几何（base64，closeEvent 保存）
            'window_maximized': False,  # 窗口是否最大化（closeEvent 保存）
        }
        try:
            settings_path = self.get_settings_path()
            if os.path.exists(settings_path):
                with open(settings_path, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    # 合并默认设置，确保所有键都存在
                    default_settings.update(loaded)
        except Exception as e:
            print(f"[设置] 加载设置失败，使用默认设置: {e}")
        return default_settings

    def save_settings(self, settings: dict = None):
        """保存设置到JSON文件（原子写入：先写 tmp 再 os.replace，避免写坏导致设置丢失）"""
        if settings is None:
            settings = self.settings
        try:
            settings_path = self.get_settings_path()
            tmp_path = settings_path + '.tmp'
            with open(tmp_path, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, settings_path)  # 原子替换，保证设置不丢失
            return True
        except Exception as e:
            print(f"[设置] 保存设置失败: {e}")
            return False

    def _restore_window_geometry(self):
        """恢复窗口几何与最大化状态（设置实时自动保存约定，v8.2.0）"""
        geom = self.settings.get('window_geometry', '')
        if geom:
            try:
                from PySide6.QtCore import QByteArray
                self.restoreGeometry(QByteArray.fromBase64(geom.encode('utf-8')))
            except Exception:
                pass
        # 记录启动是否最大化，由 __main__ 决定 show/showMaximized
        self._start_maximized = bool(self.settings.get('window_maximized', False))

    # ==================== 主题/风格系统 ====================

    # 主题信息映射
    THEME_INFO = {
        'default':              '默认风格',
        'macaron':              '马卡龙色系',
        'morandi':              '莫兰迪色系',
        'chinese_traditional':  '中国传统色系',
        'dark':                 '暗夜模式',
        'ocean':                '海洋色系',
        'forest':               '森林色系',
        'sunset':               '日落色系',
        'lavender':             '薰衣草色系',
        'minimal':              '极简灰白',
        'sakura':               '樱花色系',
        'mint':                 '薄荷色系',
        'coffee':               '咖啡色系',
        'lemon':                '柠檬色系',
        'grape':                '葡萄色系',
        'sky':                  '天空色系',
        'rose':                 '玫瑰色系',
        'aurora':               '极光色系',
        'caramel':              '焦糖色系',
        'glacier':              '冰川色系',
        'midnight':             '午夜色系',
        'autumn':               '秋叶色系',
        'candy':                '糖果色系',
        'denim':                '牛仔色系',
    }

    def apply_theme(self):
        """根据当前设置应用界面主题"""
        theme = self.settings.get('theme', 'macaron')
        stylesheet = self._get_theme_stylesheet(theme)
        self.setStyleSheet(stylesheet)

    def _get_theme_stylesheet(self, theme: str) -> str:
        """返回指定主题的 QSS 样式表"""
        if theme == 'default':
            return ''

        # 主题色板定义
        themes = {
            'macaron': {
                'bg_main':        '#f8fafc',
                'btn_new':        '#8b5cf6',  # 薰衣草紫
                'btn_save':       '#10b981',  # 薄荷绿
                'btn_danger':     '#ef4444',  # 浅玫瑰
                'btn_analyze':    '#7c3aed',  # 深薰衣草
                'btn_data':       '#f97316',  # 杏色
                'btn_secondary':  '#94a3b8',
                'btn_view':       '#a78bfa',
                'btn_batch':      '#5eead4',
                'progress_chunk': '#3b82f6',
            },
            'morandi': {
                'bg_main':        '#ede7e2',
                'btn_new':        '#9b8ea6',  # 灰紫
                'btn_save':       '#8a9a7b',  # 灰绿
                'btn_danger':     '#c4a0a0',  # 灰粉
                'btn_analyze':    '#7b8fa1',  # 灰蓝
                'btn_data':       '#c4a882',  # 灰橙
                'btn_secondary':  '#a0998b',
                'btn_view':       '#8e8ca0',
                'btn_batch':      '#8aaa9e',
                'progress_chunk': '#7b8fa1',
            },
            'chinese_traditional': {
                'bg_main':        '#f5efe6',  # 宣纸白
                'btn_new':        '#7b5ea7',  # 藕荷
                'btn_save':       '#5b8c5a',  # 竹青
                'btn_danger':     '#c04851',  # 胭脂
                'btn_analyze':    '#4a6b8a',  # 黛蓝
                'btn_data':       '#b8860b',  # 赭石
                'btn_secondary':  '#8c7b6b',
                'btn_view':       '#6b5b8a',
                'btn_batch':      '#5a8a7a',
                'progress_chunk': '#4a6b8a',
            },
            'dark': {
                'bg_main':        '#1e1e2e',
                'btn_new':        '#c084fc',  # 亮紫
                'btn_save':       '#4ade80',  # 亮绿
                'btn_danger':     '#f87171',  # 亮红
                'btn_analyze':    '#818cf8',  # 亮靛
                'btn_data':       '#fb923c',  # 亮橙
                'btn_secondary':  '#64748b',
                'btn_view':       '#a78bfa',
                'btn_batch':      '#2dd4bf',
                'progress_chunk': '#818cf8',
            },
            'ocean': {
                'bg_main':        '#f0f7fa',
                'btn_new':        '#0284c7',  # 深海蓝
                'btn_save':       '#0891b2',  # 青蓝
                'btn_danger':     '#e11d48',  # 珊瑚红
                'btn_analyze':    '#0369a1',  # 宝蓝
                'btn_data':       '#0d9488',  # 翡翠绿
                'btn_secondary':  '#94a3b8',
                'btn_view':       '#2563eb',
                'btn_batch':      '#06b6d4',
                'progress_chunk': '#0284c7',
            },
            'forest': {
                'bg_main':        '#f2f7f2',
                'btn_new':        '#7c3aed',  # 紫罗兰
                'btn_save':       '#16a34a',  # 翠绿
                'btn_danger':     '#dc2626',  # 枫叶红
                'btn_analyze':    '#4f46e5',  # 靛蓝
                'btn_data':       '#ca8a04',  # 金盏黄
                'btn_secondary':  '#78716c',
                'btn_view':       '#65a30d',
                'btn_batch':      '#059669',
                'progress_chunk': '#16a34a',
            },
            'sunset': {
                'bg_main':        '#fef7f0',
                'btn_new':        '#d946ef',  # 品红
                'btn_save':       '#f97316',  # 暖橙
                'btn_danger':     '#e11d48',  # 玫瑰红
                'btn_analyze':    '#a855f7',  # 紫罗兰
                'btn_data':       '#eab308',  # 金黄
                'btn_secondary':  '#a8a29e',
                'btn_view':       '#f59e0b',
                'btn_batch':      '#ec4899',
                'progress_chunk': '#f97316',
            },
            'lavender': {
                'bg_main':        '#f8f6fc',
                'btn_new':        '#8b5cf6',  # 薰衣草
                'btn_save':       '#a3e635',  # 青柠
                'btn_danger':     '#f43f5e',  # 莓红
                'btn_analyze':    '#6366f1',  # 深紫
                'btn_data':       '#f472b6',  # 粉红
                'btn_secondary':  '#9ca3af',
                'btn_view':       '#c084fc',
                'btn_batch':      '#6ee7b7',
                'progress_chunk': '#8b5cf6',
            },
            'minimal': {
                'bg_main':        '#fafafa',
                'btn_new':        '#374151',  # 深灰
                'btn_save':       '#4b5563',  # 中灰
                'btn_danger':     '#9ca3af',  # 浅灰
                'btn_analyze':    '#1f2937',  # 墨灰
                'btn_data':       '#6b7280',  # 灰蓝
                'btn_secondary':  '#d1d5db',
                'btn_view':       '#374151',
                'btn_batch':      '#6b7280',
                'progress_chunk': '#374151',
            },
            'sakura': {
                'bg_main':        '#fff5f6',
                'btn_new':        '#ec4899',  # 桃红
                'btn_save':       '#f43f5e',  # 玫瑰
                'btn_danger':     '#be123c',  # 深玫红
                'btn_analyze':    '#d946ef',  # 紫粉
                'btn_data':       '#fb7185',  # 浅绯
                'btn_secondary':  '#fda4af',
                'btn_view':       '#f472b6',
                'btn_batch':      '#fb923c',
                'progress_chunk': '#ec4899',
            },
            'mint': {
                'bg_main':        '#f5faf8',
                'btn_new':        '#0d9488',  # 翡翠
                'btn_save':       '#22c55e',  # 嫩绿
                'btn_danger':     '#ef4444',  # 番茄红
                'btn_analyze':    '#2563eb',  # 宝石蓝
                'btn_data':       '#eab308',  # 柠檬黄
                'btn_secondary':  '#a3a3a3',
                'btn_view':       '#14b8a6',
                'btn_batch':      '#10b981',
                'progress_chunk': '#0d9488',
            },
            'coffee': {
                'bg_main':        '#f9f5f0',
                'btn_new':        '#8b5e3c',  # 咖啡棕
                'btn_save':       '#6b8c42',  # 橄榄绿
                'btn_danger':     '#c0392b',  # 砖红
                'btn_analyze':    '#5c4033',  # 深棕
                'btn_data':       '#d4a574',  # 拿铁
                'btn_secondary':  '#a0897c',
                'btn_view':       '#7b5b3a',
                'btn_batch':      '#8f9779',
                'progress_chunk': '#8b5e3c',
            },
            'lemon': {
                'bg_main':        '#fffef5',
                'btn_new':        '#eab308',  # 明黄
                'btn_save':       '#84cc16',  # 青柠
                'btn_danger':     '#f43f5e',  # 莓红
                'btn_analyze':    '#6366f1',  # 靛蓝
                'btn_data':       '#f59e0b',  # 琥珀
                'btn_secondary':  '#d4d4d4',
                'btn_view':       '#22c55e',
                'btn_batch':      '#06b6d4',
                'progress_chunk': '#eab308',
            },
            'grape': {
                'bg_main':        '#faf5fc',
                'btn_new':        '#9333ea',  # 葡萄紫
                'btn_save':       '#16a34a',  # 翠绿
                'btn_danger':     '#dc2626',  # 赤红
                'btn_analyze':    '#7c3aed',  # 深紫
                'btn_data':       '#db2777',  # 玫红
                'btn_secondary':  '#a78bfa',
                'btn_view':       '#8b5cf6',
                'btn_batch':      '#6d28d9',
                'progress_chunk': '#9333ea',
            },
            'sky': {
                'bg_main':        '#f0f9ff',
                'btn_new':        '#0ea5e9',  # 天蓝
                'btn_save':       '#10b981',  # 碧绿
                'btn_danger':     '#f97316',  # 橘红
                'btn_analyze':    '#3b82f6',  # 宝蓝
                'btn_data':       '#06b6d4',  # 青色
                'btn_secondary':  '#94a3b8',
                'btn_view':       '#38bdf8',
                'btn_batch':      '#14b8a6',
                'progress_chunk': '#0ea5e9',
            },
            'rose': {
                'bg_main':        '#fff5f5',
                'btn_new':        '#e11d48',  # 玫瑰
                'btn_save':       '#22c55e',  # 翠绿
                'btn_danger':     '#be123c',  # 深红
                'btn_analyze':    '#a855f7',  # 紫罗兰
                'btn_data':       '#f43f5e',  # 粉红
                'btn_secondary':  '#fda4af',
                'btn_view':       '#fb7185',
                'btn_batch':      '#f97316',
                'progress_chunk': '#e11d48',
            },
            'aurora': {
                'bg_main':        '#f5fdf9',
                'btn_new':        '#0891b2',  # 孔雀蓝
                'btn_save':       '#059669',  # 翡翠绿
                'btn_danger':     '#e11d48',  # 极光红
                'btn_analyze':    '#6366f1',  # 靛蓝
                'btn_data':       '#0d9488',  # 墨绿
                'btn_secondary':  '#a5b4fc',
                'btn_view':       '#2dd4bf',
                'btn_batch':      '#06b6d4',
                'progress_chunk': '#0891b2',
            },
            'caramel': {
                'bg_main':        '#fdf6f0',
                'btn_new':        '#d97706',  # 焦糖
                'btn_save':       '#65a30d',  # 草绿
                'btn_danger':     '#dc2626',  # 朱红
                'btn_analyze':    '#7c3aed',  # 紫罗兰
                'btn_data':       '#b45309',  # 深棕
                'btn_secondary':  '#d6b89e',
                'btn_view':       '#f59e0b',
                'btn_batch':      '#ca8a04',
                'progress_chunk': '#d97706',
            },
            'glacier': {
                'bg_main':        '#f5f9fc',
                'btn_new':        '#64748b',  # 灰蓝
                'btn_save':       '#0ea5e9',  # 冰蓝
                'btn_danger':     '#94a3b8',  # 灰粉
                'btn_analyze':    '#334155',  # 深灰蓝
                'btn_data':       '#38bdf8',  # 浅蓝
                'btn_secondary':  '#cbd5e1',
                'btn_view':       '#7dd3fc',
                'btn_batch':      '#67e8f9',
                'progress_chunk': '#64748b',
            },
            'midnight': {
                'bg_main':        '#0f172a',
                'btn_new':        '#818cf8',  # 星蓝
                'btn_save':       '#34d399',  # 翠绿
                'btn_danger':     '#f87171',  # 珊瑚
                'btn_analyze':    '#a78bfa',  # 淡紫
                'btn_data':       '#fbbf24',  # 星光
                'btn_secondary':  '#475569',
                'btn_view':       '#6366f1',
                'btn_batch':      '#2dd4bf',
                'progress_chunk': '#818cf8',
            },
            'autumn': {
                'bg_main':        '#fef8f0',
                'btn_new':        '#b45309',  # 秋棕
                'btn_save':       '#4d7c0f',  # 橄榄绿
                'btn_danger':     '#b91c1c',  # 秋红
                'btn_analyze':    '#7c2d12',  # 栗色
                'btn_data':       '#d97706',  # 金橙
                'btn_secondary':  '#c4a484',
                'btn_view':       '#f59e0b',
                'btn_batch':      '#ca8a04',
                'progress_chunk': '#b45309',
            },
            'candy': {
                'bg_main':        '#fffafc',
                'btn_new':        '#ff6b9d',  # 草莓糖
                'btn_save':       '#4ade80',  # 苹果绿
                'btn_danger':     '#ff4757',  # 西瓜红
                'btn_analyze':    '#a29bfe',  # 蓝莓紫
                'btn_data':       '#ffa502',  # 橘子橙
                'btn_secondary':  '#dfe6e9',
                'btn_view':       '#fd79a8',
                'btn_batch':      '#00cec9',
                'progress_chunk': '#ff6b9d',
            },
            'denim': {
                'bg_main':        '#f2f5f8',
                'btn_new':        '#2563eb',  # 牛仔蓝
                'btn_save':       '#059669',  # 松绿
                'btn_danger':     '#dc2626',  # 赤红
                'btn_analyze':    '#1e40af',  # 深蓝
                'btn_data':       '#d97706',  # 铜黄
                'btn_secondary':  '#93c5fd',
                'btn_view':       '#3b82f6',
                'btn_batch':      '#06b6d4',
                'progress_chunk': '#2563eb',
            },
        }

        c = themes.get(theme, themes['macaron'])

        # 暗色主题需要额外的深色适配
        dark_extra = ''
        if theme in ('dark', 'midnight'):
            dark_extra = f'''
            QWidget {{
                color: #e2e8f0;
                background-color: {c['bg_main']};
            }}
            QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox, QListWidget, QTreeWidget, QTableWidget {{
                background-color: #1a1a2e;
                color: #e2e8f0;
                border: 1px solid #334155;
                border-radius: 4px;
            }}
            QStatusBar {{
                background-color: #111827;
                color: #94a3b8;
            }}
            QMenuBar {{
                background-color: #111827;
                color: #e2e8f0;
            }}
            QMenuBar::item:selected {{
                background-color: #334155;
            }}
            QMenu {{
                background-color: #1a1a2e;
                color: #e2e8f0;
                border: 1px solid #334155;
            }}
            QMenu::item:selected {{
                background-color: #475569;
            }}
            '''

        def hover(c_hex):  # 简单的颜色加深
            return c_hex  # 保持原色以简化，hover 也用同色

        ALL_BTN_CLASSES = (
            'QPushButton.new-action, QPushButton.save-action, '
            'QPushButton.danger-action, QPushButton.analyze-action, '
            'QPushButton.data-action, QPushButton.secondary-action, '
            'QPushButton.view-toggle-action, QPushButton.batch-action'
        )

        return f'''
            QMainWindow {{
                background-color: {c['bg_main']};
            }}
            {dark_extra}
            /* 仅对主界面功能按钮应用样式（显式列出所有 class，不误伤对话框按钮） */
            {ALL_BTN_CLASSES} {{
                min-width: 80px;
                padding: 7px 12px;
                border-radius: 4px;
                font-weight: 500;
                border: none;
                color: white;
            }}
            {ALL_BTN_CLASSES}:hover {{
                opacity: 0.85;
            }}
            QPushButton.new-action {{
                background-color: {c['btn_new']};
            }}
            QPushButton.save-action {{
                background-color: {c['btn_save']};
            }}
            QPushButton.danger-action {{
                background-color: {c['btn_danger']};
            }}
            QPushButton.analyze-action {{
                background-color: {c['btn_analyze']};
            }}
            QPushButton.data-action {{
                background-color: {c['btn_data']};
            }}
            QPushButton.secondary-action {{
                background-color: {c['btn_secondary']};
                color: #f8fafc;
            }}
            QPushButton.view-toggle-action {{
                background-color: {c['btn_view']};
                color: white;
            }}
            QPushButton.batch-action {{
                background-color: {c['btn_batch']};
                color: white;
            }}
            QProgressBar {{
                border: 1px solid #cbd5e1;
                border-radius: 4px;
                text-align: center;
                height: 20px;
            }}
            QProgressBar::chunk {{
                background-color: {c['progress_chunk']};
                border-radius: 3px;
            }}
        '''

    # ==================== 主题系统结束 ====================

    def get_sort_clause(self):
        """根据当前设置返回 SQL ORDER BY 子句"""
        sort_mode = self.settings.get('sort_mode', 'update_time_desc')
        sort_map = {
            'update_time_desc':  'ORDER BY t.update_time DESC',
            'update_time_asc':   'ORDER BY t.update_time ASC',
            'title_asc':         'ORDER BY t.title ASC',
            'title_desc':        'ORDER BY t.title DESC',
            'category_asc':      'ORDER BY c.name ASC, t.title ASC',
            'create_time_desc':  'ORDER BY t.create_time DESC',
            'create_time_asc':   'ORDER BY t.create_time ASC',
            'word_count_desc':   'ORDER BY t.word_count DESC',
            'word_count_asc':    'ORDER BY t.word_count ASC',
            'id_desc':           'ORDER BY t.id DESC',
            'id_asc':            'ORDER BY t.id ASC',
            'title_len_desc':    'ORDER BY LENGTH(t.title) DESC',
            'title_len_asc':     'ORDER BY LENGTH(t.title) ASC',
            'random':            'ORDER BY RANDOM()',
        }
        return sort_map.get(sort_mode, 'ORDER BY t.update_time DESC')

    def show_settings_dialog(self):
        """显示设置对话框"""
        dialog = QDialog(self)
        dialog.setWindowTitle("设置")
        dialog.setStyleSheet('')  # 使用默认风格
        dialog.setMinimumWidth(450)
        dialog.setModal(True)
        layout = QVBoxLayout()
        dialog.setLayout(layout)

        # --- 界面风格设置 ---
        theme_group = QGroupBox("界面风格")
        theme_layout = QFormLayout()
        theme_group.setLayout(theme_layout)

        theme_combo = QComboBox()
        current_theme = self.settings.get('theme', 'macaron')
        current_theme_index = 0
        for i, (key, name) in enumerate(self.THEME_INFO.items()):
            theme_combo.addItem(name, key)
            if key == current_theme:
                current_theme_index = i
        theme_combo.setToolTip("选择界面颜色风格，实时应用并自动保存")

        # 主题：变更即实时保存+应用（维护约定：设置实时自动保存+持久保存）
        def on_theme_changed(idx):
            theme_key = theme_combo.currentData()
            self.settings['theme'] = theme_key
            self.setStyleSheet(self._get_theme_stylesheet(theme_key))
            self.save_settings()
        theme_combo.currentIndexChanged.connect(on_theme_changed)
        theme_combo.blockSignals(True)
        theme_combo.setCurrentIndex(current_theme_index)
        theme_combo.blockSignals(False)
        theme_layout.addRow("风格:", theme_combo)

        layout.addWidget(theme_group)

        # --- 列表排序设置 ---
        sort_group = QGroupBox("列表排序方式")
        sort_layout = QFormLayout()
        sort_group.setLayout(sort_layout)

        sort_combo = QComboBox()
        sort_options = [
            ('update_time_desc',  '🕐 修改时间（最新在前）'),
            ('update_time_asc',   '🕐 修改时间（最早在前）'),
            ('create_time_desc',  '📅 创建时间（最新在前）'),
            ('create_time_asc',   '📅 创建时间（最早在前）'),
            ('title_asc',         '🔤 拼音排序（A → Z）'),
            ('title_desc',        '🔤 拼音排序（Z → A）'),
            ('title_len_asc',     '📏 标题长度（短 → 长）'),
            ('title_len_desc',    '📏 标题长度（长 → 短）'),
            ('word_count_desc',   '📊 字数（多 → 少）'),
            ('word_count_asc',    '📊 字数（少 → 多）'),
            ('category_asc',      '📁 按分类排序'),
            ('id_desc',           '🆔 ID（最新在前）'),
            ('id_asc',            '🆔 ID（最早在前）'),
            ('random',            '🎲 随机排序'),
        ]
        current_sort = self.settings.get('sort_mode', 'update_time_desc')
        current_index = 0
        for i, (value, label) in enumerate(sort_options):
            sort_combo.addItem(label, value)
            if value == current_sort:
                current_index = i
        sort_combo.setToolTip("选择左下角文本列表的排序方式，变更即自动保存")

        # 排序：变更即实时保存+重载列表
        def on_sort_changed(idx):
            new_sort_mode = sort_combo.currentData()
            if new_sort_mode != self.settings.get('sort_mode', 'update_time_desc'):
                self.settings['sort_mode'] = new_sort_mode
                self.save_settings()
                self.load_text_list()
        sort_combo.currentIndexChanged.connect(on_sort_changed)
        sort_combo.blockSignals(True)
        sort_combo.setCurrentIndex(current_index)
        sort_combo.blockSignals(False)
        sort_layout.addRow("排序方式:", sort_combo)

        layout.addWidget(sort_group)

        # --- 自动保存设置 ---
        auto_save_group = QGroupBox("自动保存")
        auto_save_layout = QFormLayout()
        auto_save_group.setLayout(auto_save_layout)

        interval_spin = QSpinBox()
        interval_spin.setRange(1, 99999)  # 1秒 ~ 99999秒（约27.8小时）
        interval_spin.setSuffix(" 秒")
        interval_spin.setToolTip("设置自动保存文本的时间间隔，变更即自动保存")

        # 自动保存间隔：变更即实时保存+重启定时器
        def on_interval_changed(value):
            self.settings['auto_save_interval'] = value
            self.save_settings()
            self.auto_save_timer.stop()
            self.auto_save_timer.start(value * 1000)
        interval_spin.valueChanged.connect(on_interval_changed)
        interval_spin.blockSignals(True)
        interval_spin.setValue(self.settings.get('auto_save_interval', 30))
        interval_spin.blockSignals(False)
        auto_save_layout.addRow("保存间隔:", interval_spin)

        layout.addWidget(auto_save_group)

        # --- 说明文本 ---
        info_label = QLabel(
            "<small>💡 提示：所有设置均为<strong>实时自动保存</strong>，修改后立即生效并持久保存，"
            "下次启动自动沿用。<br>"
            "保存位置：程序目录下 settings/app_settings.json。</small>"
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        layout.addStretch()

        # --- 按钮 ---
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Close)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        # 所有设置已在控件变更时实时保存+应用，此处仅展示当前状态
        dialog.exec()
        self.show_status_message(
            f"设置已实时保存！风格: {self.THEME_INFO.get(self.settings.get('theme', 'macaron'), '')} | "
            f"排序: {self.settings.get('sort_mode', 'update_time_desc')} | "
            f"自动保存间隔: {self.settings.get('auto_save_interval', 30)} 秒", 3000
        )

    # ==================== 设置功能结束 ====================

    def show_about_dialog(self):
        """显示关于对话框"""
        about_text = f"""
        <h2>{ProjectInfo.NAME}</h2>
        <p>版本: {ProjectInfo.VERSION} (Build {ProjectInfo.BUILD_DATE})</p>
        <p>{ProjectInfo.DESCRIPTION}</p>
        
        <h3>主要功能:</h3>
        <ul>
            {"".join(f"<li>{feature}</li>" for feature in self.ABOUT['features'])}
        </ul>
        
        <p>作者: {ProjectInfo.AUTHOR}<br>
        许可证: {ProjectInfo.LICENSE}<br>
        {ProjectInfo.COPYRIGHT}</p>
        
        <p>项目主页: <a href="{ProjectInfo.URL}">{ProjectInfo.URL}</a></p>
        """
        
        msg = QMessageBox(self)
        msg.setStyleSheet('')  # 使用默认风格
        msg.setWindowTitle("关于")
        msg.setTextFormat(Qt.RichText)
        msg.setText(about_text)
        msg.setIconPixmap(QIcon('icon.ico').pixmap(64, 64))
        msg.exec()



    def showEvent(self, event):
        super().showEvent(event)

    def closeEvent(self, event):
        """关闭时执行同步备份（确保数据安全）"""
        
        # 同步备份 - 关闭窗口前确保备份完成
        try:
            import glob
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = os.path.join(
                self.backup_config['backup_dir'],
                f"{self.backup_config['backup_prefix']}{timestamp}_close.db"
            )
            self.cursor.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            backup_conn = sqlite3.connect(backup_file)
            with backup_conn:
                self.conn.backup(backup_conn)
            backup_conn.close()
            
            # 清理旧备份
            backups = sorted(
                glob.glob(os.path.join(self.backup_config['backup_dir'], f"{self.backup_config['backup_prefix']}*.db")),
                key=os.path.getmtime, reverse=True
            )
            while len(backups) > self.backup_config['max_backups']:
                oldest = backups.pop()
                try:
                    os.remove(oldest)
                except Exception:
                    pass
        except Exception as e:
            print(f"关闭时备份失败: {e}")
        
        # 保存窗口几何与最大化状态（设置实时自动保存约定，v8.2.0）
        try:
            self.settings['window_geometry'] = bytes(self.saveGeometry().toBase64()).decode('utf-8')
            self.settings['window_maximized'] = self.isMaximized()
            self.save_settings()
        except Exception as e:
            print(f"保存窗口几何失败: {e}")

        # 清理逻辑
        self.auto_save_timer.stop()
        self.conn.close()
        event.accept()


    def eventFilter(self, obj, event):
        return super().eventFilter(obj, event)

    def copy_preview_content(self):
        """复制预览内容到剪贴板（保留所有格式和样式）"""
        # 获取当前内容（HTML格式）
        html_content = self.get_current_content(as_plain_text=False)
        # 获取当前内容（纯文本格式）
        plain_content = self.get_current_content(as_plain_text=True)
        
        if not html_content or not plain_content:
            QMessageBox.information(self, "提示", "没有可复制的内容")
            return
        
        # 根据当前格式进行转换
        format_index = self.format_combo.currentIndex()
        
        if format_index == 0:  # 纯文本模式
            final_html = ProjectInfo.plain_to_html(plain_content)
            final_text = plain_content
        elif format_index == 1:  # Markdown模式
            final_html = ProjectInfo.markdown_to_html(plain_content)
            final_text = plain_content
        else:  # HTML模式
            final_html = self.clean_html(html_content)
            final_text = ProjectInfo.html_to_plain(html_content)
        
        # 设置剪贴板内容
        clipboard = QApplication.clipboard()
        mime_data = QMimeData()
        mime_data.setHtml(final_html)
        mime_data.setText(final_text)
        clipboard.setMimeData(mime_data)
        
        self.show_status_message("预览内容已复制（保留格式）", 2000)


    def copy_preview_plain_text(self):
        """复制预览内容的纯文本版本（无格式）"""
        # 获取当前纯文本内容
        plain_text = self.get_current_content(as_plain_text=True)
        
        if not plain_text:
            QMessageBox.information(self, "提示", "没有可复制的内容")
            return
        
        # 根据当前格式进行额外处理
        format_index = self.format_combo.currentIndex()
        
        if format_index == 1:  # Markdown模式
            plain_text = ProjectInfo.strip_markdown(plain_text)
        elif format_index == 2:  # HTML模式
            plain_text = ProjectInfo.html_to_plain(plain_text)
        
        # 设置剪贴板内容
        clipboard = QApplication.clipboard()
        clipboard.setText(plain_text)
        
        self.show_status_message("预览内容的纯文本版本已复制", 2000)


    def get_current_content(self, as_plain_text=False):
        """获取当前编辑器内容，支持纯文本和HTML格式"""
        format_index = self.format_combo.currentIndex()
        
        if format_index == 2:  # 即见即所得模式
            if as_plain_text:
                return self.wysiwyg_editor.toPlainText()
            return self.wysiwyg_editor.toHtml()
        else:  # 纯文本或Markdown模式
            return self.content_input.toPlainText()

    def create_backup(self, backup_type="manual"):
        """创建数据库备份（使用后台线程）"""
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'text_manager_enhanced.db')
        
        self.backup_worker = BackupWorker(
            db_path,
            self.backup_config['backup_dir'],
            f"{self.backup_config['backup_prefix']}{backup_type}_",
            self.backup_config['max_backups']
        )
        self.backup_worker.finished.connect(
            lambda backup_file: self.show_status_message(f"备份完成: {backup_file}", 3000)
        )
        self.backup_worker.error.connect(
            lambda err: QMessageBox.critical(self, "备份失败", f"创建备份时出错: {err}")
        )
        self.backup_worker.start()

    def cleanup_old_backups(self):
        """清理超出数量的旧备份"""
        import glob
        try:
            # 获取所有备份文件（按时间排序）
            backups = sorted(
                glob.glob(os.path.join(
                    self.backup_config['backup_dir'],
                    f"{self.backup_config['backup_prefix']}*.db"
                )),
                key=os.path.getmtime,
                reverse=True  # 最新的在前面
            )
            
            # 保留指定数量的备份
            while len(backups) > self.backup_config['max_backups']:
                oldest_backup = backups.pop()
                try:
                    os.remove(oldest_backup)
                except Exception as e:
                    print(f"删除旧备份失败: {oldest_backup} - {str(e)}")
        except Exception as e:
            print(f"备份清理出错: {str(e)}")

    def show_backup_manager(self):
        """显示备份管理对话框"""
        dialog = QDialog(self)
        dialog.setWindowTitle("数据库备份与恢复")
        dialog.setStyleSheet('')  # 使用默认风格
        dialog.resize(800, 600)
        
        layout = QVBoxLayout()
        
        # 备份列表表格
        self.backup_table = QTableWidget()
        self.backup_table.setColumnCount(5)
        self.backup_table.setHorizontalHeaderLabels(["选择", "备份时间", "备份类型", "文件大小", "操作"])
        self.backup_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.backup_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.backup_table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        # 填充备份列表
        self.refresh_backup_list()
        
        # 操作按钮
        btn_layout = QHBoxLayout()
        
        btn_create_backup = QPushButton("创建手动备份")
        btn_create_backup.clicked.connect(self.handle_create_backup)
        btn_layout.addWidget(btn_create_backup)
        
        btn_restore = QPushButton("恢复选中备份")
        btn_restore.clicked.connect(lambda: self.handle_restore_backup(dialog))
        btn_layout.addWidget(btn_restore)
        
        btn_delete = QPushButton("删除选中备份")
        btn_delete.clicked.connect(self.handle_delete_backup)
        btn_layout.addWidget(btn_delete)
        
        # 筛选选项
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("备份类型:"))
        
        self.backup_type_filter = QComboBox()
        self.backup_type_filter.addItems(["全部", "自动", "手动", "恢复"])
        self.backup_type_filter.currentTextChanged.connect(self.refresh_backup_list)
        filter_layout.addWidget(self.backup_type_filter)
        
        layout.addLayout(filter_layout)
        layout.addWidget(self.backup_table)
        layout.addLayout(btn_layout)
        
        dialog.setLayout(layout)
        dialog.exec()

    def refresh_backup_list(self):
        """刷新备份列表"""
        import glob
        # 获取所有备份文件
        backup_files = sorted(
            glob.glob(os.path.join(
                self.backup_config['backup_dir'],
                f"{self.backup_config['backup_prefix']}*.db"
            )),
            key=os.path.getmtime,
            reverse=True
        )
        
        # 应用筛选
        filter_type = self.backup_type_filter.currentText() if hasattr(self, 'backup_type_filter') else "全部"
        
        self.backup_table.setRowCount(0)
        
        for file_path in backup_files:
            # 解析文件名获取备份信息
            filename = os.path.basename(file_path)
            timestamp_str = filename[len(self.backup_config['backup_prefix']):-3].split('_')
            
            KNOWN_TYPES = {'auto', 'manual', 'close'}
            if len(timestamp_str) >= 3:
                if timestamp_str[0] in KNOWN_TYPES:
                    # 格式A: type_date_time (如 auto_20260808_112238)
                    backup_type = timestamp_str[0]
                    date_str = timestamp_str[1]
                    time_str = timestamp_str[2]
                else:
                    # 格式B: date_time_type (如 20260808_113620_close)
                    date_str = timestamp_str[0]
                    time_str = timestamp_str[1]
                    backup_type = timestamp_str[2]
            elif len(timestamp_str) >= 2:
                # 旧格式: date_time (向后兼容，无类型标记)
                date_str = timestamp_str[0]
                time_str = timestamp_str[1]
                backup_type = "自动"
            else:
                continue
            
            # 应用筛选
            if filter_type != "全部" and backup_type != filter_type:
                continue
                
            try:
                # 格式化日期时间
                dt = datetime.datetime.strptime(f"{date_str}_{time_str}", "%Y%m%d_%H%M%S")
                formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S")
                
                # 获取文件大小
                size = os.path.getsize(file_path)
                size_str = f"{size/1024:.1f} KB"
                
                # 添加行到表格
                row = self.backup_table.rowCount()
                self.backup_table.insertRow(row)
                
                # 选择复选框
                checkbox = QCheckBox()
                checkbox.setStyleSheet("margin-left:50%; margin-right:50%;")
                self.backup_table.setCellWidget(row, 0, checkbox)
                
                # 备份时间
                self.backup_table.setItem(row, 1, QTableWidgetItem(formatted_time))
                
                # 备份类型
                self.backup_table.setItem(row, 2, QTableWidgetItem(backup_type))
                
                # 文件大小
                self.backup_table.setItem(row, 3, QTableWidgetItem(size_str))
                
                # 预览按钮
                preview_btn = QPushButton("预览")
                preview_btn.clicked.connect(lambda _, path=file_path: self.preview_backup(path))
                self.backup_table.setCellWidget(row, 4, preview_btn)
                
                # 存储文件路径
                self.backup_table.item(row, 1).setData(Qt.ItemDataRole.UserRole, file_path)
                
            except Exception as e:
                print(f"处理备份文件出错: {file_path} - {str(e)}")

    def handle_create_backup(self):
        """处理创建备份请求"""
        backup_file = self.create_backup("manual")
        if backup_file:
            self.refresh_backup_list()
            QMessageBox.information(self, "备份成功", f"已创建手动备份:\n{os.path.basename(backup_file)}")

    def handle_restore_backup(self, dialog):
        """处理恢复备份请求"""
        selected_rows = []
        for row in range(self.backup_table.rowCount()):
            if self.backup_table.cellWidget(row, 0).isChecked():
                selected_rows.append(row)
        
        if not selected_rows:
            QMessageBox.warning(self, "警告", "请先选择要恢复的备份!")
            return
        
        if len(selected_rows) > 1:
            QMessageBox.warning(self, "警告", "一次只能恢复一个备份!")
            return
        
        row = selected_rows[0]
        backup_file = self.backup_table.item(row, 1).data(Qt.ItemDataRole.UserRole)
        
        # 确认对话框
        reply = QMessageBox.question(
            self, "确认恢复",
            f"确定要恢复此备份吗?\n{os.path.basename(backup_file)}\n"
            "恢复前会创建当前数据库的备份。",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # 先创建当前状态的备份
            current_backup = self.create_backup("恢复前")
            if not current_backup:
                return
                
            try:
                # 关闭当前连接
                self.conn.close()
                
                # 复制备份文件到主数据库位置
                main_db = os.path.join(os.path.dirname(__file__), 'text_manager_enhanced.db')
                shutil.copy2(backup_file, main_db)
                
                # 重新连接数据库
                self.conn = sqlite3.connect(main_db)
                self.cursor = self.conn.cursor()
                
                # 刷新UI
                self.load_categories()
                self.load_tags()
                self.load_text_list()
                
                dialog.close()
                QMessageBox.information(self, "恢复成功", "数据库已成功恢复!")
                
            except Exception as e:
                QMessageBox.critical(self, "恢复失败", f"恢复备份时出错: {str(e)}")
                # 尝试恢复原来的连接
                self.conn = sqlite3.connect(main_db)
                self.cursor = self.conn.cursor()

    def handle_delete_backup(self):
        """处理删除备份请求"""
        selected_rows = []
        for row in range(self.backup_table.rowCount()):
            if self.backup_table.cellWidget(row, 0).isChecked():
                selected_rows.append(row)
        
        if not selected_rows:
            QMessageBox.warning(self, "警告", "请先选择要删除的备份!")
            return
        
        # 确认对话框
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除选中的 {len(selected_rows)} 个备份吗?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            success = 0
            for row in selected_rows:
                backup_file = self.backup_table.item(row, 1).data(Qt.ItemDataRole.UserRole)
                try:
                    os.remove(backup_file)
                    success += 1
                except Exception as e:
                    print(f"删除备份失败: {backup_file} - {str(e)}")
            
            self.refresh_backup_list()
            QMessageBox.information(self, "删除完成", f"已成功删除 {success}/{len(selected_rows)} 个备份")

    def preview_backup(self, backup_file):
        """预览备份内容"""
        try:
            # 连接到备份数据库
            conn = sqlite3.connect(backup_file)
            cursor = conn.cursor()
            
            # 获取文本数量
            cursor.execute("SELECT COUNT(*) FROM texts")
            text_count = cursor.fetchone()[0]
            
            # 获取分类数量
            cursor.execute("SELECT COUNT(*) FROM categories")
            category_count = cursor.fetchone()[0]
            
            # 获取标签数量
            cursor.execute("SELECT COUNT(*) FROM tags")
            tag_count = cursor.fetchone()[0]
            
            # 获取备份时间
            backup_time = os.path.getmtime(backup_file)
            backup_time_str = datetime.datetime.fromtimestamp(backup_time).strftime("%Y-%m-%d %H:%M:%S")
            
            # 显示预览信息
            preview_text = f"""
            <h3>备份预览: {os.path.basename(backup_file)}</h3>
            <p>备份时间: {backup_time_str}</p>
            
            <h4>数据库内容统计:</h4>
            <ul>
                <li>文本数量: {text_count}</li>
                <li>分类数量: {category_count}</li>
                <li>标签数量: {tag_count}</li>
            </ul>
            
            <h4>最新5条文本:</h4>
            """
            
            # 获取最新5条文本
            cursor.execute("SELECT id, title, update_time FROM texts ORDER BY update_time DESC LIMIT 5")
            texts = cursor.fetchall()
            
            preview_text += "<ol>"
            for text_id, title, update_time in texts:
                preview_text += f"<li>{title} (ID: {text_id}, 更新于: {update_time})</li>"
            preview_text += "</ol>"
            
            # 关闭连接
            conn.close()
            
            # 显示预览对话框
            preview_dialog = QDialog(self)
            preview_dialog.setWindowTitle("备份预览")
            preview_dialog.setStyleSheet('')  # 使用默认风格
            preview_dialog.resize(600, 400)
            
            layout = QVBoxLayout()
            
            text_browser = QTextBrowser()
            text_browser.setOpenExternalLinks(True)
            text_browser.setHtml(preview_text)
            layout.addWidget(text_browser)
            
            close_btn = QPushButton("关闭")
            close_btn.clicked.connect(preview_dialog.close)
            layout.addWidget(close_btn)
            
            preview_dialog.setLayout(layout)
            preview_dialog.exec()
            
        except Exception as e:
            QMessageBox.critical(self, "预览失败", f"预览备份时出错: {str(e)}")





if __name__ == '__main__':
    app = QApplication(sys.argv)

    try:
        # 设置全局字体
        font = QFont('Microsoft YaHei', 10)
        app.setFont(font)
        
        window = TextManager()
    except Exception as e:
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # 按设置恢复最大化状态（设置实时自动保存约定，v8.2.0）
    if getattr(window, '_start_maximized', False):
        window.showMaximized()
    else:
        window.show()

    sys.exit(app.exec())
    