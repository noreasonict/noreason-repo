import os
import xbmc
import xbmcgui
import urllib.request
import time
import random
import threading
import shutil
import xbmcaddon
from datetime import datetime, timedelta

# Cesty k souborům
local_file = "/storage/videos/Oresi_CZ.mp4"
remote_url = "http://oresi.eu/oresiftp/smycky/CZ/Oresi_CZ.mp4"
REBOOT_TRACK_FILE = "/storage/.kodi/userdata/reboot_log.txt"  # Soubor pro sledování restartů

def show_notification(title, message, icon=xbmcgui.NOTIFICATION_INFO, duration=5000):
    """Zobrazí informační okénko v Kodi s výchozí ikonou."""
    xbmcgui.Dialog().notification(title, message, icon, duration)

def is_internet_available():
    """Zkontroluje dostupnost internetu pomocí jednoduchého HTTP požadavku."""
    try:
        urllib.request.urlopen("http://google.com", timeout=5)
        return True
    except:
        return False

def get_remote_file_info(url):
    """Získá datum poslední úpravy a velikost souboru na vzdáleném serveru."""
    try:
        with urllib.request.urlopen(url) as response:
            last_modified = response.headers.get("Last-Modified")
            content_length = response.headers.get("Content-Length")

            remote_timestamp = time.mktime(time.strptime(last_modified, "%a, %d %b %Y %H:%M:%S %Z")) if last_modified else None
            remote_size = int(content_length) if content_length else None
            return remote_timestamp, remote_size
    except Exception as e:
        xbmc.log(f"Chyba při získávání informací o vzdáleném souboru: {str(e)}", xbmc.LOGERROR)
        return None, None

def get_local_file_info(path):
    """Získá datum poslední úpravy a velikost lokálního souboru."""
    if os.path.exists(path):
        return os.path.getmtime(path), os.path.getsize(path)
    return 0, 0  

def download_file(url, local_path):
    """Bezpečně stáhne soubor z dané URL po blocích, přepíše ho pouze pokud je kompletní, a při výpadku internetu přehraje lokální soubor."""
    
    temp_path = local_path + "_tmp"  # Dočasný název souboru
    block_size = 1024 * 1024  # 1 MB bloky pro detekci výpadku internetu

    try:
        show_notification("Stahování", "Probíhá stahování souboru...", xbmcgui.NOTIFICATION_INFO)
        xbmc.log(f"Stahuji soubor z {url} do {temp_path}", xbmc.LOGINFO)

        # Otevřeme URL a zahájíme postupné stahování
        with urllib.request.urlopen(url, timeout=10) as response, open(temp_path, "wb") as out_file:
            file_size = int(response.info().get("Content-Length", -1))  # Získáme celkovou velikost souboru
            downloaded = 0
            last_shown_mb = 0  # Pro kontrolu frekvence notifikací

            while True:
                chunk = response.read(block_size)
                if not chunk:
                    break  # Konec souboru

                out_file.write(chunk)
                downloaded += len(chunk)

                # Výpočet zbývajících dat
                remaining_mb = max(0, (file_size - downloaded) / (1024 * 1024))
                total_mb = file_size / (1024 * 1024)
                downloaded_mb = downloaded / (1024 * 1024)

                # Aktualizace notifikace pouze každých 40 MB
                if downloaded_mb - last_shown_mb >= 40:
                    show_notification("Stahování", f"Staženo: {downloaded_mb:.1f} MB / {total_mb:.1f} MB", xbmcgui.NOTIFICATION_INFO)
                    last_shown_mb = downloaded_mb

        # Ověření, že soubor existuje a není prázdný
        if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
            # Přepsání původního souboru novým
            shutil.move(temp_path, local_path)
            show_notification("Stahování dokončeno", "Soubor byl úspěšně aktualizován.", xbmcgui.NOTIFICATION_INFO)
            xbmc.log(f"Soubor {local_path} byl úspěšně aktualizován.", xbmc.LOGINFO)
        else:
            raise ValueError("Stažený soubor je prázdný!")

    except Exception as e:
        # Pokud dojde k chybě (např. výpadek internetu), dočasný soubor odstraníme a přehrajeme lokální soubor
        if os.path.exists(temp_path):
            os.remove(temp_path)

        error_message = f"Nepodařilo se stáhnout soubor: {str(e)}\nPřehrávám lokální soubor."
        show_notification("Chyba", error_message, xbmcgui.NOTIFICATION_ERROR)
        xbmc.log(f"Chyba při stahování: {str(e)}. Přehrávám lokální soubor.", xbmc.LOGERROR)

        # Spustíme přehrávání lokálního souboru
        RepeatVideo()

def RepeatVideo():
    """Spustí přehrávání videa ve smyčce."""
    playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
    playlist.clear()
    playlist.add(local_file)
    xbmc.Player().play(playlist)
    xbmc.executebuiltin("PlayerControl(RepeatOne)")
    show_notification("Přehrávání", "Smyčka byla spuštěna.")

def was_reboot_today():
    """Zjistí, zda už dnes proběhl restart."""
    if os.path.exists(REBOOT_TRACK_FILE):
        with open(REBOOT_TRACK_FILE, "r") as f:
            return f.read().strip() == datetime.now().strftime('%Y-%m-%d')
    return False

def mark_reboot_done():
    """Uloží aktuální datum jako poslední provedený restart."""
    with open(REBOOT_TRACK_FILE, "w") as f:
        f.write(datetime.now().strftime('%Y-%m-%d'))

def schedule_random_reboot():
    """Naplánuje náhodný restart mezi 21:00 a 5:00 v samostatném vlákně, každý den znovu."""

    def reboot_task():
        """Funkce běžící v samostatném vlákně, která plánuje restart."""
        now = datetime.now()

        # Načteme poslední restart a naplánovaný restart ze souboru
        last_reboot_date = "Žádný"
        planned_reboot_date = "Žádný"

        if os.path.exists(REBOOT_TRACK_FILE):
            with open(REBOOT_TRACK_FILE, "r") as f:
                lines = f.readlines()
                if len(lines) >= 2:
                    last_reboot_date = lines[0].strip().replace("Poslední restart: ", "")
                    planned_reboot_date = lines[1].strip().replace("Naplánovaný restart: ", "")

        # Pokud byl plánovaný restart v minulosti, znamená to, že výpadek elektřiny restart přerušil
        if planned_reboot_date != "Žádný":
            planned_time = datetime.strptime(planned_reboot_date, "%Y-%m-%d %H:%M:%S")
            if planned_time < now:
                xbmc.log(f"Detekován neprovedený restart ({planned_reboot_date}), plánování nového restartu.", xbmc.LOGWARNING)
                last_reboot_date = "Neprovedeno"  # Ověříme, že starý restart nebyl proveden

        # Nastavení časového okna mezi 21:00 a 05:00
        start_time = now.replace(hour=21, minute=0, second=0)
        end_time = now.replace(hour=4, minute=59, second=0) + timedelta(days=1)

        # Pokud už je po 05:00, naplánujeme restart na další noc
        if now >= end_time or last_reboot_date == datetime.now().strftime('%Y-%m-%d'):
            start_time += timedelta(days=1)
            end_time += timedelta(days=1)

        # Generování náhodného času mezi 21:00 a 05:00
        while True:
            random_reboot_time = start_time + timedelta(minutes=random.randint(0, int((end_time - start_time).total_seconds() / 60)))
            if random_reboot_time > now:  # Ověříme, že restart není naplánován na aktuální čas
                break

        restart_date_time = random_reboot_time.strftime('%Y-%m-%d %H:%M:%S')

        # Zápis informací do souboru reboot_log.txt
        with open(REBOOT_TRACK_FILE, "w") as f:
            f.write(f"Poslední restart: {last_reboot_date}\nNaplánovaný restart: {restart_date_time}")

        log_message = f"Poslední restart: {last_reboot_date} | Naplánovaný restart: {restart_date_time}"
        xbmc.log(log_message, xbmc.LOGINFO)
        show_notification("Naplánovaný restart", log_message)

        # Čekání na restart
        time.sleep((random_reboot_time - now).total_seconds())
        perform_reboot(restart_date_time)

    threading.Thread(target=reboot_task, daemon=True).start()

def perform_reboot(restart_date_time):
    """Provede restart zařízení a zaznamená ho do souboru."""
    mark_reboot_done()
    xbmc.log("Provádím restart zařízení...", xbmc.LOGINFO)
    show_notification("Restart", f"Zařízení se nyní restartuje ({restart_date_time}).", xbmcgui.NOTIFICATION_WARNING)
    xbmc.executebuiltin("Reboot")

def main():

    try:
        version = xbmcaddon.Addon().getAddonInfo('version')
        with open("/storage/.kodi/userdata/smycky_version.txt", "w") as f:
            f.write(version)
    except Exception as e:
        xbmc.log(f"[Smycky] Chyba při zápisu verze: {e}", xbmc.LOGERROR)
    """Hlavní funkce, která provede aktualizaci, přehrávání a plánování restartu."""
    if is_internet_available():
        show_notification("Aktualizace", "Kontroluji aktualizaci souboru...")
        remote_timestamp, remote_size = get_remote_file_info(remote_url)
        local_timestamp, local_size = get_local_file_info(local_file)

        if remote_timestamp and remote_size and (
            remote_timestamp > local_timestamp or remote_size != local_size
        ):
            if download_file(remote_url, local_file):
                xbmc.log("Soubor úspěšně aktualizován.", xbmc.LOGINFO)
        else:
            show_notification("Aktualizace", "Soubor je aktuální.")
    else:
        show_notification("Offline režim", "Internet není dostupný, přehrávám lokální soubor.", xbmcgui.NOTIFICATION_WARNING)

    RepeatVideo()
    schedule_random_reboot()

# Spustí hlavní funkci
main()