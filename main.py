import flet as ft
import threading
import traceback
import os

DOWNLOAD_DIR = "/storage/emulated/0/Download"
APP_PACKAGE  = "com.ghasab.downloader"


def get_ffmpeg_path():
    candidates = [
        os.path.join(os.getcwd(), "assets", "ffmpeg"),
        os.path.join(os.path.dirname(__file__), "assets", "ffmpeg"),
        f"/data/data/{APP_PACKAGE}/files/assets/ffmpeg",
        f"/data/user/0/{APP_PACKAGE}/files/assets/ffmpeg",
    ]
    for p in candidates:
        if os.path.isfile(p):
            try:
                os.chmod(p, 0o755)
            except Exception:
                pass
            return p
    return None


def main(page: ft.Page):
    # ── أول شيء: عرض نص فوري لمنع الشاشة السوداء ───────────────
    page.title      = "تحميل غصب"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor    = "#0d0d1a"
    page.padding    = 16
    page.scroll     = ft.ScrollMode.AUTO   # scroll على Page مباشرة

    splash = ft.Text("جاري تهيئة التطبيق...", color="#aaa", size=14)
    page.add(splash)
    page.update()   # ← يُظهر شيئاً فوراً قبل أي عملية ثقيلة

    # ── سجل الأخطاء ──────────────────────────────────────────────
    error_log = ft.Text("", size=11, color="#fca5a5", selectable=True)
    error_card = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Icon(ft.icons.BUG_REPORT, color="#f87171", size=16),
                ft.Text("سجل الأخطاء", size=12, color="#f87171",
                        weight=ft.FontWeight.BOLD),
            ], spacing=6),
            error_log,
        ], spacing=6),
        padding=12,
        bgcolor="#1a0808",
        border_radius=10,
        visible=False,
    )

    def show_error(context: str, exc: Exception):
        tb = traceback.format_exc()
        error_log.value   = f"[{context}]\n{type(exc).__name__}: {exc}\n\n{tb[-600:]}"
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
        value=0,
        bgcolor="#1a1a2e",
        color="#a78bfa",
        visible=False,
    )

    progress_label = ft.Text("", size=11, color="#a78bfa", visible=False)

    status_text = ft.Text(
        "جاهز للتحميل ✓",
        size=13,
        color="#6ee7b7",
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

    # ── FilePicker للكوكيز ────────────────────────────────────────
    def on_cookies_picked(e: ft.FilePickerResultEvent):
        try:
            if e.files:
                f = e.files[0]
                cookies_path["value"] = f.path
                cookies_label.value   = f"✅ {f.name}"
                cookies_label.color   = "#6ee7b7"
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
        if page.platform != ft.PagePlatform.ANDROID:
            return
        try:
            os.makedirs(DOWNLOAD_DIR, exist_ok=True)
            test = os.path.join(DOWNLOAD_DIR, ".write_test")
            with open(test, "w") as f:
                f.write("ok")
            os.remove(test)
            perm_text.value = "✅ صلاحية التخزين ممنوحة"
            perm_text.color = "#6ee7b7"
        except PermissionError:
            perm_text.value = "⚠️ لا توجد صلاحية تخزين — افتح إعدادات التطبيق"
            perm_text.color = "#f87171"
            try:
                os.system(
                    "am start -a android.settings.MANAGE_APP_ALL_FILES_ACCESS_PERMISSION"
                    f" -d package:{APP_PACKAGE} > /dev/null 2>&1 &"
                )
            except Exception:
                pass
        except Exception as ex:
            perm_text.value = f"⚠️ تحقق من الصلاحيات: {ex}"
            perm_text.color = "#fbbf24"
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
                progress_label.value = f"{pct*100:.0f}%  ·  {speed_mb:.1f} MB/s  ·  ETA: {eta}ث"
                status_text.value    = "جاري التحميل..."
                status_text.color    = "#fbbf24"
                page.update()
            elif d["status"] == "finished":
                progress_bar.value = 1
                status_text.value  = "جاري المعالجة..."
                status_text.color  = "#60a5fa"
                page.update()
        except Exception:
            pass

    def do_download(url: str, quality: str):
        try:
            import yt_dlp  # استيراد متأخر لتفادي تجميد شاشة البدء

            save_path  = DOWNLOAD_DIR if os.path.isdir(DOWNLOAD_DIR) else "./"
            ffmpeg_bin = get_ffmpeg_path()

            if quality == "audio":
                fmt  = "bestaudio/best"
                post = [{"key": "FFmpegExtractAudio",
                         "preferredcodec": "mp3", "preferredquality": "192"}]
            else:
                fmt  = ("bestvideo+bestaudio/best" if quality == "best"
                        else f"bestvideo[height<={quality}]+bestaudio/best[height<={quality}]")
                post = []

            opts = {
                "format":             fmt,
                "outtmpl":            f"{save_path}/%(title)s.%(ext)s",
                "merge_output_format":"mp4",
                "postprocessors":     post,
                "noplaylist":         False,
                "quiet":              True,
                "no_warnings":        True,
                "progress_hooks":     [progress_hook],
            }
            if ffmpeg_bin:
                opts["ffmpeg_location"] = ffmpeg_bin
            if cookies_path["value"]:
                opts["cookiefile"] = cookies_path["value"]

            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])

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
                status_text.value = "❌ فشل التحميل — راجع السجل أدناه"
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

    # ── بناء الواجهة الكاملة وتبديل splash ──────────────────────
    try:
        header = ft.Container(
            content=ft.Row([
                ft.Icon(ft.icons.DOWNLOAD_FOR_OFFLINE, size=30, color="#a78bfa"),
                ft.Column([
                    ft.Text("تحميل غصب", size=22,
                            weight=ft.FontWeight.BOLD, color="#ffffff"),
                    ft.Text("حمّل أي فيديو بسهولة وسرعة", size=11, color="#888"),
                ], spacing=2, tight=True),
            ], spacing=10),
            padding=ft.padding.symmetric(vertical=20, horizontal=0),
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
            ], spacing=8, tight=True),
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
                ft.Text("• يمكن تحميل قوائم تشغيل YouTube كاملة",
                        size=11, color="#888"),
                ft.Text("• اختر 'صوت فقط' لاستخراج الصوت MP3",
                        size=11, color="#888"),
            ], spacing=4, tight=True),
            padding=14,
            bgcolor="#0f0f22",
            border_radius=12,
        )

        # استبدال splash بالواجهة الكاملة
        page.controls.clear()
        page.add(header, card, error_card, tip_card)
        page.update()

        # فحص الصلاحيات في الخلفية بعد عرض الواجهة
        threading.Thread(target=check_storage_perm, daemon=True).start()

    except Exception as ex:
        # عرض الخطأ بدلاً من الشاشة السوداء
        tb = traceback.format_exc()
        page.controls.clear()
        page.add(
            ft.Icon(ft.icons.WARNING_ROUNDED, size=48, color="#f87171"),
            ft.Text("خطأ في تهيئة التطبيق", size=16,
                    color="#f87171", weight=ft.FontWeight.BOLD),
            ft.Text(f"{type(ex).__name__}: {ex}", size=12, color="#fca5a5"),
            ft.Divider(color="#333"),
            ft.Text(tb[-1000:], size=10, color="#666", selectable=True),
        )
        page.update()


ft.app(target=main)
