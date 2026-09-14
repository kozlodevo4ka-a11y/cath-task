# cath-task — a tiny pyqt6 task manager: todo list, pomodoro timer,
# calendar and a cat mascot that reacts to your progress.

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QListWidget,
    QLineEdit, QHBoxLayout, QComboBox, QDateEdit, QListWidgetItem, QMessageBox,
    QDialog, QFormLayout, QRadioButton, QButtonGroup, QCalendarWidget,
    QScrollArea, QMainWindow,
)
from PyQt6.QtCore import Qt, QDate, QTimer, QTime, QUrl
from PyQt6.QtGui import QPixmap, QColor, QFont, QTextCharFormat
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
import json
import os
import random
import sys


def resource_path(relative_path):
    # works both from source and from a pyinstaller bundle
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.dirname(__file__), relative_path)


TASKS_FILE = "tasks.json"
COMPLETED_TASKS_FILE = "completed_tasks.json"

HAPPY_CAT_IMAGE = resource_path("happy_cat.png")
SAD_CAT_IMAGE = resource_path("sad_cat.png")
HAPPY_BLINK_IMAGE = resource_path("happy_blink.png")
SAD_BLINK_IMAGE = resource_path("sad_blink.png")
SOUND_FILE = resource_path("sound.mp3")

TAGS = ["Study", "Other", "Selfcare", "Hobby", "Work"]
IMPORTANCE_COLORS = {1: "#99FF99", 2: "#FFFF99", 3: "#FF9999"}  # low / medium / high


def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


class WelcomeWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Welcome")
        self.setGeometry(100, 100, 400, 300)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("QWidget { background-color: #2A5D77; border-radius: 10px; }")

        layout = QHBoxLayout()

        self.cat_label = QLabel()
        pixmap = QPixmap(HAPPY_CAT_IMAGE).scaled(150, 150, Qt.AspectRatioMode.KeepAspectRatio)
        self.cat_label.setPixmap(pixmap)
        self.cat_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.cat_label)

        name = os.environ.get("COMPUTERNAME", "friend")
        self.text_label = QLabel(f"Hi, {name}, let's do our best today!")
        self.text_label.setStyleSheet("font-size: 18px; color: #F5F7F6; font-family: Bahnschrift;")
        self.text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.text_label)

        self.setLayout(layout)
        # splash for 5s, then open the main window
        QTimer.singleShot(5000, self.close_and_open_main)

    def close_and_open_main(self):
        self.close()
        self.main_window = TaskTracker()
        self.main_window.show()


class AddTaskDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add task")
        self.setModal(True)
        self.setStyleSheet("""
            QDialog { background-color: #2A5D77; border-radius: 10px; }
            QLineEdit, QComboBox, QDateEdit {
                padding: 5px; border: none; border-radius: 5px;
                background-color: #ECEFED; color: #2A5D77; font-size: 14px;
            }
            QRadioButton { color: #F5F7F6; font-size: 14px; }
            QPushButton {
                background-color: #D8E2DC; color: #2A5D77;
                padding: 5px; border-radius: 5px; font-size: 14px;
            }
            QPushButton:hover { background-color: #A9C7C2; }
            QLabel { color: #F5F7F6; font-size: 14px; }
        """)

        self.layout = QFormLayout(self)

        self.task_input = QLineEdit()
        self.task_input.setPlaceholderText("Enter a task")
        self.layout.addRow("Task:", self.task_input)

        self.date_input = QDateEdit()
        self.date_input.setDate(QDate.currentDate())
        self.layout.addRow("Start date:", self.date_input)

        self.tag_input = QComboBox()
        self.tag_input.addItems(TAGS)
        self.layout.addRow("Tag:", self.tag_input)

        self.importance_group = QButtonGroup()
        self.importance_layout = QHBoxLayout()
        for text, value in (("Low", 1), ("Medium", 2), ("High", 3)):
            rb = QRadioButton(text)
            self.importance_group.addButton(rb, value)
            self.importance_layout.addWidget(rb)
        self.importance_group.button(2).setChecked(True)
        self.layout.addRow("Importance:", self.importance_layout)

        self.repeat_input = QComboBox()
        self.repeat_input.addItems(["No repeat", "Daily", "Weekly", "Monthly"])
        self.layout.addRow("Repeat:", self.repeat_input)

        buttons = QHBoxLayout()
        self.add_button = QPushButton("Add")
        self.cancel_button = QPushButton("Cancel")
        buttons.addWidget(self.add_button)
        buttons.addWidget(self.cancel_button)
        self.layout.addRow(buttons)

        self.add_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

    def get_task_data(self):
        return {
            "name": self.task_input.text().strip(),
            "start_date": self.date_input.date().toString("yyyy-MM-dd"),
            "tag": self.tag_input.currentText(),
            "importance": self.importance_group.checkedId(),
            "repeat": self.repeat_input.currentText(),
            "completed": False,
        }


class DragMixin:
    # drag a frameless window by holding anywhere on it
    def mousePressEvent(self, event):
        self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if getattr(self, "old_pos", None) is not None:
            delta = event.globalPosition().toPoint() - self.old_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPosition().toPoint()


class CalendarWindow(DragMixin, QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Task calendar")
        self.setFixedSize(600, 500)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.old_pos = None

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.setStyleSheet("QMainWindow { background-color: #D8E2DC; border-radius: 10px; }")

        self.layout = QVBoxLayout(self.central_widget)

        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        self.calendar.setStyleSheet("""
            QCalendarWidget { background-color: #ECEFED; border: none; font-family: Arial; }
            QCalendarWidget QToolButton {
                height: 30px; font-size: 14px; color: #2A5D77;
                background-color: #D8E2DC; border: none; border-radius: 5px;
            }
            QCalendarWidget QToolButton:hover { background-color: #2A5D77; color: #F5F7F6; }
            QCalendarWidget QWidget#qt_calendar_navigationbar {
                background-color: #D8E2DC; border-radius: 5px;
            }
            QCalendarWidget QAbstractItemView {
                selection-background-color: #2A5D77; selection-color: #F5F7F6;
            }
        """)
        self.highlight_tasks()
        self.layout.addWidget(self.calendar)

        self.button_panel = QHBoxLayout()
        for btn_text in ("Add task", "Close"):
            btn = QPushButton(btn_text)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #2A5D77; color: #F5F7F6;
                    border-radius: 5px; padding: 5px; font-size: 14px;
                }
                QPushButton:hover { background-color: #1E3A5F; }
            """)
            btn.clicked.connect(self.add_task_for_date if btn_text == "Add task" else self.close)
            self.button_panel.addWidget(btn)
        self.layout.addLayout(self.button_panel)

        self.tasks_scroll = QScrollArea()
        self.tasks_scroll.setWidgetResizable(True)
        self.tasks_scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        self.tasks_container = QWidget()
        self.tasks_layout = QVBoxLayout(self.tasks_container)
        self.tasks_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.tasks_scroll.setWidget(self.tasks_container)
        self.layout.addWidget(self.tasks_scroll)

        self.calendar.selectionChanged.connect(self.load_tasks_for_date)
        self.load_tasks_for_date()

    def highlight_tasks(self):
        # paint every day from a task's start date up to today
        fmt = QTextCharFormat()
        fmt.setBackground(QColor("#A9C7C2"))
        today = QDate.currentDate()
        for task in load_json(TASKS_FILE):
            if task.get("completed", False):
                continue
            day = QDate.fromString(task["start_date"], "yyyy-MM-dd")
            while day <= today:
                self.calendar.setDateTextFormat(day, fmt)
                day = day.addDays(1)

    def add_task_for_date(self):
        selected_date = self.calendar.selectedDate()
        dialog = AddTaskDialog(self)
        dialog.date_input.setDate(selected_date)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            tasks = load_json(TASKS_FILE)
            tasks.append(dialog.get_task_data())
            save_json(TASKS_FILE, tasks)
            self.highlight_tasks()
            self.load_tasks_for_date()

    def load_tasks_for_date(self):
        for i in reversed(range(self.tasks_layout.count())):
            widget = self.tasks_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        selected = self.calendar.selectedDate().toString("yyyy-MM-dd")
        selected_date = QDate.fromString(selected, "yyyy-MM-dd")
        date_tasks = [
            t for t in load_json(TASKS_FILE)
            if not t.get("completed", False)
            and QDate.fromString(t["start_date"], "yyyy-MM-dd") <= selected_date
        ]

        if not date_tasks:
            label = QLabel("No tasks for the selected date")
            label.setStyleSheet("font-size: 14px; color: #2A5D77; padding: 10px;")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tasks_layout.addWidget(label)
            return

        for task in date_tasks:
            row = QWidget()
            row.setStyleSheet("""
                QWidget {
                    background-color: #ECEFED; border: 1px solid #2A5D77;
                    border-radius: 5px; padding: 5px; margin: 2px;
                }
                QWidget:hover { background-color: #D8E2DC; }
            """)
            row_layout = QHBoxLayout(row)

            info = QLabel(f"{task.get('tag', 'No tag')}: {task.get('name', 'Untitled')}")
            info.setStyleSheet("font-size: 14px; color: #2A5D77;")
            row_layout.addWidget(info, stretch=1)

            delete_btn = QPushButton("×")
            delete_btn.setStyleSheet("""
                QPushButton {
                    background-color: #FF9999; color: #F5F7F6; border-radius: 10px;
                    min-width: 20px; max-width: 20px; min-height: 20px; max-height: 20px;
                    font-size: 14px;
                }
                QPushButton:hover { background-color: #FF6666; }
            """)
            delete_btn.clicked.connect(lambda checked, t=task: self.delete_task(t))
            row_layout.addWidget(delete_btn)

            self.tasks_layout.addWidget(row)

    def delete_task(self, task_to_delete):
        tasks = [
            t for t in load_json(TASKS_FILE)
            if t.get("name") != task_to_delete.get("name")
            or t.get("start_date") != task_to_delete.get("start_date")
        ]
        save_json(TASKS_FILE, tasks)
        self.load_tasks_for_date()
        self.highlight_tasks()


class TaskTracker(DragMixin, QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cath-task")
        self.setGeometry(100, 100, 500, 400)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
        )
        self.old_pos = None
        self.current_cat_state = "sad"
        self.compact_mode = False
        self.countdown_seconds = 0
        self.paused_seconds = 0

        self.setStyleSheet("""
            QWidget {
                background-color: #2A5D77; color: #F5F7F6; border-radius: 10px;
            }
            QCheckBox::indicator { width: 20px; height: 20px; }
            QCheckBox::indicator:checked {
                background-color: #1E3A5F; border: 2px solid #F5F7F6;
            }
            QCheckBox::indicator:unchecked {
                background-color: #F5F7F6; border: 2px solid #1E3A5F;
            }
        """)

        button_style = """
            QPushButton {
                background-color: #D8E2DC; color: #2A5D77;
                border-radius: 5px; padding: 5px; font-size: 14px;
            }
            QPushButton:hover { background-color: #A9C7C2; }
        """

        main_layout = QHBoxLayout()

        # left column: task list + controls
        left = QVBoxLayout()

        self.task_list = QListWidget()
        self.task_list.setStyleSheet("""
            QListWidget {
                background-color: #ECEFED; color: #2A5D77; border-radius: 5px;
                padding: 5px; font-family: Courier; font-size: 16px;
            }
            QListWidget::item:selected { background-color: #A9C7C2; color: #2A5D77; }
        """)
        self.task_list.itemChanged.connect(self.task_completed)
        self.task_list.setWordWrap(True)
        left.addWidget(self.task_list)

        self.add_task_button = QPushButton("Add task")
        self.add_task_button.setStyleSheet(button_style)
        self.add_task_button.clicked.connect(self.show_add_task_dialog)
        left.addWidget(self.add_task_button)

        self.completed_button = QPushButton("Completed tasks")
        self.completed_button.setStyleSheet(button_style)
        self.completed_button.clicked.connect(self.show_completed_tasks)
        left.addWidget(self.completed_button)

        timer_layout = QHBoxLayout()
        self.timer_combo = QComboBox()
        self.timer_combo.addItems(["5 min", "10 min", "15 min", "25 min", "1 hour"])
        self.timer_combo.setStyleSheet("""
            QComboBox {
                background-color: #D8E2DC; color: #2A5D77;
                border-radius: 5px; padding: 5px;
            }
            QComboBox::drop-down { border: none; }
        """)
        timer_layout.addWidget(self.timer_combo)

        self.start_timer_button = QPushButton("Start")
        self.start_timer_button.setStyleSheet(button_style)
        self.start_timer_button.clicked.connect(self.start_timer_from_combo)
        timer_layout.addWidget(self.start_timer_button)

        self.stop_timer_button = QPushButton("Stop")
        self.stop_timer_button.setStyleSheet(button_style)
        self.stop_timer_button.clicked.connect(self.stop_timer)
        self.stop_timer_button.setEnabled(False)
        timer_layout.addWidget(self.stop_timer_button)

        self.resume_timer_button = QPushButton("Resume")
        self.resume_timer_button.setStyleSheet(button_style)
        self.resume_timer_button.clicked.connect(self.resume_timer)
        self.resume_timer_button.setEnabled(False)
        timer_layout.addWidget(self.resume_timer_button)

        left.addLayout(timer_layout)

        self.compact_button = QPushButton("Compact window")
        self.compact_button.setStyleSheet(button_style)
        self.compact_button.clicked.connect(self.toggle_compact_mode)
        left.addWidget(self.compact_button)

        main_layout.addLayout(left)

        # right column: top panel, clock, timer, mascot
        right = QVBoxLayout()

        top_panel = QHBoxLayout()
        small_btn = """
            QPushButton {
                background-color: #D8E2DC; color: #2A5D77; border-radius: 5px;
                font-size: 14px; min-width: 30px; max-width: 30px;
                min-height: 30px; max-height: 30px;
            }
            QPushButton:hover { background-color: %s; color: #F5F7F6; }
        """
        self.calendar_button = QPushButton("\U0001F4C5")
        self.calendar_button.setStyleSheet(small_btn % "#2A5D77")
        self.calendar_button.clicked.connect(self.show_calendar)
        top_panel.addWidget(self.calendar_button)

        self.exit_button = QPushButton("X")
        self.exit_button.setStyleSheet(small_btn % "#FF6666")
        self.exit_button.clicked.connect(self.close)
        top_panel.addWidget(self.exit_button)

        right.addLayout(top_panel)

        self.time_label = QLabel()
        self.time_label.setStyleSheet("font-size: 16px; color: #F5F7F6;")
        self.time_label.setFont(QFont("Bahnschrift", 16))
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right.addWidget(self.time_label)

        self.timer_label = QLabel("00:00")
        self.timer_label.setStyleSheet("font-size: 20px; color: #F5F7F6; font-family: Monospace;")
        self.timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right.addWidget(self.timer_label)

        self.cat_label = QLabel()
        self.cat_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right.addWidget(self.cat_label)

        main_layout.addLayout(right)
        self.setLayout(main_layout)

        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(0.5)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)

        self.countdown_timer = QTimer()
        self.countdown_timer.timeout.connect(self.update_countdown)

        self.blink_timer = QTimer()
        self.blink_timer.timeout.connect(self.blink_cat)
        self.start_blink_timer()

        self.load_tasks()
        self.update_time()
        self.update_cat()

    # ----- mascot -----
    def start_blink_timer(self):
        self.blink_timer.start(random.randint(2000, 15000))

    def blink_cat(self):
        img = HAPPY_BLINK_IMAGE if self.current_cat_state == "happy" else SAD_BLINK_IMAGE
        self.cat_label.setPixmap(QPixmap(img).scaled(100, 100, Qt.AspectRatioMode.KeepAspectRatio))
        QTimer.singleShot(200, lambda: self.set_cat_state(self.current_cat_state))
        self.start_blink_timer()

    def set_cat_state(self, state):
        self.current_cat_state = state
        img = HAPPY_CAT_IMAGE if state == "happy" else SAD_CAT_IMAGE
        self.cat_label.setPixmap(QPixmap(img).scaled(100, 100, Qt.AspectRatioMode.KeepAspectRatio))

    def update_cat(self):
        # happy once there's at least one completed task
        self.set_cat_state("happy" if load_json(COMPLETED_TASKS_FILE) else "sad")

    def play_sound(self):
        if os.path.exists(SOUND_FILE):
            self.media_player.setSource(QUrl.fromLocalFile(SOUND_FILE))
            self.media_player.play()

    def show_calendar(self):
        self.calendar_window = CalendarWindow()
        self.calendar_window.show()

    def update_time(self):
        self.time_label.setText(QTime.currentTime().toString("hh:mm"))

    # ----- task list -----
    def load_tasks(self):
        self.group_tasks_by_tag(load_json(TASKS_FILE))

    def group_tasks_by_tag(self, tasks):
        self.task_list.clear()
        today = QDate.currentDate()
        by_tag = {tag: [] for tag in TAGS}
        for task in tasks:
            if task["completed"]:
                continue
            if QDate.fromString(task["start_date"], "yyyy-MM-dd") <= today:
                by_tag.setdefault(task["tag"], []).append(task)

        for tag, items in by_tag.items():
            if not items:
                continue
            header = QListWidgetItem(f"{tag}:")
            header.setFlags(header.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            header.setBackground(QColor("#1E3A5F"))
            header.setForeground(QColor("#F5F7F6"))
            header.setFont(QFont("Courier", 14))
            self.task_list.addItem(header)
            for task in items:
                self.add_task_to_list(task)

    def save_tasks(self):
        # collect what's shown, then merge back so future/other-day tasks survive
        shown = []
        for i in range(self.task_list.count()):
            item = self.task_list.item(i)
            if item.text().endswith(":"):
                continue
            shown.append(item.data(Qt.ItemDataRole.UserRole))
        shown_keys = {(t["name"], t["start_date"]) for t in shown}
        others = [t for t in load_json(TASKS_FILE) if (t["name"], t["start_date"]) not in shown_keys]
        save_json(TASKS_FILE, others + shown)

    def show_add_task_dialog(self):
        dialog = AddTaskDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            tasks = load_json(TASKS_FILE)
            tasks.append(dialog.get_task_data())
            save_json(TASKS_FILE, tasks)
            self.load_tasks()
            self.update_cat()

    def add_task_to_list(self, task):
        if QDate.fromString(task["start_date"], "yyyy-MM-dd") > QDate.currentDate():
            return
        if task["completed"]:
            return
        item = QListWidgetItem(f"{task['name']} ({task['tag']})")
        item.setData(Qt.ItemDataRole.UserRole, task)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        item.setFont(QFont("Courier", 14))
        item.setBackground(QColor(IMPORTANCE_COLORS.get(task["importance"], "#FFFF99")))
        item.setCheckState(Qt.CheckState.Unchecked)
        self.task_list.addItem(item)

    def task_completed(self, item):
        if item.checkState() == Qt.CheckState.Checked:
            task = item.data(Qt.ItemDataRole.UserRole)
            task["completed"] = True
            item.setData(Qt.ItemDataRole.UserRole, task)
            self.save_tasks()
            # small grace period, then move it to the completed file
            QTimer.singleShot(5000, lambda: self.move_to_completed(item))

    def move_to_completed(self, item):
        if not item or self.task_list.row(item) == -1:
            return
        task = item.data(Qt.ItemDataRole.UserRole)
        self.task_list.takeItem(self.task_list.row(item))

        completed = load_json(COMPLETED_TASKS_FILE)
        if task["name"] not in [t["name"] for t in completed]:
            completed.append(task)
            save_json(COMPLETED_TASKS_FILE, completed)

        tasks = [
            t for t in load_json(TASKS_FILE)
            if t["name"] != task["name"] or t["start_date"] != task["start_date"]
        ]
        save_json(TASKS_FILE, tasks)

        self.update_cat()
        self.load_tasks()

    def show_completed_tasks(self):
        completed = load_json(COMPLETED_TASKS_FILE)
        text = "\n".join(f"{t['tag']}: {t['name']}" for t in completed)
        QMessageBox.information(self, "Completed tasks", text or "No completed tasks.")

    def toggle_compact_mode(self):
        self.compact_mode = not self.compact_mode
        for w in (self.add_task_button, self.completed_button, self.timer_combo,
                  self.start_timer_button, self.stop_timer_button, self.resume_timer_button):
            w.setVisible(not self.compact_mode)
        font_size = 12 if self.compact_mode else 16
        self.compact_button.setText("Normal mode" if self.compact_mode else "Compact window")
        self.task_list.setStyleSheet(f"""
            QListWidget {{
                background-color: #ECEFED; color: #2A5D77; border-radius: 5px;
                padding: 5px; font-family: Courier; font-size: {font_size}px;
            }}
        """)
        self.setFixedSize(300, 300) if self.compact_mode else self.setFixedSize(500, 400)

    # ----- pomodoro timer -----
    def start_timer_from_combo(self):
        minutes = {"5 min": 5, "10 min": 10, "15 min": 15, "25 min": 25, "1 hour": 60}
        self.start_timer(minutes[self.timer_combo.currentText()])
        self.stop_timer_button.setEnabled(True)
        self.resume_timer_button.setEnabled(False)

    def start_timer(self, minutes):
        self.countdown_seconds = minutes * 60
        self.countdown_timer.start(1000)
        self.update_countdown()

    def stop_timer(self):
        self.paused_seconds = self.countdown_seconds
        self.countdown_timer.stop()
        self.stop_timer_button.setEnabled(False)
        self.resume_timer_button.setEnabled(True)

    def resume_timer(self):
        self.countdown_seconds = self.paused_seconds
        self.countdown_timer.start(1000)
        self.stop_timer_button.setEnabled(True)
        self.resume_timer_button.setEnabled(False)

    def update_countdown(self):
        if self.countdown_seconds > 0:
            minutes, seconds = divmod(self.countdown_seconds, 60)
            self.timer_label.setText(f"{minutes:02d}:{seconds:02d}")
            self.countdown_seconds -= 1
        else:
            self.countdown_timer.stop()
            self.timer_label.setText("00:00")
            self.play_sound()
            QMessageBox.information(self, "Timer", "Time's up!")
            self.stop_timer_button.setEnabled(False)
            self.resume_timer_button.setEnabled(False)

    def closeEvent(self, event):
        self.save_tasks()
        event.accept()


if __name__ == "__main__":
    app = QApplication([])
    welcome = WelcomeWindow()
    welcome.show()
    app.exec()
