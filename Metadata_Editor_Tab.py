import os
import hashlib
import binascii
import mimetypes
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTableWidget, QTableWidgetItem, QScrollArea, QFileDialog, QMessageBox, QSystemTrayIcon
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import Qt
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from PIL import Image
import piexif
from piexif import TAGS

try:
    from mutagen.easyid3 import EasyID3
    from mutagen.id3 import ID3, APIC
    from mutagen import File
except ImportError:
    EasyID3 = None
    ID3 = None
    APIC = None
    File = None

# دیکشنری ترجمه نام لیبل‌ها به فارسی
TRANSLATIONS = {
    'title': 'عنوان',
    'artist': 'خواننده',
    'album': 'آلبوم',
    'albumartist': 'خواننده آلبوم',
    'conductor': 'رهبر ارکستر',
    'discnumber': 'شماره دیسک',
    'tracknumber': 'شماره ترک',
    'genre': 'ژانر',
    'date': 'تاریخ',
    'composer': 'آهنگساز',
    'performer': 'اجراکننده',
    'comment': 'توضیحات',
    'organization': 'سازمان',
    'copyright': 'حق نشر',
    'length': 'طول (مدت زمان)',
    'isrc': 'کد ISRC',
    'lyricist': 'ترانه‌سرا',
    'bpm': 'ضرب در دقیقه (BPM)',
    'replaygain_track_gain': 'افزایش ReplayGain ترک',
    'replaygain_track_peak': 'پیک ReplayGain ترک',
    'replaygain_album_gain': 'افزایش ReplayGain آلبوم',
    'replaygain_album_peak': 'پیک ReplayGain آلبوم',
    'DateTimeOriginal': 'تاریخ و زمان اصلی',
    'Make': 'سازنده دوربین',
    'Model': 'مدل دوربین',
    'Software': 'نرم‌افزار',
    'GPSInfo': 'اطلاعات GPS',
    'ExposureTime': 'زمان نوردهی',
    'FNumber': 'عدد F',
    'ISOSpeedRatings': 'سرعت ISO',
    'FocalLength': 'فاصله کانونی',
    'LensModel': 'مدل لنز',
    'Orientation': 'جهت‌گیری',
    'XResolution': 'رزولوشن افقی',
    'YResolution': 'رزولوشن عمودی',
    'DateTime': 'تاریخ و زمان',
    'ExifVersion': 'نسخه EXIF',
    'Flash': 'فلاش',
    'BitsPerSample': 'بیت در نمونه',
    'ColorComponents': 'اجزای رنگ',
    'EncodingProcess': 'فرآیند کدگذاری',
    'FileAccessDate': 'تاریخ دسترسی فایل',
    'FileInodeChangeDate': 'تاریخ تغییر inode فایل',
    'FileModifyDate': 'تاریخ اصلاح فایل',
    'FilePermissions': 'مجوزهای فایل',
    'FileSize': 'اندازه فایل',
    'FileType': 'نوع فایل',
    'FileTypeExtension': 'پسوند نوع فایل',
    'ImageHeight': 'ارتفاع تصویر',
    'ImageSize': 'اندازه تصویر',
    'ImageWidth': 'عرض تصویر',
    'JFIFVersion': 'نسخه JFIF',
    'MIMEType': 'نوع MIME',
    'Megapixels': 'مگاپیکسل',
    'ResolutionUnit': 'واحد رزولوشن',
    'YCbCrSubSampling': 'زیرنمونه‌برداری YCbCr',
    'checksum': 'چک‌سام',
    'file_name': 'نام فایل',
    'file_size': 'اندازه فایل',
    'file_type': 'نوع فایل',
    'file_type_extension': 'پسوند فایل',
    'mime_type': 'نوع MIME',
    'jfif_version': 'نسخه JFIF',
    'resolution_unit': 'واحد رزولوشن',
    'x_resolution': 'رزولوشن افقی',
    'y_resolution': 'رزولوشن عمودی',
    'image_width': 'عرض تصویر',
    'image_height': 'ارتفاع تصویر',
    'encoding_process': 'فرآیند کدگذاری',
    'bits_per_sample': 'بیت در نمونه',
    'color_components': 'اجزای رنگ',
    'y_cb_cr_sub_sampling': 'زیرنمونه‌برداری YCbCr',
    'image_size': 'اندازه تصویر',
    'megapixels': 'مگاپیکسل',
    'category': 'دسته‌بندی',
    'raw_header': 'هدر خام',
    'format': 'فرمت',
    'duration': 'مدت زمان',
    'bit_rate': 'نرخ بیت',
    'overall_bit_rate': 'نرخ بیت کلی',
    'frame_rate': 'نرخ فریم',
    'width': 'عرض',
    'height': 'ارتفاع',
    'color_space': 'فضای رنگ',
    'chroma_subsampling': 'زیرنمونه‌برداری کروما',
    'bit_depth': 'عمق بیت',
    'compression_mode': 'حالت فشرده‌سازی',
    'stream_size': 'اندازه جریان',
    'complete_name': 'نام کامل فایل',
    'format_profile': 'پروفایل فرمت',
    'codec_id': 'شناسه کدک',
    'encoded_date': 'تاریخ کدگذاری',
    'tagged_date': 'تاریخ برچسب‌گذاری',
    'channel_layout': 'طرح کانال‌ها',
    'sampling_rate': 'نرخ نمونه‌برداری',
    'display_aspect_ratio': 'نسبت ابعاد نمایش',
    'bits_per_pixel_frame': 'بیت در پیکسل فریم',
    'color_range': 'محدوده رنگ',
    'scan_type': 'نوع اسکن'
}

# دیکشنری توضیحات فارسی برای Tooltip
TOOLTIPS = {
    'title': 'عنوان آهنگ، تصویر یا ویدیو',
    'artist': 'نام خواننده یا هنرمند',
    'album': 'نام آلبوم',
    'albumartist': 'نام خواننده اصلی آلبوم',
    'conductor': 'نام رهبر ارکستر',
    'discnumber': 'شماره دیسک در مجموعه',
    'tracknumber': 'شماره ترک در آلبوم',
    'genre': 'ژانر موسیقی یا دسته‌بندی',
    'date': 'تاریخ انتشار یا ثبت',
    'composer': 'نام آهنگساز',
    'performer': 'نام اجراکننده',
    'comment': 'توضیحات یا یادداشت‌ها',
    'organization': 'نام سازمان یا شرکت',
    'copyright': 'اطلاعات حق نشر',
    'length': 'مدت زمان فایل (ثانیه یا میلی‌ثانیه)',
    'isrc': 'کد بین‌المللی استاندارد ضبط',
    'lyricist': 'نام ترانه‌سرا',
    'bpm': 'تعداد ضرب در دقیقه (تمپو)',
    'replaygain_track_gain': 'میزان افزایش صدا برای ترک (ReplayGain)',
    'replaygain_track_peak': 'حداکثر پیک صدا برای ترک (ReplayGain)',
    'replaygain_album_gain': 'میزان افزایش صدا برای آلبوم (ReplayGain)',
    'replaygain_album_peak': 'حداکثر پیک صدا برای آلبوم (ReplayGain)',
    'DateTimeOriginal': 'تاریخ و زمان ثبت عکس',
    'Make': 'سازنده دوربین',
    'Model': 'مدل دوربین',
    'Software': 'نرم‌افزار استفاده شده',
    'GPSInfo': 'اطلاعات موقعیت مکانی (طول و عرض جغرافیایی)',
    'ExposureTime': 'زمان نوردهی دوربین (ثانیه)',
    'FNumber': 'عدد F دوربین (دیافراگم)',
    'ISOSpeedRatings': 'سرعت ISO دوربین',
    'FocalLength': 'فاصله کانونی لنز (میلی‌متر)',
    'LensModel': 'مدل لنز دوربین',
    'Orientation': 'جهت‌گیری تصویر (افقی/عمودی)',
    'XResolution': 'رزولوشن افقی تصویر (نقطه در اینچ)',
    'YResolution': 'رزولوشن عمودی تصویر (نقطه در اینچ)',
    'DateTime': 'تاریخ و زمان تغییر فایل',
    'ExifVersion': 'نسخه اطلاعات EXIF',
    'Flash': 'وضعیت فلاش (روشن/خاموش)',
    'BitsPerSample': 'تعداد بیت در هر نمونه (عمق بیت)',
    'ColorComponents': 'تعداد اجزای رنگ در تصویر',
    'EncodingProcess': 'فرآیند کدگذاری تصویر یا ویدیو',
    'FileAccessDate': 'تاریخ آخرین دسترسی به فایل',
    'FileInodeChangeDate': 'تاریخ تغییر inode فایل (ساختار سیستم فایل)',
    'FileModifyDate': 'تاریخ آخرین اصلاح فایل',
    'FilePermissions': 'مجوزهای دسترسی فایل (مانند خواندن/نوشتن)',
    'FileSize': 'اندازه فایل بر حسب کیلوبایت یا مگابایت',
    'FileType': 'نوع فایل (مانند JPEG، MP4)',
    'FileTypeExtension': 'پسوند فایل (مانند jpg، mp4)',
    'ImageHeight': 'ارتفاع تصویر (پیکسل)',
    'ImageSize': 'اندازه تصویر (عرض x ارتفاع)',
    'ImageWidth': 'عرض تصویر (پیکسل)',
    'JFIFVersion': 'نسخه JFIF (فرمت تبادل JPEG)',
    'MIMEType': 'نوع MIME فایل (مانند image/jpeg)',
    'Megapixels': 'تعداد مگاپیکسل تصویر',
    'ResolutionUnit': 'واحد رزولوشن (مانند اینچ)',
    'YCbCrSubSampling': 'زیرنمونه‌برداری YCbCr (کاهش رنگ)',
    'checksum': 'چک‌سام MD5 برای تأیید یکپارچگی فایل',
    'file_name': 'نام فایل بدون مسیر',
    'file_size': 'اندازه فایل با واحد مناسب',
    'file_type': 'نوع فایل (مانند JPEG، MP3)',
    'file_type_extension': 'پسوند فایل بدون نقطه',
    'mime_type': 'نوع MIME برای شناسایی فرمت',
    'jfif_version': 'نسخه JFIF تصویر',
    'resolution_unit': 'واحد اندازه‌گیری رزولوشن',
    'x_resolution': 'رزولوشن افقی تصویر',
    'y_resolution': 'رزولوشن عمودی تصویر',
    'image_width': 'عرض تصویر در پیکسل',
    'image_height': 'ارتفاع تصویر در پیکسل',
    'encoding_process': 'روش کدگذاری استفاده شده',
    'bits_per_sample': 'تعداد بیت برای هر نمونه',
    'color_components': 'تعداد اجزای رنگ (مانند RGB)',
    'y_cb_cr_sub_sampling': 'زیرنمونه‌برداری YCbCr برای فشرده‌سازی',
    'image_size': 'اندازه تصویر (عرض x ارتفاع)',
    'megapixels': 'تعداد مگاپیکسل (میلیون پیکسل)',
    'category': 'دسته‌بندی فایل (تصویر، ویدیو و غیره)',
    'raw_header': 'هدر خام فایل به صورت هگزادسیمال',
    'format': 'فرمت فایل (مانند MPEG-4، JPEG)',
    'duration': 'مدت زمان پخش (ثانیه یا میلی‌ثانیه)',
    'bit_rate': 'نرخ بیت (کیلوبیت بر ثانیه)',
    'overall_bit_rate': 'نرخ بیت کلی فایل',
    'frame_rate': 'نرخ فریم (فریم بر ثانیه)',
    'width': 'عرض ویدیو یا تصویر (پیکسل)',
    'height': 'ارتفاع ویدیو یا تصویر (پیکسل)',
    'color_space': 'فضای رنگ (مانند YUV)',
    'chroma_subsampling': 'زیرنمونه‌برداری کروما (مانند 4:2:0)',
    'bit_depth': 'عمق بیت (مانند 8 بیت)',
    'compression_mode': 'حالت فشرده‌سازی (Lossy یا Lossless)',
    'stream_size': 'اندازه جریان داده (کیلوبایت یا مگابایت)',
    'complete_name': 'مسیر کامل فایل',
    'format_profile': 'پروفایل فرمت (مانند Main@L3.1)',
    'codec_id': 'شناسه کدک استفاده شده',
    'encoded_date': 'تاریخ کدگذاری فایل',
    'tagged_date': 'تاریخ برچسب‌گذاری فایل',
    'channel_layout': 'طرح کانال‌های صوتی (مانند L R)',
    'sampling_rate': 'نرخ نمونه‌برداری صوت (مانند 48.0 kHz)',
    'display_aspect_ratio': 'نسبت ابعاد نمایش (مانند 16:9)',
    'bits_per_pixel_frame': 'بیت در هر پیکسل فریم',
    'color_range': 'محدوده رنگ (مانند Full)',
    'scan_type': 'نوع اسکن ویدیو (Progressive یا Interlaced)'
}

class MetadataHandler:
    def load_metadata(self):
        raise NotImplementedError

    def save_metadata(self, metadata_dict):
        raise NotImplementedError

class MP3MetadataHandler(MetadataHandler):
    def __init__(self, file_path):
        if EasyID3 is None or ID3 is None:
            raise ImportError("کتابخانه mutagen نصب نیست. لطفاً آن را نصب کنید.")
        self.file_path = file_path
        try:
            self.audio = EasyID3(file_path)
            self.id3 = ID3(file_path)
        except Exception as e:
            raise ValueError(f"خطا در بارگذاری فایل MP3: {e}")

    def load_metadata(self):
        metadata = {}
        for key in self.audio.keys():
            try:
                value = self.audio.get(key, [''])[0] if self.audio.get(key, ['']) else ''
                metadata[key] = value
            except IndexError:
                metadata[key] = ''
        # اطلاعات اضافی از mutagen
        if File is not None:
            media_info = File(self.file_path)
            if media_info:
                metadata.update({
                    'length': f"{media_info.info.length:.3f} ثانیه" if media_info.info.length else 'N/A',
                    'bit_rate': f"{media_info.info.bitrate // 1000} kb/s" if media_info.info.bitrate else 'N/A',
                    'format': media_info.mime[0] if media_info.mime else 'N/A'
                })
        return metadata

    def save_metadata(self, metadata_dict):
        for key, value in metadata_dict.items():
            if value.strip():
                self.audio[key] = value
            elif key in self.audio:
                del self.audio[key]
        self.audio.save()

    def load_image(self):
        apic = self.id3.getall('APIC')
        return apic[0].data if apic else None

    def save_image(self, image_path):
        try:
            with open(image_path, 'rb') as img_file:
                img_data = img_file.read()
            self.id3.delall('APIC')
            self.id3.add(APIC(
                encoding=3,
                mime='image/jpeg',
                type=3,
                desc='Cover',
                data=img_data
            ))
            self.id3.save()
        except Exception as e:
            raise ValueError(f"خطا در ذخیره تصویر: {e}")

class GenericMetadataHandler(MetadataHandler):
    def __init__(self, file_path):
        self.file_path = file_path
        try:
            self.image = Image.open(file_path)
            self.exif_data = piexif.load(file_path) if 'exif' in self.image.info else {}
        except Exception:
            self.image = None
            self.exif_data = {}

    def calculate_checksum(self, algorithm='md5'):
        hash_algo = hashlib.md5()
        with open(self.file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_algo.update(chunk)
        return hash_algo.hexdigest()

    def get_file_info(self):
        stat_info = os.stat(self.file_path)
        file_type, _ = mimetypes.guess_type(self.file_path)
        file_type = file_type or 'application/octet-stream'
        return {
            'complete_name': self.file_path,
            'file_size': f"{os.path.getsize(self.file_path) / 1024:.1f} KiB",
            'file_type': file_type,
            'file_type_extension': os.path.splitext(self.file_path)[1].lower().lstrip('.'),
            'mime_type': file_type,
            'FileAccessDate': os.path.getatime(self.file_path),
            'FileModifyDate': os.path.getmtime(self.file_path),
            'FileInodeChangeDate': os.path.getctime(self.file_path),
            'FilePermissions': oct(stat_info.st_mode)[-3:]
        }

    def get_image_properties(self):
        if not self.image:
            return {}
        width, height = self.image.size
        return {
            'image_width': width,
            'image_height': height,
            'image_size': f"{width}x{height}",
            'megapixels': f"{(width * height) / 1e6:.1f}",
            'format': self.image.format,
            'color_space': 'YUV' if self.image.mode in ['YCbCr'] else self.image.mode
        }

    def get_raw_header(self):
        with open(self.file_path, 'rb') as f:
            header = f.read(64)
        return binascii.hexlify(header).decode('ascii').upper()

    def load_metadata(self):
        metadata = {}
        metadata['checksum'] = self.calculate_checksum()
        metadata.update(self.get_file_info())
        
        if self.image:
            metadata.update(self.get_image_properties())
            metadata['category'] = 'image'
            metadata['raw_header'] = self.get_raw_header()

            if self.exif_data:
                for ifd in self.exif_data:
                    if ifd == "thumbnail":
                        continue
                    for tag, value in self.exif_data[ifd].items():
                        tag_name = TAGS[ifd][tag]["name"]
                        try:
                            if isinstance(value, bytes):
                                value = value.decode('utf-8', errors='ignore')
                            elif isinstance(value, tuple):
                                if tag_name == 'ExposureTime':
                                    value = f"{value[0]}/{value[1]} ثانیه"
                                elif tag_name == 'FNumber':
                                    value = f"f/{value[0]/value[1]:.1f}"
                                elif tag_name == 'GPSInfo':
                                    gps_data = self.parse_gps_info(value)
                                    value = gps_data if gps_data else 'N/A'
                                else:
                                    value = str(value)
                            elif isinstance(value, int) and tag_name in ['ISOSpeedRatings', 'Orientation']:
                                value = str(value)
                            else:
                                value = str(value)
                            metadata[tag_name] = value
                        except Exception:
                            metadata[tag_name] = 'N/A'
            else:
                metadata['NoExifData'] = "این فایل اطلاعات EXIF ندارد"
                metadata['GPSInfo'] = 'N/A'
        else:
            metadata['category'] = 'unknown'

        # اطلاعات ویدیویی و صوتی با mutagen
        if File is not None:
            try:
                media_info = File(self.file_path)
                if media_info and hasattr(media_info, 'info'):
                    info = media_info.info
                    metadata.update({
                        'format': media_info.mime[0] if media_info.mime else 'N/A',
                        'duration': f"{info.length * 1000:.0f} ms" if info.length else 'N/A',
                        'bit_rate': f"{info.bitrate // 1000} kb/s" if hasattr(info, 'bitrate') else 'N/A',
                        'width': str(info.width) if hasattr(info, 'width') else 'N/A',
                        'height': str(info.height) if hasattr(info, 'height') else 'N/A',
                        'frame_rate': f"{info.fps:.3f} FPS" if hasattr(info, 'fps') else 'N/A',
                        'bit_depth': str(info.bit_depth) if hasattr(info, 'bit_depth') else 'N/A',
                        'compression_mode': 'Lossy' if info.bitrate else 'N/A',
                        'stream_size': f"{os.path.getsize(self.file_path) / 1024:.1f} KiB",
                        'sampling_rate': f"{info.sample_rate / 1000:.1f} kHz" if hasattr(info, 'sample_rate') else 'N/A',
                        'channel_layout': 'Stereo' if hasattr(info, 'channels') and info.channels == 2 else 'Mono' if hasattr(info, 'channels') else 'N/A'
                    })
                    for key, value in media_info.items():
                        if key.startswith('replaygain_') or key in ['isrc', 'lyricist', 'bpm']:
                            metadata[key] = str(value)
            except Exception:
                pass

        return metadata

    def parse_gps_info(self, gps_info):
        try:
            if not isinstance(gps_info, dict):
                return 'N/A'
            lat_ref = gps_info.get(1, b'N').decode('ascii')
            lat = gps_info.get(2, ((0, 1), (0, 1), (0, 1)))
            lon_ref = gps_info.get(3, b'E').decode('ascii')
            lon = gps_info.get(4, ((0, 1), (0, 1), (0, 1)))

            lat_deg = lat[0][0] / lat[0][1] + lat[1][0] / (lat[1][1] * 60) + lat[2][0] / (lat[2][1] * 3600)
            lon_deg = lon[0][0] / lon[0][1] + lon[1][0] / (lon[1][1] * 60) + lon[2][0] / (lon[2][1] * 3600)

            if lat_ref == 'S':
                lat_deg = -lat_deg
            if lon_ref == 'W':
                lon_deg = -lon_deg

            return f"Latitude: {lat_deg:.6f}, Longitude: {lon_deg:.6f}"
        except Exception:
            return 'N/A'

    def save_metadata(self, metadata_dict):
        if not self.image or not self.exif_data:
            raise ValueError("فقط برای فایل‌های تصویری با EXIF قابل استفاده است.")
        try:
            exif_dict = piexif.load(self.file_path)
            for key, value in metadata_dict.items():
                if key in ['checksum', 'file_name', 'file_size', 'file_type', 'file_type_extension', 
                          'mime_type', 'image_size', 'megapixels', 'category', 'raw_header', 'NoExifData']:
                    continue
                for ifd in exif_dict:
                    for tag in exif_dict[ifd]:
                        if TAGS[ifd][tag]["name"] == key:
                            try:
                                if isinstance(exif_dict[ifd][tag], bytes):
                                    exif_dict[ifd][tag] = value.encode('utf-8')
                                elif isinstance(exif_dict[ifd][tag], tuple):
                                    if '/' in value and key in ['ExposureTime', 'FNumber']:
                                        num, denom = map(int, value.split('/'))
                                        exif_dict[ifd][tag] = (num, denom)
                                    else:
                                        exif_dict[ifd][tag] = value
                                else:
                                    exif_dict[ifd][tag] = value
                            except Exception:
                                continue
                            break
            exif_bytes = piexif.dump(exif_dict)
            piexif.insert(exif_bytes, self.file_path)
        except Exception as e:
            raise ValueError(f"خطا در ذخیره متادیتا: {e}")

    def remove_metadata(self):
        if not self.image:
            raise ValueError("فقط برای فایل‌های تصویری قابل استفاده است.")
        try:
            piexif.remove(self.file_path)
        except Exception as e:
            raise ValueError(f"خطا در حذف متادیتا: {e}")

class MetadataEditorTab(QWidget):
    def __init__(self, update_status, tray_icon):
        super().__init__()
        self.update_status = update_status
        self.tray_icon = tray_icon
        self.current_file = None
        self.handler = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        title_label = QLabel("ویرایشگر متادیتا")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50; margin-bottom: 10px;")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        file_layout = QHBoxLayout()
        self.select_file_btn = QPushButton("انتخاب فایل")
        self.select_file_btn.setIcon(QIcon("icons/folder.png"))
        self.select_file_btn.clicked.connect(self.select_file)
        self.select_file_btn.setStyleSheet("""
            QPushButton { background-color: #3498db; color: white; padding: 8px; border-radius: 5px; }
            QPushButton:hover { background-color: #2980b9; }
        """)
        file_layout.addWidget(self.select_file_btn)
        self.file_label = QLabel("هیچ فایلی انتخاب نشده")
        self.file_label.setStyleSheet("font-size: 14px; color: #34495e;")
        file_layout.addWidget(self.file_label)
        file_layout.addStretch()
        layout.addLayout(file_layout)

        self.image_layout = QHBoxLayout()
        self.image_display = QLabel("بدون تصویر")
        self.image_display.setFixedSize(100, 100)
        self.image_display.setStyleSheet("border: 1px solid #bdc3c7; border-radius: 5px; background-color: #f5f5f5;")
        self.image_layout.addWidget(self.image_display)
        self.change_image_btn = QPushButton("تغییر تصویر")
        self.change_image_btn.setIcon(QIcon("icons/image.png"))
        self.change_image_btn.clicked.connect(self.select_image)
        self.change_image_btn.setStyleSheet("""
            QPushButton { background-color: #e67e22; color: white; padding: 6px; border-radius: 5px; }
            QPushButton:hover { background-color: #d35400; }
        """)
        self.image_layout.addWidget(self.change_image_btn)
        self.image_layout.addStretch()
        layout.addLayout(self.image_layout)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: 1px solid #bdc3c7; border-radius: 5px; }")
        self.table_widget = QTableWidget()
        self.table_widget.setColumnCount(2)
        self.table_widget.setHorizontalHeaderLabels(["فیلد", "مقدار"])
        self.table_widget.horizontalHeader().setStyleSheet("font-weight: bold; color: #2c3e50;")
        self.table_widget.setColumnWidth(1, 300)  # Increase width of "مقدار" column
        self.scroll_area.setWidget(self.table_widget)
        layout.addWidget(self.scroll_area)

        action_layout = QHBoxLayout()
        self.save_btn = QPushButton("ذخیره تغییرات")
        self.save_btn.setIcon(QIcon("icons/save.png"))
        self.save_btn.clicked.connect(self.save_metadata)
        self.save_btn.setStyleSheet("""
            QPushButton { background-color: #2ecc71; color: white; padding: 8px; border-radius: 5px; }
            QPushButton:hover { background-color: #27ae60; }
        """)
        action_layout.addWidget(self.save_btn)

        self.export_pdf_btn = QPushButton("ذخیره به PDF")
        self.export_pdf_btn.setIcon(QIcon("icons/pdf.png"))
        self.export_pdf_btn.clicked.connect(self.export_to_pdf)
        self.export_pdf_btn.setStyleSheet("""
            QPushButton { background-color: #9b59b6; color: white; padding: 8px; border-radius: 5px; }
            QPushButton:hover { background-color: #8e44ad; }
        """)
        action_layout.addWidget(self.export_pdf_btn)

        self.remove_metadata_btn = QPushButton("حذف متادیتا")
        self.remove_metadata_btn.setIcon(QIcon("icons/delete.png"))
        self.remove_metadata_btn.clicked.connect(self.remove_metadata)
        self.remove_metadata_btn.setStyleSheet("""
            QPushButton { background-color: #e74c3c; color: white; padding: 8px; border-radius: 5px; }
            QPushButton:hover { background-color: #c0392b; }
        """)
        action_layout.addWidget(self.remove_metadata_btn)

        self.reset_btn = QPushButton("ریست")
        self.reset_btn.setIcon(QIcon("icons/reset.png"))
        self.reset_btn.clicked.connect(self.reset_file)
        self.reset_btn.setStyleSheet("""
            QPushButton { background-color: #f39c12; color: white; padding: 8px; border-radius: 5px; }
            QPushButton:hover { background-color: #e67e22; }
        """)
        action_layout.addWidget(self.reset_btn)

        layout.addLayout(action_layout)
        layout.addStretch()
        self.setLayout(layout)

        self.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #FFFFFFFF, stop:1 #00C7B3FF
                font-family: 'B Nazanin', Tahoma, sans-serif;
            }
            QLabel {
                font-size: 14px;
                color: #2c3e50;
            }
            QTableWidget {
                border: 1px solid #BDC7C6FF;
                border-radius: 5px;
                background-color: #f5f5f5;
            }
            QTableWidget::item {
                padding: 6px;
                border: 1px solid #bdc3c7;
                border-radius: 3px;
            }
            QTableWidget::item:selected {
                background-color: #3498db;
                color: white;
            }
        """)

    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "انتخاب فایل", "", "All Files (*)")
        if file_path:
            self.current_file = file_path
            self.file_label.setText(os.path.basename(file_path))
            self.load_metadata()

    def load_metadata(self):
        if not self.current_file:
            self.update_status("هیچ فایلی انتخاب نشده.")
            QMessageBox.warning(self, "هشدار", "لطفاً ابتدا یک فایل انتخاب کنید.")
            return

        ext = os.path.splitext(self.current_file)[1].lower()
        try:
            if ext == '.mp3':
                self.handler = MP3MetadataHandler(self.current_file)
                self.change_image_btn.setVisible(True)
                self.image_display.setVisible(True)
                self.remove_metadata_btn.setVisible(False)
                image_data = self.handler.load_image()
                if image_data:
                    pixmap = QPixmap()
                    pixmap.loadFromData(image_data)
                    self.image_display.setPixmap(pixmap.scaled(100, 100, Qt.KeepAspectRatio))
                else:
                    self.image_display.setText("بدون تصویر")
                    self.image_display.setPixmap(QPixmap())
            else:
                self.handler = GenericMetadataHandler(self.current_file)
                self.change_image_btn.setVisible(False)
                self.image_display.setVisible(False)
                self.remove_metadata_btn.setVisible(bool(self.handler.image))

            metadata = self.handler.load_metadata()
            self.populate_table(metadata)
            self.update_status("متادیتا با موفقیت بارگذاری شد.")
            self.tray_icon.showMessage("ویرایشگر متادیتا", "متادیتا با موفقیت بارگذاری شد.", QSystemTrayIcon.Information, 3000)
        except ValueError as e:
            self.update_status(f"خطا: {e}")
            QMessageBox.warning(self, "هشدار", str(e))
        except Exception as e:
            self.update_status(f"خطا در بارگذاری متادیتا: {e}")
            QMessageBox.critical(self, "خطا", f"خطا در بارگذاری متادیتا: {e}")

    def populate_table(self, metadata):
        self.table_widget.clearContents()
        self.table_widget.setRowCount(0)
        for key, value in metadata.items():
            row = self.table_widget.rowCount()
            self.table_widget.insertRow(row)
            field_item = QTableWidgetItem(TRANSLATIONS.get(key, key))
            field_item.setToolTip(TOOLTIPS.get(key, ''))
            value_item = QTableWidgetItem(str(value))
            value_item.setToolTip(TOOLTIPS.get(key, ''))
            self.table_widget.setItem(row, 0, field_item)
            self.table_widget.setItem(row, 1, value_item)

    def select_image(self):
        if not self.current_file or not isinstance(self.handler, MP3MetadataHandler):
            QMessageBox.warning(self, "هشدار", "لطفاً ابتدا یک فایل MP3 انتخاب کنید.")
            return
        image_path, _ = QFileDialog.getOpenFileName(self, "انتخاب تصویر", "", "Image Files (*.jpg *.jpeg *.png)")
        if image_path:
            try:
                self.handler.save_image(image_path)
                pixmap = QPixmap(image_path).scaled(100, 100, Qt.KeepAspectRatio)
                self.image_display.setPixmap(pixmap)
                self.update_status("تصویر با موفقیت تغییر کرد.")
                self.tray_icon.showMessage("ویرایشگر متادیتا", "تصویر با موفقیت تغییر کرد.", QSystemTrayIcon.Information, 3000)
                QMessageBox.information(self, "موفقیت", "تصویر با موفقیت تغییر کرد.")
            except Exception as e:
                self.update_status(f"خطا در تغییر تصویر: {e}")
                QMessageBox.critical(self, "خطا", f"خطا در تغییر تصویر: {e}")

    def save_metadata(self):
        if not self.handler:
            self.update_status("هیچ فایلی انتخاب نشده.")
            QMessageBox.warning(self, "هشدار", "لطفاً ابتدا یک فایل انتخاب کنید.")
            return

        metadata_dict = {}
        for row in range(self.table_widget.rowCount()):
            key = list(TRANSLATIONS.keys())[list(TRANSLATIONS.values()).index(self.table_widget.item(row, 0).text())]
            value = self.table_widget.item(row, 1).text()
            metadata_dict[key] = value

        try:
            self.handler.save_metadata(metadata_dict)
            self.update_status("تغییرات با موفقیت ذخیره شدند.")
            self.tray_icon.showMessage("ویرایشگر متادیتا", "تغییرات با موفقیت ذخیره شدند.", QSystemTrayIcon.Information, 3000)
            QMessageBox.information(self, "موفقیت", "تغییرات متادیتا با موفقیت ذخیره شدند.")
        except ValueError as e:
            self.update_status(f"خطا: {e}")
            QMessageBox.warning(self, "هشدار", str(e))
        except Exception as e:
            self.update_status(f"خطا در ذخیره متادیتا: {e}")
            QMessageBox.critical(self, "خطا", f"خطا در ذخیره متادیتا: {e}")

    def export_to_pdf(self):
        if not self.current_file or not self.handler:
            self.update_status("هیچ فایلی انتخاب نشده.")
            QMessageBox.warning(self, "هشدار", "لطفاً ابتدا یک فایل انتخاب کنید.")
            return

        metadata = self.handler.load_metadata()
        file_name = os.path.splitext(os.path.basename(self.current_file))[0] + "_metadata.pdf"
        save_path, _ = QFileDialog.getSaveFileName(self, "ذخیره PDF", file_name, "PDF Files (*.pdf)")
        if not save_path:
            return

        try:
            doc = SimpleDocTemplate(save_path, pagesize=letter)
            styles = getSampleStyleSheet()
            story = []
            style_title = styles['Title']
            style_normal = styles['Normal']
            style_normal.fontName = 'Helvetica'
            style_title.fontName = 'Helvetica-Bold'

            story.append(Paragraph("اطلاعات متادیتا", style_title))
            story.append(Spacer(1, 12))

            for key, value in metadata.items():
                persian_label = TRANSLATIONS.get(key, key)
                text = f"<b>{persian_label}:</b> {value}"
                story.append(Paragraph(text, style_normal))
                story.append(Spacer(1, 6))

            doc.build(story)
            self.update_status("متادیتا با موفقیت به PDF ذخیره شد.")
            self.tray_icon.showMessage("ویرایشگر متادیتا", "متادیتا به PDF ذخیره شد.", QSystemTrayIcon.Information, 3000)
            QMessageBox.information(self, "موفقیت", "متادیتا با موفقیت به فایل PDF ذخیره شد.")
        except Exception as e:
            self.update_status(f"خطا در ذخیره PDF: {e}")
            QMessageBox.critical(self, "خطا", f"خطا در ذخیره PDF: {e}")

    def remove_metadata(self):
        if not self.current_file or not isinstance(self.handler, GenericMetadataHandler) or not self.handler.image:
            self.update_status("فقط برای تصاویر قابل استفاده است.")
            QMessageBox.warning(self, "هشدار", "این قابلیت فقط برای فایل‌های تصویری قابل استفاده است.")
            return

        reply = QMessageBox.question(self, "تأیید", "آیا مطمئن هستید که می‌خواهید متادیتا را حذف کنید؟", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                self.handler.remove_metadata()
                self.load_metadata()
                self.update_status("متادیتا با موفقیت حذف شد.")
                self.tray_icon.showMessage("ویرایشگر متادیتا", "متادیتا با موفقیت حذف شد.", QSystemTrayIcon.Information, 3000)
                QMessageBox.information(self, "موفقیت", "متادیتا با موفقیت حذف شد.")
            except ValueError as e:
                self.update_status(f"خطا: {e}")
                QMessageBox.warning(self, "هشدار", str(e))
            except Exception as e:
                self.update_status(f"خطا در حذف متادیتا: {e}")
                QMessageBox.critical(self, "خطا", f"خطا در حذف متادیتا: {e}")

    def reset_file(self):
        if not self.current_file:
            self.update_status("هیچ فایلی انتخاب نشده.")
            QMessageBox.warning(self, "هشدار", "لطفاً ابتدا یک فایل انتخاب کنید.")
            return

        reply = QMessageBox.question(self, "تأیید", "آیا مطمئن هستید که می‌خواهید ریست کنید؟", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                self.handler = None
                self.current_file = None
                self.file_label.setText("هیچ فایلی انتخاب نشده")
                self.table_widget.clearContents()
                self.table_widget.setRowCount(0)
                self.image_display.setText("بدون تصویر")
                self.image_display.setPixmap(QPixmap())
                self.update_status(" با موفقیت ریست شد.")
                self.tray_icon.showMessage("ویرایشگر متادیتا", " با موفقیت ریست شد.", QSystemTrayIcon.Information, 3000)
                QMessageBox.information(self, "موفقیت", " با موفقیت ریست شد.")
            except Exception as e:
                self.update_status(f"خطا در ریست : {e}")
                QMessageBox.critical(self, "خطا", f"خطا در ریست : {e}")