import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs
import os
import json
import socket
import threading
import time
import urllib.request

# Cesta ke konfiguračnímu souboru doplňku
PROFILE_DIR = xbmcvfs.translatePath(xbmcaddon.Addon().getAddonInfo('profile'))
CONFIG_FILE = os.path.join(PROFILE_DIR, 'config.json')

# Globální příznak pro zastavení smyčky monitoringu
stop_monitoring = False

# Získá čas posledního restartu ze systémového uptime
def get_boot_time():
    try:
        with open("/proc/uptime", "r") as f:
            uptime_seconds = float(f.readline().split()[0])
            boot_timestamp = time.time() - uptime_seconds
            return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(boot_timestamp))
    except:
        return None

# Načtení verze doplňku pro aktualizaci         
def get_smycky_version():
    try:
        with open("/storage/.kodi/userdata/smycky_version.txt", "r") as f:
            return f.read().strip()
    except:
        return None

# Načtení plánovaného restartu ze souboru
def get_next_reboot():
    reboot_log_path = "/storage/.kodi/userdata/reboot_log.txt"
    if not os.path.exists(reboot_log_path):
        return None
    try:
        with open(reboot_log_path, "r") as f:
            lines = f.readlines()
            for line in lines:
                if line.lower().startswith("naplánovaný restart"):
                    return line.split(":", 1)[-1].strip()
    except:
        return None

# Odeslání dat na API ve formátu JSON
def send_data(payload, url):
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'}, method="POST")
        with urllib.request.urlopen(req) as response:
            xbmc.log(f"[Dohled] Odesláno na API, status: {response.status}", xbmc.LOGINFO)
    except Exception as e:
        xbmc.log(f"[Dohled] Chyba při odesílání dat: {e}", xbmc.LOGERROR)

# Smyčka monitorující stav zařízení
def monitor_loop():
    config = load_config()
    while not stop_monitoring:
        try:
            name = config.get("name")
            locality = config.get("locality")

            # Zjistění IP adresy
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip_address = s.getsockname()[0]
            s.close()

            # Zjistění času posledního restartu
            boot_time = get_boot_time()

            # Informace o videosouboru
            video_path = "/storage/videos/Oresi_CZ.mp4"
            if os.path.exists(video_path):
                stat = os.stat(video_path)
                last_modified = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime))
                file_size = stat.st_size
            else:
                last_modified = None
                file_size = None

            # Zjištění plánovaného restartu
            next_reboot = get_next_reboot()

            # Stav přehrávání a název souboru
            player = xbmc.Player()
            is_playing = player.isPlayingVideo()
            playing_file = player.getPlayingFile() if is_playing else None

            # Detekce pauzy
            is_paused = xbmc.getCondVisibility("Player.Paused")
            
            # Získání verze doplňku z addon.xml
            ADDON_VERSION = xbmcaddon.Addon().getAddonInfo('version')

            # Záznam do kodi.log pro ladění
            xbmc.log(f"[Dohled] isPlaying: {is_playing}, Paused: {is_paused}, File: {playing_file}", xbmc.LOGINFO)

            # JSON data pro odeslání
            payload = {
                "name": name,
                "ip_address": ip_address,
                "last_modified": last_modified,
                "file_size": file_size,
                "boot_time": boot_time,
                "next_reboot": next_reboot,
                "locality": locality,
                "playing": is_playing,
                "playing_file": playing_file,
                "paused": is_paused,
                "addon_version": ADDON_VERSION,
                "smycky_version": get_smycky_version()
            }

            url = "https://apidohled.noreason.eu/api/monitoring"
            send_data(payload, url)

        except Exception as e:
            xbmc.log(f"[Dohled] Chyba v monitoringu: {e}", xbmc.LOGERROR)

        # Pauza mezi iteracemi smyčky (1 minuta)
        for _ in range(60):
            if stop_monitoring:
                break
            time.sleep(1)

# Při prvním spuštění se zeptá na jméno a lokalitu a uloží je
def prompt_for_config():
    global stop_monitoring
    stop_monitoring = True
    time.sleep(1)

    xbmcvfs.mkdirs(os.path.dirname(CONFIG_FILE))
    name = xbmcgui.Dialog().input("Zadejte název zařízení", type=xbmcgui.INPUT_ALPHANUM)
    locality = xbmcgui.Dialog().input("Zadejte lokalitu zařízení", type=xbmcgui.INPUT_ALPHANUM)

    config = {
        "configured": True,
        "name": name,
        "locality": locality
    }

    with xbmcvfs.File(CONFIG_FILE, 'w') as f:
        f.write(json.dumps(config, indent=4))

    with open("/storage/.cache/hostname", "w") as f:
        f.write(name + "\n")

    xbmcgui.Dialog().notification("Dohled", "Název a lokalita uloženy. Restart...", xbmcgui.NOTIFICATION_INFO, 3000)
    xbmc.sleep(3000)
    os.system("reboot")

# Načtení konfigurace ze souboru
def load_config():
    try:
        with xbmcvfs.File(CONFIG_FILE) as f:
            return json.loads(f.read())
    except:
        return {"configured": False}

# Hlavní spouštění doplňku
def main():
    config = load_config()
    if not config.get("configured", False):
        prompt_for_config()
    else:
        xbmc.log(f"[Dohled] Zařízení: {config.get('name')}", xbmc.LOGINFO)

    threading.Thread(target=monitor_loop, daemon=True).start()

# Start skriptu
if __name__ == "__main__":
    main()