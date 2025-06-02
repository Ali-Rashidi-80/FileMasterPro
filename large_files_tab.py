import os, psutil, math, json
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog, QMessageBox, 
    QCheckBox, QLabel, QListWidget, QListWidgetItem, QSlider, QTabWidget, QGroupBox,
    QRadioButton, QDialog, QTreeWidget, QTreeWidgetItem, QScrollArea
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.Qt import QSystemTrayIcon

# در صورت استفاده از حذف به سطل بازیافت، کتابخانه send2trash را در نظر می‌گیریم.
try:
    from send2trash import send2trash
except ImportError:
    send2trash = None

CONFIG_FILE = "config_large_files_tab.json"
default_config = {
    "scan_extensions": [],
    "min_file_size": 100,  # مگابایت
    "delete_method": "recycle_bin",  # یا "permanent"
    "safe_mode_enabled": True,
    "safe_mode_excludes": [
        r"C:\Windows",
        r"C:\Users\theal\AppData\Roaming",
        r"C:\ProgramData",
        r"C:\Program Files (x86)",
        r"C:\Program Files"
    ]
}

# ایجاد فایل پیکربندی اگر وجود نداشته باشد
if not os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(default_config, f, indent=4)
    # بلافاصله مخفی‌سازی فایل در ویندوز
    try:
        os.system(f'attrib +h "{CONFIG_FILE}"')
    except Exception as e:
        print(f"خطا در مخفی‌سازی فایل پیکربندی: {e}")

def format_size(size_bytes):
    try:
        if size_bytes == 0:
            return "0 بایت"
        size_name = ("بایت", "کیلوبایت", "مگابایت", "گیگابایت", "ترابایت")
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {size_name[i]}"
    except Exception:
        return f"{size_bytes} بایت"

class FileGroupDialog(QDialog):
    def __init__(self, file_groups, deletion_method, status_callback, tray):
        super().__init__()
        self.setWindowTitle("نتایج اسکن - انتخاب فایل‌ها برای حذف")
        self.file_groups = file_groups
        self.deletion_method = deletion_method
        self.status_callback = status_callback
        self.tray = tray
        self.resize(800, 600)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # دکمه‌های انتخاب/عدم انتخاب همه
        top_btn_layout = QHBoxLayout()
        self.selectAllBtn = QPushButton("انتخاب همه")
        self.selectAllBtn.clicked.connect(self.select_all)
        top_btn_layout.addWidget(self.selectAllBtn)
        self.deselectAllBtn = QPushButton("عدم انتخاب همه")
        self.deselectAllBtn.clicked.connect(self.deselect_all)
        top_btn_layout.addWidget(self.deselectAllBtn)
        layout.addLayout(top_btn_layout)
        
        # درخت فایل‌ها با دو ستون: نام فایل و حجم
        self.tree = QTreeWidget()
        self.tree.setColumnCount(2)
        self.tree.setHeaderLabels(["فایل", "حجم"])
        self.tree.header().setDefaultSectionSize(350)
        font = QFont("Tahoma", 10)
        self.tree.setFont(font)
        
        # اضافه کردن گروه‌ها به درخت
        for ext, files in self.file_groups.items():
            group_name = ext if ext else "بدون پسوند"
            group_item = QTreeWidgetItem(self.tree, [f"گروه {group_name} ({len(files)} فایل)", ""])
            group_item.setFlags(group_item.flags() | Qt.ItemIsUserCheckable)
            group_item.setCheckState(0, Qt.Unchecked)
            for file_path in files:
                try:
                    size = os.path.getsize(file_path)
                except Exception:
                    size = 0
                file_item = QTreeWidgetItem(group_item, [file_path, format_size(size)])
                file_item.setFlags(file_item.flags() | Qt.ItemIsUserCheckable)
                file_item.setCheckState(0, Qt.Unchecked)
        self.tree.expandAll()
        layout.addWidget(self.tree)
        
        # دکمه‌های تایید و انصراف
        btn_layout = QHBoxLayout()
        self.deleteButton = QPushButton("حذف فایل‌های انتخاب شده")
        self.deleteButton.clicked.connect(self.delete_selected_files)
        btn_layout.addWidget(self.deleteButton)
        
        self.cancelButton = QPushButton("انصراف")
        self.cancelButton.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancelButton)
        layout.addLayout(btn_layout)
        self.setLayout(layout)
    
    def select_all(self):
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            group_item = root.child(i)
            group_item.setCheckState(0, Qt.Checked)
            for j in range(group_item.childCount()):
                group_item.child(j).setCheckState(0, Qt.Checked)
    
    def deselect_all(self):
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            group_item = root.child(i)
            group_item.setCheckState(0, Qt.Unchecked)
            for j in range(group_item.childCount()):
                group_item.child(j).setCheckState(0, Qt.Unchecked)
    
    def delete_selected_files(self):
        files_to_delete = []
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            group_item = root.child(i)
            if group_item.checkState(0) == Qt.Checked:
                for j in range(group_item.childCount()):
                    files_to_delete.append(group_item.child(j).text(0))
            else:
                for j in range(group_item.childCount()):
                    file_item = group_item.child(j)
                    if file_item.checkState(0) == Qt.Checked:
                        files_to_delete.append(file_item.text(0))
        
        if not files_to_delete:
            self.status_callback("هیچ فایلی برای حذف انتخاب نشده است!")
            return
        
        confirm = QMessageBox.question(
            self, "تایید حذف", 
            f"آیا از حذف {len(files_to_delete)} فایل انتخاب شده مطمئن هستید؟",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm != QMessageBox.Yes:
            return
        
        errors = []
        for file_path in files_to_delete:
            try:
                normalized_path = os.path.normpath(file_path)
                if self.deletion_method == "recycle_bin" and send2trash is not None:
                    send2trash(normalized_path)
                else:
                    os.remove(normalized_path)
            except Exception as e:
                error_msg = f"{file_path}: {e}"
                errors.append(error_msg)
                print("خطا:", error_msg)
        if errors:
            self.status_callback("برخی فایل‌ها حذف نشدند:\n" + "\n".join(errors))
        else:
            self.status_callback("فایل‌های انتخاب شده با موفقیت حذف شدند.")
            self.tray.showMessage("حذف فایل", "فایل‌های انتخاب شده حذف شدند.", QSystemTrayIcon.Information, 3000)
        self.accept()

class LargeFilesMainPage(QWidget):
    drivesScanned = pyqtSignal(list)
    
    def __init__(self, status_callback, tray):
        super().__init__()
        self.status_callback = status_callback
        self.tray = tray
        self.selected_paths = []
        self.deletion_method = "recycle_bin"
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        self.scanButton = QPushButton("اسکن درایوها و پوشه‌ها")
        self.scanButton.clicked.connect(self.scan_drives)
        layout.addWidget(self.scanButton)
        
        self.driveList = QListWidget()
        layout.addWidget(self.driveList)
        
        self.addFolderButton = QPushButton("افزودن پوشه منبع دلخواه")
        self.addFolderButton.clicked.connect(self.add_custom_folder)
        layout.addWidget(self.addFolderButton)
        
        self.startScanButton = QPushButton("شروع اسکن عمیق")
        self.startScanButton.clicked.connect(self.start_deep_scan)
        layout.addWidget(self.startScanButton)
        
        self.setLayout(layout)
    
    def scan_drives(self):
        try:
            self.driveList.clear()
            drives = []
            for part in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    drive_info = {
                        'device': part.device,
                        'mountpoint': part.mountpoint,
                        'total': usage.total,
                        'free': usage.free
                    }
                    drives.append(drive_info)
                except Exception as e:
                    self.status_callback(f"خطا در خواندن اطلاعات {part.device}: {e}")
            for d in drives:
                item_text = f"{d['device']} - {d['mountpoint']} | کل: {format_size(d['total'])} - آزاد: {format_size(d['free'])}"
                item = QListWidgetItem(item_text)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Unchecked)
                self.driveList.addItem(item)
            self.drivesScanned.emit(drives)
            self.status_callback("درایوها اسکن شدند.")
            self.tray.showMessage("اسکن", "درایوها اسکن شدند.", QSystemTrayIcon.Information, 3000)
        except Exception as e:
            self.status_callback(f"خطا در اسکن درایوها: {e}")
    
    def add_custom_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "انتخاب پوشه منبع دلخواه")
        if folder:
            item = QListWidgetItem(f"دلخواه: {folder}")
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            self.driveList.addItem(item)
            self.status_callback("پوشه منبع دلخواه اضافه شد.")
    
    def start_deep_scan(self):
        selected_paths = []
        for index in range(self.driveList.count()):
            item = self.driveList.item(index)
            if item.checkState() == Qt.Checked:
                text = item.text()
                if text.startswith("دلخواه:"):
                    path = text.replace("دلخواه: ", "").strip()
                    selected_paths.append(path)
                else:
                    parts = text.split(" - ")
                    if len(parts) >= 2:
                        mount_info = parts[1].split(" | ")[0].strip()
                        selected_paths.append(mount_info)
        
        if not selected_paths:
            self.status_callback("هیچ مسیر انتخاب نشده است!")
            return
        
        all_found_files = {}
        for path in selected_paths:
            self.status_callback(f"شروع اسکن عمیق در مسیر: {path}")
            found_files = self.deep_scan_path(path)
            for file_path in found_files:
                ext = os.path.splitext(file_path)[1].lower()
                all_found_files.setdefault(ext, []).append(file_path)
            self.status_callback(f"پایان اسکن مسیر {path}؛ تعداد فایل‌های یافت‌شده: {len(found_files)}")
            self.tray.showMessage("اسکن عمیق", f"مسیر {path}؛ فایل‌ها: {len(found_files)}", QSystemTrayIcon.Information, 3000)
        
        if all_found_files:
            dlg = FileGroupDialog(all_found_files, self.deletion_method, self.status_callback, self.tray)
            dlg.exec_()
        else:
            self.status_callback("هیچ فایل مناسبی یافت نشد.")
    
    def deep_scan_path(self, path):
        found_files = []
        for root, dirs, files in os.walk(path):
            for file in files:
                full_path = os.path.join(root, file)
                found_files.append(full_path)
        return found_files

class LargeFilesSettingsPage(QWidget):
    settingsSaved = pyqtSignal(dict)
    
    def __init__(self, status_callback):
        super().__init__()
        self.status_callback = status_callback
        self.allowed_extensions = []
        self.safe_directories = [
            "C:\\Windows", 
            "C:\\Users\\theal\\AppData\\Roaming", 
            "C:\\ProgramData", 
            "C:\\Program Files (x86)", 
            "C:\\Program Files"
        ]
        self.init_ui()
        self.load_config()
        
    def init_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        
        self.setStyleSheet("""
            QGroupBox {font-size: 16px; font-weight: bold; border: 2px solid #3498db; border-radius: 10px; margin-top: 10px;}
            QGroupBox::title {subcontrol-origin: margin; left: 10px; padding: 0 5px 0 5px;}
            QLabel {font-size: 14px;}
            QPushButton {background-color: #3498db; color: white; border-radius: 5px; padding: 5px 10px;}
            QPushButton:hover {background-color: #2980b9;}
            QListWidget {min-height: 100px;}
        """)
        
        files_group = QGroupBox("فایل‌هایی که باید اسکن شوند")
        files_layout = QVBoxLayout()
        self.sizeToggle = QCheckBox("فقط فایل‌های بزرگتر از:")
        files_layout.addWidget(self.sizeToggle)
        self.sizeSlider = QSlider(Qt.Horizontal)
        self.sizeSlider.setMinimum(1)
        self.sizeSlider.setMaximum(1024)
        self.sizeSlider.setValue(100)
        files_layout.addWidget(self.sizeSlider)
        self.sizeLabel = QLabel("100 مگابایت")
        self.sizeSlider.valueChanged.connect(lambda val: self.sizeLabel.setText(f"{val} مگابایت"))
        files_layout.addWidget(self.sizeLabel)
        self.extList = QListWidget()
        self.extList.setMinimumHeight(100)
        files_layout.addWidget(self.extList)
        ext_btn_layout = QHBoxLayout()
        self.addExtButton = QPushButton("افزودن پسوند")
        self.addExtButton.clicked.connect(self.add_extension)
        ext_btn_layout.addWidget(self.addExtButton)
        self.removeExtButton = QPushButton("حذف پسوند")
        self.removeExtButton.clicked.connect(self.remove_extension)
        ext_btn_layout.addWidget(self.removeExtButton)
        files_layout.addLayout(ext_btn_layout)
        files_group.setLayout(files_layout)
        layout.addWidget(files_group)
        
        delete_group = QGroupBox("روش حذف")
        delete_layout = QVBoxLayout()
        self.radioRecycle = QRadioButton("انتقال به سطل بازیافت")
        self.radioPermanent = QRadioButton("حذف دائمی")
        self.radioRecycle.setChecked(True)
        delete_layout.addWidget(self.radioRecycle)
        delete_layout.addWidget(self.radioPermanent)
        delete_group.setLayout(delete_layout)
        layout.addWidget(delete_group)
        
        additional_group = QGroupBox("اضافی")
        additional_layout = QVBoxLayout()
        self.safeModeCheck = QCheckBox("حالت امن")
        self.safeModeCheck.setToolTip("اگر فعال شود، پوشه‌های حساس به‌طور پیش‌فرض از اسکن حذف می‌شوند.")
        additional_layout.addWidget(self.safeModeCheck)
        self.safeList = QListWidget()
        self.safeList.setMinimumHeight(100)
        for dir in self.safe_directories:
            item = QListWidgetItem(dir)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            self.safeList.addItem(item)
        additional_layout.addWidget(self.safeList)
        additional_group.setLayout(additional_layout)
        layout.addWidget(additional_group)
        
        self.saveButton = QPushButton("ذخیره تنظیمات")
        self.saveButton.clicked.connect(self.save_settings)
        layout.addWidget(self.saveButton)
        
        layout.addStretch()
        scroll.setWidget(content_widget)
        main_layout = QVBoxLayout()
        main_layout.addWidget(scroll)
        self.setLayout(main_layout)
    
    def add_extension(self):
        file_path, ok = QFileDialog.getOpenFileName(self, "انتخاب یک فایل نمونه برای پسوند")
        if ok and file_path:
            _, extension = os.path.splitext(file_path)
            if extension and extension not in self.allowed_extensions:
                self.allowed_extensions.append(extension)
                self.extList.addItem(extension)
    
    def remove_extension(self):
        selected = self.extList.currentRow()
        if selected >= 0:
            self.allowed_extensions.pop(selected)
            self.extList.takeItem(selected)
    
    def save_settings(self):
        settings = {
            "only_scan_larger_than": self.sizeSlider.value() if self.sizeToggle.isChecked() else None,
            "allowed_extensions": self.allowed_extensions,
            "delete_method": "recycle_bin" if self.radioRecycle.isChecked() else "permanent",
            "safe_mode": self.safeModeCheck.isChecked(),
            "safe_directories": [self.safeList.item(i).text() for i in range(self.safeList.count()) if self.safeList.item(i).checkState() == Qt.Checked]
        }
        try:
            # حذف فایل کانفیگ قبلی در صورت وجود
            if os.path.exists(CONFIG_FILE):
                os.remove(CONFIG_FILE)
                print(f"فایل کانفیگ قبلی '{CONFIG_FILE}' حذف شد.")
            
            # ذخیره تنظیمات جدید
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=4)
            
            # مخفی‌سازی فایل کانفیگ
            try:
                os.system(f'attrib +h "{CONFIG_FILE}"')
            except Exception as e:
                print(f"خطا در مخفی‌سازی فایل پیکربندی: {e}")
            
            self.settingsSaved.emit(settings)
            self.status_callback("تنظیمات پیدا کردن فایل‌های حجیم ذخیره شدند.")
        except Exception as e:
            self.status_callback(f"خطا در ذخیره تنظیمات: {e}")
    
    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    settings = json.load(f)
                if settings.get("only_scan_larger_than") is not None:
                    self.sizeToggle.setChecked(True)
                    self.sizeSlider.setValue(settings["only_scan_larger_than"])
                    self.sizeLabel.setText(f"{settings['only_scan_larger_than']} مگابایت")
                else:
                    self.sizeToggle.setChecked(False)
                self.allowed_extensions = settings.get("allowed_extensions", [])
                self.extList.clear()
                for ext in self.allowed_extensions:
                    self.extList.addItem(ext)
                delete_method = settings.get("delete_method", "recycle_bin")
                if delete_method == "recycle_bin":
                    self.radioRecycle.setChecked(True)
                else:
                    self.radioPermanent.setChecked(True)
                self.safeModeCheck.setChecked(settings.get("safe_mode", False))
                safe_dirs = settings.get("safe_directories", [])
                for i in range(self.safeList.count()):
                    item = self.safeList.item(i)
                    if item.text() in safe_dirs:
                        item.setCheckState(Qt.Checked)
                    else:
                        item.setCheckState(Qt.Unchecked)
                self.status_callback("تنظیمات قبلی بارگذاری شدند.")
            except Exception as e:
                self.status_callback(f"خطا در بارگذاری تنظیمات: {e}")

class LargeFilesTab(QWidget):
    def __init__(self, status_callback, progress_callback, tray):
        super().__init__()
        self.status_callback = status_callback
        self.progress_callback = progress_callback
        self.tray = tray
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        self.sub_tabs = QTabWidget()
        self.main_page = LargeFilesMainPage(self.status_callback, self.tray)
        self.settings_page = LargeFilesSettingsPage(self.status_callback)
        self.settings_page.settingsSaved.connect(self.update_settings)
        self.sub_tabs.addTab(self.main_page, "صفحه اصلی")
        self.sub_tabs.addTab(self.settings_page, "تنظیمات")
        layout.addWidget(self.sub_tabs)
        self.setLayout(layout)
    
    def update_settings(self, settings):
        self.main_page.deletion_method = settings.get("delete_method", "recycle_bin")
        self.status_callback("تنظیمات حذف به‌روزرسانی شدند.")