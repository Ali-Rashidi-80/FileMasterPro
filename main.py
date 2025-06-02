import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget, QProgressBar, QSystemTrayIcon, QDesktopWidget
from PyQt5.QtCore import QPropertyAnimation
from PyQt5.QtGui import QFont, QIcon
from config import load_config
from folders_tab import FoldersTab
from files_tab import FilesTab
from shuffle_tab import ShuffleTab
from custom_copy_tab import CustomCopyTab
from settings_tab import SettingsTab
from about_tab import AboutTab
from large_files_tab import LargeFilesTab
from duplicate_files_tab import DuplicateFilesTab
from file_shredder_tab import FileShredderTab
from Cryptography_tab import CryptographyTab
from Smart_multimedia_categorization import MediaClassifierTab
from Metadata_Editor_Tab import MetadataEditorTab
from PDF_Files_Management_Tab import PDFManagementTab


user_config = load_config()
default_font = QFont("B Nazanin", user_config.get("font_size", 16))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("مدیریت فایل‌ها و پوشه‌ها")
        screen = QDesktopWidget().screenGeometry()
        width = int(screen.width() * 0.85)
        height = int(screen.height() * 0.85)
        self.resize(width, height)
        self.setMinimumSize(400, 300)
        self.init_ui()

    def init_ui(self):
        self.tabs = QTabWidget()
        self.tabs.setMovable(True)
        self.tabs.setDocumentMode(True)
        self.setCentralWidget(self.tabs)

        self.status_bar = self.statusBar()
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.status_bar.addPermanentWidget(self.progress_bar)
        self.tray_icon = QSystemTrayIcon(QIcon("icons/app.png"), self)
        self.tray_icon.show()

        try:
            self.shuffle_tab = ShuffleTab(self.update_status, self.update_progress, self.tray_icon)
            self.duplicate_files_tab = DuplicateFilesTab(self.update_status, self.tray_icon)
            self.file_shredder_tab = FileShredderTab()
            self.cryptography_tab = CryptographyTab()
            self.multimedia_categorization = MediaClassifierTab(self.update_status, self.tray_icon)
            self.metadata_editor_tab = MetadataEditorTab(self.update_status, self.tray_icon)
            self.pdf_files_management_tab = PDFManagementTab()
            self.large_files_tab = LargeFilesTab(self.update_status, self.update_progress, self.tray_icon)
            self.folders_tab = FoldersTab(self.update_status, self.update_progress, self.tray_icon)
            self.files_tab = FilesTab(self.update_status, self.update_progress, self.tray_icon)
            self.custom_copy_tab = CustomCopyTab(self.update_status, self.update_progress, self.tray_icon)
            self.settings_tab = SettingsTab()
            self.settings_tab.configChanged.connect(self.on_config_changed)
            self.about_tab = AboutTab()

            # اضافه کردن تب‌ها با آیکون
            self.tabs.addTab(self.shuffle_tab, QIcon("icons/shuffle_icon.png"), "درهم سازی فایل")
            self.tabs.addTab(self.duplicate_files_tab, QIcon("icons/duplicate_icon.png"), "فایل های تکراری")
            self.tabs.addTab(self.file_shredder_tab, QIcon("icons/shredder_icon.png"), "بی ردپا")
            self.tabs.addTab(self.cryptography_tab, QIcon("icons/crypto_icon.png"), "رمزنگاری")
            self.tabs.addTab(self.multimedia_categorization, QIcon("icons/face_icon.png"), "دسته بندی رسانه")
            self.tabs.addTab(self.metadata_editor_tab, "ویرایشگر متادیتا")
            self.tabs.addTab(self.pdf_files_management_tab, "pdf tools")
            self.tabs.addTab(self.large_files_tab, QIcon("icons/large_files_icon.png"), "فایل های حجیم")
            self.tabs.addTab(self.folders_tab, QIcon("icons/folders_icon.png"), "پوشه‌ها")
            self.tabs.addTab(self.files_tab, QIcon("icons/files_icon.png"), "فایل‌ها")
            self.tabs.addTab(self.custom_copy_tab, QIcon("icons/custom_copy_icon.png"), "پوشه‌های لیستی")
            self.tabs.addTab(self.settings_tab, QIcon("icons/settings_icon.png"), "تنظیمات")
            self.tabs.addTab(self.about_tab, QIcon("icons/about_icon.png"), "درباره")

            # دیکشنری توضیحات تب‌ها
            self.tab_descriptions = {
                "درهم سازی فایل": "این تب به شما امکان می‌دهد فایل‌های صوتی را بر اساس خواننده به صورت تصادفی و پیشرفته درهم کنید.",
                "فایل های تکراری": "در این تب می‌توانید فایل‌های تکراری را در مسیرهای1های دلخواه پیدا و مدیریت کنید.",
                "بی ردپا": "ابزاری امن برای حذف کامل فایل‌ها و پوشه‌ها به گونه‌ای که قابل بازیابی نباشند.",
                "رمزنگاری": "این تب امکان رمزنگاری و رمزگشایی فایل‌ها با الگوریتم‌های مختلف را فراهم می‌کند.",
                "چهره‌یاب": "با استفاده از این تب می‌توانید تصاویر حاوی چهره را شناسایی و جدا کنید.",
                "فایل های حجیم": "این تب به شما کمک می‌کند فایل‌های بزرگ را در مسیرهای مشخص پیدا و مدیریت کنید.",
                "پوشه‌ها": "در این تب می‌توانید پوشه‌ها را جستجو، کپی، ذخیره و مدیریت کنید.",
                "فایل‌ها": "این تب امکان جستجو، کپی، ذخیره و مدیریت فایل‌ها را فراهم می‌کند.",
                "پوشه‌های لیستی": "با این تب می‌توانید پوشه‌ها را بر اساس لیست‌های سفارشی کپی یا انتقال دهید.",
                "تنظیمات": "در این تب می‌توانید تنظیمات برنامه مانند اندازه فونت، تم و رنگ اصلی را تغییر دهید.",
                "درباره": "اطلاعات مربوط به برنامه، نسخه و توسعه‌دهنده را در این تب مشاهده کنید."
            }

            # تنظیم ابزارنما برای هر تب
            for index in range(self.tabs.count()):
                tab_name = self.tabs.tabText(index)
                description = self.tab_descriptions.get(tab_name, "")
                self.tabs.setTabToolTip(index, description)

            # اتصال رویداد تغییر تب
            self.tabs.currentChanged.connect(self.update_tab_description)

        except Exception as e:
            self.update_status(f"خطا در بارگذاری تب‌ها: {e}")

        self.apply_stylesheet()
        self.fade_in = QPropertyAnimation(self, b"windowOpacity")
        self.fade_in.setDuration(1500)
        self.fade_in.setStartValue(0.0)
        self.fade_in.setEndValue(1.0)
        self.fade_in.start()

    def update_status(self, message, duration=3000):
        self.status_bar.showMessage(message, duration)

    def update_progress(self, current, total):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        QApplication.processEvents()

    def update_tab_description(self, index):
        tab_name = self.tabs.tabText(index)
        description = self.tab_descriptions.get(tab_name, "توضیحی برای این تب موجود نیست.")
        self.status_bar.showMessage(description, 5000)

    def on_config_changed(self, new_config):
        try:
            new_font = QFont("B Nazanin", new_config.get("font_size", 16))
            QApplication.setFont(new_font)
            self.apply_stylesheet()
            self.status_bar.showMessage("تنظیمات ذخیره و اعمال شدند.", 3000)
            self.tray_icon.showMessage("تنظیمات", "تنظیمات جدید اعمال شدند.", QSystemTrayIcon.Information, 3000)
        except Exception as e:
            self.status_bar.showMessage(f"خطا در اعمال تنظیمات: {e}", 3000)

    def apply_stylesheet(self):
        try:
            config = load_config()
            theme = config.get("theme", "light")
            main_color = config.get("main_color", "#3498db")
            style = f"""
                QWidget {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #ffffff, stop:1 #f2f2f2);
                    font-family: 'B Nazanin', Tahoma, sans-serif;
                    font-size: 16px;
                }}
                QTabWidget::pane {{
                    border: 1px solid #c4c4c3;
                    background: #ffffff;
                }}
                QTabBar {{
                    background: #ffffff;
                }}
                QTabBar::tab {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f6f7fa, stop:1 #e4e5e9);
                    border: 1px solid #c4c4c3;
                    border-bottom-color: #a9a9a9;
                    border-top-left-radius: 4px;
                    border-top-Left-radius: 4px;
                    min-width: 130px;
                    padding: 10px;
                    margin-Left: 2px;
                    font-weight: bold;
                    font-size: 16px;
                    color: #2c3e50;
                }}
                QTabBar::tab:selected {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffffff, stop:1 #f0f0f0);
                    border-color: #a9a9a9;
                    border-bottom-color: #ffffff;
                    color: {main_color};
                }}
                QTabBar::tab:hover {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #e4e5e9, stop:1 #d1d2d6);
                }}
                QTabBar::tab:!selected {{
                    margin-top: 2px;
                }}
                QProgressBar {{
                    border: 1px solid #bdc3c7;
                    border-radius: 8px;
                    text-align: center;
                    font-size: 16px;
                    font-weight: bold;
                }}
                QProgressBar::chunk {{
                    background-color: {main_color};
                    border-radius: 8px;
                }}
                QPushButton {{
                    background-color: {main_color};
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    border-radius: 8px;
                    font-size: 16px;
                }}
                QPushButton:hover {{
                    background-color: #2980b9;
                }}
                QPushButton:pressed {{
                    background-color: #1c5980;
                }}
                QLineEdit {{
                    border: 1px solid #bdc3c7;
                    border-radius: 8px;
                    padding: 8px;
                    font-size: 16px;
                }}
            """
            if theme == "dark":
                dark_button_color = "#e74c3c"
                dark_header_color = "#8e44ad"
                style += f"""
                    QWidget {{
                        background-color: #2c2c2c;
                        color: #eeeeee;
                    }}
                    QLineEdit {{
                        background-color: #3c3c3c;
                    }}
                    QTabWidget::pane {{
                        border: 1px solid #555555;
                        background: #2c2c2c;
                    }}
                    QTabBar {{
                        background: #2c2c2c;
                    }}
                    QTabBar::tab {{
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #555555, stop:1 #444444);
                        border: 1px solid #666666;
                        border-bottom-color: #555555;
                        border-top-left-radius: 4px;
                        border-top-Left-radius: 4px;
                        min-width: 130px;
                        padding: 10px;
                        margin-Left: 2px;
                        font-weight: bold;
                        font-size: 16px;
                        color: #eeeeee;
                    }}
                    QTabBar::tab:selected {{
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #666666, stop:1 #555555);
                        border-color: #777777;
                        border-bottom-color: #2c2c2c;
                        color: {dark_button_color};
                    }}
                    QTabBar::tab:hover {{
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #666666, stop:1 #555555);
                    }}
                    QTabBar::tab:!selected {{
                        margin-top: 2px;
                    }}
                    QPushButton {{
                        background-color: {dark_button_color};
                        color: white;
                        border: none;
                        padding: 10px 20px;
                        border-radius: 8px;
                        font-size: 16px;
                    }}
                    QPushButton:hover {{
                        background-color: #c0392b;
                    }}
                    QPushButton:pressed {{
                        background-color: #992d22;
                    }}
                """
            self.setStyleSheet(style)
        except Exception as e:
            self.status_bar.showMessage(f"خطا در اعمال استایل: {e}", 3000)

    def closeEvent(self, event):
        event.accept()

def main():
    try:
        app = QApplication(sys.argv)
        app.setFont(default_font)
        window = MainWindow()
        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        print("خطا در اجرای برنامه:", e)

if __name__ == "__main__":
    main()