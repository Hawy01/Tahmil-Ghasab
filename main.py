import flet as ft
import yt_dlp
import threading
import os

DOWNLOAD_DIR = "/storage/emulated/0/Download"

def get_ffmpeg_path():
    # مسارات محتملة لـ ffmpeg على Android مع Flet
    candidates = [
        os.path.join(os.getcwd(), "assets", "ffmpeg"),
        os.path.join(os.path.dirname(__file__), "assets", "ffmpeg"),
        "/data/data/com.ghasab.downloader/files/assets/ffmpeg",
    ]
    for p in candidates:
        if os.path.isfile(p):
            return p
    return None


def main(page: ft.Page):
    page.title = "تحميل غصب"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#0d0d1a"
    page.padding = 0
    page.scroll = None

    # ── متغيرات الحالة ──────────────────────────────────────────
    cookies_path = {"value": None}
    is_downloading = {"value": False}

    # ── عناصر الواجهة ───────────────────────────────────────────
    url_input = ft.TextField(
        label="رابط الفيديو أو قائمة التشغيل",
        hint_text="https://youtube.com/watch?v=...",
        prefix_icon=ft.Icons.LINK,
        border_radius=12,
        filled=True,
        expand=True,
        text_style=ft.TextStyle(size=14),
        border_color="#5c5cff",
        focused_border_color="#a78bfa",
        cursor_color="#a78bfa",
    )

    quality_dd = ft.Dropdown(
        label="جودة التحميل",
        width=200,
        border_radius=12,
        filled=True,
        border_color="#5c5cff",
        focused_border_color="#a78bfa",
        value="best",
        options=[
            ft.dropdown.Option("best",    "أفضل جودة"),
            ft.dropdown.Option("1080",    "1080p"),
            ft.dropdown.Option("720",     "720p"),
            ft.dropdown.Option("480",     "480p"),
            ft.dropdown.Option("audio",   "صوت فقط (MP3)"),
        ],
    )

    cookies_label = ft.Text(
        "لم يتم اختيار ملف كوكيز",
        size=12,
        color="#888",
        overflow=ft.TextOverflow.ELLIPSIS,
        max_lines=1,
    )

    progress_bar = ft.ProgressBar(
        width=None,
        value=0,
        bgcolor="#1a1a2e",
        color="#a78bfa",
        border_radius=8,
        visible=False,
    )

    progress_label = ft.Text("", size=12, color="#a78bfa", visible=False)

    status_text = ft.Text(
        "جاهز للتحميل",
        size=13,
        color="#6ee7b7",
        text_align=ft.TextAlign.CENTER,
    )

    download_btn = ft.ElevatedButton(
        content=ft.Row(
            [ft.Icon(ft.Icons.DOWNLOAD_ROUNDED), ft.Text("تحميل غصب", size=15, weight=ft.FontWeight.BOLD)],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=8,
        ),
        style=ft.ButtonStyle(
            bgcolor={"": "#5c5cff", "hovered": "#7c7cff"},
            color="#ffffff",
            shape=ft.RoundedRectangleBorder(radius=14),
            padding=ft.padding.symmetric(vertical=14, horizontal=24),
            elevation=6,
        ),
        expand=True,
    )

    # ── FilePicker للكوكيز ────────────────────────────────────────
    def on_cookies_picked(e: ft.FilePickerResultEvent):
        if e.files:
            f = e.files[0]
            cookies_path["value"] = f.path
            cookies_label.value = f"✅ {f.name}"
            cookies_label.color = "#6ee7b7"
        else:
            cookies_path["value"] = None
            cookies_label.value = "لم يتم اختيار ملف كوكيز"
            cookies_label.color = "#888"
        page.update()

    file_picker = ft.FilePicker(on_result=on_cookies_picked)
    page.overlay.append(file_picker)

    def pick_cookies(_):
        file_picker.pick_files(
            dialog_title="اختر ملف الكوكيز (.txt)",
            initial_directory=DOWNLOAD_DIR if os.path.exists(DOWNLOAD_DIR) else None,
            allowed_extensions=["txt"],
            allow_multiple=False,
        )

    cookies_btn = ft.OutlinedButton(
        content=ft.Row(
            [ft.Icon(ft.Icons.COOKIE_OUTLINED, size=18), ft.Text("إضافة كوكيز", size=13)],
            spacing=6,
        ),
        style=ft.ButtonStyle(
            side=ft.BorderSide(1, "#5c5cff"),
            shape=ft.RoundedRectangleBorder(radius=12),
            color="#a78bfa",
            padding=ft.padding.symmetric(vertical=10, horizontal=16),
        ),
        on_click=pick_cookies,
    )

    # ── منطق التحميل ─────────────────────────────────────────────
    def build_ydl_opts(quality: str) -> dict:
        save_path = DOWNLOAD_DIR if os.path.isdir(DOWNLOAD_DIR) else "./"
        ffmpeg_bin = get_ffmpeg_path()

        if quality == "audio":
            fmt = "bestaudio/best"
            postprocessors = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }]
            outtmpl = f"{save_path}/%(title)s.%(ext)s"
        else:
            if quality == "best":
                fmt = "bestvideo+bestaudio/best"
            else:
                fmt = f"bestvideo[height<={quality}]+bestaudio/best[height<={quality}]"
            postprocessors = []
            outtmpl = f"{save_path}/%(title)s.%(ext)s"

        opts = {
            "format": fmt,
            "outtmpl": outtmpl,
            "merge_output_format": "mp4",
            "postprocessors": postprocessors,
            "noplaylist": False,
            "quiet": True,
            "no_warnings": True,
            "progress_hooks": [progress_hook],
        }
        if ffmpeg_bin:
            opts["ffmpeg_location"] = ffmpeg_bin
        if cookies_path["value"]:
            opts["cookiefile"] = cookies_path["value"]

        return opts

    def progress_hook(d: dict):
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes", 0)
            speed = d.get("speed") or 0
            eta = d.get("eta") or 0

            pct = (downloaded / total) if total else 0
            speed_mb = speed / 1_048_576 if speed else 0
            title = d.get("filename", "").split("/")[-1][:40]

            progress_bar.value = pct
            progress_label.value = (
                f"{title}  |  {pct*100:.1f}%  |  {speed_mb:.1f} MB/s  |  ETA: {eta}ث"
            )
            status_text.value = "جاري التحميل..."
            status_text.color = "#fbbf24"
            page.update()

        elif d["status"] == "finished":
            progress_bar.value = 1
            status_text.value = "جاري المعالجة..."
            status_text.color = "#60a5fa"
            page.update()

    def do_download(url: str, quality: str):
        try:
            opts = build_ydl_opts(quality)
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])

            progress_bar.value = 1
            progress_bar.color = "#6ee7b7"
            status_text.value = "✅ تم التحميل بنجاح في مجلد Downloads!"
            status_text.color = "#6ee7b7"
            progress_label.value = ""
        except yt_dlp.utils.DownloadError as e:
            err = str(e)
            if "Sign in" in err or "login" in err.lower():
                status_text.value = "❌ هذا الفيديو يتطلب تسجيل دخول، أضف ملف كوكيز"
            elif "Private" in err:
                status_text.value = "❌ الفيديو خاص"
            elif "available" in err.lower():
                status_text.value = "❌ الفيديو غير متاح في منطقتك"
            else:
                status_text.value = f"❌ {err[:80]}"
            status_text.color = "#f87171"
            progress_bar.color = "#f87171"
        except Exception as e:
            status_text.value = f"❌ خطأ: {str(e)[:80]}"
            status_text.color = "#f87171"
            progress_bar.color = "#f87171"
        finally:
            is_downloading["value"] = False
            download_btn.disabled = False
            progress_bar.visible = False
            progress_label.visible = False
            page.update()

    def on_download(_):
        url = url_input.value.strip()
        if not url:
            status_text.value = "⚠️ يرجى إدخال رابط الفيديو"
            status_text.color = "#fbbf24"
            page.update()
            return
        if not (url.startswith("http://") or url.startswith("https://")):
            status_text.value = "⚠️ الرابط غير صالح، يجب أن يبدأ بـ http:// أو https://"
            status_text.color = "#fbbf24"
            page.update()
            return
        if is_downloading["value"]:
            return

        is_downloading["value"] = True
        download_btn.disabled = True
        progress_bar.visible = True
        progress_bar.value = 0
        progress_bar.color = "#a78bfa"
        progress_label.visible = True
        progress_label.value = "جاري الاتصال بالخادم..."
        status_text.value = "جاري التحميل..."
        status_text.color = "#fbbf24"
        page.update()

        threading.Thread(
            target=do_download,
            args=(url, quality_dd.value),
            daemon=True,
        ).start()

    download_btn.on_click = on_download

    # ── بناء الواجهة ──────────────────────────────────────────────
    header = ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Icon(ft.Icons.DOWNLOAD_FOR_OFFLINE_ROUNDED, size=36, color="#a78bfa"),
                        ft.Column(
                            [
                                ft.Text("تحميل غصب", size=26, weight=ft.FontWeight.BOLD, color="#ffffff"),
                                ft.Text("حمّل أي فيديو بسهولة وسرعة", size=12, color="#888"),
                            ],
                            spacing=2,
                        ),
                    ],
                    spacing=12,
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.padding.symmetric(vertical=28, horizontal=20),
        gradient=ft.LinearGradient(
            begin=ft.alignment.top_center,
            end=ft.alignment.bottom_center,
            colors=["#1a1a3e", "#0d0d1a"],
        ),
    )

    card = ft.Container(
        content=ft.Column(
            [
                ft.Text("رابط التحميل", size=13, color="#aaa", weight=ft.FontWeight.W_500),
                url_input,
                ft.Divider(height=8, color="transparent"),
                ft.Text("جودة التحميل", size=13, color="#aaa", weight=ft.FontWeight.W_500),
                quality_dd,
                ft.Divider(height=8, color="transparent"),
                ft.Text("الكوكيز (اختياري)", size=13, color="#aaa", weight=ft.FontWeight.W_500),
                ft.Row(
                    [cookies_btn, ft.Container(cookies_label, expand=True)],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=10,
                ),
                ft.Divider(height=12, color="#1e1e3e"),
                download_btn,
                ft.Divider(height=4, color="transparent"),
                progress_bar,
                progress_label,
                ft.Divider(height=4, color="transparent"),
                status_text,
            ],
            spacing=8,
        ),
        margin=ft.margin.symmetric(horizontal=16, vertical=12),
        padding=20,
        bgcolor="#13132b",
        border_radius=20,
        shadow=ft.BoxShadow(blur_radius=20, color="#00000055", offset=ft.Offset(0, 4)),
    )

    tip_card = ft.Container(
        content=ft.Column(
            [
                ft.Text("نصائح للاستخدام", size=13, color="#a78bfa", weight=ft.FontWeight.BOLD),
                ft.Text("• للفيديوهات الخاصة أضف ملف كوكيز بصيغة .txt من مجلد التنزيلات", size=12, color="#888"),
                ft.Text("• يمكنك تحميل قوائم تشغيل YouTube كاملة", size=12, color="#888"),
                ft.Text("• اختر 'صوت فقط' لاستخراج الصوت بصيغة MP3", size=12, color="#888"),
            ],
            spacing=6,
        ),
        margin=ft.margin.symmetric(horizontal=16, vertical=4),
        padding=16,
        bgcolor="#0f0f22",
        border_radius=14,
        border=ft.border.all(1, "#1e1e3e"),
    )

    page.add(
        ft.Column(
            [header, card, tip_card],
            scroll=ft.ScrollMode.AUTO,
            expand=True,
            spacing=0,
        )
    )


ft.app(target=main)
