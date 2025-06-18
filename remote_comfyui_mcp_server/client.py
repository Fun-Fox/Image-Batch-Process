import asyncio
from uu import encode

import websockets
import json

payload_1 = {
    "tool": "generate_image",
    "params": json.dumps({
        "prompt": "an english mastiff dog sitting on a large boulder, bright shiny day",
        "width": 512,
        "height": 512,
        "workflow_id": "basic_api_test",
        "model": "v1-5-pruned-emaonly.ckpt"  # 无额外引号
    })
}

payload_2 = {
    "tool": "generate_image_to_video",
    "params": json.dumps({
        "prompt": "an english mastiff dog sitting on a large boulder, bright shiny day",
        "image_path": "D:\\PycharmProjects\\PicFableWeaver\\example\\2 (1).jpg",
    })
}


async def test_mcp_server():
    uri = "ws://localhost:9000"
    try:
        async with websockets.connect(uri) as ws:
            print("已连接到MCP服务器")
            await ws.send(json.dumps(payload_2))
            response = await ws.recv()
            print("来自服务器的响应:")
            print(json.dumps(json.loads(response), indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"WebSocket错误: {e}")


if __name__ == "__main__":
    print("正在使用WebSocket测试MCP服务器...")
    asyncio.run(test_mcp_server())
