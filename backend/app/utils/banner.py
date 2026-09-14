from app.config.path_conf import BANNER_FILE


def worship() -> str:
    """读取启动 Banner（优先 `banner.txt`）。

    返回:
    - str: banner 文本。
    """
    if BANNER_FILE.exists():
        return BANNER_FILE.read_text(encoding="utf-8")
    return ""
