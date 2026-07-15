import subprocess

# Path to Brave
brave_path = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"

# URL to open
url = "https://www.youtube.com"

# Launch Brave with YouTube
subprocess.Popen([brave_path, url])