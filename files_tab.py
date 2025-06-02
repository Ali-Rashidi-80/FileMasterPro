import os
import math
import shutil
import mimetypes
from datetime import datetime
from PyQt5.QtWidgets import (
    QWidget, QLineEdit, QHBoxLayout, QVBoxLayout, QPushButton, QFileDialog,
    QTableWidget, QTableWidgetItem, QMenu, QComboBox, QGroupBox, QLabel,
    QStatusBar, QGridLayout, QDialog, QTextEdit, QMessageBox, QInputDialog,
    QDialogButtonBox, QFormLayout, QRadioButton, QCheckBox, QProgressBar
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QThread, QObject, QMutex
from PyQt5.QtGui import QFont
from PyQt5.Qt import QApplication, QSystemTrayIcon, QDesktopServices, QUrl
import time

def get_file_category(filename):
    if not filename or not os.path.exists(filename):
        return 'سایر'
    mime_type, _ = mimetypes.guess_type(filename, strict=False)
    extension = os.path.splitext(filename)[1].lower()
    if not mime_type:
        extension_map = {
            '.txt': 'متنی', '.pdf': 'متنی', '.doc': 'متنی', '.docx': 'متنی', '.rtf': 'متنی',
            '.jpg': 'تصویری', '.jpeg': 'تصویری', '.png': 'تصویری', '.gif': 'تصویری', '.bmp': 'تصویری',
            '.mp3': 'صوتی', '.wav': 'صوتی', '.flac': 'صوتی', '.aac': 'صوتی', '.ogg': 'صوتی',
            '.mp4': 'ویدیویی', '.mkv': 'ویدیویی', '.avi': 'ویدیویی', '.mov': 'ویدیویی', '.wmv': 'ویدیویی',
            '.zip': 'آرشیو', '.rar': 'آرشیو', '.7z': 'آرشیو', '.tar': 'آرشیو', '.gz': 'آرشیو',
            '.exe': 'اجرایی', '.msi': 'اجرایی',
            '.sql': 'پایگاه داده', '.db': 'پایگاه داده', '.sqlite': 'پایگاه داده',
            '.py': 'کد منبع', '.java': 'کد منبع', '.cpp': 'کد منبع', '.js': 'کد منبع', '.html': 'کد منبع',
            '.xls': 'صفحه گسترده', '.xlsx': 'صفحه گسترده', '.csv': 'صفحه گسترده',
            '.ppt': 'ارائه', '.pptx': 'ارائه'
        }
        return extension_map.get(extension, 'سایر')
    if mime_type.startswith('audio'):
        return 'صوتی'
    elif mime_type.startswith('image'):
        return 'تصویری'
    elif mime_type.startswith('video'):
        return 'ویدیویی'
    elif mime_type.startswith('text') or mime_type in [
        'application/pdf', 'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/rtf'
    ]:
        return 'متنی'
    elif mime_type.startswith('application') or mime_type.startswith('multipart'):
        if mime_type in ['application/zip', 'application/x-rar-compressed', 'application/x-7z-compressed',
                         'application/x-tar', 'application/gzip', 'application/x-bzip2']:
            return 'آرشیو'
        elif mime_type in ['application/x-msdownload', 'application/x-msi']:
            return 'اجرایی'
        elif mime_type in ['application/sql', 'application/x-sqlite3', 'application/vnd.sqlite3', 'application/x-dbf']:
            return 'پایگاه داده'
        elif mime_type in ['application/x-python-code', 'text/x-python', 'text/x-java-source',
                           'text/x-c', 'text/x-c++', 'application/javascript', 'text/html']:
            return 'کد منبع'
        elif mime_type in ['application/vnd.ms-excel',
                           'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'text/csv']:
            return 'صفحه گسترده'
        elif mime_type in ['application/vnd.ms-powerpoint',
                           'application/vnd.openxmlformats-officedocument.presentationml.presentation']:
            return 'ارائه'
        elif mime_type == 'application/json' or mime_type in ['application/xml', 'text/xml']:
            return 'داده'
    return 'سایر'

def format_size(size_bytes):
    if size_bytes == 0:
        return "0 بایت"
    size_name = ("بایت", "کیلوبایت", "مگابایت", "گیگابایت")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"

def get_size_category(size_bytes):
    if size_bytes < 1024 * 1024:
        return 'کوچک'
    elif size_bytes < 10 * 1024 * 1024:
        return 'متوسط'
    else:
        return 'بزرگ'

def get_time_category(mod_time):
    now = datetime.now().timestamp()
    one_month = 30 * 24 * 3600
    six_months = 6 * one_month
    if now - mod_time < one_month:
        return 'اخیر'
    elif now - mod_time < six_months:
        return 'متوسط'
    else:
        return 'قدیمی'

class FileScanner(QObject):
    progress = pyqtSignal(int, int)  # جاری, کل
    finished = pyqtSignal(list)
    message = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.mutex = QMutex()
        self.stop_flag = False

    def count_files(self, path):
        total_files = 0
        for root, _, files in os.walk(path):
            total_files += len(files)
            QApplication.processEvents()
        return total_files

    def scan(self, path):
        self.mutex.lock()
        self.stop_flag = False
        self.mutex.unlock()

        total_files = self.count_files(path)
        self.message.emit(f"تعداد کل فایل‌ها: {total_files}")
        file_list = []
        scanned_files = 0

        for root, _, files in os.walk(path):
            self.mutex.lock()
            if self.stop_flag:
                self.mutex.unlock()
                break
            self.mutex.unlock()

            for file in files:
                self.mutex.lock()
                if self.stop_flag:
                    self.mutex.unlock()
                    break
                self.mutex.unlock()

                full_path = os.path.join(root, file)
                try:
                    size = os.path.getsize(full_path)
                    mod_time = os.path.getmtime(full_path)
                    file_list.append((full_path, size, mod_time))
                except Exception:
                    continue
                scanned_files += 1
                self.progress.emit(scanned_files, total_files)
                QApplication.processEvents()
                time.sleep(0.001)

        self.mutex.lock()
        if not self.stop_flag:
            self.finished.emit(file_list)
            self.message.emit("فهرست فایل‌ها به‌روزرسانی شد.")
        else:
            self.message.emit("اسکن متوقف شد.")
        self.mutex.unlock()

    def stop(self):
        self.mutex.lock()
        self.stop_flag = True
        self.mutex.unlock()

class OperationDialog(QDialog):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedSize(400, 150)
        layout = QVBoxLayout()
        self.label = QLabel("در حال انجام عملیات...")
        layout.addWidget(self.label)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        layout.addWidget(self.progress_bar)
        self.cancel_button = QPushButton("انصراف")
        self.cancel_button.clicked.connect(self.reject)
        layout.addWidget(self.cancel_button)
        self.setLayout(layout)

    def update_progress(self, current, total):
        percentage = int((current / total) * 100) if total > 0 else 0
        self.progress_bar.setValue(percentage)
        self.label.setText(f"فایل‌های اسکن‌شده: {current} از {total}")

class FilesTab(QWidget):
    updateCount = pyqtSignal(int)

    def __init__(self, status_callback, progress_callback, tray):
        super().__init__()
        self.status_callback = status_callback
        self.progress_callback = progress_callback
        self.tray = tray
        self.current_path = ""
        self.file_list = []
        self.sort_column = 0
        self.sort_order = Qt.AscendingOrder
        self.custom_categories = {}
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        self.setStyleSheet("""
            QWidget { font-family: 'Arial', sans-serif; font-size: 14px; background-color: #f0f4f8; color: #333333; }
            QLineEdit { padding: 12px; border-radius: 8px; border: 1px solid #cccccc; background-color: #ffffff; }
            QComboBox { padding: 12px; border-radius: 8px; border: 1px solid #cccccc; background-color: #ffffff; }
            QPushButton { padding: 12px 24px; border-radius: 8px; background-color: #007BFF; color: white; font-weight: bold; border: none; }
            QGroupBox { border: 1px solid #dddddd; border-radius: 8px; padding: 15px; background-color: #ffffff; }
            QTableWidget { border: 1px solid #dddddd; border-radius: 8px; background-color: #ffffff; font-size: 14px; }
            QHeaderView::section { background-color: #f5f5f5; padding: 10px; border: 1px solid #dddddd; font-size: 14px; font-weight: bold; }
            QStatusBar { background-color: #ffffff; border-top: 1px solid #dddddd; padding: 8px; }
        """)
        self.setLayoutDirection(Qt.RightToLeft)

        title_label = QLabel("مدیریت حرفه‌ای فایل‌ها")
        title_label.setFont(QFont("Arial", 24, QFont.Bold))
        main_layout.addWidget(title_label)

        search_group = QGroupBox("جستجو و دسته‌بندی")
        search_layout = QGridLayout()
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("جستجوی فایل‌ها...")
        self.search_bar.textChanged.connect(self.filter_table)
        search_layout.addWidget(QLabel("جستجو:"), 0, 0)
        search_layout.addWidget(self.search_bar, 0, 1)
        self.categoryCombo = QComboBox()
        self.categoryCombo.addItems([
            "همه فایل‌ها", "فایل‌های صوتی", "فایل‌های تصویری", "فایل‌های متنی", "فایل‌های ویدیویی", "سایر فایل‌ها",
            "کوچک (<1MB)", "متوسط (1-10MB)", "بزرگ (>10MB)",
            "اخیر (<1 ماه)", "متوسط (1-6 ماه)", "قدیمی (>6 ماه)", "دسته‌بندی سفارشی"
        ])
        self.categoryCombo.currentTextChanged.connect(self.handle_category_change)
        search_layout.addWidget(QLabel("دسته‌بندی:"), 1, 0)
        search_layout.addWidget(self.categoryCombo, 1, 1)
        search_group.setLayout(search_layout)
        main_layout.addWidget(search_group)

        buttons_layout = QHBoxLayout()
        self.btn_select_dir = QPushButton("انتخاب پوشه")
        self.btn_select_dir.clicked.connect(self.open_select_directory_dialog)
        buttons_layout.addWidget(self.btn_select_dir)
        self.btn_select_all = QPushButton("انتخاب/لغو همه")
        self.btn_select_all.clicked.connect(self.toggle_select_all)
        buttons_layout.addWidget(self.btn_select_all)
        self.btn_file_ops = QPushButton("اقدامات فایل")
        self.btn_file_ops.clicked.connect(self.open_file_operations_dialog)
        buttons_layout.addWidget(self.btn_file_ops)
        self.btn_sort_settings = QPushButton("مرتب‌سازی")
        self.btn_sort_settings.clicked.connect(self.open_sort_settings_dialog)
        buttons_layout.addWidget(self.btn_sort_settings)
        main_layout.addLayout(buttons_layout)

        table_group = QGroupBox("فهرست فایل‌ها")
        table_layout = QVBoxLayout()
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["انتخاب", "نام فایل", "اندازه", "دسته‌بندی"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionMode(QTableWidget.ExtendedSelection)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.open_context_menu)
        self.table.horizontalHeader().sectionClicked.connect(self.sort_table)
        table_layout.addWidget(self.table)
        table_group.setLayout(table_layout)
        main_layout.addWidget(table_group)

        self.status_bar = QStatusBar()
        self.status_bar.showMessage("لطفاً یک پوشه برای اسکن انتخاب کنید.", 5000)
        main_layout.addWidget(self.status_bar)
        self.setLayout(main_layout)

    def open_select_directory_dialog(self):
        path = QFileDialog.getExistingDirectory(self, "انتخاب پوشه برای اسکن")
        if path:
            confirm = QMessageBox.question(self, "تأیید انتخاب", f"آیا می‌خواهید پوشه {path} را اسکن کنید؟", QMessageBox.Yes | QMessageBox.No)
            if confirm == QMessageBox.Yes:
                self.current_path = path
                self.start_scan(path)

    def start_scan(self, path):
        dialog = OperationDialog("اسکن پوشه", self)
        self.scanner = FileScanner()
        self.thread = QThread()
        self.scanner.moveToThread(self.thread)
        self.thread.started.connect(lambda: self.scanner.scan(path))
        self.scanner.progress.connect(dialog.update_progress)
        self.scanner.finished.connect(lambda file_list: self.on_scan_finished(file_list, dialog))
        self.scanner.message.connect(self.on_scan_message)
        dialog.rejected.connect(self.scanner.stop)
        self.thread.start()
        dialog.exec_()
        self.thread.quit()
        self.thread.wait()

    def on_scan_finished(self, file_list, dialog):
        self.file_list = file_list
        self.populate_table_async()
        self.updateCount.emit(len(self.file_list))
        dialog.accept()

    def on_scan_message(self, msg):
        self.status_callback(msg)
        self.status_bar.showMessage(msg, 5000)

    def populate_table_async(self):
        self.table.setRowCount(0)
        self.populate_timer = QTimer()
        self.populate_timer.setInterval(0)  # هر چه سریع‌تر
        self.populate_timer.timeout.connect(self.add_table_rows)
        self.populate_index = 0
        self.populate_timer.start()

    def add_table_rows(self):
        batch_size = 100  # تعداد ردیف‌ها در هر بار
        for _ in range(batch_size):
            if self.populate_index >= len(self.file_list):
                self.populate_timer.stop()
                self.filter_table()
                return
            file_path, size, mod_time = self.file_list[self.populate_index]
            row = self.table.rowCount()
            self.table.insertRow(row)
            check_box = QCheckBox()
            self.table.setCellWidget(row, 0, check_box)
            self.table.setItem(row, 1, QTableWidgetItem(os.path.basename(file_path)))
            self.table.setItem(row, 2, QTableWidgetItem(format_size(size)))
            self.table.setItem(row, 3, QTableWidgetItem(get_file_category(file_path)))
            self.table.item(row, 2).setData(Qt.UserRole, size)
            self.table.item(row, 2).setData(Qt.UserRole + 1, mod_time)
            self.populate_index += 1
        QApplication.processEvents()

    def filter_table(self):
        text = self.search_bar.text().lower()
        category = self.categoryCombo.currentText()
        for row in range(self.table.rowCount()):
            name_item = self.table.item(row, 1)
            size_item = self.table.item(row, 2)
            category_item = self.table.item(row, 3)
            size = size_item.data(Qt.UserRole) if size_item else 0
            mod_time = size_item.data(Qt.UserRole + 1) if size_item else 0
            hidden = False
            if text and name_item and text not in name_item.text().lower():
                hidden = True
            if category != "همه فایل‌ها":
                if category == "فایل‌های صوتی" and category_item.text() != "صوتی":
                    hidden = True
                elif category == "فایل‌های تصویری" and category_item.text() != "تصویری":
                    hidden = True
                elif category == "فایل‌های متنی" and category_item.text() != "متنی":
                    hidden = True
                elif category == "فایل‌های ویدیویی" and category_item.text() != "ویدیویی":
                    hidden = True
                elif category == "سایر فایل‌ها" and category_item.text() != "سایر":
                    hidden = True
                elif category == "کوچک (<1MB)" and get_size_category(size) != "کوچک":
                    hidden = True
                elif category == "متوسط (1-10MB)" and get_size_category(size) != "متوسط":
                    hidden = True
                elif category == "بزرگ (>10MB)" and get_size_category(size) != "بزرگ":
                    hidden = True
                elif category == "اخیر (<1 ماه)" and get_time_category(mod_time) != "اخیر":
                    hidden = True
                elif category == "متوسط (1-6 ماه)" and get_time_category(mod_time) != "متوسط":
                    hidden = True
                elif category == "قدیمی (>6 ماه)" and get_time_category(mod_time) != "قدیمی":
                    hidden = True
                elif category in self.custom_categories:
                    ext = os.path.splitext(self.file_list[row][0])[1].lower()
                    if ext not in self.custom_categories[category]:
                        hidden = True
            self.table.setRowHidden(row, hidden)

    def toggle_select_all(self):
        all_checked = all(self.table.cellWidget(row, 0).isChecked() for row in range(self.table.rowCount()) if not self.table.isRowHidden(row))
        for row in range(self.table.rowCount()):
            if not self.table.isRowHidden(row):
                self.table.cellWidget(row, 0).setChecked(not all_checked)
        self.status_bar.showMessage("وضعیت انتخاب فایل‌ها تغییر کرد.", 5000)

    def open_file_operations_dialog(self):
        dialog = FileOperationsDialog(self)
        dialog.btn_copy_names.clicked.connect(self.copy_files)
        dialog.btn_save_list.clicked.connect(self.save_files_to_file)
        dialog.btn_delete_empty.clicked.connect(self.delete_empty_files)
        dialog.btn_organize.clicked.connect(self.organize_files)
        dialog.btn_copy_to.clicked.connect(self.copy_to_folder)
        dialog.btn_move_to.clicked.connect(self.move_to_folder)
        dialog.exec_()

    def open_sort_settings_dialog(self):
        dialog = SortSettingsDialog(self)
        dialog.radio_asc.setChecked(self.sort_order == Qt.AscendingOrder)
        dialog.radio_desc.setChecked(self.sort_order == Qt.DescendingOrder)
        if dialog.exec_():
            self.sort_order = Qt.AscendingOrder if dialog.radio_asc.isChecked() else Qt.DescendingOrder
            self.sort_table(self.sort_column)

    def sort_table(self, column):
        if self.sort_column == column:
            self.sort_order = Qt.DescendingOrder if self.sort_order == Qt.AscendingOrder else Qt.AscendingOrder
        else:
            self.sort_column = column
            self.sort_order = Qt.AscendingOrder
        if self.sort_column == 1:
            self.file_list.sort(key=lambda x: os.path.basename(x[0]).lower(), reverse=self.sort_order == Qt.DescendingOrder)
        elif self.sort_column == 2:
            self.file_list.sort(key=lambda x: x[1], reverse=self.sort_order == Qt.DescendingOrder)
        elif self.sort_column == 3:
            self.file_list.sort(key=lambda x: get_file_category(x[0]), reverse=self.sort_order == Qt.DescendingOrder)
        self.populate_table_async()

    def copy_files(self):
        selected_rows = [row for row in range(self.table.rowCount()) if self.table.cellWidget(row, 0).isChecked()]
        if not selected_rows:
            self.status_bar.showMessage("هیچ فایلی انتخاب نشده است.", 5000)
            return
        confirm = QMessageBox.question(self, "تأیید کپی", "آیا مطمئن هستید که می‌خواهید نام فایل‌ها را کپی کنید؟", QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            names = [self.table.item(row, 1).text() for row in selected_rows]
            QApplication.clipboard().setText("\n".join(names))
            self.status_bar.showMessage("نام فایل‌ها کپی شد.", 5000)

    def save_files_to_file(self):
        selected_rows = [row for row in range(self.table.rowCount()) if self.table.cellWidget(row, 0).isChecked()]
        if not selected_rows:
            self.status_bar.showMessage("هیچ فایلی انتخاب نشده است.", 5000)
            return
        confirm = QMessageBox.question(self, "تأیید ذخیره", "آیا مطمئن هستید که می‌خواهید فهرست فایل‌ها را ذخیره کنید؟", QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            names = [self.table.item(row, 1).text() for row in selected_rows]
            file_path, _ = QFileDialog.getSaveFileName(self, "ذخیره فهرست فایل‌ها", "", "Text Files (*.txt)")
            if file_path:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(names) + "\n")
                self.status_bar.showMessage(f"فهرست در {os.path.basename(file_path)} ذخیره شد.", 5000)

    def delete_empty_files(self):
        if not self.current_path:
            self.status_bar.showMessage("ابتدا یک پوشه انتخاب کنید.", 5000)
            return
        confirm = QMessageBox.question(self, "تأیید حذف", "آیا مطمئن هستید که می‌خواهید فایل‌های خالی را حذف کنید؟", QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            deleted = 0
            for file_path, size, _ in self.file_list:
                if size == 0:
                    try:
                        os.remove(file_path)
                        deleted += 1
                    except Exception:
                        continue
                    QApplication.processEvents()
            self.status_bar.showMessage(f"{deleted} فایل خالی حذف شد.", 5000)
            self.start_scan(self.current_path)

    def organize_files(self):
        if not self.current_path:
            self.status_bar.showMessage("ابتدا یک پوشه انتخاب کنید.", 5000)
            return
        confirm = QMessageBox.question(self, "تأیید سازمان‌دهی", "آیا مطمئن هستید که می‌خواهید فایل‌ها را سازمان‌دهی کنید؟", QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            categories = ['صوتی', 'تصویری', 'متنی', 'ویدیویی', 'سایر'] + list(self.custom_categories.keys())
            for category in categories:
                category_path = os.path.join(self.current_path, category)
                if not os.path.exists(category_path):
                    os.makedirs(category_path)
            for file_path, _, _ in self.file_list:
                category = get_file_category(file_path)
                for custom_cat, exts in self.custom_categories.items():
                    if os.path.splitext(file_path)[1].lower() in exts:
                        category = custom_cat
                        break
                dest_path = os.path.join(self.current_path, category, os.path.basename(file_path))
                try:
                    shutil.move(file_path, dest_path)
                except Exception:
                    continue
                QApplication.processEvents()
            self.status_bar.showMessage("فایل‌ها سازمان‌دهی شدند.", 5000)
            self.start_scan(self.current_path)

    def copy_to_folder(self):
        self._copy_or_move_files(copy=True)

    def move_to_folder(self):
        self._copy_or_move_files(copy=False)

    def _copy_or_move_files(self, copy=True):
        selected_rows = [row for row in range(self.table.rowCount()) if self.table.cellWidget(row, 0).isChecked()]
        if not selected_rows:
            self.status_bar.showMessage("هیچ فایلی انتخاب نشده است.", 5000)
            return
        dest_path = QFileDialog.getExistingDirectory(self, "انتخاب پوشه مقصد")
        if not dest_path:
            return
        action = "کپی" if copy else "انتقال"
        confirm = QMessageBox.question(self, f"تأیید {action}", f"آیا مطمئن هستید که می‌خواهید فایل‌ها را {action} کنید؟", QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            for row in selected_rows:
                file_path = self.file_list[row][0]
                file_name = os.path.basename(file_path)
                dest_file_path = os.path.join(dest_path, file_name)
                try:
                    if copy:
                        shutil.copy2(file_path, dest_file_path)
                    else:
                        shutil.move(file_path, dest_file_path)
                except Exception:
                    continue
                QApplication.processEvents()
            self.status_bar.showMessage(f"فایل‌ها {action} شدند.", 5000)
            if not copy:
                self.start_scan(self.current_path)

    def open_context_menu(self, position):
        index = self.table.indexAt(position)
        if not index.isValid():
            return
        file_path = self.file_list[index.row()][0]
        menu = QMenu()
        menu.addAction("باز کردن فایل", lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(file_path)))
        menu.addAction("تغییر نام", lambda: self.rename_file(file_path))
        menu.addAction("پیش‌نمایش", lambda: FilePreviewDialog(file_path, self).exec_())
        menu.exec_(self.table.viewport().mapToGlobal(position))

    def rename_file(self, file_path):
        new_name, ok = QInputDialog.getText(self, "تغییر نام فایل", "نام جدید:", QLineEdit.Normal, os.path.basename(file_path))
        if ok and new_name:
            new_file_path = os.path.join(os.path.dirname(file_path), new_name)
            try:
                os.rename(file_path, new_file_path)
                self.status_bar.showMessage("نام فایل تغییر کرد.", 5000)
                self.start_scan(self.current_path)
            except Exception as e:
                self.status_bar.showMessage(f"خطا در تغییر نام: {e}", 5000)

    def handle_category_change(self, category):
        if category == "دسته‌بندی سفارشی":
            dialog = CustomCategoryDialog(self)
            if dialog.exec_():
                custom_name = dialog.name_input.text()
                extensions = [ext.strip() for ext in dialog.ext_input.text().split(',') if ext.strip()]
                if custom_name and extensions:
                    self.custom_categories[custom_name] = extensions
                    self.categoryCombo.addItem(custom_name)
                    self.categoryCombo.setCurrentText(custom_name)
        self.filter_table()

class CustomCategoryDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("دسته‌بندی سفارشی")
        layout = QFormLayout()
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("نام دسته‌بندی")
        layout.addRow("نام دسته‌بندی:", self.name_input)
        self.ext_input = QLineEdit()
        self.ext_input.setPlaceholderText("پسوندها (مثال: .jpg,.png)")
        layout.addRow("پسوندهای فایل:", self.ext_input)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.setLayout(layout)

class FilePreviewDialog(QDialog):
    def __init__(self, file_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("پیش‌نمایش فایل")
        layout = QVBoxLayout()
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type and mime_type.startswith('audio'):
            content = QLabel("پیش‌نمایش برای فایل‌های صوتی امکان‌پذیر نیست.")
        else:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    text = f.read(500)
                content = QTextEdit()
                content.setReadOnly(True)
                content.setText(text)
            except Exception:
                content = QLabel("خطا در پیش‌نمایش فایل.")
        layout.addWidget(content)
        close_btn = QPushButton("بستن")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)
        self.setLayout(layout)

class FileOperationsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("اقدامات روی فایل‌ها")
        layout = QVBoxLayout()
        self.btn_copy_names = QPushButton("کپی نام فایل‌ها")
        layout.addWidget(self.btn_copy_names)
        self.btn_save_list = QPushButton("ذخیره فهرست فایل‌ها")
        layout.addWidget(self.btn_save_list)
        self.btn_delete_empty = QPushButton("حذف فایل‌های خالی")
        layout.addWidget(self.btn_delete_empty)
        self.btn_organize = QPushButton("سازمان‌دهی فایل‌ها")
        layout.addWidget(self.btn_organize)
        self.btn_copy_to = QPushButton("کپی به پوشه دیگر")
        layout.addWidget(self.btn_copy_to)
        self.btn_move_to = QPushButton("انتقال به پوشه دیگر")
        layout.addWidget(self.btn_move_to)
        close_btn = QPushButton("بستن")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)
        self.setLayout(layout)

class SortSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("تنظیمات مرتب‌سازی")
        layout = QFormLayout()
        self.radio_asc = QRadioButton("صعودی")
        self.radio_desc = QRadioButton("نزولی")
        layout.addRow("نوع مرتب‌سازی:", self.radio_asc)
        layout.addRow("", self.radio_desc)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.setLayout(layout)
