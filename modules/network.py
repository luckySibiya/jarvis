"""Network scanning and device discovery — see what's on your WiFi.

Uses macOS tools (arp, networksetup) and MAC address OUI lookups to discover
and identify devices on the local network.
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


def _get_local_ip() -> str:
    """Get our own local IP."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return ""


def _get_gateway_ip() -> str:
    """Get the default gateway IP."""
    try:
        output = _run("route -n get default 2>/dev/null | grep gateway")
        match = re.search(r"gateway:\s*(\S+)", output)
        return match.group(1) if match else ""
    except Exception:
        return ""


def _lookup_mac_vendor(mac: str) -> str:
    """Look up MAC address vendor using the maclookup API (free, no key).
    Falls back to local OUI table.
    """
    try:
        import requests
        prefix = mac.replace(":", "").upper()[:6]
        resp = requests.get(
            f"https://api.maclookup.app/v2/macs/{prefix}",
            timeout=3,
        )
        if resp.status_code == 200:
            data = resp.json()
            company = data.get("company", "")
            if company:
                return company
    except Exception:
        pass
    return ""


# Local OUI table — covers the most common brands
_OUI_TABLE = {
    # Apple
    "00:1a:2b": "Apple", "3c:e0:72": "Apple", "a4:83:e7": "Apple",
    "f0:18:98": "Apple", "ac:de:48": "Apple", "14:7d:da": "Apple",
    "78:7b:8a": "Apple", "d0:81:7a": "Apple", "f8:ff:c2": "Apple",
    "b8:f6:b1": "Apple", "a8:51:ab": "Apple", "bc:d0:74": "Apple",
    "28:6a:ba": "Apple", "40:b3:95": "Apple", "c8:69:cd": "Apple",
    "dc:a4:ca": "Apple", "e0:b5:5f": "Apple", "f4:5c:89": "Apple",
    "a0:78:17": "Apple", "88:66:a5": "Apple", "1c:91:48": "Apple",
    # Samsung
    "00:07:ab": "Samsung", "34:23:ba": "Samsung", "50:01:bb": "Samsung",
    "54:92:be": "Samsung", "08:08:c2": "Samsung", "cc:07:ab": "Samsung",
    "a8:7c:01": "Samsung", "88:32:9b": "Samsung", "c4:73:1e": "Samsung",
    "e4:7c:f9": "Samsung", "84:25:19": "Samsung", "94:35:0a": "Samsung",
    # Oppo / Realme / OnePlus (BBK group)
    "2c:4d:54": "Oppo", "a4:3b:fa": "Oppo", "88:d5:0c": "Oppo",
    "e8:4e:84": "Oppo", "f8:f1:e6": "Oppo", "74:45:ce": "Oppo",
    "1c:48:f9": "Oppo", "ac:f1:70": "Oppo", "9c:2e:a1": "Oppo",
    "c4:4b:d1": "OnePlus", "94:65:2d": "OnePlus",
    # Huawei / Honor
    "00:e0:fc": "Huawei", "48:46:fb": "Huawei", "70:72:3c": "Huawei",
    "c8:d1:5e": "Huawei", "e4:68:a3": "Huawei", "f4:63:1f": "Huawei",
    "04:4f:4c": "Huawei", "08:63:61": "Huawei", "20:a6:80": "Huawei",
    "24:09:95": "Huawei", "28:31:52": "Huawei", "34:cd:be": "Huawei",
    "5c:c3:07": "Huawei", "b4:cd:27": "Huawei",
    # Xiaomi
    "00:9e:c8": "Xiaomi", "04:cf:8c": "Xiaomi", "0c:1d:af": "Xiaomi",
    "14:f6:5a": "Xiaomi", "28:e3:1f": "Xiaomi", "34:80:b3": "Xiaomi",
    "50:64:2b": "Xiaomi", "64:b4:73": "Xiaomi", "78:11:dc": "Xiaomi",
    "7c:1c:4e": "Xiaomi", "8c:de:52": "Xiaomi", "b0:e2:35": "Xiaomi",
    # Google
    "3c:5a:b4": "Google", "54:60:09": "Google", "f4:f5:d8": "Google",
    "a4:77:33": "Google", "30:fd:38": "Google",
    # Amazon
    "00:fc:8b": "Amazon", "10:2c:6b": "Amazon", "38:f7:3d": "Amazon",
    "44:65:0d": "Amazon", "68:54:fd": "Amazon", "fc:65:de": "Amazon",
    # LG
    "00:1c:62": "LG", "00:1e:75": "LG", "00:22:a9": "LG",
    "10:68:3f": "LG", "20:3d:bd": "LG", "a8:23:fe": "LG",
    # Sony
    "00:13:a9": "Sony", "00:1a:80": "Sony", "00:24:be": "Sony",
    "04:5d:4b": "Sony", "ac:9b:0a": "Sony", "fc:f1:52": "Sony",
    # TP-Link
    "50:c7:bf": "TP-Link", "60:e3:27": "TP-Link", "c0:25:e9": "TP-Link",
    "14:eb:b6": "TP-Link", "30:de:4b": "TP-Link", "ec:08:6b": "TP-Link",
    # Intel (laptops/PCs)
    "00:1b:21": "Intel", "3c:97:0e": "Intel", "8c:8d:28": "Intel",
    "a4:34:d9": "Intel", "f8:63:3f": "Intel",
    # Microsoft (Xbox, Surface)
    "28:18:78": "Microsoft", "7c:1e:52": "Microsoft", "c8:3f:26": "Microsoft",
    # Roku
    "d8:31:34": "Roku", "b0:a7:37": "Roku", "84:ea:ed": "Roku",
    # HP (printers)
    "00:1e:0b": "HP", "3c:d9:2b": "HP", "64:51:06": "HP",
}


def _identify_device(hostname: str, mac: str, ip: str,
                     local_ip: str, gateway_ip: str) -> tuple[str, str]:
    """Identify a device. Returns (type, display_name)."""
    h = (hostname or "").lower()
    mac_prefix = mac.lower()[:8] if mac else ""

    # Is this us?
    if ip == local_ip:
        return "This Mac (you)", socket.gethostname() or "Your Mac"

    # Is this the router/gateway?
    if ip == gateway_ip:
        # Try to get router brand from hostname or MAC
        vendor = _OUI_TABLE.get(mac_prefix, "")
        if not vendor and hostname and hostname != "?":
            # Extract brand from hostname (e.g. "oppowifi.com" → "Oppo")
            for brand in ["oppo", "tp-link", "tplink", "netgear", "asus",
                          "linksys", "dlink", "huawei", "xiaomi", "cisco"]:
                if brand.replace("-", "") in h.replace("-", ""):
                    vendor = brand.title()
                    break
        brand = vendor or "WiFi"
        return f"Router ({brand})", hostname if hostname != "?" else f"{brand} Router"

    # Identify by hostname
    if any(x in h for x in ["iphone", "ipad", "ipod"]):
        name = hostname.replace("-", " ").split(".")[0].title()
        return "iPhone/iPad", name
    if any(x in h for x in ["macbook", "imac", "mac-", "mac.", "macpro"]):
        name = hostname.replace("-", " ").split(".")[0].title()
        return "Mac", name
    if any(x in h for x in ["apple-tv", "appletv"]):
        return "Apple TV", hostname.split(".")[0]
    if any(x in h for x in ["galaxy", "sm-"]):
        return "Samsung Phone", hostname.split(".")[0]
    if any(x in h for x in ["oppo", "realme", "reno"]):
        return "Oppo Phone", hostname.split(".")[0]
    if any(x in h for x in ["huawei", "honor", "p30", "p40", "mate"]):
        return "Huawei Phone", hostname.split(".")[0]
    if any(x in h for x in ["xiaomi", "redmi", "poco"]):
        return "Xiaomi Phone", hostname.split(".")[0]
    if any(x in h for x in ["pixel", "oneplus"]):
        return "Android Phone", hostname.split(".")[0]
    if any(x in h for x in ["android"]):
        return "Android Device", hostname.split(".")[0]
    if any(x in h for x in ["-tv", "smarttv", "roku", "firestick", "chromecast"]):
        return "Smart TV", hostname.split(".")[0]
    if any(x in h for x in ["echo", "alexa", "homepod", "google-home", "nest"]):
        return "Smart Speaker", hostname.split(".")[0]
    if any(x in h for x in ["printer", "epson", "hp-", "canon", "brother"]):
        return "Printer", hostname.split(".")[0]
    if any(x in h for x in ["playstation", "ps4", "ps5", "xbox", "nintendo"]):
        return "Game Console", hostname.split(".")[0]

    # Identify by MAC address vendor
    vendor = _OUI_TABLE.get(mac_prefix, "")
    if not vendor:
        # Try online lookup for unknown MACs
        vendor = _lookup_mac_vendor(mac)

    if vendor:
        vendor_lower = vendor.lower()
        # Guess type from vendor
        if vendor_lower in ("apple",):
            return "Apple Device", f"{vendor} device"
        if vendor_lower in ("samsung",):
            return "Samsung Device", f"{vendor} device"
        if vendor_lower in ("oppo", "realme"):
            return "Oppo/Realme Device", f"{vendor} device"
        if vendor_lower in ("oneplus",):
            return "OnePlus Phone", f"{vendor} device"
        if vendor_lower in ("huawei", "honor"):
            return "Huawei Device", f"{vendor} device"
        if vendor_lower in ("xiaomi", "redmi"):
            return "Xiaomi Device", f"{vendor} device"
        if vendor_lower in ("google",):
            return "Google Device", f"{vendor} device"
        if vendor_lower in ("amazon",):
            return "Amazon Device (Echo/Fire)", f"{vendor} device"
        if vendor_lower in ("roku",):
            return "Roku Streaming", f"{vendor} device"
        if vendor_lower in ("sony",):
            return "Sony Device", f"{vendor} device"
        if vendor_lower in ("lg",):
            return "LG Device", f"{vendor} device"
        if vendor_lower in ("tp-link", "tplink"):
            return "TP-Link Device", f"{vendor} device"
        if vendor_lower in ("intel",):
            return "PC/Laptop (Intel)", f"{vendor} device"
        if vendor_lower in ("microsoft",):
            return "Microsoft Device", f"{vendor} device"
        if vendor_lower in ("hp", "hewlett"):
            return "HP Device/Printer", f"{vendor} device"
        return f"{vendor} Device", f"{vendor} device"

    return "Unknown Device", hostname if hostname != "?" else f"Device ({ip})"


def _is_real_device(ip: str, mac: str) -> bool:
    """Filter out non-device entries (multicast, broadcast, incomplete)."""
    if not mac or mac in ("(incomplete)", "ff:ff:ff:ff:ff:ff"):
        return False
    # Filter multicast (224.x.x.x - 239.x.x.x) and broadcast
    first_octet = int(ip.split(".")[0])
    if first_octet >= 224:
        return False
    return True


@register("network", "scan")
def scan_network() -> str:
    """Scan the local network for all connected devices."""
    try:
        local_ip = _get_local_ip()
        gateway_ip = _get_gateway_ip()

        arp_output = _run("arp -a")
        if not arp_output:
            return "Could not scan the network. No devices found."

        devices = []
        for line in arp_output.split("\n"):
            match = re.match(
                r"(\S+)\s+\((\d+\.\d+\.\d+\.\d+)\)\s+at\s+(\S+)", line
            )
            if not match:
                continue

            hostname = match.group(1)
            ip = match.group(2)
            mac = match.group(3)

            if not _is_real_device(ip, mac):
                continue

            device_type, display_name = _identify_device(
                hostname, mac, ip, local_ip, gateway_ip,
            )

            devices.append({
                "name": display_name,
                "type": device_type,
                "ip": ip,
                "mac": mac,
            })

        if not devices:
            return "No devices found on the network."

        # Print detailed table
        lines = [f"Found {len(devices)} device(s) on your network:"]
        for i, d in enumerate(devices, 1):
            lines.append(
                f"  {i}. {d['name']} — {d['type']} — {d['ip']} ({d['mac']})"
            )
        print("\n".join(lines))

        # Build spoken summary
        spoken_parts = [f"I found {len(devices)} devices on your network, sir."]
        for d in devices[:6]:
            spoken_parts.append(f"{d['name']}, which is a {d['type']}.")
        if len(devices) > 6:
            spoken_parts.append(f"And {len(devices) - 6} more.")

        return " ".join(spoken_parts)

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
                r"\S+\s+\((\d+\.\d+\.\d+\.\d+)\)\s+at\s+(\S+)", line
            )
            if match and _is_real_device(match.group(1), match.group(2)):
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
        import time
        import requests

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
        ip = _get_local_ip()
        if ip:
            return f"Your local IP address is {ip}, sir."
        return "Could not determine your local IP address."
    except Exception as e:
        logger.error(f"Local IP error: {e}")
        return f"Could not determine local IP: {e}"
