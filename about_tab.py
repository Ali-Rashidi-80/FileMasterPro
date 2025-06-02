from PyQt5.QtWidgets import QWidget, QVBoxLayout, QScrollArea, QLabel
from PyQt5.QtCore import Qt

class AboutTab(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        # لایه اصلی و اسکرول‌بار
        layout = QVBoxLayout()
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)

        # برچسب با فرمت HTML برای طراحی زیبا و راست‌چین حرفه‌ای
        about_label = QLabel()
        about_label.setTextFormat(Qt.RichText)
        about_label.setWordWrap(True)
        about_label.setText("""
            <div style="font-family:'Vazir', 'B Nazanin', sans-serif; text-align:right; padding:25px; direction:rtl; background: #F5F7FA; border-radius: 12px;">
                
                <!-- عنوان اصلی -->
                <h1 style="color:#2E86C1; text-align:center; font-size:28px; font-weight:bold; margin-bottom:25px; text-shadow: 1px 1px 2px #ddd;">
                    خوش اومدی به <span style="color:#E67E22;">FileMaster Pro</span>!
                </h1>
                <h3 style="color:#34495E; text-align:center; font-size:18px; font-weight:500; margin-bottom:30px;">
                    نسخه: 1.0 - ساخته‌شده برای مدیریت حرفه‌ای فایل‌ها و پوشه‌ها
                </h3>

                <!-- توضیح کوتاه برنامه -->
                <div style="background:#FFFFFF; padding:20px; border-radius:10px; box-shadow: 2px 2px 8px rgba(0,0,0,0.1); margin-bottom:35px;">
                    <p style="font-size:16px; color:#34495E; line-height:1.7; text-align:right;">
                        FileMaster Pro یه ابزار حرفه‌ای و دوست‌داشتنیه که بهت کمک می‌کنه فایل‌ها و پوشه‌هات رو به‌سادگی مدیریت کنی! از جستجوی پیشرفته تا رمزنگاری امن، همه‌چیز اینجاست تا کارات رو سریع‌تر و راحت‌تر کنه.
                    </p>
                </div>

                <!-- بخش تب‌ها -->
                <h2 style="color:#2E86C1; font-size:22px; font-weight:bold; margin-bottom:20px; border-bottom:2px solid #3498DB; padding-bottom:8px; text-align:right;">
                    با تب‌های برنامه آشنا شو!
                </h2>
                <ul style="list-style-type:disc; padding-right:20px; font-size:15px; color:#34495E;">
                    <li style="background:#F9FAFB; margin-bottom:15px; padding:15px; border-radius:8px; box-shadow: 0 1px 4px rgba(0,0,0,0.05); text-align:right;">
                        <strong style="color:#2E86C1;">تب پوشه‌ها:</strong> جستجوی پوشه‌ها، کپی نام‌ها، ذخیره در فایل متنی، حذف پوشه‌های خالی و تغییر نام گروهی با یه کلیک.
                    </li>
                    <li style="background:#F9FAFB; margin-bottom:15px; padding:15px; border-radius:8px; box-shadow: 0 1px 4px rgba(0,0,0,0.05); text-align:right;">
                        <strong style="color:#2E86C1;">تب فایل‌ها:</strong> جستجوی فایل‌ها، فیلتر صوتی، کپی نام‌ها و باز کردن یا تغییر نام فایل‌ها با کلیک راست.
                    </li>
                    <li style="background:#F9FAFB; margin-bottom:15px; padding:15px; border-radius:8px; box-shadow: 0 1px 4px rgba(0,0,0,0.05); text-align:right;">
                        <strong style="color:#2E86C1;">تب درهم‌سازی فایل:</strong> آهنگ‌ها رو بر اساس خواننده قاطی کن و به پوشه دلخواه منتقل کن.
                    </li>
                    <li style="background:#F9FAFB; margin-bottom:15px; padding:15px; border-radius:8px; box-shadow: 0 1px 4px rgba(0,0,0,0.05); text-align:right;">
                        <strong style="color:#2E86C1;">تب پوشه‌های لیستی:</strong> لیست پوشه‌ها رو وارد کن و کپی یا انتقالشون کن.
                    </li>
                    <li style="background:#F9FAFB; margin-bottom:15px; padding:15px; border-radius:8px; box-shadow: 0 1px 4px rgba(0,0,0,0.05); text-align:right;">
                        <strong style="color:#2E86C1;">تب تنظیمات:</strong> فونت، تم (روشن/تیره) و رنگ‌ها رو به سلیقه خودت تغییر بده.
                    </li>
                    <li style="background:#F9FAFB; margin-bottom:15px; padding:15px; border-radius:8px; box-shadow: 0 1px 4px rgba(0,0,0,0.05); text-align:right;">
                        <strong style="color:#2E86C1;">تب فایل‌های حجیم:</strong> فایل‌های بزرگ رو پیدا کن و حذف یا به سطل بازیافت منتقل کن.
                    </li>
                    <li style="background:#F9FAFB; margin-bottom:15px; padding:15px; border-radius:8px; box-shadow: 0 1px 4px rgba(0,0,0,0.05); text-align:right;">
                        <strong style="color:#2E86C1;">تب فایل‌های تکراری:</strong> فایل‌های تکراری رو پیدا کن و حذف کن تا فضای دیسکت آزاد بشه.
                    </li>
                    <li style="background:#F9FAFB; margin-bottom:15px; padding:15px; border-radius:8px; box-shadow: 0 1px 4px rgba(0,0,0,0.05); text-align:right;">
                        <strong style="color:#2E86C1;">تب بی‌ردپا:</strong> فایل‌ها و سطل بازیافت رو با روش‌های امن (مثل DoD) پاک کن.
                    </li>
                    <li style="background:#F9FAFB; margin-bottom:15px; padding:15px; border-radius:8px; box-shadow: 0 1px 4px rgba(0,0,0,0.05); text-align:right;">
                        <strong style="color:#2E86C1;">تب رمزنگاری:</strong> فایل‌هات رو با RSA، AES یا ChaCha20 رمزنگاری کن و هش بساز.
                    </li>
                </ul>

                <!-- بخش راهنما -->
                <h2 style="color:#2E86C1; font-size:22px; font-weight:bold; margin-top:40px; margin-bottom:20px; border-bottom:2px solid #3498DB; padding-bottom:8px; text-align:right;">
                    از کجا شروع کنم؟
                </h2>
                <div style="background:#FFFFFF; padding:20px; border-radius:10px; box-shadow: 2px 2px 8px rgba(0,0,0,0.1); margin-bottom:35px;">
                    <p style="font-size:16px; color:#34495E; line-height:1.7; text-align:right;">
                        کافیه تب موردنظرت رو انتخاب کنی، یه پوشه یا فایل بدی و بزنی به دل کار! اگه سوالی داشتی، پایین صفحه منتظرتم.
                    </p>
                </div>

                <!-- بخش تماس -->
                <h2 style="color:#2E86C1; font-size:22px; font-weight:bold; margin-top:40px; margin-bottom:20px; border-bottom:2px solid #3498DB; padding-bottom:8px; text-align:right;">
                    بیا با هم حرف بزنیم!
                </h2>
                <div style="background:#FFFFFF; padding:20px; border-radius:10px; box-shadow: 2px 2px 8px rgba(0,0,0,0.1);">
                    <p style="font-size:16px; color:#34495E; line-height:1.7; text-align:right;">
                        توسعه‌دهنده: <strong style="color:#2E86C1;">علی رشیدی</strong><br>
                        سوالی داری یا پیشنهادی؟ بیا به 
                        <a href="https://t.me/WriteYourWay" style="color:#2E86C1; text-decoration:none; font-weight:bold;">t.me/WriteYourWay</a>
                    </p>
                </div>

                <!-- فوتر -->
                <p style="font-size:14px; color:#7F8C8D; text-align:center; margin-top:40px; font-style:italic;">
                    © 2025 - با عشق و دقت برای تو ساخته شده!
                </p>
            </div>
        """)
        content_layout.addWidget(about_label)
        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area)
        self.setLayout(layout)