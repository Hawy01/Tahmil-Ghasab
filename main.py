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
PKG      = "com.ghasab.tahmil_ghasab"

log("module loaded | log={}".format(_path or "NONE"))


def get_save_dir():
    """Returns a writable absolute directory — tries Downloads first, then internal."""
    # اكتشاف بطاقة SD تلقائياً
    sd_dl = []        # /storage/XXXX/Download  ← يحتاج MANAGE_EXTERNAL_STORAGE
    sd_app = []       # /storage/XXXX/Android/data/<pkg>/files ← لا يحتاج صلاحية
    try:
        for d in os.listdir("/storage"):
            if d not in ("emulated", "self"):
                sd_dl.append("/storage/{}/Download".format(d))
                sd_app.append("/storage/{}/Android/data/{}/files".format(d, PKG))
    except Exception:
        pass

    # مسار الملفات الداخلية المطلق
    cwd = os.path.abspath(os.getcwd())
    home = os.environ.get("HOME", "")
    internal = os.path.join(home, "files") if home else os.path.join(cwd, "files")

    candidates = [
        # أولاً: Download (يحتاج MANAGE_EXTERNAL_STORAGE)
        "/storage/emulated/0/Download",
        "/sdcard/Download",
    ] + sd_dl + [
        # ثانياً: مجلد التطبيق على SD (لا يحتاج صلاحية خاصة)
    ] + sd_app + [
        "/sdcard/Android/data/{}/files".format(PKG),
        # أخيراً: التخزين الداخلي
        internal,
        cwd,
    ]
    for p in candidates:
        try:
            os.makedirs(p, exist_ok=True)
            test = os.path.join(p, ".wt")
            with open(test, "w") as f:
                f.write("ok")
            os.remove(test)
            log("save_dir: " + p)
            return os.path.abspath(p)
        except Exception as e:
            log("save_dir skip {}: {}".format(p, e))
            continue
    log("save_dir: fallback cwd=" + cwd)
    return cwd


# ── Main ──────────────────────────────────────────────────────────────
def main(page: ft.Page):
    log("main() | platform={}".format(page.platform))

    page.title      = "تحميل غصب"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor    = "#0d0d1a"
    page.padding    = 16
    page.scroll     = ft.ScrollMode.AUTO

    state = {"dl": False, "cookies": None, "last_file": None}

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
    snack = ft.SnackBar(
        content=ft.Text("", color="white"),
        bgcolor="#1a3a2a",
        duration=7000,
    )
    page.overlay.append(snack)

    log_dlg = ft.AlertDialog(
        title=ft.Text("سجل الأحداث"),
        content=ft.Container(
            content=ft.Column(controls=[], scroll=ft.ScrollMode.AUTO),
            width=320, height=380,
        ),
        actions=[ft.TextButton("إغلاق", on_click=lambda _: _close_dlg())],
    )
    page.overlay.append(log_dlg)

    def show_log(_):
        txt = "\n".join(_buf[-150:]) if _buf else "السجل فارغ"
        log_dlg.content.content.controls = [ft.Text(txt, size=10, selectable=True)]
        log_dlg.open = True
        page.update()

    def _close_dlg():
        log_dlg.open = False
        page.update()

    # ── Download logic ────────────────────────────────────────────
    def do_dl(url, qual):
        log("dl start: {} [{}]".format(url, qual))
        try:
            import yt_dlp
            sv = get_save_dir()
            log("save_dir={}".format(sv))

            # بدون ffmpeg: نستخدم تنسيقات لا تحتاج دمجاً
            if qual == "audio":
                fmt  = "bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio"
                post = []
            elif qual == "best":
                fmt  = "best[ext=mp4]/best"
                post = []
            else:
                fmt  = "best[height<={}][ext=mp4]/best[height<={}]".format(qual, qual)
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
                        # تشغيل Media Scanner
                        filepath = d.get("filename", "")
                        if filepath:
                            state["last_file"] = filepath
                            try:
                                import subprocess
                                subprocess.run(
                                    ["am", "broadcast",
                                     "-a", "android.intent.action.MEDIA_SCANNER_SCAN_FILE",
                                     "-d", "file://" + filepath],
                                    capture_output=True, timeout=5
                                )
                                log("media_scan: " + filepath)
                            except Exception as _e:
                                log("media_scan failed: " + str(_e))
                        page.update()
                except Exception:
                    pass

            opts = {
                "format":         fmt,
                "outtmpl":        "{}/%(title)s.%(ext)s".format(sv),
                "postprocessors": post,
                "quiet":          True,
                "no_warnings":    True,
                "progress_hooks": [hook],
                "noplaylist":     False,
            }
            ck_path = (ck_field.value or "").strip()
            if ck_path:
                if os.path.isfile(ck_path):
                    opts["cookiefile"] = ck_path
                else:
                    log("cookie path invalid (not a file): " + ck_path)
                    status.value = "⚠️ مسار الكوكيز غير صحيح — يجب أن يكون ملف .txt"
                    status.color = "#fbbf24"
                    page.update()

            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])

            log("dl complete ✓ → " + sv)
            status.value = "✅ تم التحميل!\nالمجلد: " + sv
            status.color = "#6ee7b7"
            bar.value    = 1
            snack.content.value = "✅ تم التحميل في: " + sv
            snack.bgcolor       = "#1a3a2a"
            snack.open          = True

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
            snack.content.value = status.value
            snack.bgcolor       = "#3a1a1a"
            snack.open          = True

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
        sv = get_save_dir()
        if "/Download" in sv:
            perm.value = "✅ التخزين: " + sv
            perm.color = "#6ee7b7"
        elif "/Android/data/" in sv:
            perm.value = (
                "⚠️ يُحفظ في SD: " + sv + "\n"
                "لتفعيل Downloads: الإعدادات ← التطبيقات ← تحميل غصب\n"
                "← الصلاحيات ← الوصول لكل الملفات ← تفعيل"
            )
            perm.color = "#fbbf24"
        else:
            perm.value = (
                "⚠️ يُحفظ في: " + sv + "\n"
                "لتفعيل Downloads: الإعدادات ← التطبيقات ← تحميل غصب\n"
                "← الصلاحيات ← الوصول لكل الملفات ← تفعيل"
            )
            perm.color = "#f87171"
        log("chk_perm: " + sv)
        try:
            page.update()
        except Exception:
            pass

    threading.Thread(target=chk_perm, daemon=True).start()
    log("main() done")


ft.app(target=main)
