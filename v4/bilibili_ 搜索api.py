import re
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from bilibili_api import search

# 初始化独立的 FastAPI 实例
app = FastAPI(title="B站投研雷达API", description="用于自动化检索和初筛B站视频")


# 定义请求体的数据模型
class SearchRequest(BaseModel):
    keyword: str
    order_type: str = "totalrank"  # 可接受的值: totalrank, pubdate, click
    time_range: int = 20  # 默认 20，触发 bilibili_api 中 10-30 分钟的区间
    page: int = 1


# 排序策略映射字典（核心解耦逻辑）
ORDER_MAP = {
    "totalrank": search.OrderVideo.TOTALRANK,
    "pubdate": search.OrderVideo.PUBDATE,
    "click": search.OrderVideo.CLICK
}


@app.post("/api/bili/search_videos")
async def search_videos(req: SearchRequest):
    print(f"📡 启动雷达扫描 | 关键词: '{req.keyword}' | 排序: {req.order_type} | 页码: {req.page}")

    # 校验排序参数是否合法
    if req.order_type.lower() not in ORDER_MAP:
        raise HTTPException(status_code=400, detail="排序方式错误，仅支持 totalrank, pubdate, click")

    actual_order = ORDER_MAP[req.order_type.lower()]

    try:
        # 发起底层 API 请求，取消了分区限制以扩大搜索视野
        res = await search.search_by_type(
            keyword=req.keyword,
            search_type=search.SearchObjectType.VIDEO,
            order_type=actual_order,
            time_range=req.time_range,
            page=req.page
        )

        video_list = res.get('result', [])
        extracted_data = []

        for video in video_list:
            bvid = video.get('bvid')
            raw_title = video.get('title', '')

            # 清洗 B 站搜索结果自带的 HTML 高亮标签
            clean_title = re.sub(r'<[^>]+>', '', raw_title)

            if bvid and clean_title:
                extracted_data.append({
                    "bvid": bvid,
                    "title": clean_title
                })

        print(f"✅ 扫描完成，共捕获 {len(extracted_data)} 个高价值目标。")

        return {
            "status": "success",
            "count": len(extracted_data),
            "data": extracted_data
        }

    except Exception as e:
        print(f"❌ 雷达扫描异常: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    # 独立微服务，绑定在 8003 端口
    uvicorn.run(app, host="0.0.0.0", port=8003)