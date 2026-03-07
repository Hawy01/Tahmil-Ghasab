import flet as ft
import threading
import traceback
import os
import sys
import datetime

# ── سجل في الذاكرة ────────────────────────────────────────────────
_log_buffer = []

_home   = os.environ.get("HOME", "")
_tmpdir = os.environ.get("TMPDIR", "")
_cwd    = os.getcwd()

_LOG_PATHS = [p for p in [
    os.path.join(_home,   "ghasab_log.txt") if _home   else None,
    os.path.join(_tmpdir, "ghasab_log.txt") if _tmpdir else None,
    os.path.join(_cwd,    "ghasab_log.txt"),
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "ghasab_log.txt"),
    "/storage/emulated/0/Download/ghasab_log.txt",
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
            _f.write("HOME: {} | TMPDIR: {}\n".format(_home, _tmpdir))
            _f.write("CWD: {} | __file__: {}\n".format(_cwd, __file__))
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
    log("ERROR [{}]: {}: {}\n{}".format(
        context, type(exc).__name__, exc, traceback.format_exc()))


DOWNLOAD_DIR = "/storage/emulated/0/Download"
APP_PACKAGE  = "com.flet.tahmil_ghasab"

log("module loaded | LOG={}".format(_LOG_FILE or "NONE"))


def get_ffmpeg_path():
    for p in [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "ffmpeg"),
        "/data/data/{}/files/assets/ffmpeg".format(APP_PACKAGE),
        "/data/user/0/{}/files/assets/ffmpeg".format(APP_PACKAGE),
    ]:
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
    log("main() called | platform={}".format(page.platform))

    page.title      = "تحميل غصب"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor    = "#0d0d1a"
    page.padding    = 16

    # ── Splash مع نص حالة يتحدث ─────────────────────────────────
    init_status = ft.Text("0: بدء...", size=12, color="#a78bfa")
    root = ft.Column(spacing=12)
    root.controls = [
        ft.Text("تحميل غصب", size=22,
                weight=ft.FontWeight.BOLD, color="#a78bfa"),
        init_status,
        ft.ProgressRing(width=32, height=32, stroke_width=3, color="#5c5cff"),
    ]
    page.add(root)
    page.update()
    log("splash shown")

    # upd: يحدث نص الحالة ويُظهره على الشاشة فوراً
    def upd(n, msg, color="#888"):
        log("[{}] {}".format(n, msg))
        init_status.value = "[{}] {}".format(n, msg)
        init_status.color = color
        try:
            page.update()
        except Exception as ex:
            log_exc("upd({})".format(n), ex)

    # ─────────────────────────────────────────────────────────────
    upd(1, "تعريف show_log_dialog...")

    def show_log_dialog(_):
        content = "\n".join(_log_buffer[-200:]) if _log_buffer else "السجل فارغ"
        dlg = ft.AlertDialog(
            title=ft.Text("سجل الأخطاء", color="#f87171"),
            content=ft.Container(
                content=ft.Column(
                    [ft.Text(content, size=10, color="#ccc",
                             font_family="monospace",
                             selectable=True)],
                    scroll=ft.ScrollMode.AUTO,
                ),
                width=340, height=400,
            ),
            actions=[
                ft.TextButton("نسخ", on_click=lambda _: (
                    page.set_clipboard(content), page.update()
                )),
                ft.TextButton("إغلاق", on_click=lambda _: page.close(dlg)),
            ],
        )
        try:
            page.open(dlg)
        except Exception:
            # fallback for older Flet
            try:
                page.dialog = dlg
                dlg.open = True
                page.update()
            except Exception as ex2:
                log_exc("show_log_dialog.fallback", ex2)

    upd(2, "إنشاء عناصر الواجهة...")

    # ── URL input ─────────────────────────────────────────────────
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
    except Exception as ex:
        log_exc("url_input", ex)
        url_input = ft.TextField(label="رابط الفيديو")

    # ── Dropdown ──────────────────────────────────────────────────
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
    except Exception as ex:
        log_exc("quality_dd", ex)
        try:
            quality_dd = ft.Dropdown(
                label="جودة التحميل", value="best",
                options=[ft.dropdown.Option("best", "أفضل جودة")],
            )
        except Exception:
            quality_dd = ft.Dropdown(label="جودة التحميل", value="best")

    upd(3, "إنشاء أزرار وشريط التقدم...")

    # ── Labels / progress ─────────────────────────────────────────
    cookies_label  = ft.Text("لم يتم اختيار ملف كوكيز", size=12, color="#888")
    status_text    = ft.Text("جاهز للتحميل ✓", size=13, color="#6ee7b7")
    perm_text      = ft.Text("", size=11, color="#fbbf24")
    progress_label = ft.Text("", size=11, color="#a78bfa", visible=False)

    try:
        progress_bar = ft.ProgressBar(
            value=0, bgcolor="#1a1a2e", bar_color="#a78bfa", visible=False)
    except Exception as ex:
        log_exc("progress_bar", ex)
        try:
            progress_bar = ft.ProgressBar(visible=False)
        except Exception:
            progress_bar = ft.Text("", visible=False)

    # ── Download button ───────────────────────────────────────────
    try:
        download_btn = ft.ElevatedButton(
            text="تحميل غصب",
            icon=ft.Icons.DOWNLOAD,
            bgcolor="#5c5cff",
            color="#ffffff",
        )
    except Exception as ex:
        log_exc("download_btn", ex)
        download_btn = ft.ElevatedButton(text="تحميل غصب")

    upd(4, "إنشاء FilePicker...")

    # ── FilePicker ────────────────────────────────────────────────
    cookies_path   = {"value": None}
    is_downloading = {"value": False}

    def on_cookies_picked(e):
        try:
            if e.files:
                f = e.files[0]
                cookies_path["value"] = f.path
                cookies_label.value   = "✅ " + f.name
                cookies_label.color   = "#6ee7b7"
            else:
                cookies_path["value"] = None
                cookies_label.value   = "لم يتم اختيار ملف كوكيز"
                cookies_label.color   = "#888"
            page.update()
        except Exception as ex:
            log_exc("on_cookies_picked", ex)

    try:
        file_picker = ft.FilePicker(on_result=on_cookies_picked)
        page.overlay.append(file_picker)
        page.update()
        log("file_picker added to overlay")
    except Exception as ex:
        log_exc("file_picker", ex)
        file_picker = None

    def pick_cookies(_):
        if not file_picker:
            return
        try:
            file_picker.pick_files(
                dialog_title="اختر ملف الكوكيز (.txt)",
                allowed_extensions=["txt"],
                allow_multiple=False,
            )
        except Exception as ex:
            log_exc("pick_cookies", ex)

    # ── Cookies button ────────────────────────────────────────────
    try:
        cookies_btn = ft.ElevatedButton(
            text="إضافة كوكيز",
            icon=ft.Icons.COOKIE,
            on_click=pick_cookies,
            bgcolor="#1e1e3e",
            color="#a78bfa",
        )
    except Exception as ex:
        log_exc("cookies_btn", ex)
        cookies_btn = ft.ElevatedButton(text="إضافة كوكيز", on_click=pick_cookies)

    upd(5, "تعريف منطق التحميل...")

    # ── Download logic ────────────────────────────────────────────
    def progress_hook(d):
        try:
            if d["status"] == "downloading":
                total  = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                dl     = d.get("downloaded_bytes", 0)
                speed  = d.get("speed") or 0
                eta    = d.get("eta") or 0
                pct    = (dl / total) if total else 0
                spd_mb = speed / 1_048_576 if speed else 0
                try:
                    progress_bar.value   = pct
                    progress_label.value = "{:.0f}%  {:.1f}MB/s  {}ث".format(
                        pct * 100, spd_mb, eta)
                    status_text.value = "جاري التحميل..."
                    status_text.color = "#fbbf24"
                    page.update()
                except Exception:
                    pass
            elif d["status"] == "finished":
                try:
                    progress_bar.value = 1
                    status_text.value  = "جاري المعالجة..."
                    status_text.color  = "#60a5fa"
                    page.update()
                except Exception:
                    pass
        except Exception:
            pass

    def do_download(url, quality):
        log("download: " + url)
        try:
            import yt_dlp
            save_path  = DOWNLOAD_DIR if os.path.isdir(DOWNLOAD_DIR) else _cwd
            ffmpeg_bin = get_ffmpeg_path()
            if quality == "audio":
                fmt  = "bestaudio/best"
                post = [{"key": "FFmpegExtractAudio",
                         "preferredcodec": "mp3", "preferredquality": "192"}]
            else:
                fmt  = ("bestvideo+bestaudio/best" if quality == "best"
                        else "bestvideo[height<={}]+bestaudio/best".format(quality))
                post = []
            opts = {
                "format": fmt,
                "outtmpl": "{}/%(title)s.%(ext)s".format(save_path),
                "merge_output_format": "mp4",
                "postprocessors": post,
                "noplaylist": False,
                "quiet": True,
                "no_warnings": True,
                "progress_hooks": [progress_hook],
            }
            if ffmpeg_bin:
                opts["ffmpeg_location"] = ffmpeg_bin
            if cookies_path["value"]:
                opts["cookiefile"] = cookies_path["value"]
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
            log("download complete ✓")
            progress_bar.value   = 1
            status_text.value    = "✅ تم التحميل في Downloads!"
            status_text.color    = "#6ee7b7"
            progress_label.value = ""
        except Exception as e:
            err = str(e)
            log_exc("do_download", e)
            if "Sign in" in err or "login" in err.lower():
                status_text.value = "❌ يتطلب تسجيل دخول — أضف كوكيز"
            elif "Private" in err:
                status_text.value = "❌ الفيديو خاص"
            elif "available" in err.lower():
                status_text.value = "❌ غير متاح في منطقتك"
            elif "ermission" in err:
                status_text.value = "❌ لا توجد صلاحية تخزين"
            else:
                status_text.value = "❌ فشل: " + err[:60]
            status_text.color  = "#f87171"
        finally:
            is_downloading["value"] = False
            download_btn.disabled   = False
            try:
                progress_bar.visible   = False
                progress_label.visible = False
                page.update()
            except Exception:
                pass

    def on_download(_):
        try:
            url = (url_input.value or "").strip()
            if not url:
                status_text.value = "⚠️ أدخل رابط الفيديو"
                status_text.color = "#fbbf24"
                page.update()
                return
            if not url.startswith(("http://", "https://")):
                status_text.value = "⚠️ الرابط غير صالح"
                status_text.color = "#fbbf24"
                page.update()
                return
            if is_downloading["value"]:
                return
            is_downloading["value"]  = True
            download_btn.disabled    = True
            progress_bar.visible     = True
            progress_bar.value       = 0
            progress_label.visible   = True
            progress_label.value     = "جاري الاتصال..."
            status_text.value        = "جاري التحميل..."
            status_text.color        = "#fbbf24"
            page.update()
            threading.Thread(
                target=do_download,
                args=(url, quality_dd.value),
                daemon=True,
            ).start()
        except Exception as ex:
            log_exc("on_download", ex)

    download_btn.on_click = on_download

    upd(6, "فحص صلاحية التخزين...")

    def check_storage_perm():
        try:
            os.makedirs(DOWNLOAD_DIR, exist_ok=True)
            test = os.path.join(DOWNLOAD_DIR, ".wt")
            with open(test, "w") as f:
                f.write("ok")
            os.remove(test)
            perm_text.value = "✅ صلاحية التخزين: ممنوحة"
            perm_text.color = "#6ee7b7"
            log("storage perm: OK")
            if _LOG_FILE and "/storage" not in _LOG_FILE:
                try:
                    import shutil
                    dst = "/storage/emulated/0/Download/ghasab_log.txt"
                    shutil.copy2(_LOG_FILE, dst)
                    log("log copied → " + dst)
                except Exception:
                    pass
        except Exception as ex:
            perm_text.value = "⚠️ لا توجد صلاحية تخزين"
            perm_text.color = "#f87171"
            log_exc("storage_perm", ex)
        try:
            page.update()
        except Exception:
            pass

    upd(7, "بناء الواجهة الكاملة...")

    # ── Build full UI ─────────────────────────────────────────────
    try:
        log_btn = ft.TextButton(
            text="📋 سجل",
            on_click=show_log_dialog,
        )

        main_card = ft.Container(
            content=ft.Column([
                ft.Text("رابط التحميل", size=12, color="#aaa"),
                url_input,
                ft.Text("جودة التحميل", size=12, color="#aaa"),
                quality_dd,
                ft.Text("الكوكيز (اختياري)", size=12, color="#aaa"),
                ft.Row([cookies_btn, cookies_label], spacing=8),
                perm_text,
                ft.Divider(color="#1e1e3e"),
                download_btn,
                progress_bar,
                progress_label,
                status_text,
            ], spacing=8),
            padding=16,
            bgcolor="#13132b",
            border_radius=16,
        )
        log("main_card OK")

        tips_card = ft.Container(
            content=ft.Column([
                ft.Text("نصائح", size=12, color="#a78bfa",
                        weight=ft.FontWeight.BOLD),
                ft.Text("• الفيديوهات الخاصة تحتاج ملف كوكيز .txt",
                        size=11, color="#888"),
                ft.Text("• يمكن تحميل قوائم تشغيل YouTube كاملة",
                        size=11, color="#888"),
                ft.Text("• اختر 'صوت فقط' لاستخراج MP3", size=11, color="#888"),
                log_btn,
            ], spacing=4),
            padding=14,
            bgcolor="#0f0f22",
            border_radius=12,
        )
        log("tips_card OK")

        header = ft.Column([
            ft.Text("تحميل غصب", size=24,
                    weight=ft.FontWeight.BOLD, color="#ffffff"),
            ft.Text("حمّل أي فيديو بسهولة", size=12, color="#888"),
        ], spacing=2)

        upd(8, "تطبيق الواجهة على الصفحة...", "#60a5fa")

        root.controls.clear()
        root.controls.append(header)
        root.controls.append(main_card)
        root.controls.append(tips_card)
        root.scroll = ft.ScrollMode.AUTO

        page.update()
        log("full UI displayed OK ✓")

        threading.Thread(target=check_storage_perm, daemon=True).start()

    except Exception as ex:
        log_exc("build_ui", ex)
        upd(99, "خطأ: {}: {}".format(type(ex).__name__, str(ex)[:80]), "#f87171")
        root.controls.append(
            ft.TextButton("📋 عرض السجل الكامل", on_click=show_log_dialog)
        )
        try:
            page.update()
        except Exception:
            pass


try:
    log("ft.app() calling...")
    ft.app(target=main)
except Exception as e:
    log_exc("ft.app()", e)
