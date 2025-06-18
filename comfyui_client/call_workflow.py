import asyncio
import base64
import json
import os
import time

import requests
from dotenv import load_dotenv
from loguru import logger
from .comfyui_client import ComfyUIClient

load_dotenv()
# 配置日志

# 全局ComfyUI客户端（当前上下文不可用时的备选方案）
comfyui_host = os.getenv("COMFYUI_HOST", "http://localhost:8188")
comfyui_client = ComfyUIClient(comfyui_host)

# 获取当前脚本的目录
current_dir = os.path.dirname(os.path.abspath(__file__))
# 创建tmp目录路径
tmp_dir = os.path.join(current_dir, "tmp")
# 如果tmp目录不存在，则创建
os.makedirs(tmp_dir, exist_ok=True)


async def extend_image(params: str):
    """使用ComfyUI进行扩图"""
    logger.info(f"收到请求参数: {params}")
    try:
        param_dict = json.loads(params)
        image_base64 = param_dict["image_base64"]
        # 生成唯一的文件名
        filename = f"{os.urandom(16).hex()}.jpg"
        # 创建完整的文件路径
        image_path = os.path.join(tmp_dir, filename)

        # 将base64数据解码并保存为文件
        with open(image_path, "wb") as f:
            f.write(base64.b64decode(image_base64))

        # 现在image_path变量包含图片的绝对路径
        print(f"图片已保存至: {image_path}")
        image = comfyui_client.upload_image(image_path)
        print(f"图片已上传到ComfyUI，图片名称：{image}")

        left = param_dict.get("left", 0)
        right = param_dict.get("right", 0)
        top = param_dict.get("top", 0)
        bottom = param_dict.get("bottom", 0)
        workflow_id = 'extend_image_api'
        workflow_file = os.path.join(current_dir, f"workflows/{workflow_id}.json")  # 构造工作流文件路径
        with open(workflow_file, "r", encoding="utf-8", errors="ignore") as f:
            workflow = json.load(f)
        logger.info(f"使用工作流 {workflow_id} 生成图像...")

        # 加载参数映射表
        mapping = comfyui_client.load_mapping(workflow_id)
        params = {"image": image, "left": left, "right": top, "top": right, "bottom": bottom}  # 创建基本参数字典

        # 将参数应用到工作流中的相应节点
        for param_key, value in params.items():
            if param_key in mapping:
                node_id, input_key = mapping[param_key]  # 解析节点ID和输入键
                if node_id not in workflow:
                    raise Exception(f"工作流 {workflow_id} 中未找到节点 {node_id}")
                workflow[node_id]["inputs"][input_key] = value  # 设置节点输入值

        logger.info(f"提交工作流 {workflow_id} 到ComfyUI...")  # 日志记录
        response = requests.post(f"{comfyui_host}/prompt", json={"prompt": workflow})  # 提交工作流
        if response.status_code != 200:
            raise Exception(f"提交工作流失败: {response.status_code} - {response.text}")  # 错误处理

        prompt_id = response.json()["prompt_id"]  # 获取提示ID
        logger.info(f"已排队的工作流，prompt_id: {prompt_id}")  # 日志记录
        time.sleep(30)

        # 异步等待并下载图像
        try:
            output_dir = os.path.join(current_dir, "extend_image")
            image_path = await comfyui_client.poll_for_video_or_image_or_audio(prompt_id, output_dir, max_attempts=30,
                                                                               is_video=False)
            logger.info(f"图片下载完成: {image_path}")
            return  image_path
        except Exception as e:
            logger.error(f"图片处理失败: {e}")


    except Exception as e:
        logger.error(f"错误: {e}")


async def remove_watermark(params: str):
    """使用ComfyUI进行水印去除"""
    try:
        param_dict = json.loads(params)
        image_base64 = param_dict["image_base64"]
        # 生成唯一的文件名
        filename = f"{os.urandom(16).hex()}.jpg"
        # 创建完整的文件路径
        image_path = os.path.join(tmp_dir, filename)

        # 将base64数据解码并保存为文件
        with open(image_path, "wb") as f:
            f.write(base64.b64decode(image_base64))

        # 现在image_path变量包含图片的绝对路径
        print(f"图片已保存至: {image_path}")
        image = comfyui_client.upload_image(image_path)
        print(f"图片已上传到ComfyUI，图片名称：{image}")

        workflow_id = 'remove_water_mark_api'
        workflow_file = os.path.join(current_dir, f"workflows/{workflow_id}.json")  # 构造工作流文件路径
        with open(workflow_file, "r", encoding="utf-8", errors="ignore") as f:
            workflow = json.load(f)
        logger.info(f"使用工作流 {workflow_id} 生成图像...")

        # 加载参数映射表
        mapping = comfyui_client.load_mapping(workflow_id)
        params = {"image": image, }  # 创建基本参数字典

        # 将参数应用到工作流中的相应节点
        for param_key, value in params.items():
            if param_key in mapping:
                node_id, input_key = mapping[param_key]  # 解析节点ID和输入键
                if node_id not in workflow:
                    raise Exception(f"工作流 {workflow_id} 中未找到节点 {node_id}")
                workflow[node_id]["inputs"][input_key] = value  # 设置节点输入值

        logger.info(f"提交工作流 {workflow_id} 到ComfyUI...")  # 日志记录
        response = requests.post(f"{comfyui_host}/prompt", json={"prompt": workflow})  # 提交工作流
        if response.status_code != 200:
            raise Exception(f"提交工作流失败: {response.status_code} - {response.text}")  # 错误处理

        prompt_id = response.json()["prompt_id"]  # 获取提示ID
        logger.info(f"已排队的工作流，prompt_id: {prompt_id}")  # 日志记录
        time.sleep(30)

        # 异步等待并下载图像
        try:
            output_dir = os.path.join(current_dir, "remove_water_mark")
            image_path = await comfyui_client.poll_for_video_or_image_or_audio(prompt_id, output_dir, max_attempts=30,
                                                                               is_video=False)
            logger.info(f"图片下载完成: {image_path}")
            return  image_path
        except Exception as e:
            logger.error(f"图片处理失败: {e}")

    except Exception as e:
        logger.error(f"错误: {e}")
