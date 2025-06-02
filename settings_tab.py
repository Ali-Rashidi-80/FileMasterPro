from PyQt5.QtWidgets import QWidget, QVBoxLayout, QFormLayout, QLineEdit, QComboBox, QPushButton, QGroupBox, QMessageBox, QColorDialog, QLabel
from PyQt5.QtCore import pyqtSignal , Qt
from config import load_config, save_config

class SettingsTab(QWidget):
    configChanged = pyqtSignal(dict)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.load_settings()
    def init_ui(self):
        layout = QVBoxLayout()
        header = QLabel("تنظیمات برنامه")
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("font-size: 24px; font-weight: bold; color: #3498db; margin-bottom: 20px;")
        layout.addWidget(header)
        form_group = QGroupBox("تنظیمات عمومی")
        form_group.setStyleSheet("QGroupBox { font-size: 18px; font-weight: bold; color: #34495e; padding: 10px; }")
        form_layout = QFormLayout()
        self.fontSizeInput = QLineEdit()
        self.fontSizeInput.setStyleSheet("padding: 8px; border-radius: 5px;")
        form_layout.addRow("اندازه فونت:", self.fontSizeInput)
        self.themeCombo = QComboBox()
        self.themeCombo.addItems(["light", "dark"])
        self.themeCombo.setStyleSheet("padding: 8px; border-radius: 5px;")
        form_layout.addRow("تم برنامه:", self.themeCombo)
        self.colorButton = QPushButton("انتخاب رنگ اصلی")
        self.colorButton.clicked.connect(self.choose_color)
        form_layout.addRow("رنگ اصلی:", self.colorButton)
        form_group.setLayout(form_layout)
        layout.addWidget(form_group)
        self.saveButton = QPushButton("ذخیره تنظیمات")
        self.saveButton.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px; border-radius: 5px;")
        self.saveButton.clicked.connect(self.save_settings)
        layout.addWidget(self.saveButton)
        layout.addStretch()
        self.setLayout(layout)
    def choose_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.selectedColor = color.name()
            self.colorButton.setStyleSheet(f"background-color: {self.selectedColor}; color: white; padding: 8px; border-radius: 5px;")
    def load_settings(self):
        config = load_config()
        self.fontSizeInput.setText(str(config.get("font_size", 16)))
        theme = config.get("theme", "light")
        index = self.themeCombo.findText(theme)
        if index != -1:
            self.themeCombo.setCurrentIndex(index)
        self.selectedColor = config.get("main_color", "#3498db")
        self.colorButton.setStyleSheet(f"background-color: {self.selectedColor}; color: white; padding: 8px; border-radius: 5px;")
    def save_settings(self):
        try:
            font_size = int(self.fontSizeInput.text())
        except:
            font_size = 16
        new_config = {
            "font_size": font_size,
            "theme": self.themeCombo.currentText(),
            "main_color": self.selectedColor
        }
        save_config(new_config)
        self.configChanged.emit(new_config)
        QMessageBox.information(self, "تنظیمات", "تنظیمات ذخیره و اعمال شدند.")
