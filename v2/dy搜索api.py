import time
import urllib.parse
import traceback
import subprocess
import os
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from DrissionPage import ChromiumPage


# ================= FastAPI 实例初始化 =================
app = FastAPI(
    title="抖音搜索API",
    description="搜索抖音视频，自动启动 Chrome 调试模式"
)


# ================= 请求体数据模型 =================
class SearchRequest(BaseModel):
    keyword: str
    max_pages: int = 3


# ================= Chrome 自动启动 =================
def _ensure_chrome_debug():
    """检查 9222 端口，如果没有则自动启动 Chrome 调试模式"""
    import urllib.request
    try:
        urllib.request.urlopen("http://localhost:9222/json/version", timeout=1)
        return  # Chrome 已在调试模式
    except Exception:
        pass

    print("正在启动 Chrome（远程调试模式 9222）...")
    chrome_paths = [
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ]
    chrome_exe = None
    for p in chrome_paths:
        if os.path.exists(p):
            chrome_exe = p
            break

    if not chrome_exe:
        print("未找到 Chrome，请手动启动 Chrome 调试模式")
        return

    subprocess.Popen(
        [chrome_exe, "--remote-debugging-port=9222"],
        shell=False
    )
    time.sleep(2)


# ================= 核心逻辑封装 =================
def execute_douyin_search(keyword: str, max_pages: int):
    """
    连接本地 Chrome 调试端口，搜索抖音视频
    """
    page = ChromiumPage(addr_or_opts="127.0.0.1:9222")
    videos_list = []

    try:
        page.listen.start("search/")

        encoded_keyword = urllib.parse.quote(keyword)
        target_url = f"https://www.douyin.com/search/{encoded_keyword}?source=normal_search&type=video"
        page.get(target_url)
        time.sleep(2)

        print(f"页面标题: {page.title}")

        if "verify" in page.url.lower():
            print("⚠️ 触发验证，请手动在浏览器中完成")
            input("完成后按回车继续...")

        # 滚动加载
        for i in range(max_pages):
            print(f"  - 第 {i+1} 次滚动...")
            page.actions.scroll(delta_y=6000)
            time.sleep(0.3)

        # 提取数据
        while True:
            packet = page.listen.wait(timeout=2)
            if not packet:
                break

            json_data = packet.response.body

            if isinstance(json_data, str):
                import json
                try:
                    json_data = json.loads(json_data)
                except Exception:
                    continue

            if isinstance(json_data, dict) and "data" in json_data:
                items = json_data.get("data", [])
                if not isinstance(items, list):
                    continue
            else:
                continue

            valid_items = [item for item in items if isinstance(item, dict) and item.get("aweme_info")]

            for item in valid_items:
                aweme_info = item.get("aweme_info", {})
                video_id = aweme_info.get("aweme_id", "未知ID")

                if any(v['video_id'] == video_id for v in videos_list):
                    continue

                videos_list.append({
                    "video_id": video_id,
                    "author": aweme_info.get("author", {}).get("nickname", "未知作者"),
                    "likes": aweme_info.get("statistics", {}).get("digg_count", 0),
                    "description": aweme_info.get("desc", "").strip()
                })

    except Exception as e:
        traceback.print_exc()
        raise e
    finally:
        page.listen.stop()

    return videos_list


# ================= 路由端点 =================
@app.post("/api/dy/search")
async def search_dy(req: SearchRequest):
    print(f"接收任务: {req.keyword} | 页数: {req.max_pages}")

    if not req.keyword:
        raise HTTPException(status_code=400, detail="关键词不能为空")

    try:
        results = execute_douyin_search(req.keyword, req.max_pages)
        return {
            "status": "success",
            "count": len(results),
            "data": results
        }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"运行失败: {str(e)}")


if __name__ == "__main__":
    _ensure_chrome_debug()
    print("API 服务已启动: http://localhost:8005")
    print("如果 Chrome 弹出了验证，请在浏览器中手动完成")
    uvicorn.run(app, host="0.0.0.0", port=8005)
