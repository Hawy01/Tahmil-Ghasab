import flet as ft
import yt_dlp
import threading
import os

def main(page: ft.Page):
    page.title = "تحميل غصب"
    page.theme_mode = ft.ThemeMode.DARK
    page.window_width = 400
    page.padding = 20

    # واجهة بسيطة جداً عند البدء لمنع الشاشة السوداء
    status_text = ft.Text("جاري تهيئة التطبيق...")
    page.add(ft.Column([ft.Text("تحميل غصب 🚀", size=30, weight="bold"), status_text], alignment=ft.MainAxisAlignment.CENTER))

    def request_perms():
        # طلب صلاحية الوصول للملفات على Android
        if page.platform == ft.PagePlatform.ANDROID:
            try:
                result = os.system(
                    "am start -a android.settings.MANAGE_APP_ALL_FILES_ACCESS_PERMISSION"
                    " -d package:com.ghasab.downloader"
                )
                if result == 0:
                    status_text.value = "يرجى منح صلاحية الوصول للملفات ثم العودة للتطبيق"
                else:
                    status_text.value = "جاهز للعمل"
            except Exception as e:
                print(f"request_perms error: {e}")
                status_text.value = "جاهز للعمل"
            page.update()

    def show_snack(msg: str):
        page.snack_bar = ft.SnackBar(ft.Text(msg))
        page.snack_bar.open = True
        page.update()

    def download_video(url: str):
        url = url.strip()
        if not url:
            show_snack("يرجى إدخال رابط الفيديو")
            return
        if not (url.startswith("http://") or url.startswith("https://")):
            show_snack("الرابط غير صالح، يجب أن يبدأ بـ http:// أو https://")
            return

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
            show_snack("تم التحميل بنجاح في مجلد Downloads!")
        except Exception as e:
            show_snack(f"فشل التحميل: {str(e)[:50]}")

    # واجهة التحميل الحقيقية
    url_input = ft.TextField(label="رابط الفيديو", expand=True)
    btn = ft.ElevatedButton(
        "تحميل غصب",
        on_click=lambda _: threading.Thread(
            target=download_video, args=(url_input.value,), daemon=True
        ).start()
    )

    # تبديل الواجهة بعد ثانية واحدة لضمان عدم حدوث شاشة سوداء
    def switch_ui():
        page.controls.clear()
        page.add(ft.Column([ft.Text("تحميل غصب 🚀", size=30, weight="bold"), url_input, btn]))
        page.update()
        request_perms()

    threading.Timer(1, switch_ui).start()

ft.app(target=main)
