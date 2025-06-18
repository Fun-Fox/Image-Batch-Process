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

    def _load_mapping(self, workflow_id):
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

    async def generate_audio(self, tags, lyrics,workflow_id="audio_ace_step"):
        try:
            workflow_file = os.path.join(current_dir, f"workflows/{workflow_id}.json")  # 构造工作流文件路径
            with open(workflow_file, "r", encoding="utf-8", errors="ignore") as f:
                workflow = json.load(f)
            logger.info(f"使用工作流 {workflow_id} 生成图像...")

            # 加载参数映射表
            mapping = self._load_mapping(workflow_id)

            params = {"tags": tags, "lyrics": lyrics,}  # 创建基本参数字典

            # 将参数应用到工作流中的相应节点
            for param_key, value in params.items():
                if param_key in mapping:
                    node_id, input_key = mapping[param_key]  # 解析节点ID和输入键
                    if node_id not in workflow:
                        raise Exception(f"工作流 {workflow_id} 中未找到节点 {node_id}")
                    workflow[node_id]["inputs"][input_key] = value  # 设置节点输入值

            logger.info(f"提交工作流 {workflow_id} 到ComfyUI...")  # 日志记录
            response = requests.post(f"{self.base_url}/prompt", json={"prompt": workflow})  # 提交工作流
            if response.status_code != 200:
                raise Exception(f"提交工作流失败: {response.status_code} - {response.text}")  # 错误处理

            prompt_id = response.json()["prompt_id"]  # 获取提示ID
            logger.info(f"已排队的工作流，prompt_id: {prompt_id}")  # 日志记录

            time.sleep(30)

            # 异步等待并下载音频
            try:
                audio_path = await self.poll_for_video_or_image_or_audio(prompt_id, max_attempts=30,
                                                                           is_video=False)
                logger.info(f"音频文件已保存至: {audio_path}")
            except Exception as e:
                logger.error(f"音频处理失败: {e}")
                raise

            # 超时处理
        except FileNotFoundError:
            raise Exception(f"工作流文件 '{workflow_file}' 未找到")  # 文件未找到错误
        except KeyError as e:
            raise Exception(f"工作流错误 - 无效的节点或输入: {e}")  # 键错误处理
        except requests.RequestException as e:
            raise Exception(f"ComfyUI API错误: {e}")  # 请求异常处理

    async def generate_image(self, prompt, width=512, height=512, workflow_id="basic_api", model=None):
        """生成图像
        
        Args:
            prompt (str): 提示文本
            width (int, optional): 图像宽度. 默认为512.
            height (int, optional): 图像高度. 默认为512.
            workflow_id (str, optional): 工作流ID. 默认为"basic_api".
            model (str, optional): 使用的模型. 默认为None.
            
        Returns:
            str: 生成的图像URL
            
        Raises:
            Exception: 如果图像生成过程中出现错误
        """
        try:
            workflow_file = os.path.join(current_dir, f"workflows/{workflow_id}.json")  # 构造工作流文件路径
            with open(workflow_file, "r", encoding="utf-8", errors="ignore") as f:
                workflow = json.load(f)
            logger.info(f"使用工作流 {workflow_id} 生成图像...")

            # 加载参数映射表
            mapping = self._load_mapping(workflow_id)

            params = {"prompt": prompt, "width": width, "height": height}  # 创建基本参数字典
            if model:
                # 验证或纠正模型名称
                if model.endswith("'"):  # 去除意外添加的引号
                    model = model.rstrip("'")
                    logger.info(f"纠正后的模型名称: {model}")
                if self.available_models and model not in self.available_models:
                    raise Exception(f"模型 '{model}' 不在可用模型中: {self.available_models}")
                params["model"] = model  # 添加模型参数

            # 将参数应用到工作流中的相应节点
            for param_key, value in params.items():
                if param_key in mapping:
                    node_id, input_key = mapping[param_key]  # 解析节点ID和输入键
                    if node_id not in workflow:
                        raise Exception(f"工作流 {workflow_id} 中未找到节点 {node_id}")
                    workflow[node_id]["inputs"][input_key] = value  # 设置节点输入值

            logger.info(f"提交工作流 {workflow_id} 到ComfyUI...")  # 日志记录
            response = requests.post(f"{self.base_url}/prompt", json={"prompt": workflow})  # 提交工作流
            if response.status_code != 200:
                raise Exception(f"提交工作流失败: {response.status_code} - {response.text}")  # 错误处理

            prompt_id = response.json()["prompt_id"]  # 获取提示ID
            logger.info(f"已排队的工作流，prompt_id: {prompt_id}")  # 日志记录

            time.sleep(30)

            # 异步等待并下载图像
            try:
                image_path = await self.poll_for_video_or_image_or_audio(prompt_id, max_attempts=30,
                                                                           is_video=False)
                logger.info(f"图片下载完成: {image_path}")
            except Exception as e:
                logger.error(f"图片处理失败: {e}")
                raise

            # 超时处理
        except FileNotFoundError:
            raise Exception(f"工作流文件 '{workflow_file}' 未找到")  # 文件未找到错误
        except KeyError as e:
            raise Exception(f"工作流错误 - 无效的节点或输入: {e}")  # 键错误处理
        except requests.RequestException as e:
            raise Exception(f"ComfyUI API错误: {e}")  # 请求异常处理

    async def generate_image_to_video(self, image_path, prompt, workflow_id="hy_image_to_video_api", ):
        """从图像生成视频
        
        Args:
            image_path (str): 输入图像的路径
            prompt (str): 提示文本
            workflow_id (str, optional): 工作流ID. 默认为"hy_image_to_video_api".
        Returns:
            str: 生成的视频URL
            
        Raises:
            Exception: 如果视频生成过程中出现错误
        """
        try:
            workflow_file = os.path.join(current_dir, f"workflows/{workflow_id}.json")  # 构造工作流文件路径
            with open(workflow_file, "r", encoding="utf-8", errors="ignore") as f:
                workflow = json.load(f)
            logger.info(f"使用工作流 {workflow_id} 生成视频...")
            # logger.info(f"workflow_id:\n{json.dumps(workflow, indent=2, ensure_ascii=False)}")
            # 上传图像
            uploaded_filename = self.upload_image(image_path)
            logger.info(f"上传的图像文件名: {uploaded_filename}")

            # 加载参数映射表
            mapping = self._load_mapping(workflow_id)

            params = {"prompt": prompt, "image": uploaded_filename}  # 创建基本参数字典

            # 将参数应用到工作流中的相应节点
            for param_key, value in params.items():
                if param_key in mapping:
                    node_id, input_key = mapping[param_key]  # 解析节点ID和输入键
                    if node_id not in workflow:
                        raise Exception(f"工作流 {workflow_id} 中未找到节点 {node_id}")
                    workflow[node_id]["inputs"][input_key] = value  # 设置节点输入值

            logger.info(f"提交工作流 {workflow_id} 到ComfyUI...")  # 日志记录
            response = requests.post(f"{self.base_url}/prompt", json={"prompt": workflow})  # 提交工作流
            if response.status_code != 200:
                raise Exception(f"提交工作流失败: {response.status_code} - {response.text}")  # 错误处理

            prompt_id = response.json()["prompt_id"]  # 获取提示ID
            logger.info(f"已排队的工作流，prompt_id: {prompt_id}")  # 日志记录
            await asyncio.sleep(30)
            try:
                video_path = await self.poll_for_video_or_image_or_audio(prompt_id, max_attempts=60, is_video=True)
                logger.info(f"视频下载完成: {video_path}")
            except Exception as e:
                logger.error(f"视频处理失败: {e}")
                raise

        except FileNotFoundError:
            raise Exception(f"工作流文件 '{workflow_file}' 未找到")  # 文件未找到错误
        except KeyError as e:
            raise Exception(f"工作流错误 - 无效的节点或输入: {e}")  # 键错误处理
        except requests.RequestException as e:
            raise Exception(f"ComfyUI API错误: {e}")  # 请求异常处理

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

    async def poll_for_video_or_image_or_audio(self, prompt_id, max_attempts=60, interval=2, is_video=False,
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

                        output_dir = os.getenv("OUTPUT", "downloaded_media")
                        os.makedirs(output_dir, exist_ok=True)
                        local_path = os.path.join(output_dir, filename)

                        await self.download_video_or_image_or_audio_async(file_url, local_path)
                        return local_path

            await asyncio.sleep(interval)

        raise Exception(
            f"{'音频' if is_audio else '视频' if is_video else '图像'}任务 {prompt_id} 在 {max_attempts} 秒内未完成")
