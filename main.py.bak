import flet as ft
import yt_dlp
import threading
import os

def main(page: ft.Page):
    page.title = "تحميل غصب"
    page.theme_mode = ft.ThemeMode.DARK
    page.window_width = 400
    page.padding = 20
    
    # واجهة بسيطة جداً عند البدء لمنع الشاشة السوداء [استنتاج]
    status_text = ft.Text("جاري تهيئة التطبيق...")
    page.add(ft.Column([ft.Text("تحميل غصب 🚀", size=30, weight="bold"), status_text], alignment=ft.MainAxisAlignment.CENTER))

    def request_perms():
        # محاولة طلب صلاحية الوصول للملفات بشكل مباشر [استنتاج]
        if page.platform == ft.PagePlatform.ANDROID:
            try:
                os.system("am start -a android.settings.MANAGE_APP_ALL_FILES_ACCESS_PERMISSION -d package:com.ghasab.downloader")
                status_text.value = "يرجى منح صلاحية الوصول للملفات ثم العودة للتطبيق"
                page.update()
            except:
                status_text.value = "جاهز للعمل"
                page.update()

    def download_video(url):
        # المستخدم يفضل مجلد التحميلات العام
        save_path = "/storage/emulated/0/Download/" if page.platform == ft.PagePlatform.ANDROID else "./"
        ffmpeg_bin = os.path.join(os.getcwd(), "assets", "ffmpeg")
        
        ydl_opts = {
            'ffmpeg_location': ffmpeg_bin,
            'format': 'bestvideo+bestaudio/best',
            'outtmpl': f'{save_path}%(title)s.%(ext)s',
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            page.snack_bar = ft.SnackBar(ft.Text("تم التحميل بنجاح في مجلد Downloads!"))
            page.snack_bar.open = True
        except Exception as e:
            page.snack_bar = ft.SnackBar(ft.Text(f"فشل التحميل: {str(e)[:50]}"))
            page.snack_bar.open = True
        page.update()

    # واجهة التحميل الحقيقية
    url_input = ft.TextField(label="رابط الفيديو", expand=True)
    btn = ft.ElevatedButton("تحميل غصب", on_click=lambda _: threading.Thread(target=download_video, args=(url_input.value,)).start())
    
    # تبديل الواجهة بعد ثانية واحدة لضمان عدم حدوث شاشة سوداء [استنتاج]
    def switch_ui():
        page.controls.clear()
        page.add(ft.Column([ft.Text("تحميل غصب 🚀", size=30, weight="bold"), url_input, btn]))
        page.update()
        request_perms()

    ft.Timer(1, switch_ui).start()

ft.app(target=main)
