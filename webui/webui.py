import gradio as gr
import os
from PIL import Image
from service import sync_process_image  # 上面定义的封装函数


# 图片处理函数（模拟调用你的流程）
def batch_process_images(folder_path):
    if not os.path.exists(folder_path):
        return "错误：路径不存在", []

    image_files = [f for f in os.listdir(folder_path) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    results = []

    for img_file in image_files:
        full_path = os.path.join(folder_path, img_file)
        try:
            output_path = sync_process_image(full_path)
            original = Image.open(full_path)
            processed = Image.open(output_path)
            results.append((original, processed))
        except Exception as e:
            results.append((Image.new('RGB', (200, 200), color='red'), Image.new('RGB', (200, 200), color='red')))
            print(f"处理失败 {img_file}: {e}")

    return f"共处理 {len(results)} 张图片"


# 获取当前脚本所在目录
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXTEND_IMAGE_DIR = os.path.join(ROOT_DIR, "comfyui_client", "extend_image")
SCALE_IMAGE_DIR = os.path.join(ROOT_DIR, "comfyui_client", "scale_image")


# 加载 extend_image 文件夹中的图片
def load_extend_images():
    if not os.path.exists(EXTEND_IMAGE_DIR):
        return []

    image_files = [f for f in os.listdir(EXTEND_IMAGE_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    images = []

    for img_file in image_files:
        full_path = os.path.join(EXTEND_IMAGE_DIR, img_file)
        try:
            img = Image.open(full_path)
            images.append(img)
        except Exception as e:
            print(f"无法打开图片 {img_file}: {e}")

    if not images:
        return []
    return images


def load_scale_images():
    if not os.path.exists(SCALE_IMAGE_DIR):
        return []

    image_files = [f for f in os.listdir(SCALE_IMAGE_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    images = []

    for img_file in image_files:
        full_path = os.path.join(SCALE_IMAGE_DIR, img_file)
        try:
            img = Image.open(full_path)
            images.append(img)
        except Exception as e:
            print(f"无法打开图片 {img_file}: {e}")

    if not images:
        return []
    return images


# Gradio 界面
with gr.Blocks() as demo:
    gr.Markdown("## 🖼️ 图片批量处理工具")

    # 原理说明区域
    gr.Markdown("""
    ### 🔍 对文件夹中每张图片进行以下处理：

    1. **判断是否有水印** → 若有则调用模型去水印  
    2. **调整尺寸（扩图）**：确保比例为 9:16  
    3. **放大清晰度**：若分辨率小于 1080x1920，则放大处理  
    """)
    image_path = os.path.join(ROOT_DIR, "doc", "images")
    with gr.Row():
        folder_input = gr.Textbox(label="输入图片文件夹路径", value=image_path)

    process_btn = gr.Button("开始批量处理")

    # 处理按钮绑定
    process_btn.click(
        fn=batch_process_images,
        inputs=folder_input,
        outputs=gr.Textbox(label="处理状态")
    )
    with gr.Row():
        with gr.Column():
            show_extend_btn = gr.Button("查看去水印并扩图后的图片")
            extend_gallery = gr.Gallery(label="Extend Image 文件夹图片", columns=20, height="auto")

            show_extend_btn.click(
                fn=load_extend_images,
                inputs=[],
                outputs=[extend_gallery]
            )

        with gr.Column():
            show_scale_btn = gr.Button("查看放大后的图片")
            scale_gallery = gr.Gallery(label="Scale Image 文件夹图片", columns=20, height="auto")

            show_scale_btn.click(
                fn=load_scale_images,
                inputs=[],
                outputs=[scale_gallery]
            )

# 启动 Gradio 应用
demo.launch()
