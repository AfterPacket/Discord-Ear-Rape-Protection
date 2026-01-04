🎧 Discord Ear-Rape Protection

Protect your ears from sudden, sustained loud noises in Discord. This utility monitors Discord's actual audio output and automatically throttles the application's volume when it detects "ear-rape" levels of sound.
✨ Features

    Real-time Monitoring: Tracks Discord's audio peak levels using Windows Core Audio APIs.

    Automatic Volume Limiting: Drops Discord's volume to a safe level (default 20%) when a threshold is breached.

    Intelligent Recovery: Smoothly restores volume once the loud noise subsides or after a set recovery period.

    Incident Logging: Automatically logs the date, time, and intensity of detected incidents to earrape_incidents.log.

    Auto-Update System: Integrated version checking with MD5 checksum verification for security.

    Configurable: Customize thresholds, reduction levels, and recovery times via config.json.

🚀 Installation
Option 1: Executable (Recommended)

    Download the latest DiscordEarRapeProtection.exe from the Releases page.

    Run the executable. It will automatically create a config.json and a log file in the same directory.

Option 2: Run from Source

Ensure you have Python 3.8+ installed.

    Install dependencies:
    Bash

pip install numpy pyaudio pycaw comtypes

Run the script:
Bash

    python main.py

⚙️ Configuration

On the first run, a config.json file will be created. You can modify these values to suit your needs:
Key	Default	Description
THRESHOLD	0.85	The peak audio level (0.0 to 1.0) that triggers the limiter.
REDUCTION	0.2	The volume level Discord will be set to during an incident.
RECOVERY_TIME	5.0	How many seconds to stay quiet before attempting to restore volume.
DEFAULT_VOLUME	1.0	Your standard Discord volume level (1.0 = 100%).
PEAK_WINDOW	10	Number of samples to average (higher = fewer false positives).
🛡️ Security & Updates

The application includes a built-in update mechanism that ensures you are always protected by the latest logic:

    Check: Queries afterpacket.pro for the latest version.

    Verify: Downloads the update and performs an MD5 Checksum validation to ensure the file hasn't been tampered with.

    Backup: Creates a .backup of your current version before applying changes.

📝 Usage Notes

    Detection: This tool monitors the output of Discord. This means it catches loud noises from any user in your voice channel.

    Identification: When the volume drops, immediately check your Discord window to see which user's avatar is lighting up to identify the offender!

    Permissions: On some systems, you may need to run the application as Administrator to allow it to modify the volume of other processes via pycaw.

🛠️ Contributing

Feel free to open issues or submit pull requests. For major changes, please open an issue first to discuss what you would like to change.

License: MIT
