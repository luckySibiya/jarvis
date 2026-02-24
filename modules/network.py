"""Network scanning and device discovery — see what's on your WiFi.

Uses macOS tools (arp, dns-sd) to discover devices on the local network.
"""

import subprocess
import re
import socket

from core.command_router import register
from utils.logger import get_logger

logger = get_logger(__name__)


def _run(cmd: str, timeout: int = 10) -> str:
    """Run a shell command and return stdout."""
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True, timeout=timeout,
    )
    return result.stdout.strip()


# Common MAC address prefixes (OUI) for device identification
_OUI_HINTS = {
    "apple": ["00:1a:2b", "3c:e0:72", "a4:83:e7", "f0:18:98", "ac:de:48",
              "14:7d:da", "78:7b:8a", "d0:81:7a", "f8:ff:c2", "b8:f6:b1"],
    "samsung": ["00:07:ab", "00:12:fb", "00:16:32", "00:1a:8a", "00:21:19",
                "00:26:37", "08:08:c2", "34:23:ba", "50:01:bb", "54:92:be"],
    "google": ["3c:5a:b4", "54:60:09", "f4:f5:d8", "a4:77:33"],
    "amazon": ["00:fc:8b", "10:2c:6b", "38:f7:3d", "44:65:0d", "68:54:fd"],
    "lg": ["00:1c:62", "00:1e:75", "00:22:a9", "00:26:e2", "10:68:3f"],
    "sony": ["00:13:a9", "00:1a:80", "00:1d:ba", "00:24:be", "04:5d:4b"],
}


def _guess_device_type(hostname: str, mac: str) -> str:
    """Guess device type from hostname and MAC address."""
    h = hostname.lower() if hostname else ""
    m = mac.lower()[:8] if mac else ""

    # Check hostname patterns
    if any(x in h for x in ["iphone", "ipad", "ipod"]):
        return "iPhone/iPad"
    if any(x in h for x in ["macbook", "imac", "mac-", "mac."]):
        return "Mac"
    if any(x in h for x in ["apple-tv", "appletv"]):
        return "Apple TV"
    if any(x in h for x in ["galaxy", "samsung", "sm-"]):
        return "Samsung Phone"
    if any(x in h for x in ["android", "pixel", "oneplus", "huawei", "xiaomi"]):
        return "Android Phone"
    if any(x in h for x in ["tv", "roku", "firestick", "chromecast"]):
        return "Smart TV/Streaming"
    if any(x in h for x in ["echo", "alexa", "homepod", "google-home"]):
        return "Smart Speaker"
    if any(x in h for x in ["printer", "epson", "hp-", "canon", "brother"]):
        return "Printer"
    if any(x in h for x in ["playstation", "ps4", "ps5", "xbox", "nintendo", "switch"]):
        return "Game Console"

    # Check MAC OUI
    for brand, prefixes in _OUI_HINTS.items():
        if any(m.startswith(p.lower()) for p in prefixes):
            return f"{brand.title()} Device"

    return "Unknown"


@register("network", "scan")
def scan_network() -> str:
    """Scan the local network for all connected devices."""
    try:
        # Get local IP and subnet
        local_ip = socket.gethostbyname(socket.gethostname())

        # Use arp -a to list all devices on the network
        arp_output = _run("arp -a")
        if not arp_output:
            return "Could not scan the network. No devices found."

        devices = []
        for line in arp_output.split("\n"):
            # Parse: hostname (IP) at MAC on interface [...]
            match = re.match(
                r"(\S+)\s+\((\d+\.\d+\.\d+\.\d+)\)\s+at\s+(\S+)", line
            )
            if match:
                hostname = match.group(1)
                ip = match.group(2)
                mac = match.group(3)

                if mac == "(incomplete)" or mac == "ff:ff:ff:ff:ff:ff":
                    continue

                device_type = _guess_device_type(hostname, mac)

                # Clean hostname
                name = hostname if hostname != "?" else "Unknown"

                devices.append({
                    "name": name, "ip": ip, "mac": mac, "type": device_type,
                })

        if not devices:
            return "No devices found on the network."

        lines = [f"Found {len(devices)} device(s) on your network:"]
        for i, d in enumerate(devices, 1):
            lines.append(
                f"  {i}. {d['name']} ({d['type']}) — {d['ip']}"
            )

        # Speak a summary, not the full list
        spoken = f"I found {len(devices)} devices on your network, sir."
        if len(devices) <= 5:
            for d in devices:
                spoken += f" {d['name']}, a {d['type']}."

        # Print the full list, return the spoken version
        print("\n".join(lines))
        return spoken

    except Exception as e:
        logger.error(f"Network scan error: {e}")
        return f"Could not scan the network: {e}"


@register("network", "who_is_connected")
def who_is_connected() -> str:
    """List devices connected to the current WiFi network with identification."""
    return scan_network()


@register("network", "device_count")
def device_count() -> str:
    """Count how many devices are on the network."""
    try:
        arp_output = _run("arp -a")
        count = 0
        for line in arp_output.split("\n"):
            match = re.match(
                r"\S+\s+\(\d+\.\d+\.\d+\.\d+\)\s+at\s+(\S+)", line
            )
            if match and match.group(1) not in ("(incomplete)", "ff:ff:ff:ff:ff:ff"):
                count += 1
        return f"There are {count} devices connected to your network, sir."
    except Exception as e:
        logger.error(f"Device count error: {e}")
        return f"Could not count devices: {e}"


@register("network", "ping")
def ping_device(target: str = "") -> str:
    """Ping a device or address to check if it's online."""
    if not target:
        return "What device or IP address should I ping, sir?"
    try:
        result = subprocess.run(
            ["ping", "-c", "3", "-W", "2", target],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode == 0:
            # Extract average time
            match = re.search(r"avg.*?=\s*[\d.]+/([\d.]+)/", result.stdout)
            avg = match.group(1) if match else "unknown"
            return f"{target} is online. Average response time: {avg} ms."
        else:
            return f"{target} is not responding. It may be offline or blocking pings."
    except subprocess.TimeoutExpired:
        return f"{target} did not respond within the timeout."
    except Exception as e:
        logger.error(f"Ping error: {e}")
        return f"Could not ping {target}: {e}"


@register("network", "speed_test")
def speed_test() -> str:
    """Run a basic network speed test."""
    try:
        # Simple download speed test using a known file
        import time
        import requests
        from config import REQUEST_TIMEOUT

        url = "http://speedtest.ftp.otenet.gr/files/test1Mb.db"
        start = time.time()
        resp = requests.get(url, timeout=30)
        elapsed = time.time() - start
        size_mb = len(resp.content) / (1024 * 1024)
        speed = size_mb / elapsed

        return (
            f"Download speed: approximately {speed:.1f} MB/s "
            f"({speed * 8:.1f} Mbps), sir."
        )
    except Exception as e:
        logger.error(f"Speed test error: {e}")
        return f"Could not run speed test: {e}"


@register("network", "local_ip")
def get_local_ip() -> str:
    """Get the local IP address on the current network."""
    try:
        # More reliable than socket.gethostbyname
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return f"Your local IP address is {ip}, sir."
    except Exception as e:
        logger.error(f"Local IP error: {e}")
        return f"Could not determine local IP: {e}"
