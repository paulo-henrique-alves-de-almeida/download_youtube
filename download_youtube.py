import yt_dlp
from yt_dlp.utils import DownloadError, ExtractorError, PostProcessingError
import os
from pathlib import Path

def download_youtube(url, formato):
    base_path = Path.home() / "Downloads"
    
    # Opções temporárias apenas para extrair informações (sem baixar nada)
    ydl_opts_info = {
        'no_warnings': True,
        'noplaylist': False
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts_info) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Verifica se é uma playlist
            e_playlist = 'entries' in info or info.get('_type') == 'playlist'
            
            if e_playlist:
                nome_playlist = info.get('title')
                caminho_final = base_path / nome_playlist
                template = str(caminho_final / "%(title)s.%(ext)s")
            else:
                caminho_final = base_path
                template = str(caminho_final / "%(title)s.%(ext)s")

        caminho_final.mkdir(parents=True, exist_ok=True)

        # Opções reais de download
        ydl_opts = {
            'outtmpl': template,
            'quiet': False,
            'no_warnings': True,
        }

        if formato == 'mp3':
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            })
        else:
            ydl_opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except DownloadError:
        print('\033[31mHouve um erro no Download.\033[m')
    except ExtractorError:
        print('\033[31mNão foi possível baixar o vídeo pela URL fornecida.\033[m')
    except PostProcessingError:
        print('\033[31mNão foi possível converter o vídeo para o formato mp3.\033[m')
    except Exception as e:
        print(f'\033[31mOcorreu um erro: {e}\033[m')
    else:
        print('\n\033[32mDownload concluído com sucesso!\033[m \n')


while True:
    os.system('cls')
    print('=============== DOWNLOAD YOUTUBE ===============\n')

    link = input("Digite a URL de um vídeo ou playlist: ").strip()

    while True:
        opcao = input('''
Escolha o formato:
[1] MP3
[2] MP4
''').strip()
        
        if opcao != '1' and opcao != '2':
            print('\033[31mDigite apenas [1] ou [2].\033[m \n')
        else:
            break
        print()

    download_youtube(link, 'mp3' if opcao == '1' else 'mp4')

    continuar = input('Para sair, digite [1]: ')

    if continuar == '1':
        break
