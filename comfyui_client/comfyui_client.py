import requests
import json
import time
from loguru import logger
import os
import aiohttp
import asyncio

current_dir = os.path.dirname(os.path.abspath(__file__))


class ComfyUIClient:
    def __init__(self, base_url):
        """初始化ComfyUI客户端
        
        Args:
            base_url (str): ComfyUI服务的基础URL
        """
        self.base_url = base_url  # 初始化基础URL
        self.available_models = self._get_available_models()  # 获取可用模型列表
        self.mappings_dir = "mappings"  # 参数映射表文件夹

    def _get_available_models(self):
        """获取ComfyUI中可用的检查点模型列表"""
        try:
            response = requests.get(f"{self.base_url}/object_info/CheckpointLoaderSimple")
            if response.status_code != 200:
                logger.warning("无法获取模型列表；使用默认处理")
                return []
            data = response.json()
            models = data["CheckpointLoaderSimple"]["input"]["required"]["ckpt_name"][0]
            logger.info(f"可用模型: {models}")
            return models
        except Exception as e:
            logger.warning(f"获取模型时出错: {e}")
            return []

    def load_mapping(self, workflow_id):
        """加载指定工作流的参数映射表
        
        Args:
            workflow_id (str): 工作流ID
            
        Returns:
            dict: 参数映射表
            
        Raises:
            Exception: 如果映射表文件不存在或解析失败
        """
        mapping_path = os.path.join(self.mappings_dir, f"{workflow_id}.json")
        try:
            with open(mapping_path, "r") as f:
                mapping = json.load(f)
            logger.info(f"已加载工作流 '{workflow_id}' 的参数映射表")
            return mapping
        except FileNotFoundError:
            raise Exception(f"参数映射表文件 '{mapping_path}' 未找到")
        except json.JSONDecodeError:
            raise Exception(f"解析参数映射表文件 '{mapping_path}' 失败")


    def upload_image(self, image_path):
        """上传图像到ComfyUI的input目录
        
        Args:
            image_path (str): 要上传的图像路径
            
        Returns:
            str: 上传后服务器上的文件名
            
        Raises:
            Exception: 如果上传失败
        """
        try:
            url = f"{self.base_url}/api/upload/image"
            filename = os.path.basename(image_path)
            with open(image_path, 'rb') as f:
                files = {'image': (filename, f)}
                data = {'overwrite': 'true'}
                response = requests.post(url, files=files, data=data)
                response.raise_for_status()
                return response.json()['name']
        except Exception as e:
            raise Exception(f"上传图像失败: {e}")

    async def download_video_or_image_or_audio_async(self, video_url, save_path):
        """异步下载视频文件"""
        try:
            logger.info(f"开始异步下载视频: {video_url}")
            async with aiohttp.ClientSession() as session:
                async with session.get(video_url) as resp:
                    if resp.status == 200:
                        with open(save_path, 'wb') as f:
                            while True:
                                chunk = await resp.content.read(64 * 1024)  # 每次读取64KB
                                if not chunk:
                                    break
                                f.write(chunk)
                        logger.info(f"视频已保存至: {save_path}")
                        return save_path
                    else:
                        raise Exception(f"下载失败，状态码: {resp.status}")
        except Exception as e:
            logger.error(f"异步下载出错: {e}")
            raise

    async def poll_for_video_or_image_or_audio(self, prompt_id, output_dir,max_attempts=60, interval=2, is_video=False,
                                                 is_audio=False):
        """异步轮询 ComfyUI 历史接口以获取视频、图像或音频 URL 并下载"""

        if is_audio:
            content_type = "audios"
            logger.info("开始轮询音频生成结果...")
        elif is_video:
            content_type = "videos"
            logger.info("开始轮询视频生成结果...")
        else:
            content_type = "images"
            logger.info("开始轮询图像生成结果...")

        for attempt in range(max_attempts):
            logger.info(f"轮询尝试 {attempt + 1}/{max_attempts}")
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/history/{prompt_id}") as resp:
                    if resp.status != 200:
                        logger.warning(f"HTTP 状态码错误：{resp.status}")
                        await asyncio.sleep(interval)
                        continue

                    history = await resp.json()
                    if history.get(prompt_id):
                        outputs = history[prompt_id]["outputs"]
                        logger.info("工作流输出: %s", json.dumps(outputs, indent=2))

                        # 查找输出节点
                        content_node = next((nid for nid, out in outputs.items() if content_type in out), None)
                        if not content_node:
                            raise Exception(
                                f"未找到包含{'音频' if is_audio else '视频' if is_video else '图像'}的输出节点: {outputs}")

                        filename = outputs[content_node][content_type][0]["filename"]
                        file_url = f"{self.base_url}/view?filename={filename}&subfolder=&type=output"
                        logger.info(f"生成的{'音频' if is_audio else '视频' if is_video else '图像'} URL: {file_url}")

                        os.makedirs(output_dir, exist_ok=True)
                        local_path = os.path.join(output_dir, filename)

                        await self.download_video_or_image_or_audio_async(file_url, local_path)
                        return local_path

            await asyncio.sleep(interval)

        raise Exception(
            f"{'音频' if is_audio else '视频' if is_video else '图像'}任务 {prompt_id} 在 {max_attempts} 秒内未完成")
