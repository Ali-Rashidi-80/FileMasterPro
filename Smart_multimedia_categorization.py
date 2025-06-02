import os
import sys
import shutil
import cv2
import numpy as np
from ultralytics import YOLO
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QLabel, QProgressBar, QFileDialog, 
    QHBoxLayout, QStatusBar, QDialog, QSpinBox, QFormLayout, QListWidget, QListWidgetItem
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QPixmap, QFontDatabase
import concurrent.futures
import json
import math
import threading
import subprocess
import logging

logging.basicConfig(filename="app.log", level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

CONFIG_FILE = "image_classifier_config.json"

def resource_path(relative_path):
    """تعیین مسیر صحیح فایل‌ها در محیط توسعه و اجرایی (PyInstaller)"""
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class MediaClassificationThread(QThread):
    progress_signal = pyqtSignal(int)
    status_signal = pyqtSignal(str)
    file_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()
    preview_signal = pyqtSignal(str, str)  # مسیر تصویر، متن پیش‌نمایش

    def __init__(self, source_folders, accelerator, max_workers, detection_model, classification_model, obb_model, segmentation_model, frame_count):
        super().__init__()
        self.source_folders = source_folders
        self.accelerator = accelerator
        self.max_workers = max_workers
        self.detection_model = detection_model
        self.classification_model = classification_model
        self.obb_model = obb_model
        self.segmentation_model = segmentation_model
        self.frame_count = frame_count
        self.cancel_event = threading.Event()

    def run(self):
        try:
            for source_folder in self.source_folders:
                logging.info(f"شروع پردازش پوشه: {source_folder}")
                media_files = self.get_media_files(source_folder)
                total_media = len(media_files)

                if total_media == 0:
                    self.status_signal.emit(f"هیچ فایل رسانه‌ای در پوشه {source_folder} یافت نشد!")
                    continue

                if self.accelerator == "CUDA" and cv2.cuda.getCudaEnabledDeviceCount() > 0:
                    self.process_with_cuda(media_files, total_media, source_folder)
                elif self.accelerator == "UMat":
                    self.process_with_umat(media_files, total_media, source_folder)
                else:
                    self.process_with_cpu(media_files, total_media, source_folder)

            if not self.cancel_event.is_set():
                self.status_signal.emit("پردازش رسانه‌ها با موفقیت به پایان رسید.")
            else:
                self.status_signal.emit("پردازش لغو شد.")
            self.finished_signal.emit()

        except Exception as e:
            self.status_signal.emit(f"خطای عمومی: {str(e)}")
            logging.error(f"خطای عمومی: {str(e)}")
            self.finished_signal.emit()

    def get_media_files(self, folder):
        """جمع‌آوری تمامی تصاویر و ویدیوها در پوشه و زیرپوشه‌ها"""
        media_files = []
        for root, _, files in os.walk(folder):
            for file in files:
                if file.lower().endswith(('.png', '.jpg', '.jpeg', '.mp4', '.avi', '.mov', '.mkv', '.wmv')):
                    media_files.append(os.path.join(root, file))
        return media_files

    def process_with_cpu(self, media_files, total_media, source_folder):
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(self.process_media_cpu, media, source_folder): media for media in media_files}
            processed_count = 0

            for future in concurrent.futures.as_completed(futures):
                if self.cancel_event.is_set():
                    break
                try:
                    media_name = futures[future]
                    self.file_signal.emit(os.path.basename(media_name))
                    future.result()
                    processed_count += 1
                    self.progress_signal.emit(int(processed_count / total_media * 100))
                except Exception as e:
                    media_name = futures[future]
                    self.status_signal.emit(f"خطا در پردازش {os.path.basename(media_name)}: {str(e)}")
                    logging.error(f"خطا در پردازش {os.path.basename(media_name)}: {str(e)}")

    def process_media_cpu(self, media_file, source_folder):
        if self.cancel_event.is_set():
            return
        if not os.path.exists(media_file):
            logging.error(f"فایل وجود ندارد: {media_file}")
            return
        if media_file.lower().endswith(('.png', '.jpg', '.jpeg')):
            self.process_image_cpu(media_file, source_folder)
        elif media_file.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.wmv')):
            self.process_video_cpu(media_file, source_folder)

    def process_image_cpu(self, image_file, source_folder):
        image = cv2.imread(image_file)
        if image is None:
            raise ValueError(f"ناتوانی در بارگذاری تصویر: {image_file}")
        
        detection_results = self.detection_model(image)
        if detection_results and len(detection_results) > 0 and detection_results[0].boxes:
            confidences = [box.conf.item() for box in detection_results[0].boxes]
            conf_threshold = self.calculate_smart_threshold(confidences)
            max_conf_box = max(detection_results[0].boxes, key=lambda b: b.conf)
            if max_conf_box.conf >= conf_threshold:
                primary_class = detection_results[0].names[int(max_conf_box.cls)]
                conf = max_conf_box.conf.item()
                preview_text = f"تصویر: {os.path.basename(image_file)[:50]} | کلاس: {primary_class} | اطمینان: {conf:.2f}"
                self.preview_signal.emit(image_file, preview_text)
                self.save_result(image_file, primary_class, conf)
                dest_folder = os.path.join(source_folder, f"Detected_{primary_class}")
            else:
                dest_folder = os.path.join(source_folder, "Uncategorized")
        else:
            dest_folder = os.path.join(source_folder, "Uncategorized")

        os.makedirs(dest_folder, exist_ok=True)
        shutil.move(image_file, os.path.join(dest_folder, os.path.basename(image_file)[:100]))

    def process_video_cpu(self, video_file, source_folder):
        if not os.path.exists(video_file):
            logging.error(f"فایل وجود ندارد: {video_file}")
            return
        cap = cv2.VideoCapture(video_file)
        if not cap.isOpened():
            raise ValueError(f"ناتوانی در باز کردن ویدیو: {video_file}")

        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if frame_count == 0:
            cap.release()
            return

        frame_indices = np.random.choice(frame_count, min(self.frame_count, frame_count), replace=False)
        all_confidences = []
        for idx in frame_indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()
            if ret:
                detection_results = self.detection_model(frame)
                if detection_results and len(detection_results) > 0 and detection_results[0].boxes:
                    for box in detection_results[0].boxes:
                        conf = box.conf.item()
                        all_confidences.append(conf)
        conf_threshold = self.calculate_smart_threshold(all_confidences)

        class_confidences = {}
        for idx in frame_indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()
            if ret:
                detection_results = self.detection_model(frame)
                if detection_results and len(detection_results) > 0 and detection_results[0].boxes:
                    for box in detection_results[0].boxes:
                        conf = box.conf.item()
                        if conf >= conf_threshold:
                            cls = detection_results[0].names[int(box.cls)]
                            if cls in class_confidences:
                                class_confidences[cls] += conf
                            else:
                                class_confidences[cls] = conf

        cap.release()

        if class_confidences:
            most_confident_class = max(class_confidences, key=class_confidences.get)
            total_conf = class_confidences[most_confident_class]
            dest_folder = os.path.join(source_folder, f"Detected_{most_confident_class}")
            preview_text = f"ویدیو: {os.path.basename(video_file)[:50]} | کلاس: {most_confident_class} | اطمینان: {total_conf:.2f}"
            self.preview_signal.emit(video_file, preview_text)
            self.save_result(video_file, most_confident_class, total_conf)
        else:
            dest_folder = os.path.join(source_folder, "Uncategorized")

        os.makedirs(dest_folder, exist_ok=True)
        shutil.move(video_file, os.path.join(dest_folder, os.path.basename(video_file)[:100]))

    def process_with_cuda(self, media_files, total_media, source_folder):
        for i, media in enumerate(media_files):
            if self.cancel_event.is_set():
                break
            try:
                self.file_signal.emit(os.path.basename(media))
                self.process_media_cuda(media, source_folder)
                self.progress_signal.emit(int((i + 1) / total_media * 100))
            except Exception as e:
                self.status_signal.emit(f"خطا در پردازش {os.path.basename(media)}: {str(e)}")
                logging.error(f"خطا در پردازش {os.path.basename(media)}: {str(e)}")

    def process_media_cuda(self, media_file, source_folder):
        if not os.path.exists(media_file):
            logging.error(f"فایل وجود ندارد: {media_file}")
            return
        if media_file.lower().endswith(('.png', '.jpg', '.jpeg')):
            self.process_image_cuda(media_file, source_folder)
        elif media_file.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.wmv')):
            self.process_video_cuda(media_file, source_folder)

    def process_image_cuda(self, image_file, source_folder):
        image = cv2.imread(image_file)
        if image is None:
            raise ValueError(f"ناتوانی در بارگذاری تصویر: {image_file}")
        
        gpu_image = cv2.cuda_GpuMat()
        gpu_image.upload(image)
        image_data = gpu_image.download()
        
        detection_results = self.detection_model(image_data)
        if detection_results and len(detection_results) > 0 and detection_results[0].boxes:
            confidences = [box.conf.item() for box in detection_results[0].boxes]
            conf_threshold = self.calculate_smart_threshold(confidences)
            max_conf_box = max(detection_results[0].boxes, key=lambda b: b.conf)
            if max_conf_box.conf >= conf_threshold:
                primary_class = detection_results[0].names[int(max_conf_box.cls)]
                conf = max_conf_box.conf.item()
                preview_text = f"تصویر: {os.path.basename(image_file)[:50]} | کلاس: {primary_class} | اطمینان: {conf:.2f}"
                self.preview_signal.emit(image_file, preview_text)
                self.save_result(image_file, primary_class, conf)
                dest_folder = os.path.join(source_folder, f"Detected_{primary_class}")
            else:
                dest_folder = os.path.join(source_folder, "Uncategorized")
        else:
            dest_folder = os.path.join(source_folder, "Uncategorized")

        os.makedirs(dest_folder, exist_ok=True)
        shutil.move(image_file, os.path.join(dest_folder, os.path.basename(image_file)[:100]))

    def process_video_cuda(self, video_file, source_folder):
        if not os.path.exists(video_file):
            logging.error(f"فایل وجود ندارد: {video_file}")
            return
        cap = cv2.VideoCapture(video_file)
        if not cap.isOpened():
            raise ValueError(f"ناتوانی در باز کردن ویدیو: {video_file}")

        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if frame_count == 0:
            cap.release()
            return

        frame_indices = np.random.choice(frame_count, min(self.frame_count, frame_count), replace=False)
        all_confidences = []
        for idx in frame_indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()
            if ret:
                gpu_frame = cv2.cuda_GpuMat()
                gpu_frame.upload(frame)
                frame_data = gpu_frame.download()
                detection_results = self.detection_model(frame_data)
                if detection_results and len(detection_results) > 0 and detection_results[0].boxes:
                    for box in detection_results[0].boxes:
                        conf = box.conf.item()
                        all_confidences.append(conf)
        conf_threshold = self.calculate_smart_threshold(all_confidences)

        class_confidences = {}
        for idx in frame_indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()
            if ret:
                gpu_frame = cv2.cuda_GpuMat()
                gpu_frame.upload(frame)
                frame_data = gpu_frame.download()
                detection_results = self.detection_model(frame_data)
                if detection_results and len(detection_results) > 0 and detection_results[0].boxes:
                    for box in detection_results[0].boxes:
                        conf = box.conf.item()
                        if conf >= conf_threshold:
                            cls = detection_results[0].names[int(box.cls)]
                            if cls in class_confidences:
                                class_confidences[cls] += conf
                            else:
                                class_confidences[cls] = conf

        cap.release()

        if class_confidences:
            most_confident_class = max(class_confidences, key=class_confidences.get)
            total_conf = class_confidences[most_confident_class]
            dest_folder = os.path.join(source_folder, f"Detected_{most_confident_class}")
            preview_text = f"ویدیو: {os.path.basename(video_file)[:50]} | کلاس: {most_confident_class} | اطمینان: {total_conf:.2f}"
            self.preview_signal.emit(video_file, preview_text)
            self.save_result(video_file, most_confident_class, total_conf)
        else:
            dest_folder = os.path.join(source_folder, "Uncategorized")

        os.makedirs(dest_folder, exist_ok=True)
        shutil.move(video_file, os.path.join(dest_folder, os.path.basename(video_file)[:100]))

    def process_with_umat(self, media_files, total_media, source_folder):
        for i, media in enumerate(media_files):
            if self.cancel_event.is_set():
                break
            try:
                self.file_signal.emit(os.path.basename(media))
                self.process_media_umat(media, source_folder)
                self.progress_signal.emit(int((i + 1) / total_media * 100))
            except Exception as e:
                self.status_signal.emit(f"خطا در پردازش {os.path.basename(media)}: {str(e)}")
                logging.error(f"خطا در پردازش {os.path.basename(media)}: {str(e)}")

    def process_media_umat(self, media_file, source_folder):
        if not os.path.exists(media_file):
            logging.error(f"فایل وجود ندارد: {media_file}")
            return
        if media_file.lower().endswith(('.png', '.jpg', '.jpeg')):
            self.process_image_umat(media_file, source_folder)
        elif media_file.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.wmv')):
            self.process_video_umat(media_file, source_folder)

    def process_image_umat(self, image_file, source_folder):
        image = cv2.UMat(cv2.imread(image_file))
        if image is None:
            raise ValueError(f"ناتوانی در بارگذاری تصویر: {image_file}")
        
        image_data = image.get()
        detection_results = self.detection_model(image_data)
        if detection_results and len(detection_results) > 0 and detection_results[0].boxes:
            confidences = [box.conf.item() for box in detection_results[0].boxes]
            conf_threshold = self.calculate_smart_threshold(confidences)
            max_conf_box = max(detection_results[0].boxes, key=lambda b: b.conf)
            if max_conf_box.conf >= conf_threshold:
                primary_class = detection_results[0].names[int(max_conf_box.cls)]
                conf = max_conf_box.conf.item()
                preview_text = f"تصویر: {os.path.basename(image_file)[:50]} | کلاس: {primary_class} | اطمینان: {conf:.2f}"
                self.preview_signal.emit(image_file, preview_text)
                self.save_result(image_file, primary_class, conf)
                dest_folder = os.path.join(source_folder, f"Detected_{primary_class}")
            else:
                dest_folder = os.path.join(source_folder, "Uncategorized")
        else:
            dest_folder = os.path.join(source_folder, "Uncategorized")

        os.makedirs(dest_folder, exist_ok=True)
        shutil.move(image_file, os.path.join(dest_folder, os.path.basename(image_file)[:100]))

    def process_video_umat(self, video_file, source_folder):
        if not os.path.exists(video_file):
            logging.error(f"فایل وجود ندارد: {video_file}")
            return
        cap = cv2.VideoCapture(video_file)
        if not cap.isOpened():
            raise ValueError(f"ناتوانی در باز کردن ویدیو: {video_file}")

        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if frame_count == 0:
            cap.release()
            return

        frame_indices = np.random.choice(frame_count, min(self.frame_count, frame_count), replace=False)
        all_confidences = []
        for idx in frame_indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()
            if ret:
                frame_umat = cv2.UMat(frame)
                frame_data = frame_umat.get()
                detection_results = self.detection_model(frame_data)
                if detection_results and len(detection_results) > 0 and detection_results[0].boxes:
                    for box in detection_results[0].boxes:
                        conf = box.conf.item()
                        all_confidences.append(conf)
        conf_threshold = self.calculate_smart_threshold(all_confidences)

        class_confidences = {}
        for idx in frame_indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()
            if ret:
                frame_umat = cv2.UMat(frame)
                frame_data = frame_umat.get()
                detection_results = self.detection_model(frame_data)
                if detection_results and len(detection_results) > 0 and detection_results[0].boxes:
                    for box in detection_results[0].boxes:
                        conf = box.conf.item()
                        if conf >= conf_threshold:
                            cls = detection_results[0].names[int(box.cls)]
                            if cls in class_confidences:
                                class_confidences[cls] += conf
                            else:
                                class_confidences[cls] = conf

        cap.release()

        if class_confidences:
            most_confident_class = max(class_confidences, key=class_confidences.get)
            total_conf = class_confidences[most_confident_class]
            dest_folder = os.path.join(source_folder, f"Detected_{most_confident_class}")
            preview_text = f"ویدیو: {os.path.basename(video_file)[:50]} | کلاس: {most_confident_class} | اطمینان: {total_conf:.2f}"
            self.preview_signal.emit(video_file, preview_text)
            self.save_result(video_file, most_confident_class, total_conf)
        else:
            dest_folder = os.path.join(source_folder, "Uncategorized")

        os.makedirs(dest_folder, exist_ok=True)
        shutil.move(video_file, os.path.join(dest_folder, os.path.basename(video_file)[:100]))

    def calculate_smart_threshold(self, confidences):
        """محاسبه آستانه اطمینان پویا بر اساس صدک 75"""
        if not confidences:
            return 0.5
        confidences = np.array(confidences)
        threshold = np.percentile(confidences, 75)
        return max(0.4, min(0.8, threshold))

    def save_result(self, media_file, class_name, confidence):
        """ذخیره نتایج در فایل CSV"""
        with open("results.csv", "a", encoding="utf-8") as f:
            f.write(f"{media_file},{class_name},{confidence}\n")

    def cancel(self):
        self.cancel_event.set()

class SettingsDialog(QDialog):
    """دیالوگ برای تنظیمات پیشرفته"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("تنظیمات پیشرفته")
        self.setLayout(QVBoxLayout())
        self.setStyleSheet("background-color: #ffffff; border-radius: 10px; padding: 15px;")
        self.setFixedWidth(400)

        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        self.cpu_usage_spin = QSpinBox()
        self.cpu_usage_spin.setStyleSheet("""
            QSpinBox {
                padding: 8px;
                border-radius: 5px;
                border: 1px solid #ced4da;
                background-color: #ffffff;
                font-size: 14px;
            }
            QSpinBox:hover, QSpinBox:focus {
                border: 1px solid #28a745;
            }
        """)
        self.cpu_usage_spin.setRange(1, 100)
        self.cpu_usage_spin.setValue(70)
        self.cpu_usage_spin.setSuffix("%")
        self.cpu_usage_spin.setToolTip("درصد استفاده از CPU را برای پردازش تنظیم کنید.")
        form_layout.addRow("درصد استفاده از CPU:", self.cpu_usage_spin)

        self.frame_count_spin = QSpinBox()
        self.frame_count_spin.setStyleSheet("""
            QSpinBox {
                padding: 8px;
                border-radius: 5px;
                border: 1px solid #ced4da;
                background-color: #ffffff;
                font-size: 14px;
            }
            QSpinBox:hover, QSpinBox:focus {
                border: 1px solid #28a745;
            }
        """)
        self.frame_count_spin.setRange(1, 20)
        self.frame_count_spin.setValue(5)
        self.frame_count_spin.setToolTip("تعداد فریم‌هایی که از ویدیوها برای تحلیل انتخاب می‌شوند.")
        form_layout.addRow("تعداد فریم‌های تحلیل‌شده:", self.frame_count_spin)

        self.layout().addLayout(form_layout)

        buttons_layout = QHBoxLayout()
        save_btn = QPushButton("ذخیره")
        save_btn.setStyleSheet("""
            QPushButton {
                padding: 10px;
                border-radius: 5px;
                background-color: #28a745;
                color: white;
                font-size: 14px;
                font-weight: bold;
                border: none;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        save_btn.clicked.connect(self.accept)
        buttons_layout.addWidget(save_btn)

        cancel_btn = QPushButton("انصراف")
        cancel_btn.setStyleSheet("""
            QPushButton {
                padding: 10px;
                border-radius: 5px;
                background-color: #dc3545;
                color: white;
                font-size: 14px;
                font-weight: bold;
                border: none;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)

        self.layout().addLayout(buttons_layout)

class ImagePreviewDialog(QDialog):
    """دیالوگ برای نمایش تصویر بزرگ‌تر هنگام کلیک"""
    def __init__(self, image_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("پیش‌نمایش تصویر")
        self.setLayout(QVBoxLayout())
        self.setStyleSheet("background-color: #ffffff; border-radius: 10px; padding: 10px;")
        self.setFixedSize(850, 650)

        image_label = QLabel()
        pixmap = QPixmap(image_path).scaled(800, 600, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        image_label.setPixmap(pixmap)
        image_label.setAlignment(Qt.AlignCenter)
        self.layout().addWidget(image_label)

        close_btn = QPushButton("بستن")
        close_btn.setStyleSheet("""
            QPushButton {
                padding: 10px;
                border-radius: 5px;
                background-color: #dc3545;
                color: white;
                font-size: 14px;
                font-weight: bold;
                border: none;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
        """)
        close_btn.clicked.connect(self.close)
        self.layout().addWidget(close_btn)

class MediaClassifierTab(QWidget):
    def __init__(self, status_callback, tray):
        super().__init__()
        self.setLayoutDirection(Qt.LeftToRight)
        self.status_callback = status_callback
        self.tray = tray
        self.source_folder = ""
        self.accelerator = None
        
        self.detection_model = YOLO(resource_path("Models/Detection (COCO)/yolo11x.pt"))
        self.classification_model = YOLO(resource_path("Models/Classification (ImageNet)/yolo11x-cls.pt"))
        self.obb_model = YOLO(resource_path("Models/Oriented Bounding Boxes (DOTAv1)/yolo11x-obb.pt"))
        self.segmentation_model = YOLO(resource_path("Models/Segmentation (COCO)/yolo11x-seg.pt"))
        
        self.init_ui()
        self.load_settings()
        self.detect_accelerator()

    def init_ui(self):
        # بارگذاری فونت فارسی
        font_db = QFontDatabase()
        font_id = font_db.addApplicationFont(resource_path("fonts/Vazir-Regular.ttf"))
        font_family = "Arial"
        if font_id != -1:
            font_families = font_db.applicationFontFamilies(font_id)
            if font_families:
                font_family = font_families[0]

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignTop)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        # استایل‌های مشترک
        button_style = """
            QPushButton {
                padding: 12px;
                border-radius: 8px;
                color: white;
                font-size: 14px;
                font-weight: bold;
                border: none;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """
        start_button_style = button_style + """
            QPushButton {
                background-color: #28a745;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """
        cancel_button_style = button_style + """
            QPushButton {
                background-color: #dc3545;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
        """
        label_style = f"font-family: '{font_family}'; font-size: 14px; color: #2c3e50;"
        list_style = """
            QListWidget {
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                background-color: #ffffff;
                padding: 10px;
                font-size: 14px;
            }
            QListWidget::item {
                padding: 8px;
                border-radius: 5px;
            }
            QListWidget::item:hover {
                background-color: #f8f9fa;
            }
        """

        # تنظیم استایل کلی
        self.setStyleSheet(f"""
            QWidget {{
                font-family: '{font_family}';
                font-size: 14px;
                background-color: #f4f6f9;
            }}
        """)

        # عنوان
        title_label = QLabel("دسته‌بندی هوشمند رسانه‌ها")
        title_label.setFont(QFont(font_family, 20, QFont.Bold))
        title_label.setStyleSheet(f"font-family: '{font_family}'; font-size: 20px; color: #2c3e50;")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # بخش انتخاب پوشه
        folder_layout = QHBoxLayout()
        folder_layout.setSpacing(10)

        self.folder_label = QLabel("پوشه رسانه انتخاب نشده است.")
        self.folder_label.setStyleSheet(label_style + "padding: 8px; border: 1px solid #e0e0e0; border-radius: 5px; background-color: #ffffff;")
        self.folder_label.setToolTip("مسیر پوشه انتخاب‌شده برای پردازش رسانه‌ها")
        folder_layout.addWidget(self.folder_label)

        self.select_folder_btn = QPushButton("📁 انتخاب پوشه")
        self.select_folder_btn.setStyleSheet(button_style + """
            QPushButton {
                background-color: #007bff;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        self.select_folder_btn.clicked.connect(self.select_source_folder)
        self.select_folder_btn.setToolTip("یک پوشه حاوی تصاویر یا ویدیوها انتخاب کنید.")
        folder_layout.addWidget(self.select_folder_btn)

        layout.addLayout(folder_layout)

        # بخش کنترل‌ها
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(10)

        self.start_btn = QPushButton("▶ شروع پردازش")
        self.start_btn.setStyleSheet(start_button_style)
        self.start_btn.clicked.connect(self.start_processing)
        self.start_btn.setEnabled(False)
        self.start_btn.setToolTip("پردازش و دسته‌بندی رسانه‌ها را آغاز کنید.")
        controls_layout.addWidget(self.start_btn)

        self.cancel_btn = QPushButton("⏹ انصراف")
        self.cancel_btn.setStyleSheet(cancel_button_style)
        self.cancel_btn.clicked.connect(self.cancel_processing)
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setToolTip("پردازش در حال اجرا را لغو کنید.")
        controls_layout.addWidget(self.cancel_btn)

        self.settings_btn = QPushButton("⚙ تنظیمات پیشرفته")
        self.settings_btn.setStyleSheet(button_style + """
            QPushButton {
                background-color: #6c757d;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        self.settings_btn.clicked.connect(self.show_settings_dialog)
        self.settings_btn.setToolTip("تنظیمات پیشرفته پردازش را مشاهده یا ویرایش کنید.")
        controls_layout.addWidget(self.settings_btn)

        layout.addLayout(controls_layout)

        # برچسب شتاب‌دهنده
        self.accelerator_label = QLabel("شتاب‌دهنده: در حال تشخیص...")
        self.accelerator_label.setFont(QFont(font_family, 12))
        self.accelerator_label.setStyleSheet(label_style + "padding: 8px; border: 1px solid #e0e0e0; border-radius: 5px; background-color: #ffffff;")
        self.accelerator_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.accelerator_label)

        # نوار پیشرفت
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #e0e0e0;
                border-radius: 5px;
                text-align: center;
                height: 25px;
                background-color: #ffffff;
                font-size: 14px;
                color: #2c3e50;
            }
            QProgressBar::chunk {
                background-color: #28a745;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.progress_bar)

        # برچسب وضعیت فایل
        self.current_file_label = QLabel("در حال پردازش: هیچ")
        self.current_file_label.setFont(QFont(font_family, 12))
        self.current_file_label.setStyleSheet(label_style)
        self.current_file_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.current_file_label)

        # بخش پیش‌نمایش
        self.preview_list = QListWidget()
        self.preview_list.setStyleSheet(list_style)
        self.preview_list.setFlow(QListWidget.LeftToRight)
        self.preview_list.setWrapping(True)
        self.preview_list.setResizeMode(QListWidget.Adjust)
        self.preview_list.setSpacing(10)
        self.preview_list.itemClicked.connect(self.show_image_preview)
        layout.addWidget(self.preview_list)

        # نوار وضعیت
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet("""
            QStatusBar {
                background-color: #ffffff;
                border-top: 1px solid #e0e0e0;
                padding: 8px;
                font-size: 14px;
                color: #2c3e50;
            }
            QStatusBar::item[error="true"] {
                color: #dc3545;
            }
        """)
        self.status_bar.showMessage("لطفاً یک پوشه رسانه انتخاب کنید.", 5000)
        layout.addWidget(self.status_bar)

        self.setLayout(layout)

    def show_settings_dialog(self):
        """نمایش دیالوگ تنظیمات پیشرفته"""
        dialog = SettingsDialog(self)
        dialog.cpu_usage_spin.setValue(self.cpu_usage_percent)
        dialog.frame_count_spin.setValue(self.frame_count)
        
        if dialog.exec_():
            self.cpu_usage_percent = dialog.cpu_usage_spin.value()
            self.frame_count = dialog.frame_count_spin.value()
            self.save_settings()
            self.status_callback("تنظیمات ذخیره شد.")

    def show_image_preview(self, item):
        """نمایش تصویر بزرگ‌تر هنگام کلیک روی آیتم پیش‌نمایش"""
        image_path = item.data(Qt.UserRole)
        if image_path and os.path.exists(image_path):
            dialog = ImagePreviewDialog(image_path, self)
            dialog.exec_()

    def load_settings(self):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
                self.cpu_usage_percent = config.get("cpu_usage_percent", 70)
                self.frame_count = config.get("frame_count", 5)
        except FileNotFoundError:
            self.cpu_usage_percent = 70
            self.frame_count = 5
        except json.JSONDecodeError:
            self.status_callback("خطا در بارگذاری تنظیمات: فایل JSON نامعتبر است.")

    def save_settings(self):
        config = {
            "cpu_usage_percent": self.cpu_usage_percent,
            "frame_count": self.frame_count
        }
        try:
            if os.path.exists(CONFIG_FILE):
                os.remove(CONFIG_FILE)
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
            if os.name == "nt":
                subprocess.run(["attrib", "+h", CONFIG_FILE])
        except Exception as e:
            self.status_callback(f"خطا در ذخیره تنظیمات: {str(e)}")

    def detect_accelerator(self):
        if cv2.cuda.getCudaEnabledDeviceCount() > 0:
            self.accelerator = "CUDA"
        elif hasattr(cv2, 'UMat'):
            self.accelerator = "UMat"
        else:
            self.accelerator = "CPU"
        self.accelerator_label.setText(f"شتاب‌دهنده: {self.accelerator}")
        self.status_callback(f"شتاب‌دهنده انتخاب‌شده: {self.accelerator}")
        if self.source_folder:
            self.start_btn.setEnabled(True)

    def select_source_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "انتخاب پوشه رسانه", "", QFileDialog.ShowDirsOnly)
        if folder:
            self.source_folder = folder
            self.folder_label.setText(folder)
            self.status_callback(f"پوشه انتخاب شد: {folder}")
            self.start_btn.setEnabled(True if self.accelerator else False)

    def start_processing(self):
        if not self.source_folder:
            self.status_callback("لطفاً ابتدا یک پوشه رسانه انتخاب کنید!")
            return
        if not self.accelerator:
            self.status_callback("لطفاً ابتدا شتاب‌دهنده را تشخیص دهید!")
            return

        self.start_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.select_folder_btn.setEnabled(False)
        self.settings_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.current_file_label.setText("در حال پردازش: هیچ")
        self.preview_list.clear()

        if self.accelerator == "CPU":
            total_cores = os.cpu_count()
            max_workers = max(1, math.ceil(total_cores * (self.cpu_usage_percent / 100.0)))
        else:
            max_workers = 1

        self.thread = MediaClassificationThread(
            [self.source_folder], self.accelerator, max_workers,
            self.detection_model, self.classification_model,
            self.obb_model, self.segmentation_model,
            self.frame_count
        )
        self.thread.progress_signal.connect(self.update_progress)
        self.thread.status_signal.connect(self.update_status)
        self.thread.file_signal.connect(self.update_current_file)
        self.thread.preview_signal.connect(self.add_to_preview)
        self.thread.finished_signal.connect(self.processing_finished)
        self.thread.start()

    def cancel_processing(self):
        if hasattr(self, 'thread') and self.thread.isRunning():
            self.thread.cancel()
            self.status_callback("پردازش لغو شد.")
            self.progress_bar.setValue(0)
            self.current_file_label.setText("در حال پردازش: هیچ")

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def update_status(self, message):
        if "خطا" in message:
            self.status_bar.setStyleSheet("""
                QStatusBar {
                    background-color: #ffffff;
                    border-top: 1px solid #e0e0e0;
                    padding: 8px;
                    font-size: 14px;
                    color: #dc3545;
                }
            """)
        else:
            self.status_bar.setStyleSheet("""
                QStatusBar {
                    background-color: #ffffff;
                    border-top: 1px solid #e0e0e0;
                    padding: 8px;
                    font-size: 14px;
                    color: #2c3e50;
                }
            """)
        self.status_bar.showMessage(message, 5000)
        self.status_callback(message)

    def update_current_file(self, file_name):
        self.current_file_label.setText(f"در حال پردازش: {file_name}")

    def add_to_preview(self, image_path, preview_text):
        """افزودن تصویر و متن به پیش‌نمایش با چیدمان گالری"""
        item_widget = QWidget()
        item_layout = QVBoxLayout()
        item_layout.setContentsMargins(5, 5, 5, 5)
        
        pixmap = QPixmap(image_path).scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        image_label = QLabel()
        image_label.setPixmap(pixmap)
        image_label.setStyleSheet("border-radius: 5px; border: 1px solid #e0e0e0;")
        image_label.setAlignment(Qt.AlignCenter)
        item_layout.addWidget(image_label)
        
        text_label = QLabel(preview_text)
        text_label.setStyleSheet("font-size: 12px; color: #2c3e50; text-align: center;")
        text_label.setWordWrap(True)
        item_layout.addWidget(text_label)
        
        item_widget.setLayout(item_layout)
        list_item = QListWidgetItem()
        list_item.setSizeHint(item_widget.sizeHint())
        list_item.setData(Qt.UserRole, image_path)
        self.preview_list.addItem(list_item)
        self.preview_list.setItemWidget(list_item, item_widget)

    def processing_finished(self):
        self.start_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.select_folder_btn.setEnabled(True)
        self.settings_btn.setEnabled(True)
        self.status_bar.showMessage("پردازش به پایان رسید.", 5000)
        self.current_file_label.setText("در حال پردازش: هیچ")
        self.tray.showMessage("دسته‌بندی رسانه‌ها", "پردازش رسانه‌ها به اتمام رسید.", 3000)