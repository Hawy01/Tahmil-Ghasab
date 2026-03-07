import flet as ft
import threading
import traceback
import os
import sys
import datetime

# ── سجل الأخطاء في ملف خارجي ────────────────────────────────────
# يُكتب قبل أي شيء آخر حتى نلتقط الأخطاء المبكرة

_LOG_PATHS = [
    "/storage/emulated/0/Download/ghasab_log.txt",
    "/sdcard/Download/ghasab_log.txt",
    os.path.join(os.path.dirname(__file__), "ghasab_log.txt"),
    "/data/local/tmp/ghasab_log.txt",
]
_LOG_FILE = None

for _p in _LOG_PATHS:
    try:
        os.makedirs(os.path.dirname(_p), exist_ok=True)
        with open(_p, "a", encoding="utf-8") as _f:
            _f.write(f"\n{'='*50}\n")
            _f.write(f"بدء التشغيل: {datetime.datetime.now()}\n")
            _f.write(f"Python: {sys.version}\n")
            _f.write(f"CWD: {os.getcwd()}\n")
        _LOG_FILE = _p
        break
    except Exception:
        continue


def log(msg: str):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}\n"
    if _LOG_FILE:
        try:
            with open(_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(line)
        except Exception:
            pass


def log_exc(context: str, exc: Exception):
    tb = traceback.format_exc()
    log(f"ERROR in {context}: {type(exc).__name__}: {exc}\n{tb}")


# ── إعدادات التطبيق ──────────────────────────────────────────────
DOWNLOAD_DIR = "/storage/emulated/0/Download"
APP_PACKAGE  = "com.ghasab.downloader"

log(f"LOG_FILE={_LOG_FILE}")
log(f"DOWNLOAD_DIR exists={os.path.exists(DOWNLOAD_DIR)}")


def get_ffmpeg_path():
    candidates = [
        os.path.join(os.getcwd(), "assets", "ffmpeg"),
        os.path.join(os.path.dirname(__file__), "assets", "ffmpeg"),
        f"/data/data/{APP_PACKAGE}/files/assets/ffmpeg",
        f"/data/user/0/{APP_PACKAGE}/files/assets/ffmpeg",
    ]
    for p in candidates:
        log(f"ffmpeg check: {p} exists={os.path.isfile(p)}")
        if os.path.isfile(p):
            try:
                os.chmod(p, 0o755)
            except Exception:
                pass
            return p
    return None


def main(page: ft.Page):
    log("main() called")

    # ── الإعدادات الأساسية ───────────────────────────────────────
    page.title      = "تحميل غصب"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor    = "#0d0d1a"
    page.padding    = 16
    page.scroll     = ft.ScrollMode.AUTO

    # ── Splash فوري — أول شيء يظهر على الشاشة ──────────────────
    splash = ft.Column([
        ft.Text("تحميل غصب", size=22, weight=ft.FontWeight.BOLD, color="#a78bfa"),
        ft.Text("جاري التهيئة...", size=14, color="#aaa"),
        ft.ProgressRing(width=32, height=32, stroke_width=3, color="#5c5cff"),
    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=12)

    page.add(splash)
    page.update()
    log("splash shown")

    # ── عرض خطأ فادح ─────────────────────────────────────────────
    def fatal_error(context: str, exc: Exception):
        tb = traceback.format_exc()
        log_exc(context, exc)
        page.controls.clear()
        page.add(
            ft.Text("خطأ في التطبيق", size=18, color="#f87171",
                    weight=ft.FontWeight.BOLD),
            ft.Text(f"{type(exc).__name__}: {exc}", size=12, color="#fca5a5"),
            ft.Divider(color="#333"),
            ft.Text(
                f"ملف السجل:\n{_LOG_FILE or 'غير متاح'}",
                size=11, color="#60a5fa", selectable=True,
            ),
            ft.Text(tb[-800:], size=10, color="#666", selectable=True),
        )
        page.update()

    # ── سجل الأخطاء المرئي في الواجهة ───────────────────────────
    error_log  = ft.Text("", size=11, color="#fca5a5", selectable=True)
    error_card = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Icon(ft.icons.BUG_REPORT, color="#f87171", size=16),
                ft.Text("سجل الأخطاء", size=12, color="#f87171",
                        weight=ft.FontWeight.BOLD),
            ], spacing=6),
            ft.Text(
                f"ملف السجل الكامل: {_LOG_FILE or 'غير متاح'}",
                size=10, color="#60a5fa", selectable=True,
            ),
            error_log,
        ], spacing=4),
        padding=12,
        bgcolor="#1a0808",
        border_radius=10,
        visible=False,
    )

    def show_error(context: str, exc: Exception):
        tb = traceback.format_exc()
        log_exc(context, exc)
        error_log.value    = f"[{context}]\n{type(exc).__name__}: {exc}\n\n{tb[-500:]}"
        error_card.visible = True
        try:
            page.update()
        except Exception:
            pass

    def clear_error():
        error_card.visible = False

    # ── حالة التطبيق ─────────────────────────────────────────────
    cookies_path   = {"value": None}
    is_downloading = {"value": False}

    # ── عناصر الواجهة ───────────────────────────────────────────
    url_input = ft.TextField(
        label="رابط الفيديو أو قائمة التشغيل",
        hint_text="https://youtube.com/watch?v=...",
        border_radius=12,
        filled=True,
        border_color="#5c5cff",
        focused_border_color="#a78bfa",
        cursor_color="#a78bfa",
    )

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

    cookies_label = ft.Text("لم يتم اختيار ملف كوكيز", size=12, color="#888")

    progress_bar = ft.ProgressBar(
        value=0, bgcolor="#1a1a2e", color="#a78bfa", visible=False,
    )
    progress_label = ft.Text("", size=11, color="#a78bfa", visible=False)

    status_text = ft.Text(
        "جاهز للتحميل ✓", size=13, color="#6ee7b7",
        text_align=ft.TextAlign.CENTER,
    )
    perm_text = ft.Text("", size=11, color="#fbbf24")

    download_btn = ft.ElevatedButton(
        text="تحميل غصب",
        icon=ft.icons.DOWNLOAD,
        expand=True,
        style=ft.ButtonStyle(
            bgcolor={"": "#5c5cff"},
            color="#ffffff",
            shape=ft.RoundedRectangleBorder(radius=14),
            padding=ft.padding.symmetric(vertical=14, horizontal=24),
        ),
    )

    # ── FilePicker ────────────────────────────────────────────────
    def on_cookies_picked(e: ft.FilePickerResultEvent):
        try:
            if e.files:
                f = e.files[0]
                cookies_path["value"] = f.path
                cookies_label.value   = f"✅ {f.name}"
                cookies_label.color   = "#6ee7b7"
                log(f"cookies picked: {f.path}")
            else:
                cookies_path["value"] = None
                cookies_label.value   = "لم يتم اختيار ملف كوكيز"
                cookies_label.color   = "#888"
            page.update()
        except Exception as ex:
            show_error("on_cookies_picked", ex)

    file_picker = ft.FilePicker(on_result=on_cookies_picked)
    page.overlay.append(file_picker)

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
        text="كوكيز",
        icon=ft.icons.COOKIE,
        on_click=pick_cookies,
        style=ft.ButtonStyle(
            bgcolor={"": "#1e1e3e"},
            color="#a78bfa",
            shape=ft.RoundedRectangleBorder(radius=12),
        ),
    )

    # ── فحص صلاحية التخزين ──────────────────────────────────────
    def check_storage_perm():
        log("checking storage perm...")
        if page.platform != ft.PagePlatform.ANDROID:
            log("not android, skip perm check")
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
            log(f"storage perm: DENIED - {ex}")
            try:
                os.system(
                    "am start -a android.settings.APPLICATION_DETAILS_SETTINGS"
                    f" -d package:{APP_PACKAGE} > /dev/null 2>&1 &"
                )
            except Exception:
                pass
        except Exception as ex:
            perm_text.value = f"⚠️ خطأ في فحص الصلاحية"
            perm_text.color = "#fbbf24"
            log_exc("check_storage_perm", ex)
        try:
            page.update()
        except Exception:
            pass

    # ── منطق التحميل ─────────────────────────────────────────────
    def progress_hook(d: dict):
        try:
            if d["status"] == "downloading":
                total      = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                downloaded = d.get("downloaded_bytes", 0)
                speed      = d.get("speed") or 0
                eta        = d.get("eta") or 0
                pct        = (downloaded / total) if total else 0
                speed_mb   = speed / 1_048_576 if speed else 0
                progress_bar.value   = pct
                progress_label.value = (
                    f"{pct*100:.0f}%  ·  {speed_mb:.1f} MB/s  ·  ETA: {eta}ث"
                )
                status_text.value = "جاري التحميل..."
                status_text.color = "#fbbf24"
                page.update()
            elif d["status"] == "finished":
                progress_bar.value = 1
                status_text.value  = "جاري المعالجة..."
                status_text.color  = "#60a5fa"
                page.update()
        except Exception:
            pass

    def do_download(url: str, quality: str):
        log(f"do_download: url={url} quality={quality}")
        try:
            import yt_dlp
            log("yt_dlp imported OK")

            save_path  = DOWNLOAD_DIR if os.path.isdir(DOWNLOAD_DIR) else "./"
            ffmpeg_bin = get_ffmpeg_path()
            log(f"save_path={save_path} ffmpeg={ffmpeg_bin}")

            if quality == "audio":
                fmt  = "bestaudio/best"
                post = [{"key": "FFmpegExtractAudio",
                         "preferredcodec": "mp3", "preferredquality": "192"}]
            else:
                fmt  = ("bestvideo+bestaudio/best" if quality == "best"
                        else f"bestvideo[height<={quality}]+bestaudio/best[height<={quality}]")
                post = []

            opts = {
                "format":              fmt,
                "outtmpl":             f"{save_path}/%(title)s.%(ext)s",
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
            try:
                page.update()
            except Exception:
                pass

    def on_download(_):
        try:
            url = (url_input.value or "").strip()
            if not url:
                status_text.value = "⚠️ يرجى إدخال رابط الفيديو"
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
            page.update()

            threading.Thread(
                target=do_download,
                args=(url, quality_dd.value),
                daemon=True,
            ).start()

        except Exception as ex:
            show_error("on_download", ex)

    download_btn.on_click = on_download

    # ── بناء الواجهة الكاملة ─────────────────────────────────────
    log("building UI...")
    try:
        header = ft.Container(
            content=ft.Row([
                ft.Icon(ft.icons.DOWNLOAD_FOR_OFFLINE, size=30, color="#a78bfa"),
                ft.Column([
                    ft.Text("تحميل غصب", size=22,
                            weight=ft.FontWeight.BOLD, color="#ffffff"),
                    ft.Text("حمّل أي فيديو بسهولة وسرعة", size=11, color="#888"),
                ], spacing=2),
            ], spacing=10),
            padding=ft.padding.only(bottom=8),
        )

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
                ft.Row([download_btn]),
                progress_bar,
                progress_label,
                status_text,
            ], spacing=8),
            padding=16,
            bgcolor="#13132b",
            border_radius=16,
        )

        tip_card = ft.Container(
            content=ft.Column([
                ft.Text("نصائح", size=12, color="#a78bfa",
                        weight=ft.FontWeight.BOLD),
                ft.Text("• الفيديوهات الخاصة تحتاج ملف كوكيز .txt من مجلد التنزيلات",
                        size=11, color="#888"),
                ft.Text("• يمكن تحميل قوائم تشغيل YouTube كاملة", size=11, color="#888"),
                ft.Text("• اختر 'صوت فقط' لاستخراج MP3", size=11, color="#888"),
                ft.Text(f"• ملف السجل: {_LOG_FILE or 'غير متاح'}",
                        size=10, color="#555", selectable=True),
            ], spacing=4),
            padding=14,
            bgcolor="#0f0f22",
            border_radius=12,
        )

        log("UI built OK, switching from splash...")
        page.controls.clear()
        page.add(header, card, error_card, tip_card)
        page.update()
        log("UI displayed OK")

        threading.Thread(target=check_storage_perm, daemon=True).start()

    except Exception as ex:
        fatal_error("build_ui", ex)


try:
    log("calling ft.app()...")
    ft.app(target=main)
except Exception as e:
    log_exc("ft.app()", e)
