import os, shutil
from PyQt5.QtWidgets import QWidget, QLineEdit, QHBoxLayout, QVBoxLayout, QPushButton, QFileDialog, QTableWidget, QTableWidgetItem
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QIcon
from PyQt5.Qt import QApplication, QSystemTrayIcon

class FoldersTab(QWidget):
    updateCount = pyqtSignal(int)
    def __init__(self, status_callback, progress_callback, tray):
        super().__init__()
        self.status_callback = status_callback
        self.progress_callback = progress_callback
        self.tray = tray
        self.current_path = ""
        self.init_ui()
    def init_ui(self):
        layout = QVBoxLayout()
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("جستجو در پوشه‌ها...")
        self.search_bar.textChanged.connect(self.filter_table)
        layout.addWidget(self.search_bar)
        btn_layout = QHBoxLayout()
        self.btn_select = QPushButton("انتخاب مسیر")
        self.btn_select.setIcon(QIcon("icons/folder.png"))
        self.btn_select.clicked.connect(self.select_directory)
        btn_layout.addWidget(self.btn_select)
        self.btn_copy = QPushButton("کپی نام پوشه‌ها")
        self.btn_copy.setIcon(QIcon("icons/copy.png"))
        self.btn_copy.clicked.connect(self.copy_folders)
        btn_layout.addWidget(self.btn_copy)
        self.btn_save = QPushButton("ذخیره به فایل تکست")
        self.btn_save.setIcon(QIcon("icons/save.png"))
        self.btn_save.clicked.connect(self.save_folders_to_file)
        btn_layout.addWidget(self.btn_save)
        self.btn_delete_empty = QPushButton("حذف پوشه‌های خالی")
        self.btn_delete_empty.setIcon(QIcon("icons/delete.png"))
        self.btn_delete_empty.clicked.connect(self.delete_empty_folders)
        btn_layout.addWidget(self.btn_delete_empty)
        self.btn_batch_rename = QPushButton("تغییر نام گروهی")
        self.btn_batch_rename.setIcon(QIcon("icons/rename.png"))
        self.btn_batch_rename.clicked.connect(self.batch_rename)
        btn_layout.addWidget(self.btn_batch_rename)
        layout.addLayout(btn_layout)
        self.folder_list = QTableWidget(0, 1)
        self.folder_list.setHorizontalHeaderLabels(["نام پوشه"])
        self.folder_list.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.folder_list)
        self.setLayout(layout)
    def filter_table(self, text):
        for row in range(self.folder_list.rowCount()):
            item = self.folder_list.item(row, 0)
            if item:
                self.folder_list.setRowHidden(row, text.lower() not in item.text().lower())
    def select_directory(self):
        path = QFileDialog.getExistingDirectory(self, "انتخاب مسیر برای پوشه‌ها")
        if path:
            self.current_path = path
            self.populate_folders(path)
            self.updateCount.emit(self.folder_list.rowCount())
            self.status_callback("لیست پوشه‌ها به‌روزرسانی شد.")
            self.tray.showMessage("عملیات", "لیست پوشه‌ها به‌روزرسانی شد.", QSystemTrayIcon.Information, 3000)
    def populate_folders(self, path):
        self.folder_list.setRowCount(0)
        try:
            for item in os.listdir(path):
                item_path = os.path.join(path, item)
                if os.path.isdir(item_path):
                    row = self.folder_list.rowCount()
                    self.folder_list.insertRow(row)
                    self.folder_list.setItem(row, 0, QTableWidgetItem(item))
        except Exception as e:
            self.status_callback(f"خطا: {e}")
    def copy_folders(self):
        if not self.current_path:
            self.status_callback("ابتدا مسیر را انتخاب کنید.")
            return
        folder_names = [self.folder_list.item(row, 0).text() for row in range(self.folder_list.rowCount()) if self.folder_list.item(row, 0)]
        if folder_names:
            QApplication.clipboard().setText("\n".join(folder_names))
            self.status_callback("نام پوشه‌ها در کلیپ‌بورد کپی شدند.")
            self.tray.showMessage("کپی", "نام پوشه‌ها کپی شدند.", QSystemTrayIcon.Information, 3000)
        else:
            self.status_callback("هیچ پوشه‌ای برای کپی وجود ندارد.")
    def save_folders_to_file(self):
        if not self.current_path:
            self.status_callback("ابتدا مسیر را انتخاب کنید.")
            return
        folder_names = [self.folder_list.item(row, 0).text() for row in range(self.folder_list.rowCount()) if self.folder_list.item(row, 0)]
        if not folder_names:
            self.status_callback("هیچ پوشه‌ای برای ذخیره وجود ندارد.")
            return
        file_path, _ = QFileDialog.getSaveFileName(self, "انتخاب فایل تکست", "", "Text Files (*.txt)")
        if file_path:
            try:
                with open(file_path, "a", encoding="utf-8") as f:
                    f.write("\n".join(folder_names) + "\n")
                self.status_callback(f"نام پوشه‌ها به {os.path.basename(file_path)} اضافه شدند.")
            except Exception as e:
                self.status_callback(f"خطا در ذخیره فایل: {e}")
    def delete_empty_folders(self):
        if not self.current_path:
            self.status_callback("ابتدا مسیر را انتخاب کنید.")
            return
        deleted = 0
        for item in os.listdir(self.current_path):
            folder_path = os.path.join(self.current_path, item)
            if os.path.isdir(folder_path) and not os.listdir(folder_path):
                try:
                    shutil.rmtree(folder_path)
                    deleted += 1
                except Exception as e:
                    self.status_callback(f"خطا در حذف {folder_path}: {e}")
        self.status_callback(f"{deleted} پوشه خالی حذف شدند.")
        self.select_directory()
    def batch_rename(self):
        pattern, ok = QFileDialog.getSaveFileName(self, "الگوی تغییر نام (مثلاً folder_{n})", "", "All Files (*)")
        if not ok or not pattern:
            return
        if not self.current_path:
            self.status_callback("ابتدا مسیر را انتخاب کنید.")
            return
        renamed = 0
        for idx, item in enumerate(os.listdir(self.current_path), start=1):
            folder_path = os.path.join(self.current_path, item)
            if os.path.isdir(folder_path):
                new_name = pattern.replace("{n}", str(idx))
                new_path = os.path.join(self.current_path, new_name)
                try:
                    os.rename(folder_path, new_path)
                    renamed += 1
                except Exception as e:
                    self.status_callback(f"خطا در تغییر نام {item}: {e}")
        self.status_callback(f"{renamed} پوشه تغییر نام یافتند.")
        self.select_directory()
