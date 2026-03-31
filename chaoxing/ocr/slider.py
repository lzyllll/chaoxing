from __future__ import annotations

import base64
import threading

import ddddocr
import requests

_OCR_LOCK = threading.Lock()
_SLIDER_OCR: ddddocr.DdddOcr | None = None

_IMAGE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


def _get_slider_ocr() -> ddddocr.DdddOcr:
    global _SLIDER_OCR
    with _OCR_LOCK:
        if _SLIDER_OCR is None:
            _SLIDER_OCR = ddddocr.DdddOcr(det=False, ocr=False, show_ad=False)
        return _SLIDER_OCR


def _load_image_bytes(source: str) -> bytes:
    if source.startswith("data:"):
        _, encoded = source.split(",", 1)
        return base64.b64decode(encoded)

    response = requests.get(source, headers=_IMAGE_HEADERS, timeout=10)
    response.raise_for_status()
    return response.content


def get_slider_distance(background_url: str, target_url: str) -> int:
    """
    使用 ddddocr 计算滑块验证码缺口的 x 坐标。
    """

    background_bytes = _load_image_bytes(background_url)
    target_bytes = _load_image_bytes(target_url)
    result = _get_slider_ocr().slide_match(target_bytes, background_bytes, simple_target=True)
    if result and "target" in result:
        return int(result["target"][0])
    return 0

