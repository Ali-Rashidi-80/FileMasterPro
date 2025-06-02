import os, shutil, random
from PyQt5.QtWidgets import QWidget, QLineEdit, QHBoxLayout, QVBoxLayout, QPushButton, QFileDialog, QMessageBox, QTableWidget, QTableWidgetItem, QMenu, QComboBox, QCheckBox
from PyQt5.QtGui import QIcon
from PyQt5.Qt import QApplication, QSystemTrayIcon, QDesktopServices, QUrl

def get_singer(filename):
    base = os.path.basename(filename)
    parts = base.split(" - ")
    return parts[0].strip() if len(parts) > 1 else ""

def is_audio_file(filename):
    audio_extensions = {'.mp3','.wav','.flac','.aac','.ogg','.wma','.m4a'}
    return os.path.splitext(filename)[1].lower() in audio_extensions

def compute_md5(file_path, chunk_size=4096):
    import hashlib
    hash_md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(chunk_size), b""):
                hash_md5.update(chunk)
    except Exception as e:
        print(f"Error computing MD5 for {file_path}: {e}")
        return None
    return hash_md5.hexdigest()

def check_free_space(dest_folder, required_space):
    import shutil
    _, _, free = shutil.disk_usage(dest_folder)
    return free >= required_space

class ShuffleTab(QWidget):
    def __init__(self, status_callback, progress_callback, tray):
        super().__init__()
        self.status_callback = status_callback
        self.progress_callback = progress_callback
        self.tray = tray
        self.source_folder_path = ""
        self.source_files_full = []
        self.shuffled_files = []
        self.init_ui()
    def init_ui(self):
        layout = QVBoxLayout()
        btn_layout = QHBoxLayout()
        self.btn_select_source = QPushButton("انتخاب پوشه منبع")
        self.btn_select_source.setIcon(QIcon("icons/folder.png"))
        self.btn_select_source.clicked.connect(self.select_source_folder)
        btn_layout.addWidget(self.btn_select_source)
        self.btn_shuffle = QPushButton("درهم سازی فایل‌ها")
        self.btn_shuffle.setIcon(QIcon("icons/shuffle.png"))
        self.btn_shuffle.clicked.connect(self.shuffle_files)
        btn_layout.addWidget(self.btn_shuffle)
        self.btn_copy_shuffled = QPushButton("انتقال/کپی فایل‌ها")
        self.btn_copy_shuffled.setIcon(QIcon("icons/copy.png"))
        self.btn_copy_shuffled.clicked.connect(self.copy_shuffled_files)
        btn_layout.addWidget(self.btn_copy_shuffled)
        self.chk_move = QCheckBox("حالت انتقال")
        self.chk_move.setToolTip("تیک بزنید تا فایل‌ها منتقل شوند به جای کپی")
        btn_layout.addWidget(self.chk_move)
        self.combo_mode = QComboBox()
        self.combo_mode.addItems(["بر اساس خواننده"])
        btn_layout.addWidget(self.combo_mode)
        layout.addLayout(btn_layout)
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("جستجو در لیست درهم شده...")
        self.search_bar.textChanged.connect(self.filter_table)
        layout.addWidget(self.search_bar)
        self.table = QTableWidget(0, 1)
        self.table.setHorizontalHeaderLabels(["نام فایل"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setContextMenuPolicy(3)  # Qt.CustomContextMenu
        self.table.customContextMenuRequested.connect(self.open_context_menu)
        layout.addWidget(self.table)
        self.setLayout(layout)
    def filter_table(self, text):
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item:
                self.table.setRowHidden(row, text.lower() not in item.text().lower())
    def select_source_folder(self):
        path = QFileDialog.getExistingDirectory(self, "انتخاب پوشه منبع برای فایل‌ها")
        if path:
            self.source_folder_path = path
            self.list_source_files(path)
    def list_source_files(self, path):
        self.source_files_full = []
        for root, _, files in os.walk(path):
            for file in files:
                file_path = os.path.join(root, file)
                if is_audio_file(file_path):
                    self.source_files_full.append(file_path)
        self.table.setRowCount(0)
        for f in self.source_files_full:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(os.path.basename(f)))
        self.status_callback(f"تعداد {len(self.source_files_full)} فایل صوتی پیدا شدند.")
        self.tray.showMessage("عملیات", "اسکن فایل‌های صوتی تکمیل شد.", QSystemTrayIcon.Information, 3000)
    def shuffle_files(self):
        if not self.source_files_full:
            self.status_callback("ابتدا پوشه منبع را انتخاب کنید.")
            return
        singer_dict = {}
        for f in self.source_files_full:
            singer = get_singer(f)
            singer_dict.setdefault(singer, []).append(f)
        for singer in singer_dict:
            random.shuffle(singer_dict[singer])
        result = []
        last_singer = None
        while any(singer_dict.values()):
            available = [s for s, files in singer_dict.items() if files and s != last_singer]
            if not available:
                available = [s for s, files in singer_dict.items() if files]
            chosen = random.choice(available)
            file_chosen = singer_dict[chosen].pop(0)
            result.append(file_chosen)
            last_singer = chosen
        self.shuffled_files = result
        self.table.setRowCount(0)
        for f in self.shuffled_files:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(os.path.basename(f)))
        self.status_callback("فایل‌ها به‌صورت پیشرفته درهم شدند.")
    def copy_shuffled_files(self):
        if not self.shuffled_files:
            self.status_callback("ابتدا فایل‌ها را درهم کنید.")
            return
        reply = QMessageBox.question(self, "تأیید عملیات", "آیا از عملیات کپی/انتقال مطمئن هستید؟",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes:
            self.status_callback("عملیات لغو شد.")
            return
        dest_folder = QFileDialog.getExistingDirectory(self, "انتخاب پوشه مقصد")
        if not dest_folder:
            return
        required_space = sum(os.path.getsize(f) for f in self.shuffled_files)
        if not check_free_space(dest_folder, required_space):
            self.status_callback("فضای کافی در مقصد وجود ندارد.")
            return
        total = len(self.shuffled_files)
        for idx, f in enumerate(self.shuffled_files, start=1):
            try:
                new_name = os.path.basename(f)
                dest_file = os.path.join(dest_folder, new_name)
                if os.path.exists(dest_file):
                    rep = QMessageBox.question(self, "فایل تکراری", f"فایل {new_name} وجود دارد. جایگزین شود؟",
                                               QMessageBox.Yes | QMessageBox.No)
                    if rep != QMessageBox.Yes:
                        continue
                if self.chk_move.isChecked():
                    shutil.move(f, dest_file)
                else:
                    shutil.copy2(f, dest_file)
                    if compute_md5(f) != compute_md5(dest_file):
                        self.status_callback(f"هش فایل {os.path.basename(f)} مطابقت ندارد.")
            except Exception as e:
                self.status_callback(f"خطا در {os.path.basename(f)}: {e}")
            self.progress_callback(idx, total)
        self.progress_callback(0, total)
        self.status_callback(f"عملیات کپی/انتقال در {dest_folder} تکمیل شد.")
        self.tray.showMessage("عملیات", "انتقال فایل‌ها تکمیل شد.", QSystemTrayIcon.Information, 3000)
    def open_context_menu(self, position):
        index = self.table.indexAt(position)
        if not index.isValid():
            return
        row = index.row()
        item_text = self.table.item(row, 0).text()
        file_path = ""
        for f in self.shuffled_files:
            if os.path.basename(f) == item_text:
                file_path = f
                break
        if file_path:
            menu = QMenu()
            open_action = menu.addAction("باز کردن فایل")
            action = menu.exec_(self.table.viewport().mapToGlobal(position))
            if action == open_action:
                QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))
