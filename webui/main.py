import asyncio
import base64
import json
import os
from os import remove

import websockets

from comfyui_client.call_workflow import remove_watermark, extend_image, scale_image


async def check_water_mark_image(payload):
    uri = os.getenv("VLM_MODEL_WS_HOST")
    try:
        async with websockets.connect(uri) as ws:
            print("已连接到MCP服务器")
            await ws.send(json.dumps(payload))
            response = await ws.recv()
            print("来自服务器的响应:")
            print(json.dumps(json.loads(response), indent=2, ensure_ascii=False))
            if json.loads(response).get("water_mark").lower() == "y":
                return True
            return False

    except Exception as e:
        print(f"WebSocket错误: {e}")


from PIL import Image


def calculate_extension(width, height):
    target_ratio_width = 9
    target_ratio_height = 16

    current_ratio = width / height
    target_ratio = target_ratio_width / target_ratio_height

    if abs(current_ratio - target_ratio) < 1e-5:
        return 0, 0, 0, 0

    if width > height:
        # 宽大于高 → 先假设上下扩展
        required_height = width * target_ratio_height // target_ratio_width
        if required_height > height:
            padding = (required_height - height) // 2
            top = padding
            bottom = required_height - height - padding
            left = right = 0
        else:
            # 宽度太大，高度已足够，改为左右扩展宽度
            required_width = height * target_ratio_width // target_ratio_height
            padding = (required_width - width) // 2
            left = padding
            right = required_width - width - padding
            top = bottom = 0

    elif height > width:
        # 高大于宽 → 先假设左右扩展
        required_width = height * target_ratio_width // target_ratio_height
        if required_width > width:
            padding = (required_width - width) // 2
            left = padding
            right = required_width - width - padding
            top = bottom = 0
        else:
            # 高度太大，宽度已足够，改为上下扩展高度
            required_height = width * target_ratio_height // target_ratio_width
            padding = (required_height - height) // 2
            top = padding
            bottom = required_height - height - padding
            left = right = 0

    else:
        # 宽等于高，无需扩展
        left = right = top = bottom = 0

    return left, right, top, bottom


def get_image_size(image_path):
    """
    获取图片的尺寸。

    参数:
        image_path (str): 图片的文件路径。

    返回:
        tuple: (width, height) 表示图片的宽度和高度。
    """
    with Image.open(image_path) as img:
        return img.size


async def process_image(image_path):
    if not image_path or not os.path.exists(image_path):
        print("无效的图片路径")
        return
    width, height = get_image_size(image_path)
    if width < 400:
        print(f"图片宽度 {width} 小于 400，分辨率过低，跳过处理")
        return image_path  # 或根据需求返回 None 或抛出提示
    # 读取图片并转为 base64
    with open(image_path, "rb") as f:
        image_base64 = base64.b64encode(f.read()).decode("utf-8")
    payload = {
        "tool": "image_understanding",
        "image_base64": image_base64,
    }
    if await check_water_mark_image(payload):
        print("检测到水印，正在去水印...")
        image_path = remove_watermark(image_base64)

        # 更新 base64 和尺寸
        with open(image_path, "rb") as f:
            image_base64 = base64.b64encode(f.read()).decode("utf-8")
        width, height = get_image_size(image_path)
    else:
        width, height = get_image_size(image_path)

    left, right, top, bottom = calculate_extension(width, height)
    if left != 0 or right != 0 or top != 0 or bottom != 0:
        print(f"图片需扩图，宽: {width}, 高: {height}, 左: {left}, 右: {right}, 上: {top}, 下: {bottom}")
        image_path = await extend_image(image_base64, left, right, top, bottom)
        width, height = get_image_size(image_path)

    new_width = width + left + right
    new_height = height + top + bottom

    print(f"扩图后尺寸: {new_width}x{new_height}")

    if new_width < 1080 or new_height < 1920:
        print("图片尺寸不足 1080x1920，正在进行放大...")
        # 计算放大倍数 1080/new_width/4（1.5倍放大）
        with open(image_path, "rb") as f:
            image_base64 = base64.b64encode(f.read()).decode("utf-8")
        image_path = await scale_image(image_base64, 0.38)

    print(f"最终输出图片路径: {image_path}")


if __name__ == '__main__':
    image_path = "../doc/test.png"  # 示例路径，请替换为实际路径
    asyncio.run(process_image(image_path))
