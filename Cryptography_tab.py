import os
import datetime
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout, QPushButton, QProgressBar, QFileDialog, QMessageBox, QComboBox, QLabel, QGroupBox, QFormLayout
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt
from cryptography.hazmat.primitives.asymmetric import rsa, padding, ec
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import padding as sym_padding
from cryptography.hazmat.backends import default_backend
import secrets

class CryptographyTab(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        """تنظیم رابط کاربری تب با UI/UX بهبودیافته و متون راست‌چین"""
        self.setLayoutDirection(Qt.RightToLeft)

        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)

        # گروه انتخاب الگوریتم
        algo_group = QGroupBox("انتخاب الگوریتم")
        algo_group.setStyleSheet("""
            QGroupBox { font-weight: bold; border: 1px solid #ccc; border-radius: 5px; padding: 10px; }
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top right; padding: 0 5px; }
        """)
        algo_group.setAlignment(Qt.AlignRight)

        algo_layout = QFormLayout()
        algo_layout.setLabelAlignment(Qt.AlignRight)
        algo_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        algo_layout.setHorizontalSpacing(10)
        algo_layout.setVerticalSpacing(10)

        algo_label = QLabel("الگوریتم رمزنگاری:")
        algo_label.setFont(QFont("Arial", 18))
        algo_label.setStyleSheet("color: #333;")
        algo_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        algo_label.setToolTip("الگوریتم رمزنگاری مورد نظر را انتخاب کنید")

        self.algo_combo = QComboBox()
        self.algo_combo.addItems(["RSA", "AES", "ECC", "ChaCha20"])
        self.algo_combo.setStyleSheet("""
            QComboBox { padding: 5px; border: 1px solid #ccc; border-radius: 3px; text-align: right; }
            QComboBox QAbstractItemView { text-align: right; padding: 5px; }
        """)
        self.algo_combo.setToolTip("الگوریتم رمزنگاری مورد نظر را انتخاب کنید")
        self.algo_combo.setMinimumWidth(250)
        self.algo_combo.currentTextChanged.connect(self.update_ui_based_on_algo)

        algo_layout.addRow(algo_label, self.algo_combo)
        algo_group.setLayout(algo_layout)
        layout.addWidget(algo_group)

        # گروه عملیات
        operations_group = QGroupBox("عملیات")
        operations_group.setStyleSheet("""
            QGroupBox { font-weight: bold; border: 1px solid #ccc; border-radius: 5px; padding: 10px; }
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top right; padding: 0 5px; }
        """)
        operations_group.setAlignment(Qt.AlignRight)
        operations_layout = QGridLayout()
        operations_layout.setSpacing(10)

        self.generate_button = QPushButton("تولید کلید")
        self.generate_button.setStyleSheet("""
            QPushButton { background-color: #4CAF50; color: white; padding: 8px; border-radius: 5px; text-align: center; }
        """)
        self.generate_button.setToolTip("تولید کلیدهای رمزنگاری برای الگوریتم انتخاب‌شده")
        self.generate_button.clicked.connect(self.on_generate_keys)
        operations_layout.addWidget(self.generate_button, 0, 0)

        self.encrypt_button = QPushButton("رمزنگاری فایل")
        self.encrypt_button.setStyleSheet("""
            QPushButton { background-color: #2196F3; color: white; padding: 8px; border-radius: 5px; text-align: center; }
        """)
        self.encrypt_button.setToolTip("رمزنگاری فایل با استفاده از کلید عمومی یا متقارن")
        self.encrypt_button.clicked.connect(self.on_encrypt_file)
        operations_layout.addWidget(self.encrypt_button, 0, 1)

        self.decrypt_button = QPushButton("رمزگشایی فایل")
        self.decrypt_button.setStyleSheet("""
            QPushButton { background-color: #FF5722; color: white; padding: 8px; border-radius: 5px; text-align: center; }
        """)
        self.decrypt_button.setToolTip("رمزگشایی فایل با استفاده از کلید خصوصی یا متقارن")
        self.decrypt_button.clicked.connect(self.on_decrypt_file)
        operations_layout.addWidget(self.decrypt_button, 1, 0)

        self.hash_button = QPushButton("تولید هش SHA-256")
        self.hash_button.setStyleSheet("""
            QPushButton { background-color: #FFC107; color: white; padding: 8px; border-radius: 5px; text-align: center; }
        """)
        self.hash_button.setToolTip("تولید هش SHA-256 از فایل انتخاب‌شده و ذخیره اطلاعات در فایل متنی")
        self.hash_button.clicked.connect(self.on_generate_hash)
        operations_layout.addWidget(self.hash_button, 1, 1)

        operations_group.setLayout(operations_layout)
        layout.addWidget(operations_group)

        # پروگرس‌بار
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar { border: 1px solid #ccc; border-radius: 5px; text-align: center; }
            QProgressBar::chunk { background-color: #2196F3; }
        """)
        self.progress_bar.setToolTip("نمایش پیشرفت عملیات رمزنگاری یا رمزگشایی")
        layout.addWidget(self.progress_bar)

        # برچسب وضعیت
        self.status_label = QLabel("آماده")
        self.status_label.setFont(QFont("Arial", 18))
        self.status_label.setStyleSheet("color: #555;")
        self.status_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.status_label.setToolTip("وضعیت فعلی عملیات")
        layout.addWidget(self.status_label)

        self.setLayout(layout)

    def update_ui_based_on_algo(self, algo):
        if algo in ["RSA", "ECC"]:
            self.generate_button.setText("تولید کلیدهای نامتقارن")
            self.encrypt_button.setText("رمزنگاری با کلید عمومی")
            self.decrypt_button.setText("رمزگشایی با کلید خصوصی")
        elif algo in ["AES", "ChaCha20"]:
            self.generate_button.setText("تولید کلید متقارن")
            self.encrypt_button.setText("رمزنگاری با کلید متقارن")
            self.decrypt_button.setText("رمزگشایی با کلید متقارن")

        algo_descriptions = {
            "RSA": "RSA یک الگوریتم رمزنگاری نامتقارن است که از جفت کلیدهای عمومی و خصوصی برای رمزنگاری و امضای دیجیتال استفاده می‌کند.",
            "AES": "AES یک الگوریتم رمزنگاری متقارن است که از کلیدهای 128، 192 یا 256 بیتی برای رمزنگاری سریع و امن داده‌ها استفاده می‌کند.",
            "ECC": "ECC یک الگوریتم رمزنگاری نامتقارن مبتنی بر منحنی‌های بیضوی است که با کلیدهای کوتاه‌تر، امنیت بالایی ارائه می‌دهد.",
            "ChaCha20": "ChaCha20 یک الگوریتم رمزنگاری جریان متقارن است که به دلیل سرعت بالا و مقاومت در برابر حملات جانبی استفاده می‌شود."
        }
        if algo:
            QMessageBox.information(self, f"درباره {algo}", algo_descriptions[algo])

    def select_key_save_location(self, key_type):
        return QFileDialog.getSaveFileName(self, f"ذخیره کلید {key_type}", f"{key_type}_key.pem", "فایل‌های PEM (*.pem);;تمامی فایل‌ها (*.*)")[0]

    def select_key(self, key_type):
        return QFileDialog.getOpenFileName(self, f"انتخاب کلید {key_type}", "", "فایل‌های PEM (*.pem);;تمامی فایل‌ها (*.*)")[0]

    def select_file(self):
        return QFileDialog.getOpenFileName(self, "انتخاب فایل", "", "تمامی فایل‌ها (*.*)")[0]

    def select_save_file(self, default_extension, suggested_filename=""):
        return QFileDialog.getSaveFileName(self, "ذخیره فایل", suggested_filename, f"فایل‌های رمزنگاری‌شده (*{default_extension});;تمامی فایل‌ها (*.*)")[0]

    def generate_rsa_keys(self):
        try:
            private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            public_key = private_key.public_key()
            self.save_key_pair(private_key, public_key, "RSA")
            self.status_label.setText("کلیدهای RSA با موفقیت تولید شدند.")
            QMessageBox.information(self, "موفقیت", "کلیدهای RSA با موفقیت تولید و ذخیره شدند.")
        except Exception as e:
            self.status_label.setText("خطا در تولید کلیدهای RSA")
            QMessageBox.critical(self, "خطا", f"خطا در تولید کلیدهای RSA: {str(e)}")

    def generate_ecc_keys(self):
        try:
            private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
            public_key = private_key.public_key()
            self.save_key_pair(private_key, public_key, "ECC")
            self.status_label.setText("کلیدهای ECC با موفقیت تولید شدند.")
            QMessageBox.information(self, "موفقیت", "کلیدهای ECC با موفقیت تولید و ذخیره شدند.")
        except Exception as e:
            self.status_label.setText("خطا در تولید کلیدهای ECC")
            QMessageBox.critical(self, "خطا", f"خطا در تولید کلیدهای ECC: {str(e)}")

    def generate_symmetric_key(self, algo):
        try:
            key_size = 32
            key = secrets.token_bytes(key_size)
            key_path = self.select_key_save_location(algo)
            if not key_path:
                return
            with open(key_path, "wb") as key_file:
                key_file.write(key)
            self.status_label.setText(f"کلید {algo} با موفقیت تولید شد.")
            QMessageBox.information(self, "موفقیت", f"کلید {algo} در '{key_path}' ذخیره شد.")
        except Exception as e:
            self.status_label.setText(f"خطا در تولید کلید {algo}")
            QMessageBox.critical(self, "خطا", f"خطا در تولید کلید {algo}: {str(e)}")

    def save_key_pair(self, private_key, public_key, key_type):
        private_key_path = self.select_key_save_location(f"{key_type}_خصوصی")
        if not private_key_path:
            return
        public_key_path = self.select_key_save_location(f"{key_type}_عمومی")
        if not public_key_path:
            return

        with open(private_key_path, "wb") as private_key_file:
            if key_type == "ECC":
                private_key_file.write(
                    private_key.private_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PrivateFormat.PKCS8,
                        encryption_algorithm=serialization.NoEncryption()
                    )
                )
            else:
                private_key_file.write(
                    private_key.private_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PrivateFormat.TraditionalOpenSSL,
                        encryption_algorithm=serialization.NoEncryption()
                    )
                )
        with open(public_key_path, "wb") as public_key_file:
            public_key_file.write(
                public_key.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                )
            )

    def on_generate_keys(self):
        algo = self.algo_combo.currentText()
        self.status_label.setText("در حال تولید کلید...")
        if algo == "RSA":
            self.generate_rsa_keys()
        elif algo == "ECC":
            self.generate_ecc_keys()
        elif algo in ["AES", "ChaCha20"]:
            self.generate_symmetric_key(algo)

    def extract_header(self, decrypted_data):
        original_name = ""
        if decrypted_data.startswith(b"NAME:"):
            try:
                name_end = decrypted_data.index(b":END")
                original_name = decrypted_data[5:name_end].decode()
                decrypted_data = decrypted_data[name_end + 4:]
            except Exception:
                pass
        return original_name, decrypted_data

    def encrypt_file_rsa(self, input_filename, public_key_path):
        while True:
            try:
                with open(public_key_path, "rb") as public_key_file:
                    public_key = serialization.load_pem_public_key(public_key_file.read())

                base_name = os.path.basename(input_filename)
                _, ext = os.path.splitext(input_filename)
                header = f"NAME:{base_name}:ENDEXT:{ext}:END".encode()

                with open(input_filename, "rb") as input_file:
                    file_data = input_file.read()

                file_data = header + file_data
                max_chunk_size = public_key.key_size // 8 - 2 * 32 - 2
                encrypted_data = b""
                total_size = len(file_data)
                processed_size = 0

                for i in range(0, len(file_data), max_chunk_size):
                    chunk = file_data[i:i + max_chunk_size]
                    encrypted_chunk = public_key.encrypt(
                        chunk,
                        padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None)
                    )
                    encrypted_data += encrypted_chunk
                    processed_size += len(chunk)
                    self.progress_bar.setValue(int((processed_size / total_size) * 100))

                save_path = self.select_save_file(".rsa", os.path.basename(input_filename) + ".rsa")
                if save_path:
                    with open(save_path, "wb") as encrypted_file:
                        encrypted_file.write(encrypted_data)
                    self.status_label.setText(f"فایل با RSA رمزنگاری شد.")
                    self.progress_bar.setValue(100)
                    QMessageBox.information(self, "موفقیت", f"فایل با RSA رمزنگاری شد و در '{save_path}' ذخیره شد.")
                break
            except Exception as e:
                if "Could not deserialize key data" in str(e):
                    error_message = "کلید عمومی انتخاب‌شده نامعتبر است. لطفاً کلید عمومی RSA صحیح را انتخاب کنید."
                else:
                    error_message = f"خطا در رمزنگاری RSA: {str(e)}"
                reply = QMessageBox.question(
                    self, "خطا در کلید", 
                    error_message + "\n\nآیا می‌خواهید کلید دیگری انتخاب کنید؟",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
                )
                if reply == QMessageBox.Yes:
                    public_key_path = self.select_key("RSA عمومی")
                    if not public_key_path:
                        self.status_label.setText("عملیات لغو شد.")
                        self.progress_bar.setValue(0)
                        return
                else:
                    self.status_label.setText("عملیات لغو شد.")
                    self.progress_bar.setValue(0)
                    return

    def decrypt_file_rsa(self, input_filename, private_key_path):
        while True:
            try:
                with open(private_key_path, "rb") as private_key_file:
                    private_key = serialization.load_pem_private_key(private_key_file.read(), password=None)

                with open(input_filename, "rb") as encrypted_file:
                    encrypted_data = encrypted_file.read()

                max_chunk_size = private_key.key_size // 8
                decrypted_data = b""
                total_size = len(encrypted_data)
                processed_size = 0

                for i in range(0, len(encrypted_data), max_chunk_size):
                    chunk = encrypted_data[i:i + max_chunk_size]
                    decrypted_chunk = private_key.decrypt(
                        chunk,
                        padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None)
                    )
                    decrypted_data += decrypted_chunk
                    processed_size += len(chunk)
                    self.progress_bar.setValue(int((processed_size / total_size) * 100))

                original_name, decrypted_data = self.extract_header(decrypted_data)
                suggested_name = original_name if original_name else "decrypted_" + os.path.basename(input_filename)
                save_path = self.select_save_file("", suggested_name)
                if save_path:
                    with open(save_path, "wb") as decrypted_file:
                        decrypted_file.write(decrypted_data)
                    self.status_label.setText(f"فایل با RSA رمزگشایی شد.")
                    self.progress_bar.setValue(100)
                    QMessageBox.information(self, "موفقیت", f"فایل با RSA رمزگشایی شد و در '{save_path}' ذخیره شد.")
                break
            except Exception as e:
                if "Could not deserialize key data" in str(e):
                    error_message = "کلید خصوصی انتخاب‌شده نامعتبر است. لطفاً کلید خصوصی RSA صحیح را انتخاب کنید."
                else:
                    error_message = f"خطا در رمزگشایی RSA: {str(e)}"
                reply = QMessageBox.question(
                    self, "خطا در کلید", 
                    error_message + "\n\nآیا می‌خواهید کلید دیگری انتخاب کنید؟",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
                )
                if reply == QMessageBox.Yes:
                    private_key_path = self.select_key("RSA خصوصی")
                    if not private_key_path:
                        self.status_label.setText("عملیات لغو شد.")
                        self.progress_bar.setValue(0)
                        return
                else:
                    self.status_label.setText("عملیات لغو شد.")
                    self.progress_bar.setValue(0)
                    return

    def encrypt_file_aes(self, input_filename, key_path):
        while True:
            try:
                with open(key_path, "rb") as key_file:
                    key = key_file.read()
                iv = os.urandom(16)
                cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
                encryptor = cipher.encryptor()

                base_name = os.path.basename(input_filename)
                _, ext = os.path.splitext(input_filename)
                header = f"NAME:{base_name}:ENDEXT:{ext}:END".encode()

                with open(input_filename, "rb") as input_file:
                    file_data = input_file.read()

                file_data = header + file_data
                padder = sym_padding.PKCS7(128).padder()
                padded_data = padder.update(file_data) + padder.finalize()
                encrypted_data = encryptor.update(padded_data) + encryptor.finalize()

                save_path = self.select_save_file(".aes", os.path.basename(input_filename) + ".aes")
                if save_path:
                    with open(save_path, "wb") as encrypted_file:
                        encrypted_file.write(iv + encrypted_data)
                    self.status_label.setText(f"فایل با AES رمزنگاری شد.")
                    self.progress_bar.setValue(100)
                    QMessageBox.information(self, "موفقیت", f"فایل با AES رمزنگاری شد و در '{save_path}' ذخیره شد.")
                break
            except Exception as e:
                if "Invalid key length" in str(e):
                    error_message = "اندازه کلید نامعتبر است. لطفاً یک کلید AES با اندازه 32 بایت انتخاب کنید."
                else:
                    error_message = f"خطا در رمزنگاری AES: {str(e)}"
                reply = QMessageBox.question(
                    self, "خطا در کلید", 
                    error_message + "\n\nآیا می‌خواهید کلید دیگری انتخاب کنید؟",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
                )
                if reply == QMessageBox.Yes:
                    key_path = self.select_key("AES")
                    if not key_path:
                        self.status_label.setText("عملیات لغو شد.")
                        self.progress_bar.setValue(0)
                        return
                else:
                    self.status_label.setText("عملیات لغو شد.")
                    self.progress_bar.setValue(0)
                    return

    def decrypt_file_aes(self, input_filename, key_path):
        while True:
            try:
                with open(key_path, "rb") as key_file:
                    key = key_file.read()
                with open(input_filename, "rb") as encrypted_file:
                    iv = encrypted_file.read(16)
                    encrypted_data = encrypted_file.read()

                cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
                decryptor = cipher.decryptor()
                unpadder = sym_padding.PKCS7(128).unpadder()

                decrypted_padded = decryptor.update(encrypted_data) + decryptor.finalize()
                decrypted_data = unpadder.update(decrypted_padded) + unpadder.finalize()

                original_name, decrypted_data = self.extract_header(decrypted_data)
                suggested_name = original_name if original_name else "decrypted_" + os.path.basename(input_filename)
                save_path = self.select_save_file("", suggested_name)
                if save_path:
                    with open(save_path, "wb") as decrypted_file:
                        decrypted_file.write(decrypted_data)
                    self.status_label.setText(f"فایل با AES رمزگشایی شد.")
                    self.progress_bar.setValue(100)
                    QMessageBox.information(self, "موفقیت", f"فایل با AES رمزگشایی شد و در '{save_path}' ذخیره شد.")
                break
            except Exception as e:
                if "Invalid key length" in str(e):
                    error_message = "اندازه کلید نامعتبر است. لطفاً یک کلید AES با اندازه 32 بایت انتخاب کنید."
                else:
                    error_message = f"خطا در رمزگشایی AES: {str(e)}"
                reply = QMessageBox.question(
                    self, "خطا در کلید", 
                    error_message + "\n\nآیا می‌خواهید کلید دیگری انتخاب کنید؟",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
                )
                if reply == QMessageBox.Yes:
                    key_path = self.select_key("AES")
                    if not key_path:
                        self.status_label.setText("عملیات لغو شد.")
                        self.progress_bar.setValue(0)
                        return
                else:
                    self.status_label.setText("عملیات لغو شد.")
                    self.progress_bar.setValue(0)
                    return

    def encrypt_file_chacha20(self, input_filename, key_path):
        while True:
            try:
                with open(key_path, "rb") as key_file:
                    key = key_file.read()
                nonce = os.urandom(16)
                cipher = Cipher(algorithms.ChaCha20(key, nonce), mode=None, backend=default_backend())
                encryptor = cipher.encryptor()

                base_name = os.path.basename(input_filename)
                _, ext = os.path.splitext(input_filename)
                header = f"NAME:{base_name}:ENDEXT:{ext}:END".encode()

                with open(input_filename, "rb") as input_file:
                    file_data = input_file.read()

                file_data = header + file_data
                encrypted_data = encryptor.update(file_data) + encryptor.finalize()

                save_path = self.select_save_file(".chacha", os.path.basename(input_filename) + ".chacha")
                if save_path:
                    with open(save_path, "wb") as encrypted_file:
                        encrypted_file.write(nonce + encrypted_data)
                    self.status_label.setText(f"فایل با ChaCha20 رمزنگاری شد.")
                    self.progress_bar.setValue(100)
                    QMessageBox.information(self, "موفقیت", f"فایل با ChaCha20 رمزنگاری شد و در '{save_path}' ذخیره شد.")
                break
            except Exception as e:
                if "Invalid key length" in str(e):
                    error_message = "اندازه کلید نامعتبر است. لطفاً یک کلید ChaCha20 با اندازه 32 بایت انتخاب کنید."
                else:
                    error_message = f"خطا در رمزنگاری ChaCha20: {str(e)}"
                reply = QMessageBox.question(
                    self, "خطا در کلید", 
                    error_message + "\n\nآیا می‌خواهید کلید دیگری انتخاب کنید؟",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
                )
                if reply == QMessageBox.Yes:
                    key_path = self.select_key("ChaCha20")
                    if not key_path:
                        self.status_label.setText("عملیات لغو شد.")
                        self.progress_bar.setValue(0)
                        return
                else:
                    self.status_label.setText("عملیات لغو شد.")
                    self.progress_bar.setValue(0)
                    return

    def decrypt_file_chacha20(self, input_filename, key_path):
        while True:
            try:
                with open(key_path, "rb") as key_file:
                    key = key_file.read()
                with open(input_filename, "rb") as encrypted_file:
                    nonce = encrypted_file.read(16)
                    encrypted_data = encrypted_file.read()

                cipher = Cipher(algorithms.ChaCha20(key, nonce), mode=None, backend=default_backend())
                decryptor = cipher.decryptor()

                decrypted_data = decryptor.update(encrypted_data) + decryptor.finalize()
                original_name, decrypted_data = self.extract_header(decrypted_data)
                suggested_name = original_name if original_name else "decrypted_" + os.path.basename(input_filename)
                save_path = self.select_save_file("", suggested_name)
                if save_path:
                    with open(save_path, "wb") as decrypted_file:
                        decrypted_file.write(decrypted_data)
                    self.status_label.setText(f"فایل با ChaCha20 رمزگشایی شد.")
                    self.progress_bar.setValue(100)
                    QMessageBox.information(self, "موفقیت", f"فایل با ChaCha20 رمزگشایی شد و در '{save_path}' ذخیره شد.")
                break
            except Exception as e:
                if "Invalid key length" in str(e):
                    error_message = "اندازه کلید نامعتبر است. لطفاً یک کلید ChaCha20 با اندازه 32 بایت انتخاب کنید."
                else:
                    error_message = f"خطا در رمزگشایی ChaCha20: {str(e)}"
                reply = QMessageBox.question(
                    self, "خطا در کلید", 
                    error_message + "\n\nآیا می‌خواهید کلید دیگری انتخاب کنید؟",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
                )
                if reply == QMessageBox.Yes:
                    key_path = self.select_key("ChaCha20")
                    if not key_path:
                        self.status_label.setText("عملیات لغو شد.")
                        self.progress_bar.setValue(0)
                        return
                else:
                    self.status_label.setText("عملیات لغو شد.")
                    self.progress_bar.setValue(0)
                    return

    def encrypt_file_ecc(self, input_filename, public_key_path):
        while True:
            try:
                with open(public_key_path, "rb") as public_key_file:
                    public_key = serialization.load_pem_public_key(public_key_file.read())

                private_key_ephemeral = ec.generate_private_key(ec.SECP256R1(), default_backend())
                public_key_ephemeral = private_key_ephemeral.public_key()
                shared_key = private_key_ephemeral.exchange(ec.ECDH(), public_key)
                derived_key = HKDF(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=None,
                    info=b'handshake data',
                    backend=default_backend()
                ).derive(shared_key)

                iv = os.urandom(16)
                cipher = Cipher(algorithms.AES(derived_key), modes.CBC(iv), backend=default_backend())
                encryptor = cipher.encryptor()

                base_name = os.path.basename(input_filename)
                _, ext = os.path.splitext(input_filename)
                header = f"NAME:{base_name}:ENDEXT:{ext}:END".encode()

                with open(input_filename, "rb") as input_file:
                    file_data = input_file.read()

                file_data = header + file_data
                padder = sym_padding.PKCS7(128).padder()
                padded_data = padder.update(file_data) + padder.finalize()
                encrypted_data = encryptor.update(padded_data) + encryptor.finalize()

                save_path = self.select_save_file(".ecc", os.path.basename(input_filename) + ".ecc")
                if save_path:
                    with open(save_path, "wb") as encrypted_file:
                        public_key_ephemeral_pem = public_key_ephemeral.public_bytes(
                            encoding=serialization.Encoding.PEM,
                            format=serialization.PublicFormat.SubjectPublicKeyInfo
                        )
                        encrypted_file.write(public_key_ephemeral_pem)
                        encrypted_file.write(iv + encrypted_data)
                    self.status_label.setText(f"فایل با ECC رمزنگاری شد.")
                    self.progress_bar.setValue(100)
                    QMessageBox.information(self, "موفقیت", f"فایل با ECC رمزنگاری شد و در '{save_path}' ذخیره شد.")
                break
            except Exception as e:
                if "Could not deserialize key data" in str(e):
                    error_message = "کلید عمومی انتخاب‌شده نامعتبر است. لطفاً کلید عمومی ECC صحیح را انتخاب کنید."
                else:
                    error_message = f"خطا در رمزنگاری ECC: {str(e)}"
                reply = QMessageBox.question(
                    self, "خطا در کلید", 
                    error_message + "\n\nآیا می‌خواهید کلید دیگری انتخاب کنید؟",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
                )
                if reply == QMessageBox.Yes:
                    public_key_path = self.select_key("ECC عمومی")
                    if not public_key_path:
                        self.status_label.setText("عملیات لغو شد.")
                        self.progress_bar.setValue(0)
                        return
                else:
                    self.status_label.setText("عملیات لغو شد.")
                    self.progress_bar.setValue(0)
                    return

    def decrypt_file_ecc(self, input_filename, private_key_path):
        while True:
            try:
                with open(private_key_path, "rb") as private_key_file:
                    private_key = serialization.load_pem_private_key(private_key_file.read(), password=None)

                with open(input_filename, "rb") as encrypted_file:
                    public_key_ephemeral_pem = b""
                    while True:
                        line = encrypted_file.readline()
                        if not line:
                            raise ValueError("فایل رمزنگاری‌شده ناقص است: پایان کلید عمومی یافت نشد")
                        public_key_ephemeral_pem += line
                        if line.strip() == b"-----END PUBLIC KEY-----":
                            break
                    iv = encrypted_file.read(16)
                    encrypted_data = encrypted_file.read()

                public_key_ephemeral = serialization.load_pem_public_key(public_key_ephemeral_pem)
                shared_key = private_key.exchange(ec.ECDH(), public_key_ephemeral)
                derived_key = HKDF(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=None,
                    info=b'handshake data',
                    backend=default_backend()
                ).derive(shared_key)

                cipher = Cipher(algorithms.AES(derived_key), modes.CBC(iv), backend=default_backend())
                decryptor = cipher.decryptor()
                unpadder = sym_padding.PKCS7(128).unpadder()

                decrypted_padded = decryptor.update(encrypted_data) + decryptor.finalize()
                decrypted_data = unpadder.update(decrypted_padded) + unpadder.finalize()

                original_name, decrypted_data = self.extract_header(decrypted_data)
                suggested_name = original_name if original_name else "decrypted_" + os.path.basename(input_filename)
                save_path = self.select_save_file("", suggested_name)
                if save_path:
                    with open(save_path, "wb") as decrypted_file:
                        decrypted_file.write(decrypted_data)
                    self.status_label.setText(f"فایل با ECC رمزگشایی شد.")
                    self.progress_bar.setValue(100)
                    QMessageBox.information(self, "موفقیت", f"فایل با ECC رمزگشایی شد و در '{save_path}' ذخیره شد.")
                break
            except Exception as e:
                if "Could not deserialize key data" in str(e):
                    error_message = "کلید خصوصی انتخاب‌شده نامعتبر است. لطفاً کلید خصوصی ECC صحیح را انتخاب کنید."
                else:
                    error_message = f"خطا در رمزگشایی ECC: {str(e)}"
                reply = QMessageBox.question(
                    self, "خطا در کلید", 
                    error_message + "\n\nآیا می‌خواهید کلید دیگری انتخاب کنید؟",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
                )
                if reply == QMessageBox.Yes:
                    private_key_path = self.select_key("ECC خصوصی")
                    if not private_key_path:
                        self.status_label.setText("عملیات لغو شد.")
                        self.progress_bar.setValue(0)
                        return
                else:
                    self.status_label.setText("عملیات لغو شد.")
                    self.progress_bar.setValue(0)
                    return

    def on_encrypt_file(self):
        algo = self.algo_combo.currentText()
        input_filename = self.select_file()
        if not input_filename:
            return

        self.progress_bar.setValue(0)
        self.status_label.setText("در حال رمزنگاری...")
        if algo == "RSA":
            public_key_path = self.select_key("RSA عمومی")
            if public_key_path:
                self.encrypt_file_rsa(input_filename, public_key_path)
        elif algo == "AES":
            key_path = self.select_key("AES")
            if key_path:
                self.encrypt_file_aes(input_filename, key_path)
        elif algo == "ECC":
            public_key_path = self.select_key("ECC عمومی")
            if public_key_path:
                self.encrypt_file_ecc(input_filename, public_key_path)
        elif algo == "ChaCha20":
            key_path = self.select_key("ChaCha20")
            if key_path:
                self.encrypt_file_chacha20(input_filename, key_path)

    def on_decrypt_file(self):
        algo = self.algo_combo.currentText()
        input_filename = self.select_file()
        if not input_filename:
            return

        self.progress_bar.setValue(0)
        self.status_label.setText("در حال رمزگشایی...")
        if algo == "RSA":
            private_key_path = self.select_key("RSA خصوصی")
            if private_key_path:
                self.decrypt_file_rsa(input_filename, private_key_path)
        elif algo == "AES":
            key_path = self.select_key("AES")
            if key_path:
                self.decrypt_file_aes(input_filename, key_path)
        elif algo == "ECC":
            private_key_path = self.select_key("ECC خصوصی")
            if private_key_path:
                self.decrypt_file_ecc(input_filename, private_key_path)
        elif algo == "ChaCha20":
            key_path = self.select_key("ChaCha20")
            if key_path:
                self.decrypt_file_chacha20(input_filename, key_path)

    def on_generate_hash(self):
        input_filename = self.select_file()
        if not input_filename:
            return

        try:
            digest = hashes.Hash(hashes.SHA256(), backend=default_backend())
            total_size = os.path.getsize(input_filename)
            processed_size = 0
            with open(input_filename, "rb") as input_file:
                while True:
                    chunk = input_file.read(4096)
                    if not chunk:
                        break
                    digest.update(chunk)
                    processed_size += len(chunk)
                    self.progress_bar.setValue(int((processed_size / total_size) * 100))
            hash_value = digest.finalize().hex()

            file_info = {
                "نام فایل": os.path.basename(input_filename),
                "مسیر فایل": os.path.dirname(input_filename),
                "اندازه فایل (بایت)": os.path.getsize(input_filename),
                "تاریخ ایجاد": datetime.datetime.fromtimestamp(os.path.getctime(input_filename)).strftime('%Y-%m-%d %H:%M:%S'),
                "تاریخ آخرین اصلاح": datetime.datetime.fromtimestamp(os.path.getmtime(input_filename)).strftime('%Y-%m-%d %H:%M:%S'),
                "هش SHA-256": hash_value
            }

            content = "\n".join([f"{key}: {value}" for key, value in file_info.items()])
            suggested_filename = f"{os.path.splitext(os.path.basename(input_filename))[0]}_hash.txt"
            save_path, _ = QFileDialog.getSaveFileName(self, "ذخیره فایل هش", suggested_filename, "فایل‌های متنی (*.txt);;تمامی فایل‌ها (*.*)")
            if not save_path:
                return

            with open(save_path, "w", encoding="utf-8") as hash_file:
                hash_file.write(content)

            self.status_label.setText("فایل هش با موفقیت ذخیره شد.")
            self.progress_bar.setValue(100)
            QMessageBox.information(self, "موفقیت", f"فایل هش در '{save_path}' ذخیره شد.")
        except Exception as e:
            self.status_label.setText("خطا در تولید هش")
            self.progress_bar.setValue(0)
            QMessageBox.critical(self, "خطا", f"خطا در تولید هش: {str(e)}")