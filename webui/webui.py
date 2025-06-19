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

    return f"共处理 {len(results)} 张图片", results


# 刷新文件夹内容
def refresh_folder(folder_path):
    if not os.path.exists(folder_path):
        return gr.update(choices=[])
    files = [f for f in os.listdir(folder_path) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    return gr.update(choices=files)


# Gradio 界面
with gr.Blocks() as demo:
    gr.Markdown("## 🖼️ 图片批量处理工具 - 使用 Gradio")

    # 原理说明区域
    gr.Markdown("""
    ### 🔍 处理逻辑说明

    对文件夹中每张图片进行以下处理：

    1. **判断是否有水印** → 若有则调用模型去水印  
    2. **调整尺寸（扩图）**：确保比例为 9:16  
        - 宽 > 高 → 上下扩展高度  
        - 高 > 宽 → 左右扩展宽度  
    3. **放大清晰度**：若分辨率小于 1080x1920，则放大处理  

    #### ✅ 输出格式要求：
    - 图片比例：9:16  
    - 分辨率 ≥1080x1920 或其整数倍  
    - 无水印  

    #### ⚙️ 使用到的 ComfyUI 工作流：
    - 步骤1：使用 deepseek_janus_pro_7b 判断是否图片有水印  
    - 步骤2：扩图工作流  
    - 步骤3：放大工作流
    """)

    with gr.Row():
        folder_input = gr.Textbox(label="输入图片文件夹路径", value="./images")
        refresh_btn = gr.Button("刷新文件夹")

    gallery = gr.Gallery(label="处理前后对比", columns=2, height="auto")
    status_text = gr.Textbox(label="处理状态")

    process_btn = gr.Button("开始批量处理")

    # 处理按钮绑定
    process_btn.click(
        fn=batch_process_images,
        inputs=folder_input,
        outputs=[status_text, gallery]
    )

    # 刷新按钮绑定
    refresh_btn.click(fn=refresh_folder, inputs=folder_input, outputs=gallery)

# 启动 Gradio 应用
demo.launch()
