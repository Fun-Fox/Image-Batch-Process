import base64
import json
import asyncio
import os

import yaml
import websockets
from start_inference import load_model, to_image_understanding
from loguru import logger

# 模型初始化
model_path = "deepseek-ai/Janus-Pro-7B"
vl_chat_processor, vl_gpt, tokenizer = load_model(model_path)


def image_understanding(image_path, require_element):
    question = f"""
       识别图片中是否 同时存在【 {require_element} 】：
       is_include 存在则为Y，不包含则为 N
        
       # 重要！确保输出格式如下：
       ```yaml
       is_include: |
           Y或N
       ```
       """
    # 图像分析
    image = image_path  # 需要传入图像数据
    ret = to_image_understanding(question, image, vl_chat_processor, vl_gpt, tokenizer)
    if "```yaml" not in ret:
        if "没有" in ret:
            return {"water_mark": "N"}
        elif "有" in ret:
            return {"water_mark": "Y"}
        else:
            return {"water_mark": "N"}
    yaml_str = ret.split("```yaml")[1].split("```")[0].strip()
    analysis = yaml.safe_load(yaml_str)

    return {"water_mark": str(analysis['is_include'])}


# 获取当前脚本的目录
current_dir = os.path.dirname(os.path.abspath(__file__))
# 创建tmp目录路径
tmp_dir = os.path.join(current_dir, "tmp")
# 如果tmp目录不存在，则创建
os.makedirs(tmp_dir, exist_ok=True)


async def handle_websocket(websocket):
    logger.info("WebSocket客户端已连接")
    try:
        async for message in websocket:
            request = json.loads(message)
            logger.info(f"收到消息: {request}")
            if request.get("tool") == "image_understanding":
                image_base64 = request.get("image_base64", "")
                # 生成唯一的文件名
                filename = f"{os.urandom(16).hex()}.jpg"
                # 创建完整的文件路径
                image_path = os.path.join(tmp_dir, filename)
                # 将base64数据解码并保存为文件
                with open(image_path, "wb") as f:
                    f.write(base64.b64decode(image_base64))
                result = image_understanding(image_path, require_element="水印")
                await websocket.send(json.dumps(result))
            else:
                await websocket.send(json.dumps({"error": "未知工具"}))
    except websockets.ConnectionClosed:
        logger.info("WebSocket客户端已断开连接")


async def main():
    logger.info("正在启动图片水印识别ws服务器在 ws://0.0.0.0:9200...")
    async with websockets.serve(handle_websocket, "0.0.0.0", 9200):
        await asyncio.Future()  # 永远运行


if __name__ == "__main__":
    asyncio.run(main())
