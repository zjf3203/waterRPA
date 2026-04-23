import sys
import os
import time
import json
import pyautogui
import pyperclip
import traceback
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QComboBox, QLineEdit, QScrollArea,
    QFileDialog, QTextEdit, QMessageBox, QFrame
)
from PySide6.QtCore import Qt, QThread, Signal, QPoint, QRect
from PySide6.QtGui import QPainter, QPen, QColor, QGuiApplication, QPixmap

# --------------------------
# 核心逻辑 (原 waterRPA.py)
# --------------------------

def mouseClick(clickTimes, lOrR, img, reTry, timeout=60):
    start_time = time.time()
    if reTry == 1:
        while True:
            if timeout and time.time() - start_time > timeout:
                print(f"等待图片 {img} 超时")
                return
            try:
                location = pyautogui.locateCenterOnScreen(img, confidence=0.9)
                if location:
                    pyautogui.click(location.x, location.y, clicks=clickTimes, interval=0.2, duration=0.2, button=lOrR)
                    break
            except:
                pass
            time.sleep(0.1)
    elif reTry == -1:
        while True:
            if timeout and time.time() - start_time > timeout:
                return
            try:
                location = pyautogui.locateCenterOnScreen(img, confidence=0.9)
                if location:
                    pyautogui.click(location.x, location.y, clicks=clickTimes, interval=0.2, duration=0.2, button=lOrR)
            except:
                pass
            time.sleep(0.1)
    elif reTry > 1:
        i = 1
        while i < reTry + 1:
            if timeout and time.time() - start_time > timeout:
                return
            try:
                location = pyautogui.locateCenterOnScreen(img, confidence=0.9)
                if location:
                    pyautogui.click(location.x, location.y, clicks=clickTimes, interval=0.2, duration=0.2, button=lOrR)
                    i += 1
            except:
                pass
            time.sleep(0.1)

def mouseMove(img, reTry, timeout=60):
    start_time = time.time()
    while True:
        if timeout and time.time() - start_time > timeout:
            return
        try:
            location = pyautogui.locateCenterOnScreen(img, confidence=0.9)
            if location:
                pyautogui.moveTo(location.x, location.y, duration=0.2)
                break
        except:
            pass
        time.sleep(0.1)

class RPAEngine:
    def __init__(self):
        self.is_running = False
        self.stop_requested = False
    def stop(self):
        self.stop_requested = True
        self.is_running = False
    def run_tasks(self, tasks, loop_forever=False, callback_msg=None):
        self.is_running = True
        self.stop_requested = False
        try:
            while True:
                for idx, task in enumerate(tasks):
                    if self.stop_requested:
                        callback_msg("任务已停止")
                        return
                    cmd_type = task.get("type")
                    cmd_value = task.get("value")
                    retry = task.get("retry", 1)
                    if callback_msg:
                        callback_msg(f"步骤 {idx+1}: {cmd_type} | {cmd_value}")
                    if cmd_type == 1.0:
                        mouseClick(1, "left", cmd_value, retry)
                        callback_msg(f"单击左键: {cmd_value}")
                    elif cmd_type == 2.0:
                        mouseClick(2, "left", cmd_value, retry)
                        callback_msg(f"双击左键: {cmd_value}")
                    elif cmd_type == 3.0:
                        mouseClick(1, "right", cmd_value, retry)
                        callback_msg(f"右键: {cmd_value}")
                    elif cmd_type == 4.0:
                        pyperclip.copy(str(cmd_value))
                        pyautogui.hotkey('ctrl', 'v')
                        time.sleep(0.5)
                        callback_msg(f"输入文本: {cmd_value}")
                    elif cmd_type == 5.0:
                        time.sleep(float(cmd_value))
                        callback_msg(f"等待 {cmd_value} 秒")
                    elif cmd_type == 6.0:
                        pyautogui.scroll(int(cmd_value))
                        callback_msg(f"滚轮: {cmd_value}")
                    elif cmd_type == 7.0:
                        keys = [k.strip() for k in str(cmd_value).lower().split('+')]
                        pyautogui.hotkey(*keys)
                        callback_msg(f"按键: {cmd_value}")
                    elif cmd_type == 8.0:
                        mouseMove(cmd_value, retry)
                        callback_msg(f"悬停: {cmd_value}")
                    elif cmd_type == 9.0:
                        path = str(cmd_value)
                        if os.path.isdir(path):
                            fn = os.path.join(path, f"screen_{time.strftime('%Y%m%d_%H%M%S')}.png")
                        else:
                            fn = path if path.endswith(('.png','.jpg')) else path+'.png'
                        pyautogui.screenshot(fn)
                        callback_msg(f"截图保存: {fn}")
                if not loop_forever:
                    break
                time.sleep(0.1)
        except Exception as e:
            if callback_msg:
                callback_msg(f"错误: {e}")
            traceback.print_exc()
        finally:
            self.is_running = False
            if callback_msg:
                callback_msg("任务结束")

# --------------------------
# 截图选区窗口（微信式）
# --------------------------
class SnipWindow(QWidget):
    def __init__(self, full_pix):
        super().__init__()
        self.full_pix = full_pix
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.showFullScreen()
        self.setCursor(Qt.CrossCursor)
        self.start = QPoint()
        self.end = QPoint()
        self.painter = QPainter()
    def paintEvent(self, e):
        self.painter.begin(self)
        self.painter.drawPixmap(0, 0, self.full_pix)
        self.painter.fillRect(self.rect(), QColor(0,0,0,120))
        if not self.start.isNull() and not self.end.isNull():
            rect = QRect(self.start, self.end).normalized()
            self.painter.setCompositionMode(self.painter.CompositionMode_Clear)
            self.painter.fillRect(rect, Qt.transparent)
            self.painter.setCompositionMode(self.painter.CompositionMode_SourceOver)
            self.painter.setPen(QPen(QColor(0,255,0), 2))
            self.painter.drawRect(rect)
        self.painter.end()
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.start = e.globalPos()
            self.end = e.globalPos()
            self.update()
    def mouseMoveEvent(self, e):
        if not self.start.isNull():
            self.end = e.globalPos()
            self.update()
    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.end = e.globalPos()
            rect = QRect(self.start, self.end).normalized()
            if rect.width() > 5 and rect.height() > 5:
                self.crop_and_save(rect)
            self.close()
    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.close()
    def crop_and_save(self, rect):
        save_dir = "screenshots"
        os.makedirs(save_dir, exist_ok=True)
        fn = f"snip_{int(time.time())}.png"
        path = os.path.join(save_dir, fn)
        cropped = self.full_pix.copy(rect)
        cropped.save(path, "png")
        QMessageBox.information(None, "截图成功", f"已保存：\n{path}")

# --------------------------
# GUI 界面
# --------------------------
CMD_TYPES = {
    "左键单击":1.0,"左键双击":2.0,"右键单击":3.0,"输入文本":4.0,
    "等待(秒)":5.0,"滚轮滑动":6.0,"系统按键":7.0,"鼠标悬停":8.0,"截图保存":9.0
}
CMD_TYPES_REV = {v:k for k,v in CMD_TYPES.items()}

class WorkerThread(QThread):
    log_signal = Signal(str)
    finished_signal = Signal()
    def __init__(self, engine, tasks, loop):
        super().__init__()
        self.engine = engine
        self.tasks = tasks
        self.loop = loop
    def run(self):
        self.engine.run_tasks(self.tasks, self.loop, self.log)
        self.finished_signal.emit()
    def log(self, msg):
        self.log_signal.emit(msg)

class TaskRow(QFrame):
    def __init__(self, parent_layout, delete_callback):
        super().__init__()
        self.setFrameShape(QFrame.StyledPanel)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5,5,5,5)
        self.type_combo = QComboBox()
        self.type_combo.addItems(CMD_TYPES.keys())
        self.type_combo.currentTextChanged.connect(self.on_change)
        self.value_input = QLineEdit()
        self.file_btn = QPushButton("选择图片")
        self.retry_input = QLineEdit("1")
        self.retry_input.setFixedWidth(100)
        self.del_btn = QPushButton("X")
        self.del_btn.setStyleSheet("color:red")
        self.del_btn.clicked.connect(lambda: delete_callback(self))
        layout.addWidget(self.type_combo)
        layout.addWidget(self.value_input)
        layout.addWidget(self.file_btn)
        layout.addWidget(self.retry_input)
        layout.addWidget(self.del_btn)
        parent_layout.addWidget(self)
        self.on_change(self.type_combo.currentText())
    def on_change(self, text):
        t = CMD_TYPES[text]
        show_file = t in (1,2,3,8,9)
        show_retry = t in (1,2,3,8)
        self.file_btn.setVisible(show_file)
        self.retry_input.setVisible(show_retry)
        if t in (1,2,3,8):
            self.file_btn.setText("选择图片")
            self.value_input.setPlaceholderText("图片路径")
        elif t == 4:
            self.value_input.setPlaceholderText("输入文本")
        elif t == 5:
            self.value_input.setPlaceholderText("秒数")
        elif t == 6:
            self.value_input.setPlaceholderText("正负数字")
        elif t == 7:
            self.value_input.setPlaceholderText("ctrl+c,alt+tab")
        elif t == 9:
            self.file_btn.setText("选择文件夹")
            self.value_input.setPlaceholderText("保存目录")
    def set_data(self, d):
        t = d.get("type")
        if t in CMD_TYPES_REV:
            self.type_combo.setCurrentText(CMD_TYPES_REV[t])
        self.value_input.setText(str(d.get("value","")))
        self.retry_input.setText(str(d.get("retry","1")))
    def get_data(self):
        return {
            "type": CMD_TYPES[self.type_combo.currentText()],
            "value": self.value_input.text().strip(),
            "retry": int(self.retry_input.text().strip()) if self.retry_input.isVisible() else 1
        }
    def select_file(self):
        pass

class RPAWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("不高兴就喝水 RPA 配置工具")
        self.resize(800,600)
        self.engine = RPAEngine()
        self.worker = None
        self.rows = []
        w = QWidget()
        self.setCentralWidget(w)
        main_layout = QVBoxLayout(w)
        top_bar = QHBoxLayout()
        self.add_btn = QPushButton("+ 新增指令")
        self.add_btn.clicked.connect(self.add_row)
        self.save_btn = QPushButton("保存配置")
        self.save_btn.clicked.connect(self.save_config)
        self.load_btn = QPushButton("导入配置")
        self.load_btn.clicked.connect(self.load_config)

        # ========== 区域截图按钮（真正微信式） ==========
        self.snip_btn = QPushButton("区域截图")
        self.snip_btn.setStyleSheet("background:#FF9800;color:white")
        self.snip_btn.clicked.connect(self.start_snip)
        # ==============================================

        self.loop_sel = QComboBox()
        self.loop_sel.addItems(["执行一次","循环执行"])
        self.start_btn = QPushButton("开始运行")
        self.start_btn.setStyleSheet("background:#4CAF50;color:white")
        self.start_btn.clicked.connect(self.start_task)
        self.stop_btn = QPushButton("停止")
        self.stop_btn.setStyleSheet("background:#f44333;color:white")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_task)
        top_bar.addWidget(self.add_btn)
        top_bar.addWidget(self.save_btn)
        top_bar.addWidget(self.load_btn)
        top_bar.addWidget(self.snip_btn)
        top_bar.addStretch()
        top_bar.addWidget(self.loop_sel)
        top_bar.addWidget(self.start_btn)
        top_bar.addWidget(self.stop_btn)
        main_layout.addLayout(top_bar)
        self.scroll = QScrollArea()
        self.content = QWidget()
        self.layout = QVBoxLayout(self.content)
        self.layout.addStretch()
        self.scroll.setWidget(self.content)
        self.scroll.setWidgetResizable(True)
        main_layout.addWidget(self.scroll)
        self.log_label = QLabel("运行日志:")
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setMaximumHeight(150)
        main_layout.addWidget(self.log_label)
        main_layout.addWidget(self.log_area)
        self.add_row()

    def start_snip(self):
        self.showMinimized()
        time.sleep(0.2)
        screen = QGuiApplication.primaryScreen()
        full = screen.grabWindow(0)
        self.snip_win = SnipWindow(full)
        self.snip_win.show()

    def add_row(self, d=None):
        self.layout.takeAt(self.layout.count()-1)
        row = TaskRow(self.layout, self.delete_row)
        if d:
            row.set_data(d)
        self.rows.append(row)
        self.layout.addStretch()
    def delete_row(self, row):
        self.rows.remove(row)
        row.deleteLater()
    def save_config(self):
        tasks = [r.get_data() for r in self.rows]
        if not tasks:
            QMessageBox.warning(self,"提示","无任务")
            return
        fn, _ = QFileDialog.getSaveFileName(self,"保存","","JSON (*.json)")
        if fn:
            with open(fn,"w",encoding="utf-8") as f:
                json.dump(tasks,f,indent=4,ensure_ascii=False)
            QMessageBox.information(self,"成功","配置已保存")
    def load_config(self):
        fn, _ = QFileDialog.getOpenFileName(self,"导入","","JSON (*.json)")
        if not fn:
            return
        try:
            with open(fn,encoding="utf-8") as f:
                tasks = json.load(f)
            for r in self.rows:
                r.deleteLater()
            self.rows.clear()
            for t in tasks:
                self.add_row(t)
            QMessageBox.information(self,"成功",f"导入 {len(tasks)} 条")
        except:
            QMessageBox.critical(self,"失败","格式错误")
    def start_task(self):
        tasks = []
        for r in self.rows:
            d = r.get_data()
            if not d["value"]:
                QMessageBox.warning(self,"提示","有空参数")
                return
            tasks.append(d)
        if not tasks:
            QMessageBox.warning(self,"提示","至少一条")
            return
        self.log_area.clear()
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.add_btn.setEnabled(False)
        loop = self.loop_sel.currentText() == "循环执行"
        self.worker = WorkerThread(self.engine, tasks, loop)
        self.worker.log_signal.connect(self.log)
        self.worker.finished_signal.connect(self.on_finish)
        self.worker.start()
        self.showMinimized()
    def stop_task(self):
        self.engine.stop()
        self.log("正在停止...")
    def on_finish(self):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.add_btn.setEnabled(True)
        self.log("任务已结束")
        self.showNormal()
    def log(self, msg):
        self.log_area.append(msg)
    def closeEvent(self,e):
        if self.worker and self.worker.isRunning():
            self.engine.stop()
            self.worker.quit()
            self.worker.wait()
        e.accept()

def main():
    app = QApplication(sys.argv)
    win = RPAWindow()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
