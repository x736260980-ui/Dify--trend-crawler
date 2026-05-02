import os
import asyncio
import traceback
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from bilibili_api import video, comment, Credential
from bilibili_api.utils.aid_bvid_transformer import bvid2aid

# ================= 凭证配置区域 =================
# 请在此处填入真实的 B 站 Cookie 凭证
SESSDATA = "YOUR_SESSDATA"
BILI_JCT = "YOUR_BILI_JCT"
BUVID3 = "YOUR_BUVID3"

credential = Credential(sessdata=SESSDATA, bili_jct=BILI_JCT, buvid3=BUVID3)

# ================= FastAPI 实例初始化 =================
app = FastAPI(
    title="Bilibili Data API", 
    description="为 Dify Agent 提供弹幕与评论的结构化数据接口。"
)

# ================= 请求体数据模型 =================
class BasicRequest(BaseModel):
    bvid: str

class DanmakuRequest(BaseModel):
    bvid: str
    max_limit: int = 200

class CommentRequest(BaseModel):
    bvid: str
    max_pages: int = 3

# ================= 核心接口端点 =================
@app.post("/api/bili/meta")
async def get_video_meta(req: BasicRequest):
    """获取视频基础数据指标"""
    try:
        v = video.Video(bvid=req.bvid, credential=credential)
        info = await v.get_info()
        
        meta_data = {
            "title": info.get("title"),
            "desc": info.get("desc"),
            "owner": info.get("owner", {}).get("name"),
            "view": info.get("stat", {}).get("view"),
            "danmaku_count": info.get("stat", {}).get("danmaku"),
            "reply_count": info.get("stat", {}).get("reply"),
            "like": info.get("stat", {}).get("like"),
            "coin": info.get("stat", {}).get("coin"),
            "favorite": info.get("stat", {}).get("favorite"),
            "pubdate": info.get("pubdate")
        }
        return {"status": "success", "data": meta_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/bili/danmaku")
async def get_video_danmaku(req: DanmakuRequest):
    """获取视频实时弹幕数据"""
    try:
        v = video.Video(bvid=req.bvid, credential=credential)
        danmakus = await v.get_danmakus(page_index=0)
        
        danmaku_texts = [d.text for d in danmakus[:req.max_limit]]
        return {"status": "success", "count": len(danmaku_texts), "data": danmaku_texts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/bili/comments")
async def get_video_comments(req: CommentRequest):
    """基于游标分页获取视频评论数据"""
    try:
        aid = bvid2aid(req.bvid)
        comments_list = []
        page = 1
        pag = ""

        while page <= req.max_pages:
            c = await comment.get_comments_lazy(
                oid=aid,
                type_=comment.CommentResourceType.VIDEO,
                offset=pag,
                credential=credential
            )

            replies = c.get('replies')
            if not replies:
                break

            cursor = c.get("cursor", {})
            pagination = cursor.get("pagination_reply", {})
            pag = pagination.get("next_offset", "")

            for reply in replies:
                comments_list.append({
                    "user": reply.get('member', {}).get('uname', '未知'),
                    "likes": reply.get('like', 0),
                    "message": reply.get('content', {}).get('message', '')
                })

            page += 1
            await asyncio.sleep(0.5)

        return {"status": "success", "count": len(comments_list), "data": comments_list}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    # 默认绑定到 8000 端口，符合通用部署规范
    uvicorn.run(app, host="0.0.0.0", port=8000)
