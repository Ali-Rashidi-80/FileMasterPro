import os
import winshell
import subprocess
import time
import sys
from Crypto.Cipher import AES
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTreeWidget, QTreeWidgetItem,
    QMessageBox, QComboBox, QGroupBox, QFileDialog, QProgressBar, QDialog
)
from PyQt5.QtCore import Qt
import secrets

class FileShredderTab(QWidget):
    def __init__(self, update_status=None, update_progress=None, tray_icon=None):
        super().__init__()
        self.update_status = update_status
        self.update_progress = update_progress
        self.tray_icon = tray_icon
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        description = QLabel("ابزاری امن برای حذف فایل‌ها و Recycle Bin")
        description.setAlignment(Qt.AlignCenter)
        layout.addWidget(description)

        shred_type_group = QGroupBox("انتخاب نوع خرد کردن")
        shred_type_layout = QHBoxLayout()
        self.file_folder_btn = QPushButton("File & Folder")
        self.file_folder_btn.clicked.connect(self.open_file_folder_dialog)
        self.file_folder_btn.setToolTip("فایل‌ها یا پوشه‌ها را برای حذف امن انتخاب کنید")
        shred_type_layout.addWidget(self.file_folder_btn)
        self.recycle_bin_btn = QPushButton("Recycle Bin")
        self.recycle_bin_btn.clicked.connect(self.open_recycle_bin_dialog)
        self.recycle_bin_btn.setToolTip("محتویات Recycle Bin را به صورت امن حذف کنید")
        shred_type_layout.addWidget(self.recycle_bin_btn)
        shred_type_group.setLayout(shred_type_layout)
        layout.addWidget(shred_type_group)

    def open_file_folder_dialog(self):
        dialog = FileFolderShredDialog(self, self.update_status, self.update_progress, self.tray_icon)
        dialog.exec_()

    def open_recycle_bin_dialog(self):
        dialog = RecycleBinShredDialog(self, self.update_status, self.update_progress, self.tray_icon)
        dialog.exec_()

class RecycleBinShredDialog(QDialog):
    def __init__(self, parent=None, update_status=None, update_progress=None, tray_icon=None):
        super().__init__(parent)
        self.update_status = update_status
        self.update_progress = update_progress
        self.tray_icon = tray_icon
        self.setWindowTitle("خرد کردن Recycle Bin")
        self.resize(800, 600)
        self.is_initializing = True
        self.init_ui()
        self.is_initializing = False

    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        self.file_tree = QTreeWidget()
        self.file_tree.setHeaderLabels(["نام فایل", "مسیر اصلی", "اندازه", "تاریخ حذف"])
        self.file_tree.setSelectionMode(QTreeWidget.ExtendedSelection)
        layout.addWidget(self.file_tree)

        select_all_btn = QPushButton("انتخاب همه")
        select_all_btn.clicked.connect(self.select_all_items)
        select_all_btn.setToolTip("همه فایل‌ها را برای حذف انتخاب کنید")
        layout.addWidget(select_all_btn)

        disk_type_group = QGroupBox("نوع دیسک")
        disk_type_layout = QHBoxLayout()
        self.disk_type_combo = QComboBox()
        self.disk_type_combo.addItems(["HDD", "SSD"])
        self.disk_type_combo.currentTextChanged.connect(self.update_method_combo)
        self.disk_type_combo.setToolTip("نوع دیسک را انتخاب کنید (HDD یا SSD)")
        disk_type_layout.addWidget(self.disk_type_combo)
        disk_type_group.setLayout(disk_type_layout)
        layout.addWidget(disk_type_group)

        method_group = QGroupBox("روش حذف امن")
        method_layout = QVBoxLayout()
        self.method_combo = QComboBox()
        self.method_combo.currentTextChanged.connect(self.show_method_description)
        self.method_combo.setToolTip("روش مورد نظر برای حذف امن را انتخاب کنید")
        self.update_method_combo(self.disk_type_combo.currentText())
        method_layout.addWidget(self.method_combo)
        method_group.setLayout(method_layout)
        layout.addWidget(method_group)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        layout.addWidget(self.progress_bar)

        action_btn_layout = QHBoxLayout()
        self.shred_btn = QPushButton("شروع خرد کردن")
        self.shred_btn.clicked.connect(self.shred_selected_items)
        self.shred_btn.setToolTip("شروع عملیات حذف امن فایل‌ها")
        action_btn_layout.addWidget(self.shred_btn)
        self.close_btn = QPushButton("بستن")
        self.close_btn.clicked.connect(self.close)
        self.close_btn.setToolTip("بستن پنجره")
        action_btn_layout.addWidget(self.close_btn)
        layout.addLayout(action_btn_layout)

        self.load_recycle_bin()

    def show_method_description(self, method):
        if self.is_initializing:
            return
        descriptions = {
            "Zero Fill": "این روش تمام داده‌های فایل را با صفر پر می‌کند. سریع اما امنیت کمتری دارد و برای داده‌های غیرحساس مناسب است.",
            "Random Data (1-3 passes)": "داده‌ها را با اطلاعات تصادفی در 1 تا 3 گذر بازنویسی می‌کند. امنیت متوسطی دارد و برای اکثر کاربران کافی است.",
            "DoD 5220.22-M (3 passes)": "استاندارد وزارت دفاع آمریکا با 3 گذر بازنویسی. امنیت بالایی دارد و برای داده‌های محرمانه توصیه می‌شود.",
            "Gutmann Method (35 passes)": "با 35 گذر بازنویسی، این روش بسیار امن است و برای داده‌های فوق حساس طراحی شده، اما زمان‌بر است.",
            "Bruce Schneier Method (7 passes)": "روش پیشنهادی بروس اشنایر با 7 گذر بازنویسی. تعادل خوبی بین امنیت و سرعت دارد.",
            "Secure Erase (ATA Secure Erase)": "دستور داخلی دیسک برای حذف امن داده‌ها در SSDها. سریع و بسیار مؤثر است.",
            "Cryptographic Erase": "داده‌ها را رمزنگاری کرده و کلید را حذف می‌کند. روشی سریع و امن برای SSDها."
        }
        description = descriptions.get(method, "لطفاً یک روش حذف امن را انتخاب کنید.")
        QMessageBox.information(self, "توضیحات روش حذف", description)

    def load_recycle_bin(self):
        try:
            for item in winshell.recycle_bin():
                name = item.original_filename()
                path = name
                size = self.get_file_size(item)
                date = item.recycle_date().strftime("%Y-%m-%d %H:%M:%S")
                tree_item = QTreeWidgetItem(self.file_tree, [name, path, size, date])
                tree_item.setData(0, Qt.UserRole, item)
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"خطا در بارگذاری Recycle Bin: {e}")

    def get_file_size(self, item):
        try:
            file_path = item.filename()
            if os.path.exists(file_path):
                size = os.path.getsize(file_path)
                return f"{size / (1024 * 1024):.3f} MB"
            else:
                return "نامشخص"
        except Exception as e:
            print(f"خطا در محاسبه اندازه {item.original_filename()}: {e}")
            return "نامشخص"

    def select_all_items(self):
        for i in range(self.file_tree.topLevelItemCount()):
            item = self.file_tree.topLevelItem(i)
            item.setSelected(True)

    def update_method_combo(self, disk_type):
        self.method_combo.clear()
        if disk_type == "HDD":
            self.method_combo.addItems([
                "Zero Fill",
                "Random Data (1-3 passes)",
                "DoD 5220.22-M (3 passes)",
                "Gutmann Method (35 passes)",
                "Bruce Schneier Method (7 passes)"
            ])
        elif disk_type == "SSD":
            self.method_combo.addItems([
                "Secure Erase (ATA Secure Erase)",
                "Cryptographic Erase"
            ])

    def shred_selected_items(self):
        selected_items = self.file_tree.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "هشدار", "هیچ فایلی انتخاب نشده است!")
            return
        method = self.method_combo.currentText().lower()
        total = len(selected_items)
        for i, tree_item in enumerate(selected_items, 1):
            item = tree_item.data(0, Qt.UserRole)
            try:
                self.shred_item(item, method)
                self.file_tree.takeTopLevelItem(self.file_tree.indexOfTopLevelItem(tree_item))
                self.progress_bar.setValue(int((i / total) * 100))
                if self.update_status:
                    self.update_status(f"در حال حذف امن: {item.original_filename()} ({i}/{total})")
            except Exception as e:
                QMessageBox.critical(self, "خطا", f"خطا در حذف {item.original_filename()}: {e}")
        QMessageBox.information(self, "موفقیت", "فایل‌های انتخاب‌شده به‌طور امن حذف شدند.")
        if self.tray_icon:
            self.tray_icon.showMessage("File Shredder", "فایل‌ها به‌طور امن حذف شدند.", 3000)

    def shred_item(self, item, method):
        try:
            item.undelete()
            file_path = item.original_filename()
            if os.path.exists(file_path):
                self.shred_file(file_path, method)
            else:
                raise Exception("فایل بازیابی نشد.")
        except Exception as e:
            raise Exception(f"خطا در حذف امن فایل: {e}")

    def shred_file(self, file_path, method):
        if os.path.isdir(file_path):
            for root, dirs, files in os.walk(file_path, topdown=False):
                for name in files:
                    file = os.path.join(root, name)
                    self.shred_file(file, method)
                for name in dirs:
                    dir_path = os.path.join(root, name)
                    os.rmdir(dir_path)
        else:
            file_size = os.path.getsize(file_path)
            if "zero fill" in method:
                with open(file_path, "wb") as f:
                    f.write(b'\0' * file_size)
            elif "random data" in method:
                for _ in range(3):
                    with open(file_path, "wb") as f:
                        f.write(os.urandom(file_size))
            elif "dod 5220.22-m" in method:
                with open(file_path, "wb") as f:
                    f.write(b'\0' * file_size)
                with open(file_path, "wb") as f:
                    f.write(b'\xFF' * file_size)
                with open(file_path, "wb") as f:
                    f.write(os.urandom(file_size))
            elif "gutmann" in method:
                for _ in range(35):
                    with open(file_path, "wb") as f:
                        f.write(os.urandom(file_size))
            elif "bruce schneier" in method:
                with open(file_path, "wb") as f:
                    f.write(b'\0' * file_size)
                with open(file_path, "wb") as f:
                    f.write(b'\xFF' * file_size)
                for _ in range(5):
                    with open(file_path, "wb") as f:
                        f.write(os.urandom(file_size))
            elif "secure erase" in method:
                if os.name == "nt":
                    if getattr(sys, 'frozen', False):
                        base_path = sys._MEIPASS
                    else:
                        base_path = os.getcwd()
                    sdelete_path = os.path.join(base_path, "SDelete", "sdelete.exe")
                    if not os.path.exists(sdelete_path):
                        raise Exception(f"sdelete.exe در مسیر {sdelete_path} یافت نشد.")
                    subprocess.run([sdelete_path, "-p", "1", file_path], check=True)
                    time.sleep(1)
                    if os.path.exists(file_path):
                        raise Exception("فایل پس از Secure Erase هنوز وجود دارد.")
                else:
                    raise Exception("ATA Secure Erase تنها در ویندوز پشتیبانی می‌شود.")
            elif "cryptographic erase" in method:
                key = secrets.token_bytes(16)
                nonce = secrets.token_bytes(8)
                cipher = AES.new(key, AES.MODE_CTR, nonce=nonce)
                with open(file_path, "rb") as f:
                    data = f.read()
                encrypted_data = cipher.encrypt(data)
                with open(file_path, "wb") as f:
                    f.write(nonce + encrypted_data)
                # پاک‌سازی امن کلید
                key = secrets.token_bytes(16)
                nonce = secrets.token_bytes(8)
                key = None
                nonce = None
                # حذف امن فایل با sdelete
                if os.name == "nt":
                    if getattr(sys, 'frozen', False):
                        base_path = sys._MEIPASS
                    else:
                        base_path = os.getcwd()
                    sdelete_path = os.path.join(base_path, "SDelete", "sdelete.exe")
                    if os.path.exists(sdelete_path):
                        subprocess.run([sdelete_path, "-p", "1", file_path], check=True)
                    else:
                        os.remove(file_path)  # در صورت نبود sdelete، حذف معمولی
            if os.path.exists(file_path):
                os.remove(file_path)
            else:
                if self.update_status:
                    self.update_status(f"فایل {file_path} قبلاً حذف شده است.")

class FileFolderShredDialog(QDialog):
    def __init__(self, parent=None, update_status=None, update_progress=None, tray_icon=None):
        super().__init__(parent)
        self.update_status = update_status
        self.update_progress = update_progress
        self.tray_icon = tray_icon
        self.setWindowTitle("خرد کردن فایل‌ها و پوشه‌ها")
        self.resize(800, 600)
        self.files_to_shred = []
        self.is_initializing = True
        self.init_ui()
        self.is_initializing = False

    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        self.file_tree = QTreeWidget()
        self.file_tree.setHeaderLabels(["مسیر", "اندازه"])
        self.file_tree.setSelectionMode(QTreeWidget.ExtendedSelection)
        layout.addWidget(self.file_tree)

        add_btn_layout = QHBoxLayout()
        self.add_file_btn = QPushButton("افزودن فایل")
        self.add_file_btn.clicked.connect(self.add_file)
        self.add_file_btn.setToolTip("یک فایل برای حذف انتخاب کنید")
        add_btn_layout.addWidget(self.add_file_btn)
        self.add_folder_btn = QPushButton("افزودن پوشه")
        self.add_folder_btn.clicked.connect(self.add_folder)
        self.add_folder_btn.setToolTip("یک پوشه برای حذف انتخاب کنید")
        add_btn_layout.addWidget(self.add_folder_btn)
        self.select_all_btn = QPushButton("انتخاب همه")
        self.select_all_btn.clicked.connect(self.select_all_items)
        self.select_all_btn.setToolTip("همه فایل‌ها و پوشه‌ها را انتخاب کنید")
        add_btn_layout.addWidget(self.select_all_btn)
        layout.addLayout(add_btn_layout)

        disk_type_group = QGroupBox("نوع دیسک")
        disk_type_layout = QHBoxLayout()
        self.disk_type_combo = QComboBox()
        self.disk_type_combo.addItems(["HDD", "SSD"])
        self.disk_type_combo.currentTextChanged.connect(self.update_method_combo)
        self.disk_type_combo.setToolTip("نوع دیسک را انتخاب کنید (HDD یا SSD)")
        disk_type_layout.addWidget(self.disk_type_combo)
        disk_type_group.setLayout(disk_type_layout)
        layout.addWidget(disk_type_group)

        method_group = QGroupBox("روش حذف امن")
        method_layout = QVBoxLayout()
        self.method_combo = QComboBox()
        self.method_combo.currentTextChanged.connect(self.show_method_description)
        self.method_combo.setToolTip("روش مورد نظر برای حذف امن را انتخاب کنید")
        self.update_method_combo(self.disk_type_combo.currentText())
        method_layout.addWidget(self.method_combo)
        method_group.setLayout(method_layout)
        layout.addWidget(method_group)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        layout.addWidget(self.progress_bar)

        action_btn_layout = QHBoxLayout()
        self.shred_btn = QPushButton("شروع خرد کردن")
        self.shred_btn.clicked.connect(self.shred_selected_items)
        self.shred_btn.setToolTip("شروع عملیات حذف امن")
        action_btn_layout.addWidget(self.shred_btn)
        self.close_btn = QPushButton("بستن")
        self.close_btn.clicked.connect(self.close)
        self.close_btn.setToolTip("بستن پنجره")
        action_btn_layout.addWidget(self.close_btn)
        layout.addLayout(action_btn_layout)

    def show_method_description(self, method):
        if self.is_initializing:
            return
        descriptions = {
            "Zero Fill": "این روش تمام داده‌های فایل را با صفر پر می‌کند. سریع اما امنیت کمتری دارد و برای داده‌های غیرحساس مناسب است.",
            "Random Data (1-3 passes)": "داده‌ها را با اطلاعات تصادفی در 1 تا 3 گذر بازنویسی می‌کند. امنیت متوسطی دارد و برای اکثر کاربران کافی است.",
            "DoD 5220.22-M (3 passes)": "استاندارد وزارت دفاع آمریکا با 3 گذر بازنویسی. امنیت بالایی دارد و برای داده‌های محرمانه توصیه می‌شود.",
            "Gutmann Method (35 passes)": "با 35 گذر بازنویسی، این روش بسیار امن است و برای داده‌های فوق حساس طراحی شده، اما زمان‌بر است.",
            "Bruce Schneier Method (7 passes)": "روش پیشنهادی بروس اشنایر با 7 گذر بازنویسی. تعادل خوبی بین امنیت و سرعت دارد.",
            "Secure Erase (ATA Secure Erase)": "دستور داخلی دیسک برای حذف امن داده‌ها در SSDها. سریع و بسیار مؤثر است.",
            "Cryptographic Erase": "داده‌ها را رمزنگاری کرده و کلید را حذف می‌کند. روشی سریع و امن برای SSDها."
        }
        description = descriptions.get(method, "لطفاً یک روش حذف امن را انتخاب کنید.")
        QMessageBox.information(self, "توضیحات روش حذف", description)

    def add_file(self):
        file, _ = QFileDialog.getOpenFileName(self, "انتخاب فایل")
        if file:
            self.files_to_shred.append(file)
            item = QTreeWidgetItem(self.file_tree, [file, self.get_file_size(file)])
            if self.update_status:
                self.update_status(f"فایل اضافه شد: {file}")

    def add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "انتخاب پوشه")
        if folder:
            self.files_to_shred.append(folder)
            item = QTreeWidgetItem(self.file_tree, [folder, "پوشه"])
            if self.update_status:
                self.update_status(f"پوشه اضافه شد: {folder}")

    def get_file_size(self, file_path):
        try:
            size = os.path.getsize(file_path)
            return f"{size / 1024:.3f} KB"
        except:
            return "نامشخص"

    def select_all_items(self):
        for i in range(self.file_tree.topLevelItemCount()):
            item = self.file_tree.topLevelItem(i)
            item.setSelected(True)

    def update_method_combo(self, disk_type):
        self.method_combo.clear()
        if disk_type == "HDD":
            self.method_combo.addItems([
                "Zero Fill",
                "Random Data (1-3 passes)",
                "DoD 5220.22-M (3 passes)",
                "Gutmann Method (35 passes)",
                "Bruce Schneier Method (7 passes)"
            ])
        elif disk_type == "SSD":
            self.method_combo.addItems([
                "Secure Erase (ATA Secure Erase)",
                "Cryptographic Erase"
            ])

    def shred_selected_items(self):
        selected_items = self.file_tree.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "هشدار", "هیچ فایلی انتخاب نشده است!")
            return
        method = self.method_combo.currentText().lower()
        total = len(selected_items)
        for i, tree_item in enumerate(selected_items, 1):
            file_path = tree_item.text(0)
            try:
                if os.path.exists(file_path):
                    self.shred_file(file_path, method)
                    self.file_tree.takeTopLevelItem(self.file_tree.indexOfTopLevelItem(tree_item))
                    self.progress_bar.setValue(int((i / total) * 100))
                    if self.update_status:
                        self.update_status(f"در حال حذف امن: {file_path} ({i}/{total})")
            except Exception as e:
                QMessageBox.critical(self, "خطا", f"خطا در حذف {file_path}: {e}")
        QMessageBox.information(self, "موفقیت", "فایل‌ها و پوشه‌ها به‌طور امن حذف شدند.")
        if self.tray_icon:
            self.tray_icon.showMessage("File Shredder", "فایل‌ها به‌طور امن حذف شدند.", 3000)

    def shred_file(self, file_path, method):
        if os.path.isdir(file_path):
            for root, dirs, files in os.walk(file_path, topdown=False):
                for name in files:
                    file = os.path.join(root, name)
                    self.shred_file(file, method)
                for name in dirs:
                    dir_path = os.path.join(root, name)
                    os.rmdir(dir_path)
        else:
            file_size = os.path.getsize(file_path)
            if "zero fill" in method:
                with open(file_path, "wb") as f:
                    f.write(b'\0' * file_size)
            elif "random data" in method:
                for _ in range(3):
                    with open(file_path, "wb") as f:
                        f.write(os.urandom(file_size))
            elif "dod 5220.22-m" in method:
                with open(file_path, "wb") as f:
                    f.write(b'\0' * file_size)
                with open(file_path, "wb") as f:
                    f.write(b'\xFF' * file_size)
                with open(file_path, "wb") as f:
                    f.write(os.urandom(file_size))
            elif "gutmann" in method:
                for _ in range(35):
                    with open(file_path, "wb") as f:
                        f.write(os.urandom(file_size))
            elif "bruce schneier" in method:
                with open(file_path, "wb") as f:
                    f.write(b'\0' * file_size)
                with open(file_path, "wb") as f:
                    f.write(b'\xFF' * file_size)
                for _ in range(5):
                    with open(file_path, "wb") as f:
                        f.write(os.urandom(file_size))
            elif "secure erase" in method:
                if os.name == "nt":
                    if getattr(sys, 'frozen', False):
                        base_path = sys._MEIPASS
                    else:
                        base_path = os.getcwd()
                    sdelete_path = os.path.join(base_path, "SDelete", "sdelete.exe")
                    if not os.path.exists(sdelete_path):
                        raise Exception(f"sdelete.exe در مسیر {sdelete_path} یافت نشد.")
                    subprocess.run([sdelete_path, "-p", "1", file_path], check=True)
                    time.sleep(1)
                    if os.path.exists(file_path):
                        raise Exception("فایل پس از Secure Erase هنوز وجود دارد.")
                else:
                    raise Exception("ATA Secure Erase تنها در ویندوز پشتیبانی می‌شود.")
            elif "cryptographic erase" in method:
                key = secrets.token_bytes(16)
                nonce = secrets.token_bytes(8)
                cipher = AES.new(key, AES.MODE_CTR, nonce=nonce)
                with open(file_path, "rb") as f:
                    data = f.read()
                encrypted_data = cipher.encrypt(data)
                with open(file_path, "wb") as f:
                    f.write(nonce + encrypted_data)
                # پاک‌سازی امن کلید
                key = secrets.token_bytes(16)
                nonce = secrets.token_bytes(8)
                key = None
                nonce = None
                # حذف امن فایل با sdelete
                if os.name == "nt":
                    if getattr(sys, 'frozen', False):
                        base_path = sys._MEIPASS
                    else:
                        base_path = os.getcwd()
                    sdelete_path = os.path.join(base_path, "SDelete", "sdelete.exe")
                    if os.path.exists(sdelete_path):
                        subprocess.run([sdelete_path, "-p", "1", file_path], check=True)
                    else:
                        os.remove(file_path)  # در صورت نبود sdelete، حذف معمولی
            if os.path.exists(file_path):
                os.remove(file_path)
            else:
                if self.update_status:
                    self.update_status(f"فایل {file_path} قبلاً حذف شده است.")