import os, shutil
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTextEdit, QFileDialog
from PyQt5.QtGui import QIcon
from PyQt5.Qt import QApplication, QSystemTrayIcon

class CustomCopyTab(QWidget):
    def __init__(self, status_callback, progress_callback, tray):
        super().__init__()
        self.status_callback = status_callback
        self.progress_callback = progress_callback
        self.tray = tray
        self.custom_source_path = ""
        self.custom_dest_path = ""
        self.init_ui()
    def init_ui(self):
        layout = QVBoxLayout()
        btn_layout = QHBoxLayout()
        self.btn_source = QPushButton("انتخاب پوشه منبع")
        self.btn_source.setIcon(QIcon("icons/folder.png"))
        self.btn_source.clicked.connect(self.select_custom_source)
        btn_layout.addWidget(self.btn_source)
        self.btn_dest = QPushButton("انتخاب پوشه مقصد")
        self.btn_dest.setIcon(QIcon("icons/folder.png"))
        self.btn_dest.clicked.connect(self.select_custom_destination)
        btn_layout.addWidget(self.btn_dest)
        self.lbl_source = QLabel("منبع: انتخاب نشده")
        btn_layout.addWidget(self.lbl_source)
        self.lbl_dest = QLabel("مقصد: انتخاب نشده")
        btn_layout.addWidget(self.lbl_dest)
        layout.addLayout(btn_layout)
        self.lbl_list = QLabel("نام پوشه‌ها (هر خط یک نام):")
        layout.addWidget(self.lbl_list)
        self.text_edit = QTextEdit()
        self.text_edit.setAcceptDrops(True)
        layout.addWidget(self.text_edit)
        self.btn_copy = QPushButton("کپی پوشه‌های وارد شده")
        self.btn_copy.setIcon(QIcon("icons/copy.png"))
        self.btn_copy.clicked.connect(self.copy_custom_folders)
        layout.addWidget(self.btn_copy)
        self.setLayout(layout)
    def select_custom_source(self):
        path = QFileDialog.getExistingDirectory(self, "انتخاب پوشه منبع")
        if path:
            self.custom_source_path = path
            self.lbl_source.setText(f"منبع: {self.custom_source_path}")
    def select_custom_destination(self):
        path = QFileDialog.getExistingDirectory(self, "انتخاب پوشه مقصد")
        if path:
            self.custom_dest_path = path
            self.lbl_dest.setText(f"مقصد: {self.custom_dest_path}")
    def copy_custom_folders(self):
        if not self.custom_source_path:
            self.status_callback("ابتدا پوشه منبع را انتخاب کنید.")
            return
        folder_list = self.text_edit.toPlainText().strip().splitlines()
        if not folder_list:
            self.status_callback("لیست نام پوشه خالی است.")
            return
        total = len(folder_list)
        copied = 0
        for idx, folder_name in enumerate(folder_list, start=1):
            folder_name = folder_name.strip()
            if not folder_name:
                continue
            source_folder = os.path.join(self.custom_source_path, folder_name)
            if os.path.isdir(source_folder):
                dest_folder = os.path.join(self.custom_dest_path, folder_name) if self.custom_dest_path else self.custom_source_path
                try:
                    shutil.copytree(source_folder, dest_folder, dirs_exist_ok=True)
                    copied += 1
                except Exception as e:
                    self.status_callback(f"خطا در کپی {folder_name}: {e}")
            else:
                self.status_callback(f"پوشه‌ای به نام {folder_name} یافت نشد.")
            self.progress_callback(idx, total)
        self.progress_callback(0, total)
        self.status_callback(f"{copied} پوشه کپی شدند.")
        self.tray.showMessage("کپی", "پوشه‌های وارد شده کپی شدند.", QSystemTrayIcon.Information, 3000)
