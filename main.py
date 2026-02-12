import flet as ft
import yt_dlp
import threading
import json
import os
import ffmpeg_android # مكتبة توفير FFmpeg للأندرويد

# ملف سجل التحميلات
HISTORY_FILE = "download_history.json"

def main(page: ft.Page):
    page.title = "تحميل غصب - الإصدار الشامل"
    page.theme_mode = ft.ThemeMode.DARK
    page.scroll = ft.ScrollMode.AUTO
    page.padding = 20

    # متغير لتخزين مسار ملف الكوكيز المختار
    state = {"cookies_path": None}

    # طلب صلاحيات أندرويد للوصول للمجلدات العامة وحفظ الملفات [استنتاج]
    def request_android_permissions():
        if page.platform == ft.PagePlatform.ANDROID:
            package_name = "com.ghasab.downloader" # معرف الحزمة المتفق عليه
            try:
                os.system(f"am start -a android.settings.MANAGE_APP_ALL_FILES_ACCESS_PERMISSION -d package:{package_name}")
                page.snack_bar = ft.SnackBar(ft.Text("يرجى تفعيل 'الوصول لجميع الملفات' لضمان حفظ الفيديوهات"))
                page.snack_bar.open = True
                page.update()
            except:
                pass

    # تحميل سجل التحميلات من الذاكرة
    def load_history():
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                return []
        return []

    # حفظ السجل لضمان بقائه بعد إغلاق التطبيق
    def save_history(data):
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    # عناصر الواجهة الرسومية
    url_input = ft.TextField(label="رابط الفيديو", hint_text="الصق الرابط هنا...", expand=True, border_radius=15)
    pb = ft.ProgressBar(width=400, value=0, visible=False, color="blueaccent")
    status_text = ft.Text("جاهز لسحب الفيديو...")
    cookies_info = ft.Text("لم يتم اختيار ملف كوكيز (اختياري)", size=12, italic=True)
    history_column = ft.Column(spacing=10)
    
    history_data = load_history()

    # إضافة عنصر جديد لسجل التحميلات في الواجهة
    def add_to_ui_history(title, status, error=""):
        icon = ft.icons.CHECK_CIRCLE if status == "تم" else ft.icons.ERROR
        color = "green" if status == "تم" else "red"
        history_column.controls.insert(0, ft.ListTile(
            leading=ft.Icon(icon, color=color),
            title=ft.Text(title, max_lines=1, overflow="ellipsis"),
            subtitle=ft.Text(f"الحالة: {status}" + (f"\nخطأ: {error}" if error else "")),
            is_three_line=True if error else False
        ))
        page.update()

    # عرض السجل القديم عند فتح التطبيق
    for item in history_data:
        add_to_ui_history(item['title'], item['status'], item.get('error', ""))

    # معالج اختيار الملف لملف الكوكيز
    def on_file_result(e: ft.FilePickerResultEvent):
        if e.files:
            state["cookies_path"] = e.files[0].path
            cookies_info.value = f"تم ربط الكوكيز: {e.files[0].name}"
            page.update()

    file_picker = ft.FilePicker(on_result=on_file_result)
    page.overlay.append(file_picker)

    # تحديث شريط التقدم أثناء عملية التحميل
    def progress_hook(d):
        if d['status'] == 'downloading':
            downloaded = d.get('downloaded_bytes', 0)
            total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
            if total > 0:
                pb.value = downloaded / total
                status_text.value = f"جاري السحب.. { (downloaded/total)*100:.1f}%"
                page.update()

    # المهمة البرمجية الأساسية للتحميل
    def download_task(url, cookies_path):
        ffmpeg_path = ffmpeg_android.get_ffmpeg_path()
        # المستخدم يفضل الحفظ في تطبيق "الملفات"
        download_dir = "/storage/emulated/0/Download/" if page.platform == ft.PagePlatform.ANDROID else "./"
        
        ydl_opts = {
            'ffmpeg_location': ffmpeg_path, # دمج الصوت والفيديو بجودة عالية [استنتاج]
            'format': 'bestvideo+bestaudio/best',
            'progress_hooks': [progress_hook],
            'outtmpl': os.path.join(download_dir, '%(title)s.%(ext)s'),
            'no_overwrites': True,
            'windows_filenames': True,
        }
        
        if cookies_path:
            ydl_opts['cookiefile'] = cookies_path

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                title = info.get('title', 'فيديو')
                res_status, res_error = "تم", ""
        except Exception as e:
            title = url
            res_status = "فشل"
            error_msg = str(e).lower()
            
            # تحليل الخطأ ذكياً ليناسب المستخدم العربي [استنتاج]
            if "ffmpeg" in error_msg:
                res_error = "مشكلة في دمج الجودة العالية (FFmpeg)."
            elif "not available" in error_msg or "404" in error_msg:
                res_error = "الفيديو غير متاح أو تم حذفه."
            elif "network" in error_msg or "connection" in error_msg:
                res_error = "فشل في الاتصال بالإنترنت."
            elif "cookie" in error_msg:
                res_error = "ملف الكوكيز غير صالح أو انتهت صلاحيته."
            else:
                res_error = f"خطأ: {error_msg[:40]}..."

        # تحديث وحفظ السجل
        history_data.append({"title": title, "status": res_status, "error": res_error})
        save_history(history_data)
        
        pb.visible = False
        status_text.value = "تمت المهمة بنجاح ✅" if res_status == "تم" else "فشل التحميل ❌"
        add_to_ui_history(title, res_status, res_error)
        page.update()

    def on_click_download(e):
        if not url_input.value:
            return
        pb.visible, pb.value = True, 0
        status_text.value = "⏳ جاري التحقق..."
        page.update()
        threading.Thread(target=download_task, args=(url_input.value, state["cookies_path"]), daemon=True).start()

    # بناء واجهة المستخدم
    page.add(
        ft.Text("تحميل غصب 🚀", size=35, weight="bold", color="blueaccent"),
        ft.Row([
            url_input, 
            ft.IconButton(ft.icons.GET_APP, on_click=on_click_download, icon_size=35)
        ]),
        ft.Row([
            ft.ElevatedButton("اختيار الكوكيز", icon=ft.icons.KEY, on_click=lambda _: file_picker.pick_files()),
            cookies_info
        ]),
        status_text,
        pb,
        ft.Divider(),
        ft.Text("📜 سجل التحميلات", size=20, weight="bold"),
        history_column
    )
    
    request_android_permissions()

ft.app(target=main)
