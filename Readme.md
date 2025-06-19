# 图片批量处理工具

## 处理逻辑说明

筛选图片文件夹中

- 不是（比例：9:16）（宽9长16）的图片 --> 改尺寸（扩图）
    - 如果宽>高： 则按上下进行扩图，但上和下扩展的像素为（（宽的像素/9*16）-高的像素）/2
        - 宽度太大，高度已足够，改为左右扩展宽度
    - 如果高>宽： 则按左右进行扩图，但左右扩展的像素为（（高的像素/16*9）-宽的像素）/2
        - 如果 高度太大，宽度已足够，改为上下扩展高度
- 有水印的图片 --> 去水印
- 不清晰的图片 --> 放大（变清晰）
    - 查看图片尺寸为9：16, 但分辨率 <1080*1920,就需要放大

如果单张图片不符合多个要求
处理优先顺序：去水印-->改尺寸（扩图）-->放大

![](/doc/1.png)

## 输出格式

查看尺寸为9：16，分辨率 >1080*1920或者是它的倍数，没有水印的图片

## 部署

```commandline
# 下载视觉模型
# 视觉模型服务离线部署
set HF_ENDPOINT=https://hf-mirror.com
# 下载模型到 项目 目录下
huggingface-cli download deepseek-ai/Janus-Pro-7B --repo-type=model --local-dir /deepseek-ai/Janus-Pro-7B

# 安装PyTorch
pip install torch torchvision torchaudio --extra-index-url https://download.pytorch.org/whl/cu128
pip install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu128

```

## 使用到的ComfyUI工作流

### 步骤1

使用deepseek_janus_pro_7b判断是否图片有水印

### 步骤2

扩图工作流

### 步骤3

放大工作流
