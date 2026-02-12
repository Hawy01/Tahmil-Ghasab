import flet as ft
import yt_dlp
import threading
import os
import json

# ثابت لملف السجل
HISTORY_FILE = "download_history.json"

def main(page: ft.Page):
    # إعدادات الصفحة الأساسية
    page.title = "تحميل غصب 🚀"
    page.theme_mode = ft.ThemeMode.DARK
    page.scroll = ft.ScrollMode.AUTO
    page.padding = 20

    # متغيرات الحالة
    state = {"ffmpeg_bin": "ffmpeg"}

    # --- عناصر واجهة المستخدم ---
    status_text = ft.Text("...جاري تهيئة التطبيق", color="blueaccent")
    url_input = ft.TextField(
        label="رابط الفيديو", 
        hint_text="الصق الرابط هنا...", 
        expand=True, 
        border_radius=15,
        disabled=True # معطل حتى تنتهي التهيئة
    )
    pb = ft.ProgressBar(width=400, value=0, visible=False)
    history_column = ft.Column(spacing=10)

    # --- الوظائف الأساسية ---

    def request_perms():
        """طلب صلاحية الوصول للملفات بشكل مباشر [استنتاج]"""
        if page.platform == ft.PagePlatform.ANDROID:
            try:
                # محاولة فتح إعدادات الوصول لجميع الملفات للمستخدم [استنتاج]
                os.system("am start -a android.settings.MANAGE_APP_ALL_FILES_ACCESS_PERMISSION -d package:com.ghasab.downloader")
            except:
                pass

    def check_ffmpeg():
        """التأكد من وجود FFmpeg وتحديث حالة التطبيق [استنتاج]"""
        # مسار FFmpeg المتوقع في مجلد الأصول داخل APK [استنتاج]
        asset_ffmpeg = os.path.join(os.getcwd(), "assets", "ffmpeg")
        if os.path.exists(asset_ffmpeg):
            state["ffmpeg_bin"] = asset_ffmpeg
            status_text.value = "جاهز للسحب غصب ✅"
        else:
            status_text.value = "FFmpeg غير موجود (سيتم التحميل بدون دمج جودة عالية)"
        
        url_input.disabled = False
        page.update()

    def download_video(url):
        """مهمة التحميل في خلفية التطبيق"""
        # مسار الحفظ المفضل للمستخدم في مجلد Downloads
        save_path = "/storage/emulated/0/Download/" if page.platform == ft.PagePlatform.ANDROID else "./"
        
        ydl_opts = {
            'ffmpeg_location': state["ffmpeg_bin"],
            'format': 'bestvideo+bestaudio/best',
            'outtmpl': f'{save_path}%(title)s.%(ext)s',
        }
        
        pb.visible = True
        status_text.value = "⏳ جاري التحميل... يرجى عدم إغلاق التطبيق"
        page.update()

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            status_text.value = "✅ اكتمل التحميل في مجلد Downloads!"
            status_text.color = "green"
        except Exception as e:
            status_text.value = f"❌ خطأ: {str(e)[:50]}"
            status_text.color = "red"
        
        pb.visible = False
        page.update()

    # --- بناء الواجهة ---
    page.add(
        ft.Column([
            ft.Text("تحميل غصب 🚀", size=35, weight="bold"),
            status_text,
            ft.Row([
                url_input,
                ft.IconButton(
                    ft.icons.DOWNLOAD_FOR_OFFLINE, 
                    icon_size=35, 
                    on_click=lambda _: threading.Thread(target=download_video, args=(url_input.value,), daemon=True).start()
                )
            ]),
            pb,
            ft.Divider(),
            ft.Text("سجل العمليات", size=18, weight="bold"),
            history_column
        ])
    )

    # تشغيل التهيئة وطلب الصلاحيات بعد ظهور الواجهة فوراً لمنع التعليق
    page.update()
    request_perms()
    threading.Thread(target=check_ffmpeg, daemon=True).start()

# تشغيل التطبيق
ft.app(target=main)
