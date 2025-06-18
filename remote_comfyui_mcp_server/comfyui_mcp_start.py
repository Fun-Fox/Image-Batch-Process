import asyncio
import json
from loguru import logger
from typing import AsyncIterator
from contextlib import asynccontextmanager
import websockets
from mcp.server.fastmcp import FastMCP
from comfyui_client import ComfyUIClient

# 配置日志

# 全局ComfyUI客户端（当前上下文不可用时的备选方案）
comfyui_client = ComfyUIClient("http://localhost:8188")


# 定义应用程序上下文（供将来使用）
class AppContext:
    def __init__(self, comfyui_client: ComfyUIClient):
        self.comfyui_client = comfyui_client


# 生命周期管理（占位符，供将来上下文支持使用）
@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """管理应用程序生命周期"""
    logger.info("Starting MCP server lifecycle...")
    try:
        # 启动：未来可添加ComfyUI健康检查
        logger.info("ComfyUI客户端已全局初始化")
        yield AppContext(comfyui_client=comfyui_client)
    finally:
        # 关闭：清理（如果需要）
        logger.info("正在关闭MCP服务器")


# 使用生命周期初始化FastMCP
mcp = FastMCP("ComfyUI_MCP_Server", lifespan=app_lifespan)


# 定义音乐生成基础模型
@mcp.tool()
def generate_music(params: str) -> dict:
    """使用ComfyUI生成图像"""
    logger.info(f"收到请求参数: {params}")
    try:
        param_dict = json.loads(params)
        tags = param_dict["tags"]
        lyrics = param_dict.get("lyrics", None)
        workflow_id = param_dict.get("workflow_id", "audio_ace_step_api")

        # 使用全局comfyui_client（因为mcp.context不可用）
        image_url = asyncio.run(comfyui_client.generate_audio(
            tags=tags,
            lyrics=lyrics,
            workflow_id=workflow_id,
        ))
        logger.info(f"返回图像URL: {image_url}")
        return {"image_url": image_url}
    except Exception as e:
        logger.error(f"错误: {e}")
        return {"error": str(e)}


@mcp.tool()
def generate_image(params: str) -> dict:
    """使用ComfyUI生成图像"""
    logger.info(f"收到请求参数: {params}")
    try:
        param_dict = json.loads(params)
        prompt = param_dict["prompt"]
        width = param_dict.get("width", 512)
        height = param_dict.get("height", 512)
        workflow_id = param_dict.get("workflow_id", "basic_api")
        model = param_dict.get("model", None)

        # 使用全局comfyui_client（因为mcp.context不可用）
        image_url = asyncio.run(comfyui_client.generate_image(
            prompt=prompt,
            width=width,
            height=height,
            workflow_id=workflow_id,
            model=model
        ))
        logger.info(f"返回图像URL: {image_url}")
        return {"image_url": image_url}
    except Exception as e:
        logger.error(f"错误: {e}")
        return {"error": str(e)}


# 定义视频生成工具
@mcp.tool()
def generate_image_to_video(params: str) -> dict:
    """使用ComfyUI生成图像"""
    logger.info(f"收到请求参数: {params}")
    try:
        param_dict = json.loads(params)
        prompt = param_dict["prompt"]
        image_path = param_dict["image_path"]
        workflow_id = param_dict.get("workflow_id", "hy_image_to_video_api")

        # 使用全局comfyui_client（因为mcp.context不可用）
        video_url = asyncio.run(comfyui_client.generate_image_to_video(
            image_path=image_path,
            prompt=prompt,
            workflow_id=workflow_id,
        ))
        logger.info(f"返回视频URL: {video_url}")
        return {"image_url": video_url}
    except Exception as e:
        logger.error(f"错误: {e}")
        return {"error": str(e)}


# WebSocket服务器
async def handle_websocket(websocket):
    logger.info("WebSocket客户端已连接")
    try:
        async for message in websocket:
            request = json.loads(message)
            logger.info(f"收到消息: {request}")
            if request.get("tool") == "generate_image":
                result = generate_image(request.get("params", ""))
                await websocket.send(json.dumps(result))
            elif request.get("tool") == "generate_image_to_video":
                result = generate_image_to_video(request.get("params", ""))
                await websocket.send(json.dumps(result))
            elif request.get("tool") == "generate_music":
                result = generate_music(request.get("params", ""))
                await websocket.send(json.dumps(result))
            else:
                await websocket.send(json.dumps({"error": "未知工具"}))
    except websockets.ConnectionClosed:
        logger.info("WebSocket客户端已断开连接")


# 主服务器循环
async def main():
    logger.info("正在启动MCP服务器在 ws://0.0.0.0:9100...")
    async with websockets.serve(handle_websocket, "0.0.0.0", 9100):
        await asyncio.Future()  # 永远运行


if __name__ == "__main__":
    asyncio.run(main())
