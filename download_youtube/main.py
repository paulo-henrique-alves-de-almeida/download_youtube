import flet as ft
import yt_dlp
from yt_dlp.utils import DownloadError, ExtractorError, PostProcessingError
import asyncio
from pathlib import Path
import re
import sys

# ── Cores e constantes
BG        = "#0D0D0D"
SURFACE   = "#161616"
CARD      = "#1C1C1C"
BORDER    = "#2A2A2A"
RED       = "#FF3B3B"
RED_DARK  = "#C0392B"
WHITE     = "#F5F5F5"
MUTED     = "#888888"
SUCCESS   = "#2ECC71"
WARNING   = "#F39C12"


def strip_ansi(text: str) -> str:
    return re.sub(r'\x1b\[[0-9;]*m', '', text).strip()

def get_download_path():
    if sys.platform == "android":
        try:
            from android.storage import primary_external_storage_path
            return Path(primary_external_storage_path()) / "Download"
        except Exception:
            return Path("/sdcard/Download")
    return Path.home() / "Downloads"

def download_youtube(url: str, formato: str, progress_cb, status_cb, done_cb):
    base_path = get_download_path()
    error_msg = None
    caminho_final = base_path  # fallback

    ydl_opts_info = {"no_warnings": True, "noplaylist": False, "quiet": True}

    try:
        status_cb("Obtendo informações do vídeo…", WARNING)
        with yt_dlp.YoutubeDL(ydl_opts_info) as ydl:
            info = ydl.extract_info(url, download=False)

        e_playlist = "entries" in info or info.get("_type") == "playlist"

        if e_playlist:
            nome_playlist = info.get("title", "playlist")
            caminho_final = base_path / nome_playlist
        else:
            caminho_final = base_path

        template = str(caminho_final / "%(title)s.%(ext)s")
        caminho_final.mkdir(parents=True, exist_ok=True)

        def hook(d):
            if d["status"] == "downloading":
                try:
                    pct_raw = strip_ansi(d.get("_percent_str", "0%")).replace("%", "")
                    pct = float(pct_raw) if pct_raw else 0.0
                    progress_cb(pct / 100)
                    downloaded = strip_ansi(d.get("_downloaded_bytes_str", ""))
                    total = strip_ansi(d.get("_total_bytes_str") or d.get("_total_bytes_estimate_str", ""))
                    speed = strip_ansi(d.get("_speed_str", ""))
                    eta = strip_ansi(d.get("_eta_str", ""))
                    status_cb(f"{downloaded} / {total}  •  {speed}  •  ETA {eta}", MUTED)
                except Exception:
                    pass
            elif d["status"] == "finished":
                progress_cb(1.0)
                status_cb("Processando arquivo…", WARNING)

        ydl_opts = {
            "outtmpl":        template,
            "quiet":          True,
            "no_warnings":    True,
            "progress_hooks": [hook],
        }

        if formato == "mp3":
            ydl_opts.update({
                "format": "bestaudio/best",
                "postprocessors": [{
                    "key":              "FFmpegExtractAudio",
                    "preferredcodec":   "mp3",
                    "preferredquality": "192",
                }],
            })
        else:
            ydl_opts["format"] = (
                "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
            )

        status_cb("Baixando…", WARNING)
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

    except DownloadError:
        error_msg = "Erro no download. Verifique a URL e tente novamente."
    except ExtractorError:
        error_msg = "Não foi possível extrair informações da URL."
    except PostProcessingError:
        error_msg = "Falha ao converter para MP3. FFmpeg está instalado?"
    except Exception as e:
        error_msg = f"Erro inesperado: {type(e).__name__}: {e}"
    finally:
        if error_msg:
            done_cb(False, error_msg)
        else:
            done_cb(True, f"Download concluído!  Salvo em: {caminho_final}")


# ── App principal
async def main(page: ft.Page):
    page.title            = "Download Youtube"
    page.window.icon      = str(Path(__file__).parent / "download_youtube_logo.png")
    page.theme_mode       = ft.ThemeMode.DARK
    page.bgcolor          = BG
    page.padding          = 0
    page.window_width     = 480
    page.window_min_width = 360

    if sys.platform == "android":
        await page.request_permission_async(ft.Permission.STORAGE)

    page.fonts = {
        "Mono": "https://fonts.gstatic.com/s/spacemono/v13/i7dPIFZifjKcF5UAWdDRUEZ2RFq7AwU.woff2",
        "Sans": "https://fonts.gstatic.com/s/figtree/v5/_Xmq-HWyrCNqmCxkKTpe75U.woff2",
    }

    # ── Estado
    class State:
        formato     = "mp4"
        downloading = False

    state = State()

    # ── Widgets
    url_field = ft.TextField(
        hint_text            = "Cole o link do YouTube aqui…",
        hint_style           = ft.TextStyle(color=MUTED, font_family="Sans"),
        text_style           = ft.TextStyle(color=WHITE, font_family="Mono", size=13),
        border_color         = BORDER,
        focused_border_color = RED,
        border_radius        = 10,
        bgcolor              = SURFACE,
        color                = WHITE,
        cursor_color         = RED,
        expand               = True,
        content_padding      = ft.Padding.symmetric(horizontal=16, vertical=14),
    )

    progress_bar = ft.ProgressBar(
        value   = 0,
        color   = RED,
        bgcolor = BORDER,
        height  = 4,
    )

    status_text = ft.Text(
        "",
        color      = MUTED,
        size       = 11,
        text_align = ft.TextAlign.CENTER,
        style      = ft.TextStyle(font_family="Mono"),
    )

    progress_row = ft.Column(
        [progress_bar, status_text],
        spacing = 6,
        visible = False,
    )

    download_btn_content = ft.Row(
        [
            ft.Icon(ft.Icons.DOWNLOAD_ROUNDED, color=WHITE, size=18),
            ft.Text("BAIXAR", color=WHITE,
                    style=ft.TextStyle(font_family="Sans", weight=ft.FontWeight.BOLD,
                                       size=14, letter_spacing=2)),
        ],
        alignment          = ft.MainAxisAlignment.CENTER,
        vertical_alignment = ft.CrossAxisAlignment.CENTER,
        spacing            = 8,
    )

    download_btn = ft.Button(
        content = download_btn_content,
        bgcolor = RED,
        style   = ft.ButtonStyle(
            overlay_color = ft.Colors.with_opacity(0.15, ft.Colors.WHITE),
            shape         = ft.RoundedRectangleBorder(radius=10),
        ),
        height  = 52,
        expand  = True,
    )

    # ── Seletor de formato
    def make_format_chip(label: str, value: str, icon: str):
        is_active = state.formato == value

        chip = ft.Container(
            content = ft.Row(
                [
                    ft.Icon(icon, color=WHITE if is_active else MUTED, size=16),
                    ft.Text(label,
                            color = WHITE if is_active else MUTED,
                            size  = 13,
                            style = ft.TextStyle(
                                font_family = "Sans",
                                weight      = ft.FontWeight.BOLD if is_active else ft.FontWeight.NORMAL,
                            )),
                ],
                spacing            = 6,
                alignment          = ft.MainAxisAlignment.CENTER,
                vertical_alignment = ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor       = RED if is_active else CARD,
            border_radius = 8,
            padding       = ft.Padding.symmetric(horizontal=20, vertical=10),
            border        = ft.Border.all(1, RED if is_active else BORDER),
            animate       = ft.Animation(200, ft.AnimationCurve.EASE_OUT),
            data          = value,
        )

        async def on_tap(e):
            state.formato = e.control.data
            await refresh_chips()

        chip.on_click = on_tap
        return chip

    mp3_chip = make_format_chip("MP3", "mp3", ft.Icons.MUSIC_NOTE_ROUNDED)
    mp4_chip = make_format_chip("MP4", "mp4", ft.Icons.VIDEOCAM_ROUNDED)

    format_row = ft.Row(
        [mp3_chip, mp4_chip],
        spacing   = 10,
        alignment = ft.MainAxisAlignment.CENTER,
    )

    async def refresh_chips():
        fmt = state.formato
        for chip, val in [(mp3_chip, "mp3"), (mp4_chip, "mp4")]:
            active = fmt == val
            chip.bgcolor = RED if active else CARD
            chip.border  = ft.Border.all(1, RED if active else BORDER)
            chip.content.controls[0].color = WHITE if active else MUTED
            chip.content.controls[1].color = WHITE if active else MUTED
            chip.content.controls[1].style = ft.TextStyle(
                font_family = "Sans",
                weight      = ft.FontWeight.BOLD if active else ft.FontWeight.NORMAL,
            )
        page.update()

    # ── Callbacks chamados da thread síncrona
    loop = asyncio.get_event_loop()

    def on_progress(pct: float):
        async def _():
            progress_bar.value = pct
            page.update()
        asyncio.run_coroutine_threadsafe(_(), loop)

    def on_status(msg: str, color: str):
        async def _():
            status_text.value = msg
            status_text.color = color
            page.update()
        asyncio.run_coroutine_threadsafe(_(), loop)

    def on_done(success: bool, msg: str):
        async def _():
            state.downloading = False
            progress_bar.value = 1.0 if success else 0
            status_text.value  = msg
            status_text.color  = SUCCESS if success else RED
            download_btn_content.controls[1].value = "BAIXAR"
            download_btn.bgcolor  = RED
            download_btn.disabled = False
            page.mouse_cursor     = ft.MouseCursor.BASIC
            page.update()
        asyncio.run_coroutine_threadsafe(_(), loop)

    # ── Ação do botão
    async def on_download(e):
        url = url_field.value.strip() if url_field.value else ""

        if not url:
            status_text.value    = "⚠  Cole uma URL válida."
            status_text.color    = WARNING
            progress_row.visible = True
            page.update()
            return
    
        if sys.platform == "android" and state.formato == "mp3":
            import shutil
            if not shutil.which("ffmpeg"):
                progress_row.visible = True
                status_text.value = (
                    "⚠  FFmpeg não encontrado. Instale pelo Termux:\n"
                    "pkg install ffmpeg"
                )
                status_text.color = WARNING
                page.update()
                return

        if state.downloading:
            return

        state.downloading = True
        progress_bar.value   = 0
        progress_row.visible = True
        download_btn_content.controls[1].value = "BAIXANDO…"
        download_btn.bgcolor  = RED_DARK
        download_btn.disabled = True
        page.mouse_cursor     = ft.MouseCursor.WAIT
        page.update()

        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: download_youtube(url, state.formato, on_progress, on_status, on_done)
        )

    download_btn.on_click = on_download

    # ── Layout
    header = ft.Container(
        content = ft.Row(
            [
                ft.Container(
                    content       = ft.Text("▶", color=RED, size=22,
                                            style=ft.TextStyle(font_family="Mono")),
                    bgcolor       = ft.Colors.with_opacity(0.12, RED),
                    border_radius = 8,
                    padding       = ft.Padding.symmetric(horizontal=10, vertical=6),
                ),
                ft.Column(
                    ft.Text("Download Youtube",
                        color=WHITE, size=18,
                        style=ft.TextStyle(font_family="Sans", weight=ft.FontWeight.BOLD)),
                    spacing=2,
                ),
            ],
            spacing=12,
        ),
        padding = ft.Padding.symmetric(horizontal=24, vertical=20),
    )

    divider = ft.Divider(height=1, color=BORDER)

    body = ft.Container(
        content = ft.Column(
            [
                ft.Text("URL do vídeo ou playlist", color=MUTED, size=12,
                        style=ft.TextStyle(font_family="Sans", weight=ft.FontWeight.W_500)),
                ft.Row([url_field], spacing=0),
                ft.Container(height=4),
                ft.Text("Formato de saída", color=MUTED, size=12,
                        style=ft.TextStyle(font_family="Sans", weight=ft.FontWeight.W_500)),
                format_row,
                ft.Container(height=8),
                ft.Row([download_btn]),
                ft.Container(height=6),
                progress_row,
            ],
            spacing = 10,
        ),
        padding = ft.Padding.symmetric(horizontal=24, vertical=20),
    )

    footer = ft.Container(
        content = ft.Text(
            f"Os arquivos são salvos em {get_download_path()}",
            color      = ft.Colors.with_opacity(0.35, WHITE),
            size       = 10,
            text_align = ft.TextAlign.CENTER,
            style      = ft.TextStyle(font_family="Mono"),
        ),
        alignment = ft.Alignment(0, 0),
        padding   = ft.Padding.only(bottom=20),
    )

    card = ft.Container(
        content = ft.Column(
            [header, divider, body, footer],
            spacing = 0,
        ),
        bgcolor       = SURFACE,
        border_radius = 16,
        border        = ft.Border.all(1, BORDER),
        margin        = ft.Margin.symmetric(horizontal=16, vertical=32),
        shadow        = ft.BoxShadow(
            spread_radius = 0,
            blur_radius   = 40,
            color         = ft.Colors.with_opacity(0.5, "#000000"),
            offset        = ft.Offset(0, 8),
        ),
    )

    page.add(
        ft.Container(
            content   = card,
            expand    = True,
            alignment = ft.Alignment(0, -1),
        )
    )


if __name__ == '__main__':
    ft.run(main)
