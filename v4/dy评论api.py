import os
import queue
import urllib.parse
import traceback
import uvicorn
from typing import Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
load_dotenv()

import subprocess as sp
import requests


# ================= a_bogus 进程池 =================
class _ABogusPool:
    """管理多个 a_bogus 计算进程，支持并发请求"""

    def __init__(self, size=3):
        self._pool = queue.Queue()
        self._procs = []
        base_dir = os.path.dirname(__file__)
        for _ in range(size):
            proc = sp.Popen(
                ["node", "a_bogus_server.js"],
                cwd=base_dir,
                stdin=sp.PIPE, stdout=sp.PIPE, stderr=sp.PIPE,
                text=True, bufsize=1
            )
            self._procs.append(proc)
            self._pool.put(proc)

    def get_ab(self, query, data=""):
        proc = self._pool.get()
        try:
            proc.stdin.write(f"{query}||{data}\n")
            proc.stdin.flush()
            return proc.stdout.readline().strip()
        finally:
            self._pool.put(proc)

    def shutdown(self):
        for proc in self._procs:
            proc.terminate()
        for proc in self._procs:
            try:
                proc.wait(timeout=3)
            except Exception:
                pass


_ab_pool: Optional[_ABogusPool] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _ab_pool
    _ab_pool = _ABogusPool(size=3)
    yield
    _ab_pool.shutdown()


# ================= FastAPI 实例初始化 =================
app = FastAPI(
    title="抖音评论API",
    description="通过 a_bogus 签名获取抖音视频评论",
    lifespan=lifespan,
)


# ================= 请求体数据模型 =================
class CommentRequest(BaseModel):
    aweme_id: str
    max_comments: int = 100


# ================= 核心逻辑封装 =================
def _make_session():
    """创建带 cookie 的请求会话"""
    cookies_str = os.getenv("DY_COOKIES", "")
    cookie_dict = {}
    for item in cookies_str.split("; "):
        item = item.strip()
        if "=" in item:
            k, v = item.split("=", 1)
            cookie_dict[k] = v

    session = requests.Session()
    session.trust_env = False
    session.cookies.update(cookie_dict)
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
    })
    return session


def execute_fetch_comments(aweme_id: str, max_comments: int):
    """使用 a_bogus 签名获取抖音视频评论"""
    get_ab = _ab_pool.get_ab
    session = _make_session()

    comments = []
    cursor = "0"
    has_more = 1

    while has_more == 1 and len(comments) < max_comments:
        need = max_comments - len(comments)
        count = min(20, need)

        params = {
            "aweme_id": aweme_id,
            "cursor": cursor,
            "count": str(count),
            "device_platform": "webapp",
            "aid": "6383",
            "webid": "",
        }
        session.headers.update({
            "Referer": f"https://www.douyin.com/video/{aweme_id}",
        })

        query_str = "&".join([f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items()])
        params["a_bogus"] = get_ab(query_str)

        resp = session.get(
            "https://www.douyin.com/aweme/v1/web/comment/list/",
            params=params, verify=False
        )
        if not resp.text.strip():
            break
        data = resp.json()
        items = data.get("comments", [])
        if not items:
            break

        for c in items:
            user = c.get("user", {})
            comments.append({
                "nickname": user.get("nickname", "未知用户"),
                "digg_count": c.get("digg_count", 0),
                "text": c.get("text", ""),
                "reply_total": c.get("reply_comment_total", 0),
            })

        cursor = str(data.get("cursor", "0"))
        has_more = data.get("has_more", 0)

    return comments


# ================= 路由端点 =================
@app.post("/api/dy/comments")
async def fetch_comments(req: CommentRequest):
    print(f"接收任务: {req.aweme_id} | 数量: {req.max_comments}")

    if not req.aweme_id:
        raise HTTPException(status_code=400, detail="aweme_id 不能为空")

    try:
        results = execute_fetch_comments(req.aweme_id, req.max_comments)
        return {
            "status": "success",
            "count": len(results),
            "data": results
        }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"运行失败: {str(e)}")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8006)
