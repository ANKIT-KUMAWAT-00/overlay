"""OS Version Guard Utilities."""
import platform

def is_macos_version_supported(min_major: int = 12) -> bool:
    if platform.system() != "Darwin":
        return False
    mac_ver = int(platform.mac_ver()[0].split(".")[0])
    return mac_ver >= min_major
