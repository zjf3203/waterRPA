import sys
import os
import time
import json
import pyautogui
import pyperclip
import traceback
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QPushButton, QLabel, QComboBox, QLineEdit, QScrollArea,
                               QFileDialog, QTextEdit, QMessageBox, QFrame)
from PySide6.QtCore import Qt, QThread, Signal, QRect, QPoint
from PySide6.QtGui import QPainter, QPen, QColor, QGuiApplication, QPixmap, QFont, QBrush

# -----------------------------------------------------------------------------
# SmartScreenSnapper 风格截图工具（带放大镜、尺寸显示、右键取消）
# -----------------------------------------------------------------------------
class ScreenshotTool(QWidget):
    captured = Signal(str)  # 截图完成，返回保存路径

    def __init__(self, save_dir='snap_temp'):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.showFullScreen()

        self.save_dir = save_dir
        os.makedirs(save_dir, exist_ok=True)

        self.start = QPoint()
        self.end = QPoint()
        self.is_selecting = False
        self.screen_pix = QGuiApplication.primaryScreen().grabWindow(0)

        self.mag_scale = 2
        self.mag_size = 120
        self.mag_radius = 60

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self.screen_pix)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 70))

        if self.is_selecting and not self.start.isNull() and not self.end.isNull():
            rect = QRect(self.start, self.end).normalized()
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
            painter.fillRect(rect, Qt.transparent)
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
            painter.setPen(QPen(QColor(255, 0, 0), 2))
            painter.drawRect(rect)

            w = rect.width()
            h = rect.height()
            text = f'{w} × {h}'
            painter.setFont(QFont('Microsoft YaHei', 10))
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(rect.bottomRight() + QPoint(5, 15), text)

        cursor = self.mapFromGlobal(QCursor.pos())
        self.draw_magnifier(painter, cursor)

    def draw_magnifier(self, painter, center):
        src_rect = QRect(
            center.x() - self.mag_radius // self.mag_scale,
            center.y() - self.mag_radius // self.mag_scale,
            self.mag_size // self.mag_scale,
            self.mag_size // self.mag_scale
        )
        part = self.screen_pix.copy(src_rect)
        magnified = part.scaled(self.mag_size, self.mag_size, Qt.IgnoreAspectRatio, Qt.FastTransformation)

        painter.setClipRect(center.x() - self.mag_radius, center.y() - self.mag_radius,
                            self.mag_size, self.mag_size)
        painter.drawPixmap(center.x() - self.mag_radius, center.y() - self.mag_radius, magnified)
        painter.setClipping(False)

        painter.setPen(QPen(QColor(255, 255, 255), 1))
        painter.drawEllipse(center, self.mag_radius, self.mag_radius)
        painter.setPen(QPen(QColor(255, 0, 0), 1))
        painter.drawLine(center.x() - self.mag_radius, center.y(),
                         center.x() + self.mag_radius, center.y())
        painter.drawLine(center.x(), center.y() - self.mag_radius,
                         center.x(), center.y() + self.mag_radius)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.start = e.pos()
            self.is_selecting = True
        elif e.button() == Qt.RightButton:
            self.close()

    def mouseMoveEvent(self, e):
        if self.is_selecting:
            self.end = e.pos()
            self.update()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and self.is_selecting:
            self.end = e.pos()
            self.is_selecting = False
            self.capture()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.close()
        elif e.key() in (Qt.Key_Enter, Qt.Key_Return):
            self.capture()

    def capture(self):
        rect = QRect(self.start, self.end).normalized()
        if rect.width() < 3 or rect.height() < 3:
            self.close()
            return

        snap = self.screen_pix.copy(rect)
        filename = os.path.join(self.save_dir, f'snap_{int(time.time())}.png')
        snap.save(filename, 'png', 100)
        self.captured.emit(filename)
        self.close()

# --------------------------
# 核心逻辑
# --------------------------
def mouseClick(clickTimes, lOrR, img, reTry, timeout=60):
    start_time = time.time()
    if reTry == 1:
        while True:
            if timeout and time.time()-start_time > timeout:
                print(f"等待图片 {img} 超时")
                return
            try:
                loc = pyautogui.locateCenterOnScreen(img, confidence=0.9)
                if loc:
                    pyautogui.click(loc.x, loc.y, clicks=clickTimes, interval=0.2, duration=0.2, button=lOrR)
                    break
            except:
                pass
            time.sleep(0.1)
    elif reTry == -1:
        while True:
            if timeout and time.time()-start_time > timeout: return
            try:
                loc = pyautogui.locateCenterOnScreen(img, confidence=0.9)
                if loc: pyautogui.click(loc.x, loc.y, clicks=clickTimes, interval=0.2, duration=0.2, button=lOrR)
            except: pass
            time.sleep(0.1)
    elif reTry > 1:
        i = 1
        while i < reTry+1:
            if timeout and time.time()-start_time > timeout: return
            try:
                loc = pyautogui.locateCenterOnScreen(img, confidence=0.9)
                if loc:
                    pyautogui.click(loc.x, loc.y, clicks=clickTimes, interval=0.2, duration=0.2, button=lOrR)
                    i += 1
            except: pass
            time.sleep(0.1)

def mouseMove(img, reTry, timeout=60):
    start_time = time.time()
    while True:
        if timeout and time.time()-start_time>timeout: return
        try:
            loc = pyautogui.locateCenterOnScreen(img, confidence=0.9)
            if loc:
                pyautogui.moveTo(loc.x, loc.y, duration=0.2)
                break
        except: pass
        time.sleep(0.1)

class RPAEngine:
    def __init__(self):
        self.is_running = False
        self.stop_requested = False
    def stop(self):
        self.stop_requested = True
        self.is_running = False
    def run_tasks(self, tasks, loop_forever=False, callback=None):
        self.is_running = True
        self.stop_requested = False
        try:
            while True:
                for idx, t in enumerate(tasks):
                    if self.stop_requested:
                        if callback: callback("任务已停止")
                        return
                    typ = t.get('type')
                    val = t.get('value')
                    rty = t.get('retry', 1)
                    if callback: callback(f"步骤 {idx+1}: {typ} | {val}")

                    if typ == 1.0:
                        mouseClick(1, 'left', val, rty)
                        if callback: callback(f"左键单击: {val}")
                    elif typ == 2.0:
                        mouseClick(2, 'left', val, rty)
                        if callback: callback(f"左键双击: {val}")
                    elif typ == 3.0:
                        mouseClick(1, 'right', val, rty)
                        if callback: callback(f"右键: {val}")
                    elif typ == 4.0:
                        pyperclip.copy(str(val))
                        pyautogui.hotkey('ctrl','v')
                        time.sleep(0.5)
                        if callback: callback(f"输入: {val}")
                    elif typ == 5.0:
                        time.sleep(float(val))
                        if callback: callback(f"等待 {val}s")
                    elif typ == 6.0:
                        pyautogui.scroll(int(val))
                        if callback: callback(f"滚轮 {val}")
                    elif typ == 7.0:
                        ks = [k.strip() for k in val.lower().split('+')]
                        pyautogui.hotkey(*ks)
                        if callback: callback(f"按键: {val}")
                    elif typ == 8.0:
                        mouseMove(val, rty)
                        if callback: callback(f"悬停: {val}")
                    elif typ == 9.0:
                        d = val
                        if os.path.isdir(d):
                            fn = os.path.join(d, f"shot_{int(time.time())}.png")
                        else:
                            fn = d if d.endswith(('.png','.jpg')) else d+'.png'
                        pyautogui.screenshot(fn)
                        if callback: callback(f"截图保存: {fn}")
                if not loop_forever: break
                time.sleep(0.1)
        except Exception as e:
            if callback: callback(f"异常: {e}")
            traceback.print_exc()
        finally:
            self.is_running = False
            if callback: callback("任务结束")

# --------------------------
# GUI
# --------------------------
CMD_TYPES = {
    "左键单击":1.0,"左键双击":2.0,"右键单击":3.0,"输入文本":4.0,
    "等待(秒)":5.0,"滚轮滑动":6.0,"系统按键":7.0,"鼠标悬停":8.0,"截图保存":9.0
}
CMD_REV = {v:k for k,v in CMD_TYPES.items()}

class Worker(QThread):
    log = Signal(str)
    done = Signal()
    def __init__(self, eng, tasks, loop):
        super().__init__()
        self.eng = eng
        self.tasks = tasks
        self.loop = loop
    def run(self):
        self.eng.run_tasks(self.tasks, self.loop, self.log.emit)
        self.done.emit()

class TaskRow(QFrame):
    def __init__(self, layout, delete_cb):
        super().__init__()
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(5,5,5,5)
        self.del_cb = delete_cb

        self.cb = QComboBox()
        self.cb.addItems(CMD_TYPES.keys())
        self.cb.currentTextChanged.connect(self.on_type)
        self.layout.addWidget(self.cb)

        self.val = QLineEdit()
        self.val.setPlaceholderText("路径/文本/时间")
        self.layout.addWidget(self.val)

        self.file_btn = QPushButton("选择图片")
        self.file_btn.clicked.connect(self.on_file)
        self.layout.addWidget(self.file_btn)

        self.retry = QLineEdit("1")
        self.retry.setPlaceholderText("重试")
        self.retry.setFixedWidth(80)
        self.layout.addWidget(self.retry)

        self.del_btn = QPushButton("X")
        self.del_btn.setStyleSheet("color:red; font-weight:bold;")
        self.del_btn.setFixedWidth(30)
        self.del_btn.clicked.connect(self.on_del)
        self.layout.addWidget(self.del_btn)

        layout.addWidget(self)
        self.on_type(self.cb.currentText())

    def on_type(self, txt):
        t = CMD_TYPES[txt]
        img_types = (1.0,2.0,3.0,8.0)
        if t in img_types:
            self.file_btn.setVisible(1)
            self.file_btn.setText("选择图片")
            self.retry.setVisible(1)
        elif t == 9.0:
            self.file_btn.setVisible(1)
            self.file_btn.setText("选择目录")
            self.retry.setVisible(0)
        else:
            self.file_btn.setVisible(0)
            self.retry.setVisible(0)

    def on_file(self):
        t = CMD_TYPES[self.cb.currentText()]
        if t == 9.0:
            d = QFileDialog.getExistingDirectory()
            if d: self.val.setText(d)
        else:
            f,_ = QFileDialog.getOpenFileName(filter="Images (*.png *.jpg *.bmp)")
            if f: self.val.setText(f)

    def on_del(self):
        self.del_cb(self)

    def get_data(self):
        return {
            "type": CMD_TYPES[self.cb.currentText()],
            "value": self.val.text().strip(),
            "retry": int(self.retry.text()) if self.retry.isVisible() else 1
        }
    def set_data(self, d):
        t = d.get('type')
        if t in CMD_REV:
            self.cb.setCurrentText(CMD_REV[t])
        self.val.setText(str(d.get('value','')))
        self.retry.setText(str(d.get('retry',1)))

class RPAWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RPA工具 - Smart截图")
        self.resize(900,650)
        self.eng = RPAEngine()
        self.worker = None
        self.rows = []
        self.snap_widget = None

        c = QWidget()
        self.setCentralWidget(c)
        main = QVBoxLayout(c)

        # 工具栏
        bar = QHBoxLayout()
        self.add_btn = QPushButton("+ 新增")
        self.add_btn.clicked.connect(self.add_row)
        bar.addWidget(self.add_btn)

        self.save = QPushButton("保存配置")
        self.save.clicked.connect(self.save_cfg)
        bar.addWidget(self.save)

        self.load = QPushButton("导入配置")
        self.load.clicked.connect(self.load_cfg)
        bar.addWidget(self.load)

        # ---------------- 截图按钮 ----------------
        self.snap_btn = QPushButton("📷 Smart截图")
        self.snap_btn.clicked.connect(self.start_snap)
        self.snap_btn.setStyleSheet("font-weight:bold; color:#165DFF;")
        bar.addWidget(self.snap_btn)
        # ------------------------------------------

        bar.addStretch()
        self.loop = QComboBox()
        self.loop.addItems(["执行一次","循环执行"])
        bar.addWidget(self.loop)

        self.start = QPushButton("开始运行")
        self.start.setStyleSheet("background:#4CAF50; color:white")
        self.start.clicked.connect(self.run)
        bar.addWidget(self.start)

        self.stop = QPushButton("停止")
        self.stop.setStyleSheet("background:#f44336; color:white")
        self.stop.clicked.connect(self.do_stop)
        self.stop.setEnabled(0)
        bar.addWidget(self.stop)
        main.addLayout(bar)

        # 任务列表
        scroll = QScrollArea()
        scroll.setWidgetResizable(1)
        self.container = QWidget()
        self.task_layout = QVBoxLayout(self.container)
        self.task_layout.addStretch()
        scroll.setWidget(self.container)
        main.addWidget(scroll)

        # 日志
        main.addWidget(QLabel("日志"))
        self.log = QTextEdit()
        self.log.setReadOnly(1)
        self.log.setMaximumHeight(160)
        main.addWidget(self.log)

        self.add_row()

    def start_snap(self):
        self.showMinimized()
        time.sleep(0.2)
        self.snap_widget = ScreenshotTool()
        self.snap_widget.captured.connect(self.on_snap_captured)
        self.snap_widget.show()
        self.log.append("截图已启动：拖动框选，回车确认，右键/ESC取消")

    def on_snap_captured(self, path):
        for row in reversed(self.rows):
            if row.isVisible() and row.val.text().strip() == '':
                row.val.setText(path)
                self.log.append(f"已填入截图路径：{path}")
                self.showNormal()
                return
        if self.rows:
            self.rows[-1].val.setText(path)
            self.log.append(f"截图已填入最后一行：{path}")
        self.showNormal()

    def add_row(self, data=None):
        self.task_layout.takeAt(self.task_layout.count()-1)
        r = TaskRow(self.task_layout, self.del_row)
        if data: r.set_data(data)
        self.rows.append(r)
        self.task_layout.addStretch()

    def del_row(self, r):
        self.rows.remove(r)
        r.deleteLater()

    def save_cfg(self):
        ts = [r.get_data() for r in self.rows]
        if not ts:
            QMessageBox.warning(self,"","无任务")
            return
        fn,_ = QFileDialog.getSaveFileName(filter="JSON (*.json)")
        if fn:
            with open(fn,'w',encoding='utf-8') as f:
                json.dump(ts,f,indent=4,ensure_ascii=False)
            QMessageBox.information(self,"","保存成功")

    def load_cfg(self):
        fn,_ = QFileDialog.getOpenFileName(filter="JSON (*.json)")
        if not fn: return
        try:
            with open(fn,encoding='utf-8') as f:
                ts = json.load(f)
            for r in self.rows: r.deleteLater()
            self.rows.clear()
            for t in ts: self.add_row(t)
            QMessageBox.information(self,"","导入成功")
        except:
            QMessageBox.critical(self,"","导入失败")

    def run(self):
        ts = []
        for r in self.rows:
            d = r.get_data()
            if not d['value']:
                QMessageBox.warning(self,"","存在空参数")
                return
            ts.append(d)
        if not ts:
            QMessageBox.warning(self,"","无任务")
            return
        self.log.clear()
        self.log.append("开始运行")
        self.start.setEnabled(0)
        self.stop.setEnabled(1)
        self.add_btn.setEnabled(0)
        lp = self.loop.currentText()=="循环执行"
        self.worker = Worker(self.eng, ts, lp)
        self.worker.log.connect(self.log.append)
        self.worker.done.connect(self.on_done)
        self.worker.start()
        self.showMinimized()

    def do_stop(self):
        self.eng.stop()
        self.log.append("正在停止")

    def on_done(self):
        self.start.setEnabled(1)
        self.stop.setEnabled(0)
        self.add_btn.setEnabled(1)
        self.log.append("运行结束")
        self.showNormal()
        self.activateWindow()

def main():
    app = QApplication(sys.argv)
    w = RPAWindow()
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
