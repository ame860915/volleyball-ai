"""統一錯誤型別。每個錯誤帶有穩定的錯誤代碼，供 CLI、API 與測試判斷。"""

from __future__ import annotations


class VballError(Exception):
    """vball 所有可預期錯誤的基底類別。"""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.message = message


class ProbeError(VballError):
    """讀取影片 metadata 失敗。

    代碼：INPUT_NOT_FOUND、INVALID_VIDEO、FFPROBE_NOT_FOUND、FFPROBE_FAILED
    """
