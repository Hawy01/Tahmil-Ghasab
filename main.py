import flet as ft
import threading
import traceback
import os
import datetime

# ── Logging ───────────────────────────────────────────────────────────
_buf  = []
_path = None

def _init_log():
    global _path
    for p in [
        os.path.join(os.environ.get("HOME", ""), "g.log"),
        "/storage/emulated/0/Download/ghasab.log",
        os.path.join(os.getcwd(), "g.log"),
    ]:
        if not p.strip():
            continue
        try:
            d = os.path.dirname(p)
            if d:
                os.makedirs(d, exist_ok=True)
            with open(p, "a", encoding="utf-8") as f:
                f.write("\n=== {} ===\n".format(datetime.datetime.now()))
            _path = p
            return
        except Exception:
            pass

_init_log()


def log(m):
    e = "[{}] {}".format(datetime.datetime.now().strftime("%H:%M:%S"), m)
    _buf.append(e)
    if len(_buf) > 400:
        _buf.pop(0)
    if _path:
        try:
            with open(_path, "a", encoding="utf-8") as f:
                f.write(e + "\n")
        except Exception:
            pass


def log_exc(ctx, ex):
    log("ERR[{}]: {}: {}\n{}".format(
        ctx, type(ex).__name__, ex, traceback.format_exc()))


# ── Constants ─────────────────────────────────────────────────────────
SAVE_DIR = "/storage/emulated/0/Download"
PKG      = "com.flet.tahmil_ghasab"

log("module loaded | log={}".format(_path or "NONE"))


def get_ffmpeg():
    for p in [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "ffmpeg"),
        "/data/user/0/{}/files/assets/ffmpeg".format(PKG),
        "/data/data/{}/files/assets/ffmpeg".format(PKG),
    ]:
        if os.path.isfile(p):
            try:
                os.chmod(p, 0o755)
            except Exception:
                pass
            log("ffmpeg: " + p)
            return p
    log("ffmpeg: not found")
    return None


# ── Main ──────────────────────────────────────────────────────────────
def main(page: ft.Page):
    log("main() | platform={}".format(page.platform))

    page.title      = "تحميل غصب"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor    = "#0d0d1a"
    page.padding    = 16
    page.scroll     = ft.ScrollMode.AUTO

    state = {"dl": False, "cookies": None}

    # ── Controls ──────────────────────────────────────────────────
    url_in = ft.TextField(
        label="رابط الفيديو أو قائمة التشغيل",
        hint_text="https://youtube.com/watch?v=...",
        filled=True,
        border_color="#5c5cff",
        focused_border_color="#a78bfa",
    )

    quality = ft.Dropdown(
        label="الجودة",
        value="best",
        options=[
            ft.dropdown.Option(key="best",  text="أفضل جودة"),
            ft.dropdown.Option(key="1080",  text="1080p"),
            ft.dropdown.Option(key="720",   text="720p"),
            ft.dropdown.Option(key="480",   text="480p"),
            ft.dropdown.Option(key="audio", text="صوت فقط (MP3)"),
        ],
    )

    status   = ft.Text("جاهز للتحميل ✓", size=13, color="#6ee7b7")
    bar      = ft.ProgressBar(value=0, visible=False)
    blabel   = ft.Text("", size=11, color="#aaaaaa", visible=False)
    perm     = ft.Text("", size=11, color="#fbbf24")
    ck_field = ft.TextField(
        label="مسار ملف الكوكيز (اختياري)",
        hint_text="/storage/emulated/0/Download/cookies.txt",
        filled=True,
        border_color="#444466",
    )

    # ── Log dialog ────────────────────────────────────────────────
    def show_log(_):
        txt = "\n".join(_buf[-150:]) if _buf else "السجل فارغ"
        dlg = ft.AlertDialog(
            title=ft.Text("سجل الأخطاء"),
            content=ft.Container(
                content=ft.Column(
                    controls=[ft.Text(txt, size=10, selectable=True)],
                    scroll=ft.ScrollMode.AUTO,
                ),
                width=320,
                height=380,
            ),
            actions=[
                ft.TextButton(
                    "إغلاق",
                    on_click=lambda _: _close_dlg(dlg),
                ),
            ],
        )
        try:
            page.open(dlg)
        except Exception:
            try:
                page.dialog = dlg
                dlg.open = True
                page.update()
            except Exception as ex:
                log_exc("show_log.open", ex)

    def _close_dlg(dlg):
        try:
            page.close(dlg)
        except Exception:
            try:
                dlg.open = False
                page.update()
            except Exception:
                pass

    # ── Download logic ────────────────────────────────────────────
    def do_dl(url, qual):
        log("dl start: {} [{}]".format(url, qual))
        try:
            import yt_dlp
            sv = SAVE_DIR if os.path.isdir(SAVE_DIR) else os.getcwd()
            ff = get_ffmpeg()
            log("save_dir={} ffmpeg={}".format(sv, ff))

            if qual == "audio":
                fmt  = "bestaudio/best"
                post = [{"key": "FFmpegExtractAudio",
                         "preferredcodec": "mp3", "preferredquality": "192"}]
            elif qual == "best":
                fmt, post = "bestvideo+bestaudio/best", []
            else:
                fmt  = "bestvideo[height<={}]+bestaudio/best".format(qual)
                post = []

            def hook(d):
                try:
                    s = d.get("status", "")
                    if s == "downloading":
                        tot = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                        dl  = d.get("downloaded_bytes", 0)
                        pct = dl / tot if tot else 0
                        spd = (d.get("speed") or 0) / 1_000_000
                        bar.value    = pct
                        blabel.value = "{:.0f}%  {:.1f}MB/s".format(pct * 100, spd)
                        status.value = "جاري التحميل..."
                        status.color = "#fbbf24"
                        page.update()
                    elif s == "finished":
                        bar.value    = 1
                        status.value = "جاري المعالجة..."
                        status.color = "#60a5fa"
                        page.update()
                except Exception:
                    pass

            opts = {
                "format":              fmt,
                "outtmpl":             "{}/%(title)s.%(ext)s".format(sv),
                "merge_output_format": "mp4",
                "postprocessors":      post,
                "quiet":               True,
                "no_warnings":         True,
                "progress_hooks":      [hook],
                "noplaylist":          False,
            }
            ck_path = (ck_field.value or "").strip()
            if ff:      opts["ffmpeg_location"] = ff
            if ck_path: opts["cookiefile"]      = ck_path

            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])

            log("dl complete ✓")
            status.value = "✅ تم التحميل في مجلد Downloads!"
            status.color = "#6ee7b7"
            bar.value    = 1

        except Exception as ex:
            log_exc("do_dl", ex)
            err = str(ex)
            if   "Sign in" in err or "login" in err.lower():
                status.value = "❌ يحتاج تسجيل دخول — أضف كوكيز"
            elif "Private" in err:
                status.value = "❌ الفيديو خاص"
            elif "available" in err.lower():
                status.value = "❌ غير متاح في منطقتك"
            elif "ermission" in err:
                status.value = "❌ لا توجد صلاحية تخزين"
            else:
                status.value = "❌ فشل: " + err[:60]
            status.color = "#f87171"

        finally:
            state["dl"]      = False
            dl_btn.disabled  = False
            bar.visible      = False
            blabel.visible   = False
            try:
                page.update()
            except Exception:
                pass

    def on_dl(_):
        url = (url_in.value or "").strip()
        if not url:
            status.value = "⚠️ أدخل رابط الفيديو"
            status.color = "#fbbf24"
            page.update()
            return
        if not url.startswith(("http://", "https://")):
            status.value = "⚠️ الرابط غير صالح"
            status.color = "#fbbf24"
            page.update()
            return
        if state["dl"]:
            return

        state["dl"]      = True
        dl_btn.disabled  = True
        bar.visible      = True
        bar.value        = 0
        blabel.visible   = True
        blabel.value     = "جاري الاتصال..."
        status.value     = "جاري التحميل..."
        status.color     = "#fbbf24"
        page.update()
        threading.Thread(
            target=do_dl, args=(url, quality.value), daemon=True
        ).start()

    dl_btn = ft.ElevatedButton("تحميل غصب", on_click=on_dl)
    lg_btn = ft.TextButton("📋 سجل",       on_click=show_log)

    # ── Build page ────────────────────────────────────────────────
    log("building page...")
    page.add(
        ft.Text("تحميل غصب", size=26,
                weight=ft.FontWeight.BOLD, color="#a78bfa"),
        ft.Text("حمّل أي فيديو بسهولة وسرعة", size=12, color="#666666"),
        ft.Divider(color="#222244"),
        url_in,
        quality,
        ck_field,
        perm,
        dl_btn,
        bar,
        blabel,
        status,
        ft.Divider(color="#222244"),
        ft.Text("نصائح", size=12, color="#a78bfa",
                weight=ft.FontWeight.BOLD),
        ft.Text("• الفيديوهات الخاصة تحتاج ملف كوكيز .txt",
                size=11, color="#666666"),
        ft.Text("• يمكن تحميل قوائم تشغيل YouTube كاملة",
                size=11, color="#666666"),
        ft.Text("• اختر 'صوت فقط' لاستخراج MP3",
                size=11, color="#666666"),
        lg_btn,
    )
    log("page.add() done")

    # ── Storage permission check ──────────────────────────────────
    def chk_perm():
        try:
            os.makedirs(SAVE_DIR, exist_ok=True)
            t = os.path.join(SAVE_DIR, ".wt")
            with open(t, "w") as f:
                f.write("ok")
            os.remove(t)
            perm.value = "✅ صلاحية التخزين: ممنوحة"
            perm.color = "#6ee7b7"
            log("perm: OK")
        except Exception as ex:
            perm.value = "⚠️ لا توجد صلاحية تخزين — افتح الإعدادات"
            perm.color = "#f87171"
            log_exc("chk_perm", ex)
        try:
            page.update()
        except Exception:
            pass

    threading.Thread(target=chk_perm, daemon=True).start()
    log("main() done")


ft.app(target=main)
