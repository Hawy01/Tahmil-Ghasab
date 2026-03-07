import flet as ft
import threading
import traceback
import os
import sys
import datetime

# ── سجل في الذاكرة (يعمل دائماً بلا إذن) ────────────────────────
_log_buffer = []

# ── سجل في ملف (أولوية للذاكرة الداخلية للتطبيق) ────────────────
_home   = os.environ.get("HOME", "")
_tmpdir = os.environ.get("TMPDIR", "")
_cwd    = os.getcwd()

_LOG_PATHS = [p for p in [
    os.path.join(_home,   "ghasab_log.txt") if _home   else None,
    os.path.join(_tmpdir, "ghasab_log.txt") if _tmpdir else None,
    os.path.join(_cwd,    "ghasab_log.txt"),
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "ghasab_log.txt"),
    "/storage/emulated/0/Download/ghasab_log.txt",
    "/sdcard/Download/ghasab_log.txt",
    "/data/local/tmp/ghasab_log.txt",
] if p]

_LOG_FILE = None
for _p in _LOG_PATHS:
    try:
        _dir = os.path.dirname(_p)
        if _dir:
            os.makedirs(_dir, exist_ok=True)
        with open(_p, "a", encoding="utf-8") as _f:
            _f.write("\n" + "=" * 50 + "\n")
            _f.write("START: {}\n".format(datetime.datetime.now()))
            _f.write("Python: {}\n".format(sys.version))
            _f.write("HOME: {}\n".format(_home))
            _f.write("TMPDIR: {}\n".format(_tmpdir))
            _f.write("CWD: {}\n".format(_cwd))
            _f.write("__file__: {}\n".format(__file__))
        _LOG_FILE = _p
        break
    except Exception:
        continue


def log(msg):
    ts   = datetime.datetime.now().strftime("%H:%M:%S")
    line = "[{}] {}".format(ts, msg)
    _log_buffer.append(line)
    if len(_log_buffer) > 500:
        _log_buffer.pop(0)
    if _LOG_FILE:
        try:
            with open(_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass


def log_exc(context, exc):
    tb = traceback.format_exc()
    log("ERROR [{}]: {}: {}\n{}".format(context, type(exc).__name__, exc, tb))


DOWNLOAD_DIR = "/storage/emulated/0/Download"
APP_PACKAGE  = "com.ghasab.downloader"

log("module loaded")
log("LOG_FILE={}".format(_LOG_FILE or "NONE - all paths failed"))
log("DOWNLOAD_DIR exists={}".format(os.path.exists(DOWNLOAD_DIR)))


def get_ffmpeg_path():
    candidates = [
        os.path.join(_cwd, "assets", "ffmpeg"),
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
            log("ffmpeg: {}".format(p))
            return p
    log("ffmpeg: NOT FOUND")
    return None


def main(page: ft.Page):
    log("main() called")
    log("platform={}".format(page.platform))

    page.title      = "تحميل غصب"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor    = "#0d0d1a"
    page.padding    = 16

    # root Column — نستبدل محتواه بدلاً من مسح الصفحة
    root = ft.Column(spacing=12)
    root.controls = [
        ft.Text("تحميل غصب", size=22,
                weight=ft.FontWeight.BOLD, color="#a78bfa"),
        ft.Text("جاري التهيئة...", size=14, color="#888"),
        ft.ProgressRing(width=36, height=36, stroke_width=3, color="#5c5cff"),
    ]
    page.add(root)
    page.update()
    log("splash shown")

    # ── دالة تحديث آمنة ─────────────────────────────────────────
    def safe_update():
        try:
            page.update()
        except Exception as ex:
            log_exc("safe_update", ex)

    # ── نافذة عرض السجل ─────────────────────────────────────────
    def show_log_dialog(_):
        content = "\n".join(_log_buffer[-200:]) if _log_buffer else "السجل فارغ"
        log_text = ft.Text(content, size=10, color="#ccc", font_family="monospace")
        dlg = ft.AlertDialog(
            title=ft.Text("سجل الأخطاء", color="#f87171"),
            content=ft.Container(
                content=ft.Column([log_text], scroll=ft.ScrollMode.AUTO),
                width=340,
                height=400,
            ),
            actions=[
                ft.TextButton("نسخ", on_click=lambda _: (
                    page.set_clipboard(content), safe_update()
                )),
                ft.TextButton("إغلاق", on_click=lambda _: (
                    setattr(dlg, "open", False), safe_update()
                )),
            ],
        )
        page.dialog = dlg
        dlg.open    = True
        safe_update()

    # ── دالة خطأ فادح ────────────────────────────────────────────
    def show_fatal(title, detail):
        log("FATAL: " + title)
        root.controls = [
            ft.Text(title, size=16, color="#f87171",
                    weight=ft.FontWeight.BOLD),
            ft.Text(detail, size=12, color="#fca5a5"),
            ft.Text("ملف السجل: " + str(_LOG_FILE or "غير متاح"),
                    size=11, color="#60a5fa"),
            ft.ElevatedButton("عرض السجل الكامل",
                              on_click=show_log_dialog,
                              style=ft.ButtonStyle(
                                  bgcolor="#1e1e3e",
                                  color="#a78bfa",
                              )),
        ]
        safe_update()

    # ── حالة التطبيق ─────────────────────────────────────────────
    cookies_path   = {"value": None}
    is_downloading = {"value": False}

    # ── سجل الأخطاء المرئي ──────────────────────────────────────
    error_log  = ft.Text("", size=11, color="#fca5a5")
    error_card = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Text("سجل الأخطاء", size=12, color="#f87171",
                        weight=ft.FontWeight.BOLD),
                ft.TextButton("عرض الكامل", on_click=show_log_dialog),
            ], spacing=8),
            error_log,
        ], spacing=4),
        padding=12,
        bgcolor="#1a0808",
        border_radius=10,
        visible=False,
    )

    def show_error(context, exc):
        log_exc(context, exc)
        error_log.value    = "[{}] {}: {}".format(
            context, type(exc).__name__, exc)
        error_card.visible = True
        safe_update()

    def clear_error():
        error_card.visible = False

    # ── عناصر الواجهة ───────────────────────────────────────────
    log("creating widgets...")

    try:
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
    except Exception as ex:
        log_exc("url_input", ex)
        url_input = ft.TextField(label="رابط الفيديو أو قائمة التشغيل")

    try:
        quality_dd = ft.Dropdown(
            label="جودة التحميل",
            value="best",
            options=[
                ft.DropdownOption(key="best",  text="أفضل جودة"),
                ft.DropdownOption(key="1080",  text="1080p"),
                ft.DropdownOption(key="720",   text="720p"),
                ft.DropdownOption(key="480",   text="480p"),
                ft.DropdownOption(key="audio", text="صوت فقط (MP3)"),
            ],
        )
        log("quality_dd OK")
    except Exception as ex:
        log_exc("quality_dd", ex)
        quality_dd = ft.Dropdown(label="جودة التحميل", value="best", options=[
            ft.DropdownOption(key="best", text="أفضل جودة"),
        ])

    cookies_label  = ft.Text("لم يتم اختيار ملف كوكيز", size=12, color="#888")
    progress_bar   = ft.ProgressBar(value=0, bgcolor="#1a1a2e",
                                    color="#a78bfa", visible=False)
    progress_label = ft.Text("", size=11, color="#a78bfa", visible=False)
    status_text    = ft.Text("جاهز للتحميل ✓", size=13, color="#6ee7b7",
                             text_align=ft.TextAlign.CENTER)
    perm_text      = ft.Text("", size=11, color="#fbbf24")

    try:
        download_btn = ft.ElevatedButton(
            text="تحميل غصب",
            icon=ft.Icons.DOWNLOAD,
            style=ft.ButtonStyle(
                bgcolor="#5c5cff",
                color="#ffffff",
                shape=ft.RoundedRectangleBorder(radius=14),
            ),
        )
        log("download_btn OK")
    except Exception as ex:
        log_exc("download_btn", ex)
        download_btn = ft.ElevatedButton(text="تحميل غصب")

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
    log("file_picker OK")

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

    try:
        cookies_btn = ft.ElevatedButton(
            text="إضافة كوكيز",
            icon=ft.Icons.COOKIE,
            on_click=pick_cookies,
            style=ft.ButtonStyle(
                bgcolor="#1e1e3e",
                color="#a78bfa",
                shape=ft.RoundedRectangleBorder(radius=12),
            ),
        )
        log("cookies_btn OK")
    except Exception as ex:
        log_exc("cookies_btn icon", ex)
        cookies_btn = ft.ElevatedButton(
            text="إضافة كوكيز",
            on_click=pick_cookies,
        )

    # زر عرض السجل
    log_btn = ft.TextButton(
        text="📋 سجل",
        on_click=show_log_dialog,
        style=ft.ButtonStyle(color="#555"),
    )

    # ── فحص صلاحية التخزين ──────────────────────────────────────
    def check_storage_perm():
        log("checking storage perm...")
        if page.platform != ft.PagePlatform.ANDROID:
            log("not android, skip")
            return
        try:
            os.makedirs(DOWNLOAD_DIR, exist_ok=True)
            test = os.path.join(DOWNLOAD_DIR, ".write_test")
            with open(test, "w") as f:
                f.write("ok")
            os.remove(test)
            perm_text.value = "✅ صلاحية التخزين ممنوحة"
            perm_text.color = "#6ee7b7"
            log("storage: OK")
            # حاول نسخ ملف السجل إلى Downloads
            if _LOG_FILE and not _LOG_FILE.startswith("/storage"):
                try:
                    import shutil
                    dst = "/storage/emulated/0/Download/ghasab_log.txt"
                    shutil.copy2(_LOG_FILE, dst)
                    log("log copied to Downloads: " + dst)
                    perm_text.value += " | سجل: " + dst
                except Exception:
                    pass
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
                total  = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                dl     = d.get("downloaded_bytes", 0)
                speed  = d.get("speed") or 0
                eta    = d.get("eta") or 0
                pct    = (dl / total) if total else 0
                spd_mb = speed / 1_048_576 if speed else 0
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
        log("download start: " + url)
        try:
            import yt_dlp
            log("yt_dlp imported OK")
            save_path  = DOWNLOAD_DIR if os.path.isdir(DOWNLOAD_DIR) else _cwd
            ffmpeg_bin = get_ffmpeg_path()
            log("save_path=" + save_path)

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

            log("download complete ✓")
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
                status_text.value = "❌ فشل التحميل — اضغط سجل"
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

    # ── بناء الواجهة الكاملة ─────────────────────────────────────
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
                ft.Text("• الفيديوهات الخاصة تحتاج ملف كوكيز .txt من التنزيلات",
                        size=11, color="#888"),
                ft.Text("• يمكن تحميل قوائم تشغيل YouTube كاملة",
                        size=11, color="#888"),
                ft.Text("• اختر 'صوت فقط' لاستخراج MP3", size=11, color="#888"),
                ft.Row([
                    log_btn,
                    ft.Text("v{}".format(_LOG_FILE or "no-log"),
                            size=9, color="#333"),
                ]),
            ], spacing=4),
            padding=14,
            bgcolor="#0f0f22",
            border_radius=12,
        )
        log("tip_card OK")

        # استبدال محتوى root بدلاً من مسح الصفحة
        root.controls = [header, card, error_card, tip_card]
        root.scroll   = ft.ScrollMode.AUTO
        safe_update()
        log("full UI displayed OK")

        threading.Thread(target=check_storage_perm, daemon=True).start()

    except Exception as ex:
        log_exc("build_ui", ex)
        show_fatal("خطأ في بناء الواجهة",
                   "{}: {}".format(type(ex).__name__, ex))


try:
    log("ft.app() calling...")
    ft.app(target=main)
except Exception as e:
    log_exc("ft.app()", e)
