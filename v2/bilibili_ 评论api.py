import asyncio
import traceback
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from bilibili_api import video, comment, Credential
from bilibili_api.utils.aid_bvid_transformer import bvid2aid

# ================= 凭证配置区域 =================
# 从底稿中提取并注入的有效 Cookie 凭证
SESSDATA = "031ca7b5%2C1792060943%2C98d62%2A42CjA4Uv9uTY5gXJWhfaqSGYgrRFEva3EJdInrPrJU0U7nNMSHlAdHUgjaqX-DndiEL6USVm5ueGFuX3QzdU9PUXVNcmNubERTdi0xcThYNjZaZVAyU1haaVhrdllEVmJQNl9iZWNkMllpTzIydWxTeFlIY0FVSzdsX1dwMkc4Q25zaFJRQ0d6ei1BIIEC"
BILI_JCT = "a8b99dc998e960fe312cafadb6e06af9"
BUVID3 = "7750018E-6A75-E944-6097-B1D637749DC506926infoc"

credential = Credential(sessdata=SESSDATA, bili_jct=BILI_JCT, buvid3=BUVID3)

# ================= FastAPI 实例初始化 =================
app = FastAPI(title="B站多维舆情获取服务", description="为 Dify Agent 提供基础信息、弹幕与评论的结构化数据。")


# ================= 请求体数据模型 =================
class BatchFullRequest(BaseModel):
    """批量查一个或多个视频的完整数据（元数据+弹幕+评论）"""
    bvids: list[str]
    max_limit: int = 200
    max_pages: int = 3


# ================= 核心接口端点 =================

@app.post("/api/bili/batch-full")
async def get_batch_full_video_data(req: BatchFullRequest):
    """批量完整数据：多个视频同时取元数据+弹幕+评论"""
    print(f"📥 收到批量完整数据请求: {len(req.bvids)} 个视频")
    try:
        async def fetch_one_full(bvid: str):
            v = video.Video(bvid=bvid, credential=credential)

            async def fetch_meta():
                info = await v.get_info()
                return {
                    "title": info.get("title"),
                    "desc": info.get("desc"),
                    "owner": info.get("owner", {}).get("name"),
                    "view": info.get("stat", {}).get("view"),
                    "danmaku_count": info.get("stat", {}).get("danmaku"),
                    "reply_count": info.get("stat", {}).get("reply"),
                    "like": info.get("stat", {}).get("like"),
                    "coin": info.get("stat", {}).get("coin"),
                    "favorite": info.get("stat", {}).get("favorite"),
                    "pubdate": info.get("pubdate"),
                }

            async def fetch_danmaku():
                danmakus = await v.get_danmakus(page_index=0)
                return [d.text for d in danmakus[:req.max_limit]]

            async def fetch_comments():
                aid = bvid2aid(bvid)
                comments_list = []
                page = 1
                pag = ""
                while page <= req.max_pages:
                    c = await comment.get_comments_lazy(
                        oid=aid,
                        type_=comment.CommentResourceType.VIDEO,
                        offset=pag,
                        credential=credential,
                    )
                    replies = c.get("replies")
                    if not replies:
                        break
                    cursor = c.get("cursor", {})
                    pagination = cursor.get("pagination_reply", {})
                    pag = pagination.get("next_offset", "")
                    for reply in replies:
                        comments_list.append({
                            "user": reply.get("member", {}).get("uname", "未知"),
                            "likes": reply.get("like", 0),
                            "message": reply.get("content", {}).get("message", ""),
                        })
                    page += 1
                    await asyncio.sleep(0.5)
                return comments_list

            meta, danmaku, comments = await asyncio.gather(
                fetch_meta(), fetch_danmaku(), fetch_comments()
            )
            return {
                "bvid": bvid,
                "meta": meta,
                "danmaku": {"count": len(danmaku), "data": danmaku},
                "comments": {"count": len(comments), "data": comments},
            }

        results = await asyncio.gather(*[fetch_one_full(bvid) for bvid in req.bvids])
        return {"status": "success", "count": len(results), "data": results}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"批量获取完整数据失败: {e}")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)