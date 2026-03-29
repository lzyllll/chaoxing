import ddddocr
import requests

def get_slider_distance(background_url: str, target_url: str) -> int:
    """
    使用 ddddocr 计算滑块验证码的缺口距离
    
    Args:
        background_url (str): 带缺口的背景图 URL
        target_url (str): 滑块图 URL
        
    Returns:
        int: 滑块需要移动的距离
    """
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"
    }

    # 下载背景图
    bg_response = requests.get(background_url, headers=headers)
    bg_response.raise_for_status()
    bg_bytes = bg_response.content
    
    # 下载滑块图
    target_response = requests.get(target_url, headers=headers)
    target_response.raise_for_status()
    target_bytes = target_response.content
    
    # 初始化 ddddocr 滑块识别模块，参数 kwargs 根据需要可选
    det = ddddocr.DdddOcr(det=False, ocr=False, show_ad=False)
    
    # slide_match 返回值是一个字典，包含 target_y 等信息，通常我们要的是 x 方向的偏移量
    # 注意参数位置: target_bytes 是滑块, background_bytes 是带有缺口的背景图
    res = det.slide_match(target_bytes, bg_bytes, simple_target=True)
    
    # res 为 {'target': [x1, y1, x2, y2]} 的形式
    if res and 'target' in res:
        distance = res['target'][0]  # 返回 x 轴方向的移动距离
        return distance
    return 0

