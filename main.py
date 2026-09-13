import os
import sys
import time
import math
import random
import json
import re
from PyQt6.QtCore import Qt, QTimer, QPoint, QRect, QSize, QThread, pyqtSignal, QUrl
from PyQt6.QtGui import (
    QPixmap, QPainter, QCursor, QFont, QColor, QPen, QBrush, QPainterPath, QClipboard, QTextDocument, QIcon
)
from PyQt6.QtWidgets import (
    QApplication, QWidget, QMenu, QLabel, QVBoxLayout, QHBoxLayout,
    QTextEdit, QPushButton, QDialog, QLineEdit, QComboBox, QScrollArea, QFrame, QMessageBox, QCheckBox
)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput

import mentor_engine

def get_assets_dir():
    candidates = []
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        candidates.append(os.path.join(sys._MEIPASS, "assets"))
    if getattr(sys, 'frozen', False):
        candidates.append(os.path.join(os.path.dirname(sys.executable), "assets"))
    candidates.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets"))
    candidates.append(os.path.join(os.getcwd(), "assets"))
    candidates.append(os.path.join(mentor_engine.get_app_dir(), "assets"))
    for c in candidates:
        if os.path.isdir(c):
            return c
    return candidates[0]

ASSETS_DIR = get_assets_dir()

ANIMATION_NAMES = {
    "idle": "待机状态",
    "start_typing": "开始分析",
    "typing": "持续分析",
    "end_typing": "结束分析",
    "start_talk": "开始说话",
    "talk": "持续说话",
    "end_talk": "说话结束"
}


class AnalysisWorker(QThread):
    finished = pyqtSignal(dict)
    
    def __init__(self, chat_text):
        super().__init__()
        self.chat_text = chat_text

    def run(self):
        result = mentor_engine.analyze_chat(self.chat_text)
        self.finished.emit(result)


class FreeChatWorker(QThread):
    finished = pyqtSignal(str)

    def __init__(self, question):
        super().__init__()
        self.question = question

    def run(self):
        ans = mentor_engine.ask_tong_freely(self.question)
        self.finished.emit(ans)


class TTSWorker(QThread):
    finished = pyqtSignal(str)

    def __init__(self, text, api_key=None, reference_id=None):
        super().__init__()
        self.text = text
        self.api_key = api_key
        self.reference_id = reference_id

    def run(self):
        try:
            audio_p = mentor_engine.synthesize_tong_voice(self.text, self.api_key, self.reference_id)
            self.finished.emit(audio_p or "")
        except Exception as e:
            print("TTSWorker error:", e)
            self.finished.emit("")


class SpeechBubble(QWidget):
    """Floating comic speech bubble above pet's head with locked anchor and fixed width"""
    clicked = pyqtSignal()
    BUBBLE_WIDTH = 290

    def __init__(self, pet_parent=None):
        super().__init__()
        self.pet = pet_parent
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.SubWindow
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setFixedWidth(self.BUBBLE_WIDTH)
        
        self.label = QLabel(self)
        self.label.setWordWrap(True)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("""
            QLabel {
                color: #1A1D20;
                font-family: "Microsoft YaHei", sans-serif;
                font-size: 13px;
                font-weight: bold;
                background: transparent;
            }
        """)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(16, 12, 16, 22)
        self.layout.addWidget(self.label)
        
        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.hide)

    def show_text(self, text, duration_ms=5000):
        self.label.setText(text)
        
        # Accurate text height calculation via QTextDocument to prevent vertical squishing
        doc = QTextDocument()
        font = QFont("Microsoft YaHei", 10)
        font.setBold(True)
        doc.setDefaultFont(font)
        text_avail_w = self.BUBBLE_WIDTH - 32
        doc.setTextWidth(text_avail_w)
        if "<" in text and ">" in text:
            doc.setHtml(text.replace("\n", "<br>"))
        else:
            doc.setPlainText(text)
        
        needed_text_h = int(math.ceil(doc.size().height()))
        total_h = needed_text_h + 12 + 22 + 8  # margins + safe bottom tail clearance
        self.setFixedHeight(max(64, total_h))
        
        self.reposition()
        self.show()
        if duration_ms > 0:
            self.hide_timer.start(duration_ms)
        else:
            self.hide_timer.stop()

    def reposition(self):
        """Solidly lock position directly above character's head with zero jitter"""
        if not self.pet:
            return
        bx = self.pet.x() + (self.pet.width() - self.width()) // 2
        by = self.pet.y() - self.height() - 4
        self.move(bx, by)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
            event.accept()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        w = self.width()
        h = self.height() - 12
        rect = QRect(2, 2, w - 4, h - 4)
        
        path = QPainterPath()
        path.addRoundedRect(rect.x(), rect.y(), rect.width(), rect.height(), 14, 14)
        
        tail = QPainterPath()
        tail.moveTo(w // 2 - 9, h - 4)
        tail.lineTo(w // 2, h + 10)
        tail.lineTo(w // 2 + 9, h - 4)
        tail.closeSubpath()
        path = path.united(tail)
        
        painter.setBrush(QBrush(QColor(255, 255, 255, 250)))
        painter.setPen(QPen(QColor(45, 52, 64, 220), 2))
        painter.drawPath(path)


class FreeChatDialog(QDialog):
    """Direct free-form Q&A with Tong Jincheng Emotional Mentor"""
    def __init__(self, on_send_callback, parent=None):
        super().__init__(parent)
        self.setWindowTitle("💬 向童锦程自由倾诉 / 情感提问")
        self.resize(500, 320)
        self.on_send_callback = on_send_callback
        self.setStyleSheet("""
            QDialog {
                background-color: #1E222A;
                color: #E0E0E0;
                font-family: "Microsoft YaHei", sans-serif;
            }
            QLabel {
                color: #CCCCCC;
                font-size: 13px;
            }
            QTextEdit {
                background-color: #282C34;
                color: #FFFFFF;
                border: 1px solid #3E4451;
                border-radius: 6px;
                padding: 8px;
                font-size: 13px;
            }
            QPushButton {
                background-color: #FF5722;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 8px 18px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #E64A19;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        lbl = QLabel("🧠 <b>童锦程情感洞察视角</b>：<br>输入任何你想探讨的问题（感情困惑、两性博弈、吸引力法则、职场瓶颈等），以深情祖师爷的人间清醒为你指点迷津！", self)
        lbl.setWordWrap(True)
        layout.addWidget(lbl)
        
        self.text_input = QTextEdit(self)
        self.text_input.setPlaceholderText("例如：\n- 祖师爷，相亲对象开门见山要高额彩礼，我该怎么接话？\n- 追女生天天秒回，为什么她越来越敷衍冷漠？\n- 感觉自己陷在单向讨好里出不来，怎么打破内耗？")
        layout.addWidget(self.text_input)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        send_btn = QPushButton("🚀 立即请教祖师爷", self)
        send_btn.clicked.connect(self.on_send)
        btn_layout.addWidget(send_btn)
        
        layout.addLayout(btn_layout)

    def on_send(self):
        txt = self.text_input.toPlainText().strip()
        if txt:
            self.accept()
            self.on_send_callback(txt)


class ChatInputDialog(QDialog):
    """Dialog to paste chat messages for analysis"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🔥 童锦程情感研报室 · 投喂对话")
        self.resize(520, 380)
        self.setStyleSheet("""
            QDialog {
                background-color: #1E222A;
                color: #E0E0E0;
                font-family: "Microsoft YaHei", sans-serif;
            }
            QLabel {
                color: #CCCCCC;
                font-size: 13px;
            }
            QTextEdit {
                background-color: #282C34;
                color: #FFFFFF;
                border: 1px solid #3E4451;
                border-radius: 6px;
                padding: 8px;
                font-size: 13px;
                line-height: 1.4;
            }
            QPushButton {
                background-color: #FF5722;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #E64A19;
            }
            QPushButton#pasteBtn {
                background-color: #3E4451;
            }
            QPushButton#pasteBtn:hover {
                background-color: #4B5263;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        tip = QLabel("🧠 <b>深情祖师爷童锦程已就位</b>：支持直接粘贴微信/QQ复制的聊天记录，系统将自动清洗时间戳、精准识别人物主体，看穿真实博弈！", self)
        tip.setWordWrap(True)
        layout.addWidget(tip)
        
        self.text_edit = QTextEdit(self)
        self.text_edit.setPlaceholderText("可直接粘贴微信/QQ复制的记录（支持带昵称、时间戳，系统将自动识别我方与对方），例如：\n小美 21:10\n在干嘛呢？\n我 21:11\n刚下班，怎么啦宝\n小美 21:12\n今天好累，看中一个包包...")
        layout.addWidget(self.text_edit)
        
        btn_layout = QHBoxLayout()
        self.paste_btn = QPushButton("📋 一键粘贴剪贴板", self)
        self.paste_btn.setObjectName("pasteBtn")
        self.paste_btn.clicked.connect(self.paste_clipboard)
        btn_layout.addWidget(self.paste_btn)
        
        btn_layout.addStretch()
        
        self.submit_btn = QPushButton("🚀 启动童锦程深度研报分析", self)
        self.submit_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.submit_btn)
        
        layout.addLayout(btn_layout)

    def paste_clipboard(self):
        cb = QApplication.clipboard()
        text = cb.text()
        if text:
            self.text_edit.setPlainText(text)

    def get_text(self):
        return self.text_edit.toPlainText().strip()


class TongJinchengReportDialog(QDialog):
    """Detailed visual emotional analysis report modal strictly divided into two sections"""
    def __init__(self, report_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📜 童锦程 · 情感深度剖析研报")
        self.resize(680, 720)
        self.setStyleSheet("""
            QDialog {
                background-color: #181A1F;
                color: #E2E4E9;
                font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
            }
            QScrollArea {
                border: none;
                background: transparent;
            }
            QWidget#scrollContent {
                background: transparent;
            }
            QFrame.card {
                background-color: #21252B;
                border: 1px solid #2C313C;
                border-radius: 8px;
                padding: 16px;
            }
            QFrame.replyBox {
                background-color: #282C34;
                border: 1px solid #3E4451;
                border-radius: 6px;
                padding: 12px;
            }
            QFrame.replyBox QLabel {
                border: none;
                background: transparent;
            }
            QLabel.sectionTitle {
                color: #61AFEF;
                font-size: 15px;
                font-weight: bold;
                padding-bottom: 6px;
                border-bottom: 1px solid #2C313C;
                margin-bottom: 10px;
            }
            QLabel.content {
                color: #D1D5DB;
                font-size: 14px;
                line-height: 1.65;
            }
            QPushButton.copyBtn {
                background-color: #2A303C;
                color: #00E676;
                border: 1px solid #00E676;
                border-radius: 4px;
                padding: 5px 12px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton.copyBtn:hover {
                background-color: #00E676;
                color: #121212;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(12)
        
        # Clean title header
        title_lbl = QLabel("📜 <b>童锦程 · 情感深度剖析研报</b>", self)
        title_lbl.setStyleSheet("font-size: 16px; color: #FFFFFF; padding-bottom: 4px;")
        main_layout.addWidget(title_lbl)
        
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        content_widget = QWidget()
        content_widget.setObjectName("scrollContent")
        layout = QVBoxLayout(content_widget)
        layout.setSpacing(16)
        
        # ==========================================
        # 顶部：对话主体与局势研判
        # ==========================================
        protagonists = report_data.get("protagonists") or {}
        user_side = protagonists.get("user_side", "")
        target_side = protagonists.get("target_side", "")
        rel_state = protagonists.get("relationship_state", "")
        
        if not user_side:
            user_side = "连麦求助兄弟（我方立场）"
        if not target_side:
            target_side = "聊天对象（对方）"
        if not rel_state:
            scenario = mentor_engine.detect_chat_scenario(report_data.get("chat_text", ""))
            states = {
                "money": "真实金钱索取局 · 对方借机索取利益，拒绝当ATM提款机",
                "cold": "冷淡敷衍局 · 对方爱搭不理，我方单向患得患失",
                "pua": "甩锅责问局 · 对方倒打一耙，我方陷入自证陷阱",
                "fishing": "暧昧养鱼局 · 对方忽冷忽热，我方沦为备胎",
                "ex": "前任纠缠局 · 前任深夜试探，好马不吃回头草",
                "blind_date": "相亲盘查局 · 现实条件审视与博弈",
                "general": "常规社交局 · 吸引力博弈与框架树立"
            }
            rel_state = states.get(scenario, "两性吸引力与情感博弈局")

        card0 = QFrame()
        card0.setProperty("class", "card")
        card0.setStyleSheet("""
            QFrame.card {
                background-color: #1A1F29;
                border: 1px solid #FF5722;
                border-radius: 8px;
                padding: 14px;
            }
        """)
        c0_layout = QVBoxLayout(card0)
        c0_layout.setSpacing(8)
        
        t0 = QLabel("🎭 <b>【人物主体辨析与局势研判】</b>", card0)
        t0.setStyleSheet("color: #FF7043; font-size: 14px; font-weight: bold;")
        c0_layout.addWidget(t0)
        
        info_html = (
            f"<div style='font-size: 13px; line-height: 1.7; color: #D1D5DB;'>"
            f"👤 <b>我方求助兄弟</b>：<span style='color: #4FC3F7; font-weight: bold;'>{user_side}</span><br>"
            f"🎯 <b>聊天目标对象</b>：<span style='color: #FF8A80; font-weight: bold;'>{target_side}</span><br>"
            f"🧭 <b>当前局势定性</b>：<span style='color: #FFD54F; font-weight: bold;'>{rel_state}</span>"
            f"</div>"
        )
        info_lbl = QLabel(info_html, card0)
        info_lbl.setTextFormat(Qt.TextFormat.RichText)
        info_lbl.setWordWrap(True)
        c0_layout.addWidget(info_lbl)
        
        layout.addWidget(card0)

        # ==========================================
        # 第一部分：深度情感剖析长文
        # ==========================================
        card1 = QFrame()
        card1.setProperty("class", "card")
        c1_layout = QVBoxLayout(card1)
        c1_layout.setSpacing(10)
        
        # 用户要求：标题换成一个能总结这段分析报告的有趣犀利标题
        raw_title = report_data.get("title", "").strip() or report_data.get("analysis_title", "").strip()
        clean_title = mentor_engine.clean_report_title(raw_title, report_data)
            
        t1 = QLabel(clean_title, card1)
        t1.setProperty("class", "sectionTitle")
        c1_layout.addWidget(t1)
        
        analysis_text = report_data.get("tong_analysis", "").strip()
        if not analysis_text:
            # Fallback combining historical parts into a flowing essay
            parts = [
                report_data.get("tong_review", ""),
                report_data.get("risk_warning", ""),
                report_data.get("strategic_action", "")
            ]
            valid_parts = [p.strip() for p in parts if p and p.strip()]
            analysis_text = "\n\n".join(valid_parts)
            if not analysis_text:
                analysis_text = report_data.get("one_line_summary", "（暂无剖析内容）")
                
        rev_lbl = QLabel(analysis_text, card1)
        rev_lbl.setProperty("class", "content")
        rev_lbl.setWordWrap(True)
        rev_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        c1_layout.addWidget(rev_lbl)
        layout.addWidget(card1)
        
        # ==========================================
        # 第二部分：可复制的文案
        # ==========================================
        card2 = QFrame()
        card2.setProperty("class", "card")
        c2_layout = QVBoxLayout(card2)
        c2_layout.setSpacing(12)
        
        t2 = QLabel("第二部分：可复制的文案", card2)
        t2.setProperty("class", "sectionTitle")
        c2_layout.addWidget(t2)
        
        reply_list = report_data.get("reply_options", [])
        if not reply_list:
            empty_lbl = QLabel("（暂无备选文案）", card2)
            empty_lbl.setStyleSheet("color: #7F848E; font-size: 13px;")
            c2_layout.addWidget(empty_lbl)
        else:
            for idx, item in enumerate(reply_list):
                reply_box = QFrame()
                reply_box.setProperty("class", "replyBox")
                r_box_layout = QVBoxLayout(reply_box)
                r_box_layout.setSpacing(8)
                
                top_row = QHBoxLayout()
                title_str = item.get("title", f"方案 {idx+1}")
                sub_t = QLabel(f"<b>{title_str}</b>", reply_box)
                sub_t.setStyleSheet("color: #61AFEF; font-size: 13px;")
                top_row.addWidget(sub_t)
                top_row.addStretch()
                
                reply_content = item.get("text", "")
                copy_btn = QPushButton("📋 一键复制", reply_box)
                copy_btn.setProperty("class", "copyBtn")
                copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                copy_btn.clicked.connect(lambda ch, text=reply_content, b=copy_btn: self.copy_reply(text, b))
                top_row.addWidget(copy_btn)
                r_box_layout.addLayout(top_row)
                
                body_lbl = QLabel(reply_content, reply_box)
                body_lbl.setWordWrap(True)
                body_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                body_lbl.setStyleSheet("color: #E5C07B; font-size: 14px; line-height: 1.5; padding-top: 2px;")
                r_box_layout.addWidget(body_lbl)
                
                c2_layout.addWidget(reply_box)
                
        layout.addWidget(card2)
        
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)

    def copy_reply(self, text, btn):
        QApplication.clipboard().setText(text)
        old_text = btn.text()
        btn.setText("✅ 已复制！")
        btn.setStyleSheet("background-color: #00E676; color: #121212; border-radius: 4px; padding: 4px 10px; font-weight: bold;")
        QTimer.singleShot(2000, lambda: [
            btn.setText(old_text),
            btn.setStyleSheet("")
        ])


class ApiConfigDialog(QDialog):
    """API Configuration Dialog with quick presets for Zhipu, DeepSeek, Gemini, etc."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🔑 配置大模型 API")
        self.resize(520, 340)
        self.setStyleSheet("""
            QDialog { background-color: #21252B; color: #E0E0E0; font-family: "Microsoft YaHei"; }
            QLabel { color: #CCCCCC; font-size: 13px; }
            QLineEdit, QComboBox { background-color: #282C34; color: #FFF; border: 1px solid #3E4451; border-radius: 4px; padding: 6px; }
            QPushButton { background-color: #0078D4; color: #FFF; border: none; border-radius: 4px; padding: 8px 16px; font-weight: bold; }
            QPushButton:hover { background-color: #106EBE; }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        self.cfg = mentor_engine.load_config()
        
        layout.addWidget(QLabel("大模型服务服务商 (Provider)："))
        self.provider_combo = QComboBox(self)
        self.provider_combo.addItems([
            "Kimi (Moonshot AI) - 推荐：细腻对话与长文分析",
            "DeepSeek (深度求索) - 推荐：顶级逻辑推理与情感博弈",
            "智谱 AI (GLM) - 国内极速免费",
            "Google Gemini",
            "OpenAI 官方",
            "自定义通用兼容接口"
        ])
        
        # Detect current preset
        b_url = self.cfg.get("base_url", "").lower()
        m_name = self.cfg.get("model", "").lower()
        prov = self.cfg.get("provider", "").lower()
        if "moonshot" in b_url or "kimi" in m_name or "moonshot" in m_name:
            self.provider_combo.setCurrentIndex(0)
        elif "deepseek" in b_url or "deepseek" in m_name:
            self.provider_combo.setCurrentIndex(1)
        elif "bigmodel.cn" in b_url or "glm" in m_name:
            self.provider_combo.setCurrentIndex(2)
        elif "gemini" in prov:
            self.provider_combo.setCurrentIndex(3)
        elif "openai.com" in b_url:
            self.provider_combo.setCurrentIndex(4)
        else:
            self.provider_combo.setCurrentIndex(5)
            
        self.provider_combo.currentIndexChanged.connect(self.on_preset_changed)
        layout.addWidget(self.provider_combo)
        
        layout.addWidget(QLabel("API Key："))
        self.key_edit = QLineEdit(self)
        self.key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_edit.setText(self.cfg.get("api_key", ""))
        self.key_edit.setPlaceholderText("请输入您的 API Key (如 sk-... 或 your-api-key)")
        layout.addWidget(self.key_edit)
        
        layout.addWidget(QLabel("Base URL："))
        self.url_edit = QLineEdit(self)
        self.url_edit.setText(self.cfg.get("base_url", "https://open.bigmodel.cn/api/paas/v4"))
        layout.addWidget(self.url_edit)
        
        layout.addWidget(QLabel("模型名称 (Model)："))
        self.model_edit = QLineEdit(self)
        self.model_edit.setText(self.cfg.get("model", "glm-4-flash"))
        layout.addWidget(self.model_edit)
        
        self.hint = QLabel("💡 提示：可从上方下拉列表快速切换 Kimi、DeepSeek 或 智谱 AI")
        self.hint.setStyleSheet("color: #FFD54F; font-size: 11px;")
        layout.addWidget(self.hint)
        
        # Fish Audio TTS Configuration
        sep = QFrame(self)
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #3E4451; margin: 6px 0;")
        layout.addWidget(sep)
        
        layout.addWidget(QLabel("<b>🎙️ 童锦程原声语音克隆 (Fish Audio)：</b>"))
        self.tts_cb = QCheckBox("每次给出分析总结时，用童锦程原声音色朗读总结词", self)
        self.tts_cb.setChecked(bool(self.cfg.get("tts_enabled", True)))
        self.tts_cb.setStyleSheet("color: #00E676; font-weight: bold;")
        layout.addWidget(self.tts_cb)
        
        layout.addWidget(QLabel("Fish Audio API Key："))
        self.fish_key_edit = QLineEdit(self)
        self.fish_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.fish_key_edit.setText(self.cfg.get("fish_api_key", ""))
        self.fish_key_edit.setPlaceholderText("请输入您的 Fish Audio API Key (sk-...)")
        layout.addWidget(self.fish_key_edit)
        
        layout.addWidget(QLabel("童锦程音色模型 ID (Reference ID)："))
        self.fish_ref_edit = QLineEdit(self)
        self.fish_ref_edit.setText(self.cfg.get("fish_reference_id", "93d4dc1cbd6f4d55aee5ca54c0f9c6bb"))
        layout.addWidget(self.fish_ref_edit)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        save_btn = QPushButton("💾 保存配置并测试", self)
        save_btn.clicked.connect(self.save_and_close)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

    def on_preset_changed(self, idx):
        if idx == 0:  # Kimi
            self.url_edit.setText("https://api.moonshot.cn/v1")
            self.model_edit.setText("moonshot-v1-8k")
            self.hint.setText("💡 Kimi (Moonshot AI) 极度擅长中文细腻对话与长上下文！API Key 从 platform.moonshot.cn 获取，可选 moonshot-v1-8k 或 moonshot-v1-32k")
        elif idx == 1:  # DeepSeek
            self.url_edit.setText("https://api.deepseek.com/v1")
            self.model_edit.setText("deepseek-chat")
            self.hint.setText("💡 DeepSeek 具备顶级逻辑推理与情感博弈洞察！API Key 从 platform.deepseek.com 获取，推荐 deepseek-chat 或 deepseek-reasoner")
        elif idx == 2:  # 智谱
            self.url_edit.setText("https://open.bigmodel.cn/api/paas/v4")
            self.model_edit.setText("glm-4-flash")
            self.hint.setText("💡 智谱推荐填 glm-4-flash（响应极速且全免费）或 glm-4-plus（高精度旗舰，更准）")
        elif idx == 3:  # Gemini
            self.url_edit.setText("https://generativelanguage.googleapis.com/v1beta")
            self.model_edit.setText("gemini-2.5-flash")
            self.hint.setText("💡 Google Gemini 官方接口需自备科学环境")
        elif idx == 4:  # OpenAI
            self.url_edit.setText("https://api.openai.com/v1")
            self.model_edit.setText("gpt-4o-mini")
            self.hint.setText("💡 OpenAI 官方接口需具备可用额度的 sk- 密钥")
        elif idx == 5:  # 自定义
            self.hint.setText("💡 支持任何兼容 OpenAI 协议的 API（如 OneAPI、Ollama、NewAPI 等）")

    def save_and_close(self):
        idx = self.provider_combo.currentIndex()
        prov = "gemini" if idx == 3 else "openai"
        
        raw_cfg = {
            "provider": prov,
            "api_key": self.key_edit.text().strip(),
            "base_url": self.url_edit.text().strip(),
            "model": self.model_edit.text().strip()
        }
        # Auto-normalize and correct wrong URL/model names (e.g. bigmodel.cn/console -> api/paas/v4, GLM-5.3 -> glm-4-flash)
        norm_prov, norm_url, norm_model = mentor_engine.normalize_api_config(raw_cfg)
        
        self.cfg["provider"] = norm_prov
        self.cfg["api_key"] = raw_cfg["api_key"]
        self.cfg["base_url"] = norm_url
        self.cfg["model"] = norm_model
        self.cfg["fish_api_key"] = self.fish_key_edit.text().strip()
        self.cfg["fish_reference_id"] = self.fish_ref_edit.text().strip()
        self.cfg["tts_enabled"] = self.tts_cb.isChecked()
        
        mentor_engine.save_config(self.cfg)
        tts_status = "已开启 ✅" if self.cfg["tts_enabled"] else "未开启"
        QMessageBox.information(
            self, "配置成功",
            f"✅ 配置已保存！\n\n服务商: {norm_prov}\n模型名称: {norm_model}\n童锦程原声语音: {tts_status}\n\nAI 情感导师已全面就绪，随时为您提供清醒洞察！"
        )
        self.accept()


class DesktopPet(QWidget):
    def __init__(self):
        super().__init__()
        
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.SubWindow
        )
        self.setWindowTitle("祖师爷桌宠")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAcceptDrops(True)
        
        # State variables
        self.current_state = "idle"
        self.frame_index = 0
        self.scale_ratio = 0.30  # ~228x414 px for full body
        self.fps = 10.0  # Slow relaxed speed (~100ms per frame)
        self.is_dragging = False
        self.drag_start_pos = QPoint()
        self.mouse_pressed_pos = QPoint()
        self.is_locked = False
        self.auto_random_action = True
        self.talk_loops = 0
        
        self.latest_report = None
        self.pending_report = None
        self.pending_chat_reply = None
        self.waiting_to_end_typing = False
        self.typing_purpose = None
        self.random_typing_loops = 0
        self.analysis_worker = None
        self.chat_worker = None
        
        self.animations = {}
        self.load_all_animations()
        
        # Multimedia voice player
        self.audio_output = QAudioOutput()
        self.audio_output.setVolume(1.0)
        self.media_player = QMediaPlayer()
        self.media_player.setAudioOutput(self.audio_output)
        self.media_player.playbackStateChanged.connect(self.on_voice_playback_changed)
        self.tts_worker = None

        # Solidly anchored speech bubble
        self.bubble = SpeechBubble(self)
        self.bubble.clicked.connect(self.on_bubble_clicked)
        
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self.next_frame)
        self.anim_timer.start(int(round(1000 / self.fps)))
        
        self.random_timer = QTimer(self)
        self.random_timer.timeout.connect(self.on_random_idle_trigger)
        self.random_timer.start(50000)
        
        self.init_position()
        self.update()

    def speak_tong_voice(self, text):
        cfg = mentor_engine.load_config()
        if not cfg.get("tts_enabled", True):
            return
        if self.tts_worker and self.tts_worker.isRunning():
            self.tts_worker.terminate()
            self.tts_worker.wait()
            
        self.tts_worker = TTSWorker(text)
        self.tts_worker.finished.connect(self.on_voice_ready)
        self.tts_worker.start()

    def on_voice_ready(self, audio_path):
        if audio_path and os.path.exists(audio_path):
            self.media_player.setSource(QUrl.fromLocalFile(audio_path))
            self.media_player.play()
            if self.current_state in ["start_talk", "talk", "idle"]:
                self.set_state("talk")

    def on_voice_playback_changed(self, state):
        if state == QMediaPlayer.PlaybackState.StoppedState:
            # Audio finished playing! Smoothly transition talk -> end_talk -> idle
            if self.current_state in ["start_talk", "talk"]:
                self.set_state("end_talk")

    def init_position(self):
        screen = QApplication.primaryScreen().availableGeometry()
        w = int(760 * self.scale_ratio)
        h = int(1380 * self.scale_ratio)
        self.resize(w, h)
        self.move(screen.right() - w - 80, screen.bottom() - h - 50)
        if self.bubble:
            self.bubble.reposition()

    def load_all_animations(self):
        print(f"Loading animation assets from: {ASSETS_DIR}...")
        for state_key, dir_name in ANIMATION_NAMES.items():
            folder = os.path.join(ASSETS_DIR, dir_name)
            frames = []
            if os.path.exists(folder):
                files = sorted([f for f in os.listdir(folder) if f.endswith(".png")])
                for f in files:
                    pix = QPixmap(os.path.join(folder, f))
                    frames.append(pix)
            self.animations[state_key] = frames
            print(f" - Loaded [{state_key}] ({dir_name}): {len(frames)} frames")

    def set_state(self, state_key):
        if state_key not in self.animations or len(self.animations[state_key]) == 0:
            return
        self.current_state = state_key
        self.frame_index = 0
        if state_key in ["start_talk", "talk"]:
            self.talk_loops = 0
        self.update()

    def next_frame(self):
        frames = self.animations.get(self.current_state, [])
        if not frames:
            return
        
        self.frame_index += 1
        
        if self.frame_index >= len(frames):
            if self.current_state == "idle":
                self.frame_index = 0
            elif self.current_state == "start_typing":
                if self.waiting_to_end_typing:
                    self.waiting_to_end_typing = False
                    self.set_state("end_typing")
                else:
                    self.set_state("typing")
                return
            elif self.current_state == "typing":
                if self.waiting_to_end_typing:
                    self.waiting_to_end_typing = False
                    self.set_state("end_typing")
                    return
                elif self.typing_purpose == "random":
                    self.random_typing_loops += 1
                    if self.random_typing_loops >= 2:
                        self.set_state("end_typing")
                        return
                    else:
                        self.frame_index = 0
                else:
                    self.frame_index = 0
            elif self.current_state == "end_typing":
                # 分析动效完全结束，进入说话状态并展示报告或解答
                if self.pending_report:
                    report = self.pending_report
                    self.pending_report = None
                    self.latest_report = report
                    
                    summary_text = report.get("one_line_summary", "")
                    clean_summary = mentor_engine.clean_one_line_summary(summary_text)
                    # 智能场景研判与决策兜底（坚决不在非金钱场景无脑乱入“这钱不要给”）
                    clean_summary = mentor_engine.ensure_smart_summary(clean_summary, report)
                    
                    # 用户要求：前面的句式不要，直接总结！气泡与童锦程原声语音均直接开门见山
                    bubble_msg = f"{clean_summary}\n\n【点击此气泡】查看完整研报"
                    self.bubble.show_text(bubble_msg, 0)
                    self.speak_tong_voice(clean_summary)
                elif self.pending_chat_reply:
                    ans = self.pending_chat_reply
                    self.pending_chat_reply = None
                    clean_ans = re.sub(r"^(\s*(\[.*?\]|【.*?】|\(.*?\)|（.*?）|[：:])\s*)+", "", ans).strip()
                    self.bubble.show_text(f"{clean_ans or ans}", 8000)
                    self.speak_tong_voice(clean_ans or ans)
                
                self.typing_purpose = None
                self.talk_loops = 0
                self.set_state("start_talk")
                return
            elif self.current_state == "start_talk":
                self.talk_loops = 0
                self.set_state("talk")
                return
            elif self.current_state == "talk":
                # 若音频正在播放，持续保持说话动作循环
                if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                    self.frame_index = 0
                else:
                    self.talk_loops += 1
                    if self.talk_loops >= 2 or not self.bubble.isVisible():
                        self.set_state("end_talk")
                        return
                    else:
                        self.frame_index = 0
            elif self.current_state == "end_talk":
                self.set_state("idle")
                return
            else:
                self.frame_index = 0
        
        self.update()

    # Drag and Drop support
    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event):
        text = event.mimeData().text().strip()
        if text:
            self.start_mentor_analysis(text)
            event.acceptProposedAction()

    def start_mentor_analysis(self, chat_text):
        """Trigger emotional mentor analysis flow"""
        if not chat_text:
            return
        
        self.typing_purpose = "analysis"
        self.pending_report = None
        self.waiting_to_end_typing = False
        self.analysis_start_time = time.time()
        
        self.set_state("start_typing")
        self.bubble.show_text("正在运用童锦程5大心智模型深度审读...\n请稍候...", 0)
        
        self.analysis_worker = AnalysisWorker(chat_text)
        self.analysis_worker.finished.connect(self.on_analysis_finished)
        self.analysis_worker.start()

    def on_analysis_finished(self, report):
        self.pending_report = report
        elapsed = time.time() - getattr(self, "analysis_start_time", 0)
        min_typing_sec = 2.0  # 确保打字推演至少持续2秒以上
        remaining_ms = int(max(0.0, min_typing_sec - elapsed) * 1000)
        
        if remaining_ms > 0:
            QTimer.singleShot(remaining_ms, self._request_end_typing)
        else:
            self._request_end_typing()

    def _request_end_typing(self):
        if self.current_state == "typing":
            self.set_state("end_typing")
        elif self.current_state == "start_typing":
            self.waiting_to_end_typing = True
        elif self.current_state == "end_typing":
            pass
        else:
            self.set_state("end_typing")

    def start_free_chat(self, question_text):
        """Ask Tong Jincheng anything freely"""
        self.typing_purpose = "free_chat"
        self.pending_chat_reply = None
        self.waiting_to_end_typing = False
        self.chat_start_time = time.time()
        
        self.set_state("start_typing")
        self.bubble.show_text("祖师爷正在深入思考与组织建议...\n请稍候...", 0)
        
        self.chat_worker = FreeChatWorker(question_text)
        self.chat_worker.finished.connect(self.on_free_chat_finished)
        self.chat_worker.start()

    def on_free_chat_finished(self, answer_text):
        self.pending_chat_reply = answer_text
        elapsed = time.time() - getattr(self, "chat_start_time", 0)
        min_typing_sec = 2.0
        remaining_ms = int(max(0.0, min_typing_sec - elapsed) * 1000)
        
        if remaining_ms > 0:
            QTimer.singleShot(remaining_ms, self._request_end_typing)
        else:
            self._request_end_typing()

    def on_bubble_clicked(self):
        if self.latest_report:
            dialog = TongJinchengReportDialog(self.latest_report, self)
            dialog.exec()
        else:
            self.open_free_chat()

    def open_chat_input(self):
        dialog = ChatInputDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            text = dialog.get_text()
            if text:
                self.start_mentor_analysis(text)

    def open_free_chat(self):
        dialog = FreeChatDialog(self.start_free_chat, self)
        dialog.exec()

    def on_random_idle_trigger(self):
        if not self.auto_random_action or self.current_state != "idle":
            return
        
        r = random.random()
        if r < 0.65:
            self.set_state("start_talk")
            self.say_random_quote()
        else:
            self.typing_purpose = "random"
            self.random_typing_loops = 0
            self.set_state("start_typing")

    def say_random_quote(self):
        # Pick from massive dynamic, non-repeating Tong Jincheng corpus!
        quote = mentor_engine.get_smart_tong_quote()
        self.bubble.show_text(quote, 5000)

    def paintEvent(self, event):
        frames = self.animations.get(self.current_state, [])
        if not frames:
            return
        
        idx = self.frame_index % len(frames)
        pix = frames[idx]
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        
        scaled = pix.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        x = (self.width() - scaled.width()) // 2
        y = (self.height() - scaled.height()) // 2
        painter.drawPixmap(x, y, scaled)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.mouse_pressed_pos = event.globalPosition().toPoint()
            if not self.is_locked:
                self.is_dragging = True
                self.drag_start_pos = self.mouse_pressed_pos - self.pos()
                self.setCursor(QCursor(Qt.CursorShape.ClosedHandCursor))
            event.accept()

    def mouseMoveEvent(self, event):
        if self.is_dragging and not self.is_locked:
            new_pos = event.globalPosition().toPoint() - self.drag_start_pos
            self.move(new_pos)
            if self.bubble:
                self.bubble.reposition()
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = False
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
            released_pos = event.globalPosition().toPoint()
            if (released_pos - self.mouse_pressed_pos).manhattanLength() < 5:
                self.on_pet_clicked()
            event.accept()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Double click opens free chat or input dialog!
            self.open_free_chat()
            event.accept()

    def on_pet_clicked(self):
        if self.current_state == "idle":
            self.set_state("start_talk")
            self.say_random_quote()
        elif self.current_state == "typing":
            self.say_random_quote()

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #2D3035;
                color: #FFFFFF;
                border: 1px solid #444850;
                border-radius: 8px;
                padding: 6px;
                font-family: "Microsoft YaHei", sans-serif;
                font-size: 13px;
            }
            QMenu::item {
                padding: 6px 24px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #FF5722;
            }
            QMenu::separator {
                height: 1px;
                background-color: #444850;
                margin: 4px 8px;
            }
        """)

        # Mentor features
        act_ask = menu.addAction("💬 向童锦程自由倾诉 / 情感提问")
        act_ask.triggered.connect(self.open_free_chat)

        act_feed = menu.addAction("🔥 投喂聊天记录开启童锦程研报")
        act_feed.triggered.connect(self.open_chat_input)
        
        act_clip = menu.addAction("📋 一键分析剪贴板最新聊天记录")
        act_clip.triggered.connect(self.analyze_clipboard_directly)
        
        if self.latest_report:
            act_rep = menu.addAction("📊 查看最新童锦程深度研报")
            act_rep.triggered.connect(self.on_bubble_clicked)

        menu.addSeparator()

        # Action Submenu
        action_menu = menu.addMenu("🎭 切换动效")
        act_idle = action_menu.addAction("🛋️ 待机状态 (循环)")
        act_idle.triggered.connect(lambda: self.set_state("idle"))
        
        act_start_type = action_menu.addAction("🔍 开始分析")
        act_start_type.triggered.connect(lambda: self.set_state("start_typing"))
        
        act_typing = action_menu.addAction("⚙️ 持续分析 (循环)")
        act_typing.triggered.connect(lambda: self.set_state("typing"))
        
        act_end_type = action_menu.addAction("⏹️ 结束分析")
        act_end_type.triggered.connect(lambda: self.set_state("end_typing"))
        
        act_start_talk = action_menu.addAction("🗣️ 开始说话")
        act_start_talk.triggered.connect(lambda: [self.set_state("start_talk"), self.say_random_quote()])

        act_talk = action_menu.addAction("💬 持续说话 (循环)")
        act_talk.triggered.connect(lambda: [self.set_state("talk"), self.say_random_quote()])

        act_end_talk = action_menu.addAction("🤐 说话结束 → 待机")
        act_end_talk.triggered.connect(lambda: self.set_state("end_talk"))

        # Scale Submenu
        scale_menu = menu.addMenu("🔍 调整大小")
        scales = [
            ("迷你 (20%)", 0.20),
            ("精巧 (25%)", 0.25),
            ("标准 (30% - 推荐)", 0.30),
            ("适中 (35%)", 0.35),
            ("放大 (45%)", 0.45)
        ]
        for label, val in scales:
            act = scale_menu.addAction(label)
            act.setCheckable(True)
            act.setChecked(abs(self.scale_ratio - val) < 0.01)
            act.triggered.connect(lambda checked, v=val: self.change_scale(v))

        # Speed Submenu
        speed_menu = menu.addMenu("⚡ 动画速度")
        speeds = [
            ("🛋️ 从容舒缓 (10 FPS - 默认推荐)", 10.0),
            ("🍵 悠闲慢速 (8 FPS)", 8.0),
            ("🌿 极度闲适 (6 FPS)", 6.0),
            ("✨ 适度放慢 (14 FPS)", 14.0),
            ("☕ 稍慢轻快 (20 FPS)", 20.0),
            ("🚀 原速标准 (30 FPS)", 30.0)
        ]
        for label, val in speeds:
            act = speed_menu.addAction(label)
            act.setCheckable(True)
            act.setChecked(abs(self.fps - val) < 0.5)
            act.triggered.connect(lambda checked, v=val: self.change_speed(v))

        menu.addSeparator()

        act_api = menu.addAction("🔑 配置大模型 API")
        act_api.triggered.connect(self.open_api_config)

        act_top = menu.addAction("📌 始终置顶")
        act_top.setCheckable(True)
        is_top = bool(self.windowFlags() & Qt.WindowType.WindowStaysOnTopHint)
        act_top.setChecked(is_top)
        act_top.triggered.connect(self.toggle_always_on_top)

        act_lock = menu.addAction("🔒 锁定位置 (防拖动)")
        act_lock.setCheckable(True)
        act_lock.setChecked(self.is_locked)
        act_lock.triggered.connect(self.toggle_lock)

        act_rand = menu.addAction("🎲 自动随机动作/金句")
        act_rand.setCheckable(True)
        act_rand.setChecked(self.auto_random_action)
        act_rand.triggered.connect(self.toggle_random_action)

        cur_cfg = mentor_engine.load_config()
        act_tts = menu.addAction("🎙️ 启用童锦程原声语音朗读")
        act_tts.setCheckable(True)
        act_tts.setChecked(bool(cur_cfg.get("tts_enabled", True)))
        act_tts.triggered.connect(self.toggle_tts_enabled)

        menu.addSeparator()

        act_say = menu.addAction("💬 换一句祖师爷金句")
        act_say.triggered.connect(lambda: [self.set_state("start_talk"), self.say_random_quote()])

        menu.addSeparator()

        act_exit = menu.addAction("❌ 退出桌宠")
        act_exit.triggered.connect(self.quit_app)

        menu.exec(event.globalPos())

    def toggle_tts_enabled(self):
        cfg = mentor_engine.load_config()
        cfg["tts_enabled"] = not cfg.get("tts_enabled", True)
        mentor_engine.save_config(cfg)
        status = "已开启 ✅" if cfg["tts_enabled"] else "已关闭 ⏸️"
        self.bubble.show_text(f"童锦程原声朗读总结：{status}", 3000)

    def analyze_clipboard_directly(self):
        text = QApplication.clipboard().text().strip()
        if text:
            self.start_mentor_analysis(text)
        else:
            self.bubble.show_text("剪贴板里空空如也，先复制一段聊天记录再来分析！", 3500)

    def open_api_config(self):
        dlg = ApiConfigDialog(self)
        dlg.exec()

    def change_scale(self, new_ratio):
        self.scale_ratio = new_ratio
        w = int(760 * self.scale_ratio)
        h = int(1380 * self.scale_ratio)
        self.resize(w, h)
        if self.bubble:
            self.bubble.reposition()
        self.update()

    def change_speed(self, new_fps):
        self.fps = new_fps
        interval = max(10, int(round(1000.0 / self.fps)))
        self.anim_timer.setInterval(interval)

    def toggle_always_on_top(self):
        is_top = bool(self.windowFlags() & Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, not is_top)
        self.show()

    def toggle_lock(self):
        self.is_locked = not self.is_locked

    def toggle_random_action(self):
        self.auto_random_action = not self.auto_random_action

    def quit_app(self):
        if self.bubble:
            self.bubble.close()
        self.close()
        QApplication.quit()


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)
    app.setApplicationName("祖师爷桌宠")
    app.setApplicationDisplayName("祖师爷桌宠")
    
    # Set application icon
    icon_candidates = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico"),
        os.path.join(os.path.dirname(sys.executable), "icon.ico"),
        os.path.join(mentor_engine.get_app_dir(), "icon.ico")
    ]
    for ic in icon_candidates:
        if os.path.exists(ic):
            app.setWindowIcon(QIcon(ic))
            break
            
    pet = DesktopPet()
    pet.show()
    
    QTimer.singleShot(600, lambda: pet.bubble.show_text("💡 祖师爷童锦程情感洞察导师就位！\n单击我听深情金句，双击我自由提问 ✨", 5000))

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
