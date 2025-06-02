import os, json, math, psutil, hashlib, time
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog, QMessageBox,
    QLabel, QListWidget, QListWidgetItem, QSlider, QTabWidget, QGroupBox, QCheckBox,
    QRadioButton, QTreeWidget, QTreeWidgetItem, QDialog, QProgressBar, QSystemTrayIcon, QComboBox, QScrollArea
)
from PyQt5.QtCore import Qt, pyqtSignal, QThread
from PyQt5.QtGui import QFont

# مسیر فایل پیکربندی این تب
CONFIG_FILE = "config_duplicate_files_tab.json"

# تنظیمات پیش‌فرض
default_config = {
    "exclude_list": [
        r"C:\Windows",
        r"C:\Users\theal\AppData\Local\Packages",
        r"C:\Users\theal\AppData\Local\Temp",
        r"C:\Users\theal\AppData\Roaming",
        r"C:\ProgramData",
        r"C:\Program Files (x86)",
        r"C:\Program Files"
    ],
    "allowed_file_types": ["*.*"],
    "only_scan_larger_than": None,
    "scan_extensions_only": [],
    "duplicate_criteria": "name_size",  # گزینه‌ها: name_size, md5, byte_by_byte
    "delete_method": "recycle_bin"      # گزینه‌ها: recycle_bin, permanent
}

# ایجاد فایل پیکربندی در صورت عدم وجود و مخفی‌سازی آن
if not os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(default_config, f, indent=4)
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

# دسته‌بندی پسوندها
FILE_CATEGORIES = {
    "آرشیوها": [".zip", ".rar", ".7z", ".tar", ".gz"],
    "اسناد": [".doc", ".docx", ".pdf", ".txt", ".xls", ".xlsx", ".ppt", ".pptx"],
    "موسیقی": [".mp3", ".wav", ".flac", ".aac", ".ogg"],
    "ویدیوها": [".mp4", ".mkv", ".avi", ".mov", ".wmv"],
    "تصاویر": [".jpg", ".jpeg", ".png", ".gif", ".bmp"],
}

def get_file_category(file_path):
    _, ext = os.path.splitext(file_path.lower())
    for category, extensions in FILE_CATEGORIES.items():
        if ext in extensions:
            return category
    return "سایر"

# توابع کمکی برای تشخیص فایل‌های تکراری
def get_file_md5(file_path, block_size=65536):
    md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            while True:
                data = f.read(block_size)
                if not data:
                    break
                md5.update(data)
        return md5.hexdigest()
    except Exception:
        return None

def are_files_identical(file1, file2, block_size=65536):
    try:
        with open(file1, "rb") as f1, open(file2, "rb") as f2:
            while True:
                b1 = f1.read(block_size)
                b2 = f2.read(block_size)
                if b1 != b2:
                    return False
                if not b1:
                    return True
    except Exception:
        return False

def group_files_by_byte_to_byte(files):
    groups = {}
    processed = set()
    for i in range(len(files)):
        file1 = files[i]
        if file1 in processed:
            continue
        group = [file1]
        processed.add(file1)
        for j in range(i + 1, len(files)):
            file2 = files[j]
            if file2 in processed:
                continue
            if are_files_identical(file1, file2):
                group.append(file2)
                processed.add(file2)
        if len(group) > 1:
            groups[file1] = group
    return groups

# کلاس رشته‌ای برای اسکن و گروه‌بندی فایل‌های تکراری
class DuplicateScanWorker(QThread):
    progress_changed = pyqtSignal(int)
    status_update = pyqtSignal(str)
    result = pyqtSignal(dict)

    def __init__(self, paths, criteria):
        super().__init__()
        self.paths = paths
        self.criteria = criteria

    def run(self):
        all_found_files = []
        total_paths = len(self.paths)
        count = 0
        for path in self.paths:
            self.status_update.emit(f"اسکن مسیر: {path}")
            for root, dirs, files in os.walk(path):
                for file in files:
                    all_found_files.append(os.path.join(root, file))
            count += 1
            self.progress_changed.emit(int(count/total_paths*50))
        duplicate_groups = {}
        total_files = len(all_found_files)
        processed_count = 0
        if self.criteria == "name_size":
            temp = {}
            for file_path in all_found_files:
                try:
                    key = (os.path.basename(file_path), os.path.getsize(file_path))
                except Exception:
                    continue
                temp.setdefault(key, []).append(file_path)
                processed_count += 1
                self.progress_changed.emit(50 + int(processed_count/total_files*25))
            duplicate_groups = {str(k): v for k, v in temp.items() if len(v) > 1}
        elif self.criteria == "md5":
            temp = {}
            for file_path in all_found_files:
                key = get_file_md5(file_path)
                if key:
                    temp.setdefault(key, []).append(file_path)
                processed_count += 1
                self.progress_changed.emit(50 + int(processed_count/total_files*25))
            duplicate_groups = {key: v for key, v in temp.items() if len(v) > 1}
        elif self.criteria == "byte_by_byte":
            size_groups = {}
            for file_path in all_found_files:
                try:
                    size = os.path.getsize(file_path)
                except Exception:
                    continue
                size_groups.setdefault(size, []).append(file_path)
                processed_count += 1
                self.progress_changed.emit(50 + int(processed_count/total_files*15))
            for size, files in size_groups.items():
                if len(files) > 1:
                    groups = group_files_by_byte_to_byte(files)
                    for k, v in groups.items():
                        duplicate_groups[k] = v
            self.progress_changed.emit(75)
        self.progress_changed.emit(100)
        self.result.emit(duplicate_groups)

# دیالوگ نمایش فایل‌های گروه‌بندی شده
class DuplicateFilesGroupDialog(QDialog):
    def __init__(self, duplicate_groups, deletion_method, status_callback, tray):
        super().__init__()
        self.setWindowTitle("نتایج اسکن فایل‌های تکراری")
        self.duplicate_groups = duplicate_groups
        self.deletion_method = deletion_method
        self.status_callback = status_callback
        self.tray = tray
        self.resize(1000, 700)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # گزینه‌های انتخاب
        select_layout = QHBoxLayout()
        select_label = QLabel("گزینه‌های انتخاب:")
        select_layout.addWidget(select_label)
        self.select_combo = QComboBox()
        self.select_combo.addItems([
            "انتخاب دستی",
            "نگهداری قدیمی‌ترین ایجاد شده",
            "نگهداری جدیدترین ایجاد شده"
        ])
        self.select_combo.currentTextChanged.connect(self.apply_selection)
        select_layout.addWidget(self.select_combo)
        layout.addLayout(select_layout)

        # گروه‌بندی
        category_layout = QHBoxLayout()
        category_label = QLabel("نمایش بر اساس:")
        category_layout.addWidget(category_label)
        self.category_combo = QComboBox()
        self.category_combo.addItems([
            "همه فایل‌ها",
            "آرشیوها",
            "اسناد",
            "موسیقی",
            "ویدیوها",
            "تصاویر",
            "سایر"
        ])
        self.category_combo.currentTextChanged.connect(self.update_tree)
        category_layout.addWidget(self.category_combo)
        layout.addLayout(category_layout)

        # درخت فایل‌ها
        self.tree = QTreeWidget()
        self.tree.setColumnCount(4)
        self.tree.setHeaderLabels(["فایل", "حجم", "تاریخ دسترسی", "تاریخ ایجاد"])
        self.tree.header().setDefaultSectionSize(300)
        font = QFont("Tahoma", 10)
        self.tree.setFont(font)
        self.update_tree()
        layout.addWidget(self.tree)

        # دکمه‌ها
        action_layout = QHBoxLayout()
        self.delete_button = QPushButton("حذف فایل‌های انتخاب شده")
        self.delete_button.clicked.connect(self.delete_selected_files)
        action_layout.addWidget(self.delete_button)
        self.cancel_button = QPushButton("انصراف")
        self.cancel_button.clicked.connect(self.reject)
        action_layout.addWidget(self.cancel_button)
        layout.addLayout(action_layout)

        self.setLayout(layout)

    def update_tree(self):
        self.tree.clear()
        selected_category = self.category_combo.currentText()
        for group_key, files in self.duplicate_groups.items():
            if len(files) < 2:
                continue
            group_files = []
            for file_path in files:
                category = get_file_category(file_path)
                if selected_category == "همه فایل‌ها" or category == selected_category:
                    group_files.append(file_path)
            if not group_files:
                continue
            group_title = f"گروه: {group_key} ({len(group_files)} فایل)"
            group_item = QTreeWidgetItem(self.tree, [group_title, "", "", ""])
            group_item.setFlags(group_item.flags() | Qt.ItemIsUserCheckable)
            group_item.setCheckState(0, Qt.Unchecked)
            for file_path in group_files:
                try:
                    size = os.path.getsize(file_path)
                    atime = time.ctime(os.path.getatime(file_path))
                    ctime = time.ctime(os.path.getctime(file_path))
                except Exception:
                    size = 0
                    atime = "نامشخص"
                    ctime = "نامشخص"
                file_item = QTreeWidgetItem(group_item, [file_path, format_size(size), atime, ctime])
                file_item.setFlags(file_item.flags() | Qt.ItemIsUserCheckable)
                file_item.setCheckState(0, Qt.Unchecked)
        self.tree.expandAll()

    def apply_selection(self, selection_mode):
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            group_item = root.child(i)
            files = []
            for j in range(group_item.childCount()):
                file_item = group_item.child(j)
                file_path = file_item.text(0)
                try:
                    ctime = os.path.getctime(file_path)
                except Exception:
                    ctime = float('inf') if "قدیمی‌ترین" in selection_mode else float('-inf')
                files.append((file_path, ctime))
            if not files:
                continue
            if selection_mode == "انتخاب دستی":
                for j in range(group_item.childCount()):
                    group_item.child(j).setCheckState(0, Qt.Unchecked)
            elif selection_mode == "نگهداری قدیمی‌ترین ایجاد شده":
                oldest_ctime = min(f[1] for f in files)
                for j in range(group_item.childCount()):
                    file_item = group_item.child(j)
                    file_ctime = files[j][1]
                    file_item.setCheckState(0, Qt.Unchecked if file_ctime != oldest_ctime else Qt.Checked)
            elif selection_mode == "نگهداری جدیدترین ایجاد شده":
                latest_ctime = max(f[1] for f in files)
                for j in range(group_item.childCount()):
                    file_item = group_item.child(j)
                    file_ctime = files[j][1]
                    file_item.setCheckState(0, Qt.Unchecked if file_ctime != latest_ctime else Qt.Checked)

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
                if self.deletion_method == "recycle_bin":
                    from send2trash import send2trash
                    send2trash(normalized_path)
                else:
                    os.remove(normalized_path)
            except Exception as e:
                errors.append(f"{file_path}: {e}")
        if errors:
            self.status_callback("برخی فایل‌ها حذف نشدند:\n" + "\n".join(errors))
        else:
            self.status_callback("فایل‌های انتخاب شده با موفقیت حذف شدند.")
            self.tray.showMessage("حذف فایل", "فایل‌های انتخاب شده حذف شدند.", QSystemTrayIcon.Information, 3000)
        self.accept()

# صفحه اصلی تب فایل‌های تکراری
class DuplicateFilesMainPage(QWidget):
    def __init__(self, status_callback, tray):
        super().__init__()
        self.status_callback = status_callback
        self.tray = tray
        self.deletion_method = default_config.get("delete_method", "recycle_bin")
        self.duplicate_criteria = default_config.get("duplicate_criteria", "name_size")
        self.worker = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.progressBar = QProgressBar()
        self.progressBar.setMinimum(0)
        self.progressBar.setMaximum(100)
        self.progressBar.setValue(0)
        layout.addWidget(self.progressBar)
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
                    self.status_callback(f"خطا در خواندن {part.device}: {e}")
            for d in drives:
                item_text = (f"{d['device']} - {d['mountpoint']} | کل: {format_size(d['total'])} - "
                             f"آزاد: {format_size(d['free'])}")
                item = QListWidgetItem(item_text)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Unchecked)
                self.driveList.addItem(item)
            self.status_callback("درایوها اسکن شدند.")
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
        for i in range(self.driveList.count()):
            item = self.driveList.item(i)
            if item.checkState() == Qt.Checked:
                text = item.text()
                if text.startswith("دلخواه:"):
                    selected_paths.append(text.replace("دلخواه: ", "").strip())
                else:
                    parts = text.split(" - ")
                    if len(parts) >= 2:
                        mount_info = parts[1].split(" | ")[0].strip()
                        selected_paths.append(mount_info)
        if not selected_paths:
            self.status_callback("هیچ مسیر انتخاب نشده است!")
            return
        self.scanButton.setEnabled(False)
        self.addFolderButton.setEnabled(False)
        self.startScanButton.setEnabled(False)
        self.progressBar.setValue(0)
        self.status_callback("شروع اسکن عمیق...")
        self.worker = DuplicateScanWorker(selected_paths, self.duplicate_criteria)
        self.worker.progress_changed.connect(self.progressBar.setValue)
        self.worker.status_update.connect(self.status_callback)
        self.worker.result.connect(self.handle_scan_result)
        self.worker.start()

    def handle_scan_result(self, duplicate_groups):
        self.scanButton.setEnabled(True)
        self.addFolderButton.setEnabled(True)
        self.startScanButton.setEnabled(True)
        if duplicate_groups:
            dlg = DuplicateFilesGroupDialog(duplicate_groups, self.deletion_method, self.status_callback, self.tray)
            dlg.exec_()
        else:
            self.status_callback("هیچ فایل تکراری یافت نشد.")

# صفحه تنظیمات تب فایل‌های تکراری
class DuplicateFilesSettingsPage(QWidget):
    settingsSaved = pyqtSignal(dict)

    def __init__(self, status_callback):
        super().__init__()
        self.status_callback = status_callback
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

        self.excludeGroup = QGroupBox("لیست مستثنی")
        ex_layout = QVBoxLayout()
        ex_label = QLabel("دیسک‌ها و دایرکتوری‌هایی که باید از اسکن مستثنی شوند را اضافه کنید:")
        ex_layout.addWidget(ex_label)
        self.excludeList = QListWidget()
        self.excludeList.setMinimumHeight(100)
        ex_layout.addWidget(self.excludeList)
        ex_btn_layout = QHBoxLayout()
        self.addExcludeBtn = QPushButton("افزودن")
        self.addExcludeBtn.clicked.connect(self.add_exclude)
        self.removeExcludeBtn = QPushButton("حذف")
        self.removeExcludeBtn.clicked.connect(self.remove_exclude)
        ex_btn_layout.addWidget(self.addExcludeBtn)
        ex_btn_layout.addWidget(self.removeExcludeBtn)
        ex_layout.addLayout(ex_btn_layout)
        self.excludeGroup.setLayout(ex_layout)
        layout.addWidget(self.excludeGroup)

        self.fileTypeGroup = QGroupBox("نوع فایل")
        ft_layout = QVBoxLayout()
        ft_label = QLabel("نوع فایل‌هایی را که می‌خواهید اسکن کنید انتخاب کنید:")
        ft_layout.addWidget(ft_label)
        self.fileTypeList = QListWidget()
        self.fileTypeList.setMinimumHeight(100)
        ft_layout.addWidget(self.fileTypeList)
        ft_btn_layout = QHBoxLayout()
        self.addFileTypeBtn = QPushButton("افزودن")
        self.addFileTypeBtn.clicked.connect(self.add_file_type)
        self.removeFileTypeBtn = QPushButton("حذف")
        self.removeFileTypeBtn.clicked.connect(self.remove_file_type)
        ft_btn_layout.addWidget(self.addFileTypeBtn)
        ft_btn_layout.addWidget(self.removeFileTypeBtn)
        ft_layout.addLayout(ft_btn_layout)
        self.fileTypeGroup.setLayout(ft_layout)
        layout.addWidget(self.fileTypeGroup)

        self.fileSizeGroup = QGroupBox("اندازه فایل")
        fs_layout = QVBoxLayout()
        self.sizeCheck = QCheckBox("فقط فایل‌های بزرگتر از:")
        fs_layout.addWidget(self.sizeCheck)
        self.sizeSlider = QSlider(Qt.Horizontal)
        self.sizeSlider.setMinimum(1)
        self.sizeSlider.setMaximum(1024)
        self.sizeSlider.setValue(100)
        fs_layout.addWidget(self.sizeSlider)
        self.sizeLabel = QLabel("100 مگابایت")
        self.sizeSlider.valueChanged.connect(lambda val: self.sizeLabel.setText(f"{val} مگابایت"))
        fs_layout.addWidget(self.sizeLabel)
        ext_label = QLabel("فقط فایل‌هایی با پسوندهای زیر اسکن شوند:")
        fs_layout.addWidget(ext_label)
        self.extList = QListWidget()
        self.extList.setMinimumHeight(100)
        fs_layout.addWidget(self.extList)
        fs_btn_layout = QHBoxLayout()
        self.addExtBtn = QPushButton("افزودن")
        self.addExtBtn.clicked.connect(self.add_extension)
        self.removeExtBtn = QPushButton("حذف")
        self.removeExtBtn.clicked.connect(self.remove_extension)
        fs_btn_layout.addWidget(self.addExtBtn)
        fs_btn_layout.addWidget(self.removeExtBtn)
        fs_layout.addLayout(fs_btn_layout)
        self.fileSizeGroup.setLayout(fs_layout)
        layout.addWidget(self.fileSizeGroup)

        self.dupCriteriaGroup = QGroupBox("معیار تکراری")
        dc_layout = QVBoxLayout()
        dc_label = QLabel("معیاری را که بر اساس آن فایل‌های تکراری شناسایی می‌شوند مشخص کنید:")
        dc_layout.addWidget(dc_label)
        self.radioNameSize = QRadioButton("نام فایل و اندازه فایل")
        self.radioMD5 = QRadioButton("MD5")
        self.radioByte = QRadioButton("بایت به بایت")
        self.radioNameSize.setChecked(True)
        dc_layout.addWidget(self.radioNameSize)
        dc_layout.addWidget(self.radioMD5)
        dc_layout.addWidget(self.radioByte)
        self.dupCriteriaGroup.setLayout(dc_layout)
        layout.addWidget(self.dupCriteriaGroup)

        self.deleteMethodGroup = QGroupBox("روش حذف")
        dm_layout = QVBoxLayout()
        self.radioRecycle = QRadioButton("انتقال به سطل بازیافت")
        self.radioPermanent = QRadioButton("حذف دائمی")
        self.radioRecycle.setChecked(True)
        dm_layout.addWidget(self.radioRecycle)
        dm_layout.addWidget(self.radioPermanent)
        self.deleteMethodGroup.setLayout(dm_layout)
        layout.addWidget(self.deleteMethodGroup)

        self.saveBtn = QPushButton("ذخیره تنظیمات")
        self.saveBtn.clicked.connect(self.save_settings)
        layout.addWidget(self.saveBtn)

        layout.addStretch()
        scroll.setWidget(content_widget)
        main_layout = QVBoxLayout()
        main_layout.addWidget(scroll)
        self.setLayout(main_layout)

    def add_exclude(self):
        path = QFileDialog.getExistingDirectory(self, "انتخاب مسیر برای اضافه کردن")
        if path:
            item = QListWidgetItem(path)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            self.excludeList.addItem(item)

    def remove_exclude(self):
        row = self.excludeList.currentRow()
        if row >= 0:
            self.excludeList.takeItem(row)

    def add_file_type(self):
        file_type, ok = QFileDialog.getOpenFileName(self, "انتخاب یک فایل نمونه برای پسوند")
        if ok and file_type:
            _, ext = os.path.splitext(file_type)
            if ext and ext not in [self.fileTypeList.item(i).text() for i in range(self.fileTypeList.count())]:
                self.fileTypeList.addItem(ext)

    def remove_file_type(self):
        row = self.fileTypeList.currentRow()
        if row >= 0:
            self.fileTypeList.takeItem(row)

    def add_extension(self):
        ext, ok = QFileDialog.getOpenFileName(self, "انتخاب یک فایل نمونه برای پسوند")
        if ok and ext:
            _, extension = os.path.splitext(ext)
            if extension and extension not in [self.extList.item(i).text() for i in range(self.extList.count())]:
                self.extList.addItem(extension)

    def remove_extension(self):
        row = self.extList.currentRow()
        if row >= 0:
            self.extList.takeItem(row)

    def save_settings(self):
        settings = {
            "exclude_list": [self.excludeList.item(i).text() for i in range(self.excludeList.count()) if self.excludeList.item(i).checkState() == Qt.Checked],
            "allowed_file_types": [self.fileTypeList.item(i).text() for i in range(self.fileTypeList.count())],
            "only_scan_larger_than": self.sizeSlider.value() if self.sizeCheck.isChecked() else None,
            "scan_extensions_only": [self.extList.item(i).text() for i in range(self.extList.count())],
            "duplicate_criteria": "name_size" if self.radioNameSize.isChecked() else ("md5" if self.radioMD5.isChecked() else "byte_by_byte"),
            "delete_method": "recycle_bin" if self.radioRecycle.isChecked() else "permanent"
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
            self.status_callback("تنظیمات فایل‌های تکراری ذخیره شدند.")
        except Exception as e:
            self.status_callback(f"خطا در ذخیره تنظیمات: {e}")

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    settings = json.load(f)
                self.excludeList.clear()
                for path in settings.get("exclude_list", default_config["exclude_list"]):
                    item = QListWidgetItem(path)
                    item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                    item.setCheckState(Qt.Checked)
                    self.excludeList.addItem(item)
                self.fileTypeList.clear()
                for ft in settings.get("allowed_file_types", default_config["allowed_file_types"]):
                    self.fileTypeList.addItem(ft)
                if settings.get("only_scan_larger_than") is not None:
                    self.sizeCheck.setChecked(True)
                    self.sizeSlider.setValue(settings["only_scan_larger_than"])
                    self.sizeLabel.setText(f"{settings['only_scan_larger_than']} مگابایت")
                else:
                    self.sizeCheck.setChecked(False)
                self.extList.clear()
                for ext in settings.get("scan_extensions_only", []):
                    self.extList.addItem(ext)
                crit = settings.get("duplicate_criteria", "name_size")
                if crit == "name_size":
                    self.radioNameSize.setChecked(True)
                elif crit == "md5":
                    self.radioMD5.setChecked(True)
                else:
                    self.radioByte.setChecked(True)
                if settings.get("delete_method", "recycle_bin") == "recycle_bin":
                    self.radioRecycle.setChecked(True)
                else:
                    self.radioPermanent.setChecked(True)
                self.status_callback("تنظیمات قبلی فایل‌های تکراری بارگذاری شدند.")
            except Exception as e:
                self.status_callback(f"خطا در بارگذاری تنظیمات: {e}")

# کلاس اصلی تب فایل‌های تکراری
class DuplicateFilesTab(QWidget):
    def __init__(self, status_callback, tray):
        super().__init__()
        self.status_callback = status_callback
        self.tray = tray
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.tabs = QTabWidget()
        self.main_page = DuplicateFilesMainPage(self.status_callback, self.tray)
        self.settings_page = DuplicateFilesSettingsPage(self.status_callback)
        self.settings_page.settingsSaved.connect(self.update_settings)
        self.tabs.addTab(self.main_page, "صفحه اصلی")
        self.tabs.addTab(self.settings_page, "تنظیمات")
        layout.addWidget(self.tabs)
        self.setLayout(layout)

    def update_settings(self, new_settings):
        self.main_page.deletion_method = new_settings.get("delete_method", "recycle_bin")
        self.main_page.duplicate_criteria = new_settings.get("duplicate_criteria", "name_size")
        self.status_callback("تنظیمات تب فایل‌های تکراری به‌روزرسانی شدند.")