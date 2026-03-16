"""
屏幕截图模块

使用 mss 高速截图，Pillow 做等比压缩和 JPEG 编码。
所有函数都是同步的，调用方应用 asyncio.to_thread() 包裹，避免阻塞事件循环。

max_width=1280 / quality=75 在视觉清晰度与 Vision API token 消耗之间取得较好平衡。
返回 (base64字符串, 宽, 高) 三元组，宽高供调试和日志使用。
"""
import base64
import io


def capture_screen(
    region: str = "fullscreen",
    max_width: int = 1280,
    quality: int = 75,
) -> tuple[str, int, int]:
    """
    截取屏幕并压缩，返回 (base64字符串, 宽, 高)。

    region 格式：
        "fullscreen"   — 主显示器（monitors[1]）
        "monitor:N"    — 第 N 块显示器（从 1 开始）
    """
    try:
        import mss
        from PIL import Image
    except ImportError as e:
        raise ImportError(f"截图依赖缺失，请运行: pip install mss Pillow\n原始错误: {e}")

    with mss.mss() as sct:
        monitor = _resolve_monitor(sct, region)
        screenshot = sct.grab(monitor)
        # mss 输出 BGRA 格式，转为 RGB
        img = Image.frombytes(
            "RGB",
            (screenshot.width, screenshot.height),
            screenshot.bgra,
            "raw",
            "BGRX",
        )

    # 等比缩放（只在超出 max_width 时才缩，避免无谓的质量损失）
    if img.width > max_width:
        ratio = max_width / img.width
        img = img.resize((max_width, int(img.height * ratio)), Image.LANCZOS)

    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=quality)
    b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return b64, img.width, img.height


def list_monitors() -> list[dict]:
    """枚举系统所有显示器，供设置界面「截图区域」下拉框使用。"""
    try:
        import mss
    except ImportError:
        return []

    with mss.mss() as sct:
        return [
            {
                "index": i,
                "width": m["width"],
                "height": m["height"],
                "label": f"显示器 {i}（{m['width']}×{m['height']}）",
            }
            for i, m in enumerate(sct.monitors)
            if i > 0  # index=0 是所有屏幕拼合，通常不需要
        ]


def _resolve_monitor(sct, region: str) -> dict:
    """将 region 字符串解析为 mss 的 monitor 字典。"""
    monitors = sct.monitors
    default = monitors[1] if len(monitors) > 1 else monitors[0]
    if not region or region == "fullscreen":
        return default
    if region.startswith("monitor:"):
        try:
            idx = int(region.split(":")[1])
            return monitors[idx] if 0 < idx < len(monitors) else default
        except (ValueError, IndexError):
            pass
    return default