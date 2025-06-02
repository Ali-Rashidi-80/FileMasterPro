import os
import shutil
import cv2
import mediapipe as mp
import numpy as np
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QProgressBar, QFileDialog, QGroupBox, QFormLayout, QSpinBox, QDoubleSpinBox, QCheckBox, QListWidget, QListWidgetItem, QHBoxLayout, QToolButton
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QIcon
import concurrent.futures
import json
import math
import threading
import subprocess
import colorama
from colorama import Fore, Style

colorama.init()

CONFIG_FILE = "face_finder_config.json"

class FaceDetectionThread(QThread):
    progress_signal = pyqtSignal(int)
    status_signal = pyqtSignal(str)
    file_signal = pyqtSignal(str)  # سیگنال جدید برای ارسال نام فایل
    finished_signal = pyqtSignal()

    def __init__(self, source_folders, accelerator, max_workers, min_detection_confidence):
        super().__init__()
        self.source_folders = source_folders
        self.accelerator = accelerator
        self.max_workers = max_workers
        self.min_detection_confidence = min_detection_confidence
        self.cancel_event = threading.Event()
        self.mp_face_detection = mp.solutions.face_detection
        self.face_detection = self.mp_face_detection.FaceDetection(model_selection=1, min_detection_confidence=self.min_detection_confidence)

    def run(self):
        try:
            for source_folder in self.source_folders:
                with_face_folder = os.path.join(source_folder, "With_Face")
                without_face_folder = os.path.join(source_folder, "Without_Face")
                os.makedirs(with_face_folder, exist_ok=True)
                os.makedirs(without_face_folder, exist_ok=True)

                image_files = [f for f in os.listdir(source_folder) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
                total_images = len(image_files)

                if total_images == 0:
                    self.status_signal.emit(f"هیچ تصویری در پوشه {source_folder} یافت نشد!")
                    continue

                if self.accelerator == "CUDA" and cv2.cuda.getCudaEnabledDeviceCount() > 0:
                    self.process_with_cuda(image_files, total_images, source_folder, with_face_folder, without_face_folder)
                elif self.accelerator == "UMat":
                    self.process_with_umat(image_files, total_images, source_folder, with_face_folder, without_face_folder)
                else:
                    self.process_with_cpu(image_files, total_images, source_folder, with_face_folder, without_face_folder)

            if not self.cancel_event.is_set():
                self.status_signal.emit("پردازش تصاویر با موفقیت به پایان رسید.")
            else:
                self.status_signal.emit("پردازش لغو شد.")
            self.finished_signal.emit()

        except Exception as e:
            self.status_signal.emit(f"خطای عمومی: {str(e)}")
            print(Fore.RED + f"General error: {str(e)}" + Style.RESET_ALL)
            self.finished_signal.emit()

    def process_with_cpu(self, image_files, total_images, source_folder, with_face_folder, without_face_folder):
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(self.process_image_cpu, img, source_folder, with_face_folder, without_face_folder): img for img in image_files}
            processed_count = 0

            for future in concurrent.futures.as_completed(futures):
                if self.cancel_event.is_set():
                    break
                try:
                    img_name = futures[future]
                    self.file_signal.emit(img_name)  # ارسال نام فایل
                    future.result()
                    processed_count += 1
                    self.progress_signal.emit(int(processed_count / total_images * 100))
                except Exception as e:
                    img_name = futures[future]
                    self.status_signal.emit(f"خطا در پردازش {img_name}: {str(e)}")
                    print(Fore.RED + f"Error processing {img_name}: {str(e)}" + Style.RESET_ALL)

    def process_with_umat(self, image_files, total_images, source_folder, with_face_folder, without_face_folder):
        for i, img in enumerate(image_files):
            if self.cancel_event.is_set():
                break
            try:
                self.file_signal.emit(img)  # ارسال نام فایل
                self.process_image_umat(img, source_folder, with_face_folder, without_face_folder)
                self.progress_signal.emit(int((i + 1) / total_images * 100))
            except Exception as e:
                self.status_signal.emit(f"خطا در پردازش {img}: {str(e)}")
                print(Fore.RED + f"Error processing {img}: {str(e)}" + Style.RESET_ALL)

    def process_with_cuda(self, image_files, total_images, source_folder, with_face_folder, without_face_folder):
        for i, img in enumerate(image_files):
            if self.cancel_event.is_set():
                break
            try:
                self.file_signal.emit(img)  # ارسال نام فایل
                self.process_image_cuda(img, source_folder, with_face_folder, without_face_folder)
                self.progress_signal.emit(int((i + 1) / total_images * 100))
            except Exception as e:
                self.status_signal.emit(f"خطا در پردازش {img}: {str(e)}")
                print(Fore.RED + f"Error processing {img}: {str(e)}" + Style.RESET_ALL)

    def process_image_cpu(self, image_file, source_folder, with_face_folder, without_face_folder):
        if self.cancel_event.is_set():
            return
        image_path = os.path.join(source_folder, image_file)
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"ناتوانی در بارگذاری تصویر: {image_file}")
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = self.face_detection.process(image_rgb)
        dest_folder = with_face_folder if results.detections else without_face_folder
        shutil.move(image_path, os.path.join(dest_folder, image_file))

    def process_image_umat(self, image_file, source_folder, with_face_folder, without_face_folder):
        if self.cancel_event.is_set():
            return
        image_path = os.path.join(source_folder, image_file)
        image = cv2.UMat(cv2.imread(image_path))
        if image is None:
            raise ValueError(f"ناتوانی در بارگذاری تصویر: {image_file}")
        image_rgb = cv2.UMat(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        results = self.face_detection.process(image_rgb.get())
        dest_folder = with_face_folder if results.detections else without_face_folder
        shutil.move(image_path, os.path.join(dest_folder, image_file))

    def process_image_cuda(self, image_file, source_folder, with_face_folder, without_face_folder):
        if self.cancel_event.is_set():
            return
        image_path = os.path.join(source_folder, image_file)
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"ناتوانی در بارگذاری تصویر: {image_file}")
        gpu_image = cv2.cuda_GpuMat()
        gpu_image.upload(image)
        gpu_image_rgb = cv2.cuda.cvtColor(gpu_image, cv2.COLOR_BGR2RGB)
        image_rgb = gpu_image_rgb.download()
        results = self.face_detection.process(image_rgb)
        dest_folder = with_face_folder if results.detections else without_face_folder
        shutil.move(image_path, os.path.join(dest_folder, image_file))

    def cancel(self):
        self.cancel_event.set()

class FaceFinderTab(QWidget):
    def __init__(self, status_callback, tray):
        super().__init__()
        self.setLayoutDirection(Qt.RightToLeft)  # راست‌چین کردن کل رابط کاربری
        self.status_callback = status_callback
        self.tray = tray
        self.source_folders = []
        self.accelerator = None
        self.init_ui()
        self.load_settings()
        self.detect_accelerator()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignTop)
        layout.setSpacing(15)

        title_label = QLabel("پیدا کردن چهره در تصاویر")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        self.select_folders_btn = QPushButton("انتخاب پوشه‌های تصاویر")
        self.select_folders_btn.setStyleSheet("""
            QPushButton { background-color: #4CAF50; color: white; padding: 10px; border-radius: 5px; font-size: 14px; }
            QPushButton:hover { background-color: #45a049; }
        """)
        self.select_folders_btn.clicked.connect(self.select_source_folders)
        self.select_folders_btn.setToolTip("پوشه‌هایی را انتخاب کنید که حاوی تصاویر مورد نظر برای پردازش و تشخیص چهره هستند.")
        layout.addWidget(self.select_folders_btn)

        self.folders_list = QListWidget()
        self.folders_list.setStyleSheet("QListWidget { border: 1px solid #ccc; border-radius: 5px; padding: 5px; }")
        layout.addWidget(self.folders_list)

        self.start_btn = QPushButton("شروع پردازش")
        self.start_btn.setStyleSheet("""
            QPushButton { background-color: #2196F3; color: white; padding: 10px; border-radius: 5px; font-size: 14px; }
            QPushButton:hover { background-color: #1e88e5; }
            QPushButton:disabled { background-color: #cccccc; }
        """)
        self.start_btn.clicked.connect(self.start_processing)
        self.start_btn.setEnabled(False)
        self.start_btn.setToolTip("پردازش تصاویر برای تشخیص چهره را آغاز کنید.")
        layout.addWidget(self.start_btn)

        self.cancel_btn = QPushButton("انصراف")
        self.cancel_btn.setStyleSheet("""
            QPushButton { background-color: #f44336; color: white; padding: 10px; border-radius: 5px; font-size: 14px; }
            QPushButton:hover { background-color: #e53935; }
            QPushButton:disabled { background-color: #cccccc; }
        """)
        self.cancel_btn.clicked.connect(self.cancel_processing)
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setToolTip("پردازش در حال اجرا را لغو کنید.")
        layout.addWidget(self.cancel_btn)

        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet("""
            QProgressBar { border: 2px solid grey; border-radius: 5px; text-align: center; height: 25px; }
            QProgressBar::chunk { background-color: #4CAF50; width: 10px; }
        """)
        layout.addWidget(self.progress_bar)

        self.current_file_label = QLabel("در حال پردازش: هیچ")  # برچسب جدید برای نمایش نام فایل
        self.current_file_label.setFont(QFont("Arial", 12))
        self.current_file_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.current_file_label)

        self.status_label = QLabel("لطفاً پوشه‌های تصاویر را انتخاب کنید.")
        self.status_label.setFont(QFont("Arial", 12))
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

        self.settings_group = QGroupBox("تنظیمات پیشرفته")
        settings_layout = QFormLayout()
        self.disable_accelerator_check = QCheckBox("بدون استفاده از شتاب‌دهنده سخت‌افزاری")
        self.disable_accelerator_check.stateChanged.connect(self.on_disable_accelerator_changed)
        settings_layout.addRow(self.disable_accelerator_check)
        self.cpu_usage_label = QLabel("درصد استفاده از CPU:")
        self.cpu_usage_spin = QSpinBox()
        self.cpu_usage_spin.setRange(1, 100)
        self.cpu_usage_spin.setValue(70)
        self.cpu_usage_spin.setSuffix("%")
        settings_layout.addRow(self.cpu_usage_label, self.cpu_usage_spin)
        self.confidence_spin = QDoubleSpinBox()
        self.confidence_spin.setRange(0.0, 1.0)
        self.confidence_spin.setSingleStep(0.1)
        self.confidence_spin.setValue(0.5)
        settings_layout.addRow("حداقل اطمینان تشخیص چهره:", self.confidence_spin)
        self.settings_group.setLayout(settings_layout)
        layout.addWidget(self.settings_group)

        self.save_settings_btn = QPushButton("ذخیره تنظیمات")
        self.save_settings_btn.setStyleSheet("""
            QPushButton { background-color: #FF9800; color: white; padding: 10px; border-radius: 5px; font-size: 14px; }
            QPushButton:hover { background-color: #F57C00; }
        """)
        self.save_settings_btn.clicked.connect(self.save_settings)
        layout.addWidget(self.save_settings_btn)

        self.setLayout(layout)

    def load_settings(self):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
                self.disable_accelerator_check.setChecked(config.get("disable_accelerator", False))
                self.cpu_usage_spin.setValue(config.get("cpu_usage_percent", 70))
                self.confidence_spin.setValue(config.get("min_detection_confidence", 0.5))
        except FileNotFoundError:
            pass
        except json.JSONDecodeError:
            self.status_callback("خطا در بارگذاری تنظیمات: فایل JSON نامعتبر است.")

    def save_settings(self):
        config = {
            "disable_accelerator": self.disable_accelerator_check.isChecked(),
            "cpu_usage_percent": self.cpu_usage_spin.value(),
            "min_detection_confidence": self.confidence_spin.value()
        }
        try:
            if os.path.exists(CONFIG_FILE):
                os.remove(CONFIG_FILE)
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
            if os.name == "nt":
                subprocess.run(["attrib", "+h", CONFIG_FILE])
            self.status_callback("تنظیمات با موفقیت ذخیره و فایل مخفی شد.")
            self.start_btn.setEnabled(True)
        except Exception as e:
            self.status_callback(f"خطا در ذخیره تنظیمات: {str(e)}")

    def detect_accelerator(self):
        if self.disable_accelerator_check.isChecked():
            self.accelerator = "CPU"
            self.cpu_usage_label.setVisible(True)
            self.cpu_usage_spin.setVisible(True)
        else:
            if cv2.cuda.getCudaEnabledDeviceCount() > 0:
                self.accelerator = "CUDA"
            elif cv2.UMat:
                self.accelerator = "UMat"
            else:
                self.accelerator = "CPU"
            self.cpu_usage_label.setVisible(False)
            self.cpu_usage_spin.setVisible(False)
        self.status_callback(f"شتاب‌دهنده تشخیص‌داده‌شده: {self.accelerator}")
        self.start_btn.setEnabled(True)

    def on_disable_accelerator_changed(self, state):
        self.detect_accelerator()

    def select_source_folders(self):
        folder = QFileDialog.getExistingDirectory(self, "انتخاب پوشه‌های تصاویر", "", QFileDialog.ShowDirsOnly)
        if folder and folder not in self.source_folders:
            self.source_folders.append(folder)
            item_widget = QWidget()
            item_layout = QHBoxLayout()
            item_layout.setContentsMargins(0, 0, 0, 0)
            item_label = QLabel(folder)
            item_label.setStyleSheet("padding: 5px;")
            delete_btn = QToolButton()
            delete_btn.setIcon(QIcon("icons/delete.png"))  # فرض بر وجود آیکون حذف
            delete_btn.setToolTip("حذف پوشه")
            delete_btn.clicked.connect(lambda: self.remove_folder(folder))
            item_layout.addWidget(delete_btn)
            item_layout.addWidget(item_label)
            item_layout.addStretch()
            item_widget.setLayout(item_layout)
            list_item = QListWidgetItem()
            list_item.setSizeHint(item_widget.sizeHint())
            self.folders_list.addItem(list_item)
            self.folders_list.setItemWidget(list_item, item_widget)
            self.status_callback(f"پوشه منبع انتخاب شد: {folder}")

    def remove_folder(self, folder):
        if folder in self.source_folders:
            self.source_folders.remove(folder)
            for i in range(self.folders_list.count()):
                item = self.folders_list.item(i)
                widget = self.folders_list.itemWidget(item)
                if widget and widget.findChild(QLabel).text() == folder:
                    self.folders_list.takeItem(i)
                    break
            self.status_callback(f"پوشه {folder} از لیست حذف شد.")

    def start_processing(self):
        if not self.source_folders:
            self.status_callback("لطفاً ابتدا پوشه‌های منبع را انتخاب کنید!")
            return
        if not self.accelerator:
            self.status_callback("لطفاً ابتدا شتاب‌دهنده را تشخیص دهید!")
            return

        self.start_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.select_folders_btn.setVisible(False)
        self.folders_list.setVisible(False)
        self.save_settings_btn.setVisible(False)
        self.settings_group.setVisible(False)
        self.status_label.setVisible(False)
        self.progress_bar.setValue(0)
        self.current_file_label.setText("در حال پردازش: هیچ")

        if self.accelerator == "CPU":
            cpu_usage_percent = self.cpu_usage_spin.value()
            total_cores = os.cpu_count()
            max_workers = max(1, math.ceil(total_cores * (cpu_usage_percent / 100.0)))
        else:
            max_workers = 1

        min_detection_confidence = self.confidence_spin.value()

        self.thread = FaceDetectionThread(self.source_folders, self.accelerator, max_workers, min_detection_confidence)
        self.thread.progress_signal.connect(self.update_progress)
        self.thread.status_signal.connect(self.update_status)
        self.thread.file_signal.connect(self.update_current_file)  # اتصال سیگنال جدید
        self.thread.finished_signal.connect(self.processing_finished)
        self.thread.start()

    def cancel_processing(self):
        if hasattr(self, 'thread') and self.thread.isRunning():
            self.thread.cancel()
            self.status_callback("در حال لغو پردازش...")
            self.progress_bar.setValue(0)
            self.current_file_label.setText("در حال پردازش: هیچ")

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def update_status(self, message):
        self.status_label.setText(message)
        self.status_callback(message)

    def update_current_file(self, file_name):
        self.current_file_label.setText(f"در حال پردازش: {file_name}")

    def processing_finished(self):
        self.start_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.select_folders_btn.setVisible(True)
        self.folders_list.setVisible(True)
        self.save_settings_btn.setVisible(True)
        self.settings_group.setVisible(True)
        self.status_label.setVisible(True)
        self.status_label.setText("پردازش به پایان رسید.")
        self.current_file_label.setText("در حال پردازش: هیچ")
        self.tray.showMessage("پردازش چهره", "پردازش تصاویر به اتمام رسید.", 3000)