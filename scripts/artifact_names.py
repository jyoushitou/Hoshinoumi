"""产物命名（v19.5.7 起统一）

格式：REC-v<major.minor.patch>-<kind>[.ext]

    REC-v19.5.7-src.zip
    REC-v19.5.7-full.zip
    REC-v19.5.7-exe.exe
    REC-v19.5.7-docker.tar.gz
    REC-v19.5.7-bundle.bundle
    REC-v19.5.7-SHA256SUMS.txt

历史 nao-v* / nao-bot-* 产物保留不动，只作为归档，不再由脚本生成。
"""

PREFIX = "REC"


def _ver(version):
    return str(version).strip().lstrip("vV")


def name(version, kind, ext=""):
    return f"{PREFIX}-v{_ver(version)}-{kind}{ext}"


def src(version):
    return name(version, "src", ".zip")


def full(version):
    return name(version, "full", ".zip")


def exe(version, windows=False):
    return name(version, "exe", ".exe" if windows else "")


def docker(version, browser=False):
    return name(version, "docker-browser" if browser else "docker", ".tar.gz")


def bundle(version):
    return name(version, "bundle", ".bundle")


def checksums(version):
    return name(version, "SHA256SUMS", ".txt")
