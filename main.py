import flet as ft
import yt_dlp
import threading
import json
import os

HISTORY_FILE = "download_history.json"

def main(page: ft.Page):
    page.title = "تحميل غصب - الإصدار النهائي"
    page.theme_mode = ft.ThemeMode.DARK
    page.scroll = ft.ScrollMode.AUTO
    page.padding = 20

    state = {"cookies_path": None}

    def request_android_permissions():
        if page.platform == ft.PagePlatform.ANDROID:
            try:
                # طلب صلاحية الوصول للملفات بشكل مباشر
                os.system(f"am start -a android.settings.MANAGE_APP_ALL_FILES_ACCESS_PERMISSION -d package:com.ghasab.downloader")
            except: pass

    def load_history():
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except: return []
        return []

    def save_history(data):
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    url_input = ft.TextField(label="رابط الفيديو", expand=True, border_radius=15)
    pb = ft.ProgressBar(width=400, value=0, visible=False, color="blueaccent")
    status_text = ft.Text("جاهز لسحب الفيديو غصب...")
    cookies_info = ft.Text("لم يتم اختيار كوكيز", size=12, italic=True)
    history_column = ft.Column(spacing=10)
    
    history_data = load_history()

    def add_to_ui_history(title, status, error=""):
        icon = ft.icons.CHECK_CIRCLE if status == "تم" else ft.icons.ERROR
        history_column.controls.insert(0, ft.ListTile(
            leading=ft.Icon(icon, color="green" if status == "تم" else "red"),
            title=ft.Text(title, max_lines=1, overflow="ellipsis"),
            subtitle=ft.Text(f"الحالة: {status} {error}"),
        ))
        page.update()

    for item in history_data:
        add_to_ui_history(item['title'], item['status'], item.get('error', ""))

    def on_file_result(e):
        if e.files:
            state["cookies_path"] = e.files[0].path
            cookies_info.value = f"تم الربط: {e.files[0].name}"
            page.update()

    file_picker = ft.FilePicker(on_result=on_file_result)
    page.overlay.append(file_picker)

    def progress_hook(d):
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate', 1)
            pb.value = d.get('downloaded_bytes', 0) / total
            page.update()

    def download_task(url, cookies_path):
        # البحث عن FFmpeg المدمج في الأصول أولاً
        ffmpeg_bin = os.path.join(os.getcwd(), "assets", "ffmpeg")
        if not os.path.exists(ffmpeg_bin): ffmpeg_bin = "ffmpeg"
        
        # حفظ الملفات في مجلد التحميلات لسهولة الوصول إليها
        download_dir = "/storage/emulated/0/Download/" if page.platform == ft.PagePlatform.ANDROID else "./"
        
        ydl_opts = {
            'ffmpeg_location': ffmpeg_bin,
            'format': 'bestvideo+bestaudio/best',
            'progress_hooks': [progress_hook],
            'outtmpl': os.path.join(download_dir, '%(title)s.%(ext)s'),
        }
        
        if cookies_path: ydl_opts['cookiefile'] = cookies_path

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                title, res_status, res_error = info.get('title', 'فيديو'), "تم", ""
        except Exception as ex:
            title, res_status, res_error = url, "فشل", str(ex)[:40]

        history_data.append({"title": title, "status": res_status, "error": res_error})
        save_history(history_data)
        pb.visible = False
        add_to_ui_history(title, res_status, res_error)
        page.update()

    def on_click_download(e):
        if not url_input.value: return
        pb.visible, pb.value = True, 0
        status_text.value = "⏳ جاري التحميل..."
        page.update()
        threading.Thread(target=download_task, args=(url_input.value, state["cookies_path"]), daemon=True).start()

    page.add(
        ft.Text("تحميل غصب 🚀", size=30, weight="bold", color="blueaccent"),
        ft.Row([url_input, ft.IconButton(ft.icons.GET_APP, on_click=on_click_download)]),
        ft.Row([ft.ElevatedButton("اختيار الكوكيز", on_click=lambda _: file_picker.pick_files()), cookies_info]),
        pb,
        status_text,
        history_column
    )
    request_android_permissions()

ft.app(target=main)
