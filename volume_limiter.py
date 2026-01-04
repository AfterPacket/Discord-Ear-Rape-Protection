import json
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
import warnings
import hashlib
from ctypes import POINTER, cast
from datetime import datetime

import numpy as np
import pyaudio
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioMeterInformation, ISimpleAudioVolume

warnings.filterwarnings("ignore")

# Version info
VERSION = "1.0.4"
UPDATE_CHECK_URL = "https://afterpacket.pro/Software/EarProtect/version.json"
UPDATE_CHECK_TIMEOUT = 5  # seconds
CONFIG_FILE = "config.json"


def calculate_md5(file_path):
    """Calculate MD5 checksum of a file"""
    md5_hash = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                md5_hash.update(chunk)
        return md5_hash.hexdigest()
    except Exception as e:
        print(f"⚠️  Error calculating MD5: {e}")
        return None


def verify_checksum(file_path, expected_md5):
    """Verify file against expected MD5 checksum"""
    if not expected_md5:
        print("⚠️  No checksum provided, skipping verification")
        return True

    print(f"🔐 Verifying file integrity...")
    actual_md5 = calculate_md5(file_path)

    if not actual_md5:
        return False

    if actual_md5.lower() == expected_md5.lower():
        print(f"✅ Checksum verified: {actual_md5}")
        return True
    else:
        print(f"❌ CHECKSUM MISMATCH!")
        print(f"   Expected: {expected_md5}")
        print(f"   Got:      {actual_md5}")
        print(f"⚠️  File may be corrupted or tampered with!")
        return False


def download_update(download_url, version, expected_md5=None):
    """Download the new version"""
    try:
        print(f"\n⬇️  Downloading version {version}...")
        if not os.path.exists("updates"):
            os.makedirs("updates")
        file_extension = ".exe" if download_url.endswith(".exe") else ".py"
        temp_file = f"updates/volume_limiter_v{version}{file_extension}"

        req = urllib.request.Request(
            download_url, headers={"User-Agent": f"DiscordVolumeLimiter/{VERSION}"}
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            total_size = int(response.headers.get("content-length", 0))
            downloaded = 0
            chunk_size = 8192

            with open(temp_file, "wb") as f:
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        bar_length = 30
                        filled = int(bar_length * downloaded / total_size)
                        bar = "█" * filled + "░" * (bar_length - filled)
                        print(f"\r   Progress: [{bar}] {percent:.1f}%", end="")

        print(f"\n✅ Download complete!")

        # Verify checksum if provided
        if expected_md5:
            if not verify_checksum(temp_file, expected_md5):
                print(f"❌ Checksum verification failed!")
                response = input("Continue anyway? (NOT RECOMMENDED) (y/n): ").lower().strip()
                if response not in ["y", "yes"]:
                    os.remove(temp_file)
                    print("❌ Download deleted for safety")
                    return None
                print("⚠️  Proceeding at your own risk...")

        return temp_file
    except Exception as e:
        print(f"\n❌ Download failed: {e}")
        return None


def install_update(temp_file, is_executable):
    """Install the downloaded update"""
    try:
        if is_executable:
            current_file = os.path.abspath(sys.argv[0])
            backup_file = current_file + ".backup"

            # Create backup
            if os.path.exists(current_file):
                shutil.copy2(current_file, backup_file)
                print(f"   Backup created: {backup_file}")

            # Create a batch script to handle the update
            batch_script = os.path.join(os.path.dirname(current_file), "update_install.bat")
            with open(batch_script, "w") as f:
                f.write("@echo off\n")
                f.write("echo Waiting for application to close...\n")
                f.write("timeout /t 2 /nobreak >nul\n")
                f.write(f'copy /Y "{temp_file}" "{current_file}"\n')
                f.write("echo Update installed!\n")
                f.write(f'start "" "{current_file}"\n')
                f.write(f'del "{batch_script}"\n')

            print(f"✅ Update prepared!\n🔄 Restarting application...")

            # Start the batch script and exit immediately
            subprocess.Popen(batch_script, shell=True,
                           creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            time.sleep(0.5)
            sys.exit(0)
        else:
            current_file = os.path.abspath(__file__)
            backup_file = current_file + ".backup"
            shutil.copy2(current_file, backup_file)
            print(f"   Backup created: {backup_file}")
            shutil.copy2(temp_file, current_file)
            print(f"✅ Update installed successfully!\n🔄 Restarting application...")
            os.execv(sys.executable, [sys.executable] + sys.argv)
    except Exception as e:
        print(f"\n❌ Installation failed: {e}")
        print("   You can manually install from the updates folder")
        return False
    return True


def check_for_updates():
    """Check if a newer version is available and offer to download"""
    try:
        req = urllib.request.Request(
            UPDATE_CHECK_URL, headers={"User-Agent": f"DiscordVolumeLimiter/{VERSION}"}
        )
        with urllib.request.urlopen(req, timeout=UPDATE_CHECK_TIMEOUT) as response:
            data = json.loads(response.read().decode())
            latest_version = data.get("version", VERSION)
            download_url = data.get("download_url", "")
            changelog = data.get("changelog", "")
            md5_checksum = data.get("md5_checksum", "")  # Get MD5 from version.json

            if latest_version != VERSION:
                print("\n" + "🔔" * 35)
                print(f"📢 UPDATE AVAILABLE!")
                print(f"   Current Version: {VERSION}")
                print(f"   Latest Version:  {latest_version}")
                if md5_checksum:
                    print(f"   MD5 Checksum:    {md5_checksum}")
                if changelog:
                    print(f"\n   What's New:")
                    for line in changelog.split("\n"):
                        if line.strip():
                            print(f"   {line}")
                print("🔔" * 35 + "\n")
                if download_url:
                    response = input(
                        "Would you like to download and install this update now? (y/n): "
                    ).lower().strip()
                    if response in ["y", "yes"]:
                        temp_file = download_update(download_url, latest_version, md5_checksum)
                        if temp_file:
                            is_executable = temp_file.endswith(".exe")
                            print(f"\n📦 Update downloaded to: {temp_file}")
                            install_response = input(
                                "Install now? This will restart the application. (y/n): "
                            ).lower().strip()
                            if install_response in ["y", "yes"]:
                                install_update(temp_file, is_executable)
                            else:
                                print(
                                    f"✅ Update saved. You can install it manually later from '{temp_file}'"
                                )
                    else:
                        print("Update skipped. You can download it later from:")
                        print(f"   {download_url}\n")
                else:
                    print("⚠️  No download URL provided\n")
                return True
            else:
                print(f"✅ You're running the latest version ({VERSION})\n")
                return False
    except Exception as e:
        print(f"⚠️  Update check failed: {e}")
        return False


class DiscordOutputLimiter:
    def __init__(self):
        # Load config if exists
        self.load_config()

        self.is_running = False
        self.is_limiting = False
        self.peak_history = []

        # Logging setup
        self.log_file = "earrape_incidents.log"
        self.init_log_file()

    def load_config(self):
        """Load settings from JSON config"""
        defaults = {
            "THRESHOLD": 0.85,
            "REDUCTION": 0.2,
            "RECOVERY_TIME": 5.0,
            "DEFAULT_VOLUME": 1.0,
            "PEAK_WINDOW": 10
        }
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    cfg = json.load(f)
                    for key in defaults:
                        setattr(self, key, cfg.get(key, defaults[key]))
            except Exception as e:
                print(f"⚠️ Failed to load config.json, using defaults ({e})")
                for key in defaults:
                    setattr(self, key, defaults[key])
        else:
            for key in defaults:
                setattr(self, key, defaults[key])
            # Create a default config
            with open(CONFIG_FILE, "w") as f:
                json.dump(defaults, f, indent=4)

    def init_log_file(self):
        """Initialize log file with header if it doesn't exist"""
        if not os.path.exists(self.log_file):
            with open(self.log_file, "w") as f:
                f.write("=" * 80 + "\n")
                f.write("Discord Ear-Rape Detection Log\n")
                f.write("=" * 80 + "\n\n")

    def log_incident(self, peak_level, avg_peak):
        """Log an ear-rape incident with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.log_file, "a") as f:
            f.write(f"[{timestamp}] EAR-RAPE DETECTED!\n")
            f.write(f"  - Peak Level: {int(peak_level * 100)}%\n")
            f.write(f"  - Average Peak: {int(avg_peak * 100)}%\n")
            f.write(
                f"  - Action: Reduced Discord volume to {int(self.REDUCTION * 100)}%\n"
            )
            f.write(f"  ⚠️  CHECK DISCORD NOW to see who is speaking!\n")
            f.write("-" * 80 + "\n\n")

    def get_discord_session(self):
        """Robustly detect Discord session with improved error handling"""
        try:
            sessions = AudioUtilities.GetAllSessions()
            discord_variants = ["discord.exe", "discordptb.exe", "discordcanary.exe",
                              "discord", "discordptb", "discordcanary"]

            for session in sessions:
                if session.Process:
                    try:
                        process_name = session.Process.name()
                        if process_name:
                            name_lower = process_name.lower()
                            # Check if any Discord variant matches
                            if any(variant in name_lower for variant in discord_variants):
                                return session
                    except (AttributeError, OSError) as e:
                        # Process may have terminated, skip it
                        continue
                    except Exception as e:
                        # Log unexpected errors but continue searching
                        continue
        except Exception as e:
            print(f"❌ Error getting audio sessions: {e}")

        return None

    def get_discord_peak_level(self, session):
        """Get Discord's audio output peak level"""
        try:
            meter = session._ctl.QueryInterface(IAudioMeterInformation)
            return meter.GetPeakValue()
        except Exception:
            return 0.0

    def monitor_discord_output(self):
        """Monitor Discord's actual audio output with improved session detection"""
        print("\n" + "=" * 70)
        print("🎮 Discord Output Monitor & Limiter")
        print("=" * 70)
        print(f"\n📊 Trigger Threshold: {int(self.THRESHOLD * 100)}% peak")
        print(f"📉 Will reduce to: {int(self.REDUCTION * 100)}%")
        print(f"🔊 Default volume: {int(self.DEFAULT_VOLUME * 100)}%")
        print(f"⏱️  Must sustain {self.PEAK_WINDOW / 10:.1f}s to trigger")
        print(f"📝 Logging incidents to: {self.log_file}")
        print("\n💡 Monitoring Discord's AUDIO OUTPUT (what you hear)")
        print("⚠️  When ear-rape is detected, check Discord to see who's speaking!")
        print("=" * 70 + "\n")

        # Wait for Discord session with retry logic
        session = None
        retry_count = 0
        max_retries = 30  # 60 seconds total (30 * 2s)

        print("🔍 Searching for Discord process...")
        print("   Make sure Discord is running and playing audio!")

        self.is_running = True

        while not session and retry_count < max_retries:
            try:
                session = self.get_discord_session()
                if session:
                    print("✅ Discord session detected and locked!")
                    # Initialize volume
                    vol_iface = session._ctl.QueryInterface(ISimpleAudioVolume)
                    vol_iface.SetMasterVolume(self.DEFAULT_VOLUME, None)
                    break

                retry_count += 1
                elapsed = retry_count * 2
                print(f"⏳ Waiting for Discord... ({elapsed}s elapsed)                     ", end="\r")
                time.sleep(2)

            except KeyboardInterrupt:
                print("\n❌ Cancelled by user")
                self.is_running = False
                return
            except Exception as e:
                print(f"\n⚠️  Error during detection: {e}")
                time.sleep(2)

        if not session:
            print("\n❌ Could not find Discord after 60 seconds.")
            print("   Please ensure:")
            print("   • Discord is running")
            print("   • You're in a voice channel or playing audio")
            print("   • Discord is not muted in Windows Volume Mixer")
            self.is_running = False
            return

        # Start monitoring loop with session recovery
        last_session_check = time.time()
        SESSION_CHECK_INTERVAL = 5  # Re-verify session every 5 seconds

        while self.is_running:
            try:
                # Periodically re-check if Discord session is still valid
                if time.time() - last_session_check > SESSION_CHECK_INTERVAL:
                    test_session = self.get_discord_session()
                    if not test_session:
                        print("\n⚠️  Discord session lost! Reconnecting...")
                        session = None
                        while not session and self.is_running:
                            session = self.get_discord_session()
                            if session:
                                print("✅ Reconnected to Discord!")
                                vol_iface = session._ctl.QueryInterface(ISimpleAudioVolume)
                                vol_iface.SetMasterVolume(self.DEFAULT_VOLUME, None)
                                break
                            time.sleep(2)
                    else:
                        session = test_session
                    last_session_check = time.time()

                if not session:
                    time.sleep(1)
                    continue

                peak_level = self.get_discord_peak_level(session)
                self.peak_history.append(peak_level)
                if len(self.peak_history) > self.PEAK_WINDOW:
                    self.peak_history.pop(0)

                vol_iface = session._ctl.QueryInterface(ISimpleAudioVolume)
                current_volume = vol_iface.GetMasterVolume()

                if len(self.peak_history) >= self.PEAK_WINDOW:
                    avg_peak = np.mean(self.peak_history)
                    max_peak = max(self.peak_history)
                    if avg_peak > self.THRESHOLD and not self.is_limiting:
                        self.is_limiting = True
                        vol_iface.SetMasterVolume(self.REDUCTION, None)
                        self.log_incident(max_peak, avg_peak)
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        print(
                            f"\n🔇 [{timestamp}] EAR-RAPE DETECTED! Discord reduced to {int(self.REDUCTION*100)}%"
                        )
                        threading.Thread(target=self.restore_after_delay, daemon=True).start()
                    elif avg_peak <= self.THRESHOLD * 0.7 and self.is_limiting:
                        self.restore_volume_now()

                # Visual display
                status = "🔴 LIMITING" if self.is_limiting else "🟢 MONITORING"
                peak_bar = "█" * int(peak_level * 30)
                peak_pct = int(peak_level * 100)
                vol_bar = "█" * int(current_volume * 20)
                vol_pct = int(current_volume * 100)
                if peak_level > 0.85:
                    indicator = "🔴 VERY LOUD"
                elif peak_level > 0.6:
                    indicator = "🟡 LOUD"
                elif peak_level > 0.2:
                    indicator = "🟢 ACTIVE"
                else:
                    indicator = "🔵 QUIET"

                print(
                    f"{status} | Peak:[{peak_bar:<30}]{peak_pct:3d}% | Vol:[{vol_bar:<20}]{vol_pct:3d}% | {indicator}    ",
                    end="\r",
                )

            except Exception as e:
                # Log errors but keep trying
                time.sleep(1)

            time.sleep(0.1)

    def restore_after_delay(self):
        time.sleep(self.RECOVERY_TIME)
        self.restore_volume_now()

    def restore_volume_now(self):
        if not self.is_limiting:
            return
        session = self.get_discord_session()
        if session:
            try:
                vol_iface = session._ctl.QueryInterface(ISimpleAudioVolume)
                current = vol_iface.GetMasterVolume()
                target = self.DEFAULT_VOLUME
                steps = 20
                step_size = (target - current) / steps
                for _ in range(steps):
                    if not self.is_running:
                        break
                    current += step_size
                    vol_iface.SetMasterVolume(min(current, 1.0), None)
                    time.sleep(0.05)
                print(f"\n🔊 RESTORED: Discord back to {int(target*100)}%                    ")
            except Exception:
                pass
        self.is_limiting = False
        self.peak_history.clear()

    def start(self):
        if self.is_running:
            print("⚠️ Already running!")
            return
        self.is_running = True
        try:
            self.monitor_discord_output()
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        self.is_running = False
        session = self.get_discord_session()
        if session and self.is_limiting:
            try:
                vol_iface = session._ctl.QueryInterface(ISimpleAudioVolume)
                vol_iface.SetMasterVolume(self.DEFAULT_VOLUME, None)
            except Exception:
                pass
        print("\n\n❌ Stopped")


if __name__ == "__main__":
    print("=" * 70)
    print("🎧 Discord Ear-Rape Protection")
    print(f"   Version {VERSION}")
    print("=" * 70)
    print("\nThis monitors Discord's AUDIO OUTPUT and limits volume")
    print("when someone is ear-raping (sustained loud audio)")
    print("\n⚠️  IMPORTANT: When ear-rape is detected, immediately check Discord")
    print("   to see who is speaking and manually note their username/ID!")
    print("   All incidents are logged to 'earrape_incidents.log'\n")

    print("🔍 Checking for updates...")
    check_for_updates()

    limiter = DiscordOutputLimiter()
    try:
        limiter.start()
    except KeyboardInterrupt:
        limiter.stop()
