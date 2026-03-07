import flet as ft
import threading
import traceback
import os
import sys
import datetime

# ── سجل الأخطاء في ملف خارجي ────────────────────────────────────
_LOG_PATHS = [
    "/storage/emulated/0/Download/ghasab_log.txt",
    "/sdcard/Download/ghasab_log.txt",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "ghasab_log.txt"),
    "/data/local/tmp/ghasab_log.txt",
]
_LOG_FILE = None

for _p in _LOG_PATHS:
    try:
        os.makedirs(os.path.dirname(_p), exist_ok=True)
        with open(_p, "a", encoding="utf-8") as _f:
            _f.write("\n" + "=" * 50 + "\n")
            _f.write(f"START: {datetime.datetime.now()}\n")
            _f.write(f"Python: {sys.version}\n")
            _f.write(f"CWD: {os.getcwd()}\n")
            _f.write(f"__file__: {__file__}\n")
        _LOG_FILE = _p
        break
    except Exception:
        continue


def log(msg):
    line = "[{}] {}\n".format(datetime.datetime.now().strftime("%H:%M:%S"), msg)
    if _LOG_FILE:
        try:
            with open(_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(line)
        except Exception:
            pass


def log_exc(context, exc):
    log("ERROR [{}]: {} : {}\n{}".format(context, type(exc).__name__, exc, traceback.format_exc()))


DOWNLOAD_DIR = "/storage/emulated/0/Download"
APP_PACKAGE  = "com.ghasab.downloader"

log("module loaded, LOG_FILE={}".format(_LOG_FILE))


def get_ffmpeg_path():
    candidates = [
        os.path.join(os.getcwd(), "assets", "ffmpeg"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "ffmpeg"),
        "/data/data/{}/files/assets/ffmpeg".format(APP_PACKAGE),
        "/data/user/0/{}/files/assets/ffmpeg".format(APP_PACKAGE),
    ]
    for p in candidates:
        if os.path.isfile(p):
            try:
                os.chmod(p, 0o755)
            except Exception:
                pass
            log("ffmpeg found: {}".format(p))
            return p
    log("ffmpeg NOT found")
    return None


def main(page: ft.Page):
    log("main() start")

    page.title      = "تحميل غصب"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor    = "#0d0d1a"
    page.padding    = 16

    # ── Container رئيسي — نستبدل محتواه بدلاً من مسح الصفحة ────
    # هذا يمنع مشكلة page.controls.clear() + page.add() الصامتة
    root = ft.Column(spacing=12)

    root.controls = [
        ft.Text("تحميل غصب", size=22, weight=ft.FontWeight.BOLD, color="#a78bfa"),
        ft.Text("جاري التهيئة...", size=14, color="#888"),
        ft.ProgressRing(width=36, height=36, stroke_width=3, color="#5c5cff"),
    ]
    page.add(root)
    page.update()
    log("splash shown OK")

    # ── دالة تحديث آمنة ─────────────────────────────────────────
    def safe_update():
        try:
            page.update()
        except Exception as ex:
            log_exc("safe_update", ex)

    def show_fatal(title, detail):
        log("show_fatal: " + title)
        root.controls = [
            ft.Text(title, size=16, color="#f87171", weight=ft.FontWeight.BOLD),
            ft.Text(detail, size=12, color="#fca5a5"),
            ft.Text("ملف السجل: " + str(_LOG_FILE), size=11, color="#60a5fa"),
        ]
        safe_update()

    # ── حالة التطبيق ─────────────────────────────────────────────
    cookies_path   = {"value": None}
    is_downloading = {"value": False}

    # ── سجل الأخطاء المرئي ──────────────────────────────────────
    error_log  = ft.Text("", size=11, color="#fca5a5")
    error_card = ft.Container(
        content=ft.Column([
            ft.Text("سجل الأخطاء", size=12, color="#f87171",
                    weight=ft.FontWeight.BOLD),
            ft.Text("السجل الكامل: " + str(_LOG_FILE), size=10, color="#60a5fa"),
            error_log,
        ], spacing=4),
        padding=12,
        bgcolor="#1a0808",
        border_radius=10,
        visible=False,
    )

    def show_error(context, exc):
        log_exc(context, exc)
        error_log.value    = "[{}] {}: {}".format(context, type(exc).__name__, exc)
        error_card.visible = True
        safe_update()

    def clear_error():
        error_card.visible = False

    # ── عناصر الواجهة ───────────────────────────────────────────
    log("creating widgets...")

    url_input = ft.TextField(
        label="رابط الفيديو أو قائمة التشغيل",
        hint_text="https://youtube.com/watch?v=...",
        border_radius=12,
        filled=True,
        border_color="#5c5cff",
        focused_border_color="#a78bfa",
        cursor_color="#a78bfa",
    )
    log("url_input OK")

    quality_dd = ft.Dropdown(
        label="جودة التحميل",
        value="best",
        options=[
            ft.dropdown.Option("best",  "أفضل جودة"),
            ft.dropdown.Option("1080",  "1080p"),
            ft.dropdown.Option("720",   "720p"),
            ft.dropdown.Option("480",   "480p"),
            ft.dropdown.Option("audio", "صوت فقط (MP3)"),
        ],
    )
    log("quality_dd OK")

    cookies_label = ft.Text("لم يتم اختيار ملف كوكيز", size=12, color="#888")

    progress_bar   = ft.ProgressBar(value=0, bgcolor="#1a1a2e",
                                    color="#a78bfa", visible=False)
    progress_label = ft.Text("", size=11, color="#a78bfa", visible=False)
    status_text    = ft.Text("جاهز للتحميل ✓", size=13, color="#6ee7b7",
                             text_align=ft.TextAlign.CENTER)
    perm_text      = ft.Text("", size=11, color="#fbbf24")
    log("basic widgets OK")

    download_btn = ft.ElevatedButton(
        text="تحميل غصب",
        icon=ft.icons.DOWNLOAD,
        style=ft.ButtonStyle(
            bgcolor={"": "#5c5cff"},
            color={"": "#ffffff"},
            shape=ft.RoundedRectangleBorder(radius=14),
        ),
    )
    log("download_btn OK")

    # ── FilePicker ────────────────────────────────────────────────
    def on_cookies_picked(e):
        try:
            if e.files:
                f = e.files[0]
                cookies_path["value"] = f.path
                cookies_label.value   = "✅ " + f.name
                cookies_label.color   = "#6ee7b7"
                log("cookies: " + str(f.path))
            else:
                cookies_path["value"] = None
                cookies_label.value   = "لم يتم اختيار ملف كوكيز"
                cookies_label.color   = "#888"
            safe_update()
        except Exception as ex:
            show_error("on_cookies_picked", ex)

    file_picker = ft.FilePicker(on_result=on_cookies_picked)
    page.overlay.append(file_picker)
    log("file_picker added to overlay")

    def pick_cookies(_):
        try:
            file_picker.pick_files(
                dialog_title="اختر ملف الكوكيز (.txt)",
                initial_directory=DOWNLOAD_DIR if os.path.exists(DOWNLOAD_DIR) else None,
                allowed_extensions=["txt"],
                allow_multiple=False,
            )
        except Exception as ex:
            show_error("pick_cookies", ex)

    cookies_btn = ft.ElevatedButton(
        text="إضافة كوكيز",
        on_click=pick_cookies,
        style=ft.ButtonStyle(
            bgcolor={"": "#1e1e3e"},
            color={"": "#a78bfa"},
            shape=ft.RoundedRectangleBorder(radius=12),
        ),
    )
    log("cookies_btn OK")

    # ── فحص صلاحية التخزين ──────────────────────────────────────
    def check_storage_perm():
        log("checking storage perm...")
        if page.platform != ft.PagePlatform.ANDROID:
            log("not android")
            return
        try:
            os.makedirs(DOWNLOAD_DIR, exist_ok=True)
            test = os.path.join(DOWNLOAD_DIR, ".write_test")
            with open(test, "w") as f:
                f.write("ok")
            os.remove(test)
            perm_text.value = "✅ صلاحية التخزين ممنوحة"
            perm_text.color = "#6ee7b7"
            log("storage perm: OK")
        except PermissionError as ex:
            perm_text.value = "⚠️ لا توجد صلاحية تخزين — افتح إعدادات التطبيق"
            perm_text.color = "#f87171"
            log_exc("storage_perm", ex)
            try:
                os.system(
                    "am start -a android.settings.APPLICATION_DETAILS_SETTINGS"
                    " -d package:{} > /dev/null 2>&1 &".format(APP_PACKAGE)
                )
            except Exception:
                pass
        except Exception as ex:
            perm_text.value = "⚠️ خطأ في فحص الصلاحية"
            perm_text.color = "#fbbf24"
            log_exc("storage_perm", ex)
        safe_update()

    # ── منطق التحميل ─────────────────────────────────────────────
    def progress_hook(d):
        try:
            if d["status"] == "downloading":
                total    = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                dl       = d.get("downloaded_bytes", 0)
                speed    = d.get("speed") or 0
                eta      = d.get("eta") or 0
                pct      = (dl / total) if total else 0
                spd_mb   = speed / 1_048_576 if speed else 0
                progress_bar.value   = pct
                progress_label.value = "{:.0f}%  ·  {:.1f} MB/s  ·  ETA: {}ث".format(
                    pct * 100, spd_mb, eta)
                status_text.value = "جاري التحميل..."
                status_text.color = "#fbbf24"
                safe_update()
            elif d["status"] == "finished":
                progress_bar.value = 1
                status_text.value  = "جاري المعالجة..."
                status_text.color  = "#60a5fa"
                safe_update()
        except Exception:
            pass

    def do_download(url, quality):
        log("do_download start: " + url)
        try:
            import yt_dlp
            log("yt_dlp imported")

            save_path  = DOWNLOAD_DIR if os.path.isdir(DOWNLOAD_DIR) else "./"
            ffmpeg_bin = get_ffmpeg_path()

            if quality == "audio":
                fmt  = "bestaudio/best"
                post = [{"key": "FFmpegExtractAudio",
                         "preferredcodec": "mp3", "preferredquality": "192"}]
            else:
                fmt  = ("bestvideo+bestaudio/best" if quality == "best"
                        else "bestvideo[height<={}]+bestaudio/best[height<={}]".format(
                            quality, quality))
                post = []

            opts = {
                "format":              fmt,
                "outtmpl":             "{}/%(title)s.%(ext)s".format(save_path),
                "merge_output_format": "mp4",
                "postprocessors":      post,
                "noplaylist":          False,
                "quiet":               True,
                "no_warnings":         True,
                "progress_hooks":      [progress_hook],
            }
            if ffmpeg_bin:
                opts["ffmpeg_location"] = ffmpeg_bin
            if cookies_path["value"]:
                opts["cookiefile"] = cookies_path["value"]

            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])

            log("download complete")
            progress_bar.value   = 1
            progress_bar.color   = "#6ee7b7"
            status_text.value    = "✅ تم التحميل بنجاح في مجلد Downloads!"
            status_text.color    = "#6ee7b7"
            progress_label.value = ""
            clear_error()

        except Exception as e:
            err = str(e)
            if "Sign in" in err or "login" in err.lower():
                status_text.value = "❌ يتطلب تسجيل دخول — أضف ملف كوكيز"
            elif "Private" in err:
                status_text.value = "❌ الفيديو خاص"
            elif "available" in err.lower():
                status_text.value = "❌ الفيديو غير متاح في منطقتك"
            elif "ermission" in err:
                status_text.value = "❌ لا توجد صلاحية تخزين"
            else:
                status_text.value = "❌ فشل التحميل — راجع السجل"
            status_text.color  = "#f87171"
            progress_bar.color = "#f87171"
            show_error("do_download", e)

        finally:
            is_downloading["value"] = False
            download_btn.disabled   = False
            progress_bar.visible    = False
            progress_label.visible  = False
            safe_update()

    def on_download(_):
        try:
            url = (url_input.value or "").strip()
            if not url:
                status_text.value = "⚠️ يرجى إدخال رابط الفيديو"
                status_text.color = "#fbbf24"
                safe_update()
                return
            if not url.startswith(("http://", "https://")):
                status_text.value = "⚠️ الرابط غير صالح"
                status_text.color = "#fbbf24"
                safe_update()
                return
            if is_downloading["value"]:
                return

            is_downloading["value"] = True
            download_btn.disabled   = True
            progress_bar.visible    = True
            progress_bar.value      = 0
            progress_bar.color      = "#a78bfa"
            progress_label.visible  = True
            progress_label.value    = "جاري الاتصال بالخادم..."
            status_text.value       = "جاري التحميل..."
            status_text.color       = "#fbbf24"
            clear_error()
            safe_update()
            threading.Thread(target=do_download,
                             args=(url, quality_dd.value),
                             daemon=True).start()
        except Exception as ex:
            show_error("on_download", ex)

    download_btn.on_click = on_download

    # ── بناء الواجهة ─────────────────────────────────────────────
    # نستبدل محتوى root بدلاً من مسح الصفحة
    log("building full UI...")
    try:
        header = ft.Container(
            content=ft.Column([
                ft.Text("تحميل غصب", size=24,
                        weight=ft.FontWeight.BOLD, color="#ffffff"),
                ft.Text("حمّل أي فيديو بسهولة وسرعة", size=12, color="#888"),
            ], spacing=2),
            padding=ft.padding.only(bottom=8),
        )
        log("header OK")

        card = ft.Container(
            content=ft.Column([
                ft.Text("رابط التحميل", size=12, color="#aaa"),
                url_input,
                ft.Text("جودة التحميل", size=12, color="#aaa"),
                quality_dd,
                ft.Text("الكوكيز (اختياري)", size=12, color="#aaa"),
                ft.Row([cookies_btn, cookies_label], spacing=8,
                       vertical_alignment=ft.CrossAxisAlignment.CENTER),
                perm_text,
                ft.Divider(height=1, color="#1e1e3e"),
                download_btn,
                progress_bar,
                progress_label,
                status_text,
            ], spacing=8),
            padding=16,
            bgcolor="#13132b",
            border_radius=16,
        )
        log("card OK")

        tip_card = ft.Container(
            content=ft.Column([
                ft.Text("نصائح", size=12, color="#a78bfa",
                        weight=ft.FontWeight.BOLD),
                ft.Text("• للفيديوهات الخاصة أضف كوكيز .txt من مجلد التنزيلات",
                        size=11, color="#888"),
                ft.Text("• يمكن تحميل قوائم تشغيل YouTube كاملة",
                        size=11, color="#888"),
                ft.Text("• اختر 'صوت فقط' لاستخراج MP3", size=11, color="#888"),
                ft.Text("• ملف السجل: " + str(_LOG_FILE), size=10, color="#555"),
            ], spacing=4),
            padding=14,
            bgcolor="#0f0f22",
            border_radius=12,
        )
        log("tip_card OK")

        # ── استبدال محتوى root مباشرة ────────────────────────────
        root.controls = [header, card, error_card, tip_card]
        root.scroll   = ft.ScrollMode.AUTO
        safe_update()
        log("full UI shown OK")

        threading.Thread(target=check_storage_perm, daemon=True).start()

    except Exception as ex:
        log_exc("build_ui", ex)
        show_fatal("خطأ في بناء الواجهة", "{}: {}".format(type(ex).__name__, ex))


try:
    log("calling ft.app()")
    ft.app(target=main)
    log("ft.app() returned")
except Exception as e:
    log_exc("ft.app()", e)
