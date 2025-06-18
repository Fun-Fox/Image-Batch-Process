import json
import os
from os import remove

import websockets

from comfyui_client.call_workflow import remove_watermark, extend_image


async def check_water_mark_image(payload):
    uri = os.getenv("VLM_MODEL_HOST")
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
    """
    根据图片宽高计算需要扩展的像素值。

    参数:
        width (int): 图片的宽度。
        height (int): 图片的高度。

    返回:
        tuple: (left, right, top, bottom) 表示左右上下需要扩展的像素值。
    """
    target_ratio_width = 9
    target_ratio_height = 16

    if width > height:
        # 宽大于高，按上下扩展
        new_height = (width / target_ratio_width) * target_ratio_height
        padding = (new_height - height) / 2
        top = int(padding)
        bottom = int(padding)
        left = 0
        right = 0
    elif height > width:
        # 高大于宽，按左右扩展
        new_width = (height / target_ratio_height) * target_ratio_width
        padding = (new_width - width) / 2
        left = int(padding)
        right = int(padding)
        top = 0
        bottom = 0
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


if __name__ == '__main__':
    image_path = ""

    check_water_image_payload = {
        "tool": "image_understanding",
        "params": json.dumps({
            "image_base64": "",
        })
    }
    image_base64 = open(image_path, "rb").read().decode("utf-8")
    if check_water_mark_image(check_water_image_payload):
        image_path = remove_watermark(image_base64)
        image_base64 = open(image_path, "rb").read().decode("utf-8")
        width, height = get_image_size(image_path)
        left, right, top, bottom = calculate_extension(width, height)
        # - 不是（比例：9: 16）（宽9长16）的图片 --> 改尺寸（扩图）
        # - 如果宽 > 高： 则按上下进行扩图，但上和下扩展的像素为（（宽的像素 / 9 * 16）-高的像素） / 2
        # - 如果高 > 宽： 则按左右进行扩图，但左右扩展的像素为（（高的像素 / 16 * 9）-宽的像素） / 2
        image_path = extend_image(image_base64, left, right, top, bottom)
