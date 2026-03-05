import asyncio
import csv
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, AliasChoices
from typing import Any, Dict, List, Optional
import uuid
from datetime import datetime
import json
import io

from services.minimax_service import (
    generate_outline_with_minimax,
    generate_section_content_stream,
    refine_content_with_minimax,
    strip_think_content
)
from services.word_service import create_word_document
from services.storage import initialize_storage, save_papers
from services.community_storage import initialize_community_storage, save_community_data

app = FastAPI(title="YiziPaper API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

papers_db = initialize_storage()
paper_locks: dict[str, asyncio.Lock] = {}
community_db = initialize_community_storage()

class Section(BaseModel):
    id: str
    title: str
    content: str = ""
    word_count: int = 0

class Chapter(BaseModel):
    id: str
    title: str
    sections: List[Section] = Field(default_factory=list)

class Paper(BaseModel):
    id: str
    title: str
    paper_type: str = "graduation"
    direction: str = "finance"
    major: str = ""
    keywords: List[str] = Field(default_factory=list)
    word_count: int = 0
    target_word_count: int = 0
    generated_word_count: int = 0
    outline: List[Chapter] = Field(default_factory=list)
    status: str = "draft"
    created_at: str = ""
    updated_at: str = ""

class PaperCreate(BaseModel):
    title: str
    paper_type: str = "graduation"
    direction: str = "finance"
    major: str = ""
    keywords: List[str] = Field(default_factory=list)
    word_count: int = 10000
    custom_prompt: str = Field(
        default="",
        validation_alias=AliasChoices("custom_prompt", "customPrompt")
    )

class OutlineUpdate(BaseModel):
    outline: List[Chapter]

class SectionContent(BaseModel):
    content: str

class RefineRequest(BaseModel):
    instruction: str
    original_content: str = ""

class OutlineGenerateRequest(BaseModel):
    word_count: int = 10000


class CommunityPostCreate(BaseModel):
    title: str
    content: str
    author: str = "匿名用户"
    tags: List[str] = Field(default_factory=list)


class CommunityTemplateCreate(BaseModel):
    name: str
    description: str = ""
    content: str
    author: str = "匿名用户"
    category: str = "通用"


class CommissionCreate(BaseModel):
    title: str
    description: str
    requester: str = "匿名用户"
    deadline: str = ""


class AnalysisTextRequest(BaseModel):
    description: str


def get_paper_lock(paper_id: str) -> asyncio.Lock:
    lock = paper_locks.get(paper_id)
    if lock is None:
        lock = asyncio.Lock()
        paper_locks[paper_id] = lock
    return lock


def refresh_paper_metadata(paper: dict) -> None:
    total_words = 0
    has_sections = False
    has_any_content = False
    has_empty_sections = False

    for chapter in paper.get("outline", []):
        for section in chapter.get("sections", []):
            has_sections = True
            content = (section.get("content") or "").strip()
            word_count = len(content)
            section["word_count"] = word_count
            total_words += word_count
            if content:
                has_any_content = True
            else:
                has_empty_sections = True

    target_word_count = int(
        paper.get("target_word_count")
        or paper.get("word_count")
        or 10000
    )

    paper["target_word_count"] = target_word_count
    paper["generated_word_count"] = total_words
    # Keep word_count for frontend compatibility; it now represents target words.
    paper["word_count"] = target_word_count

    if not paper.get("outline"):
        paper["status"] = "draft"
    elif has_sections and has_any_content:
        paper["status"] = "generating" if has_empty_sections else "completed"
    else:
        paper["status"] = "outline_generated"

    paper["updated_at"] = datetime.now().isoformat()


def build_paper_context(paper: dict, chapter_id: str, section_id: str, max_chars: int = 6000) -> str:
    """Build in-paper context for generation, excluding current target section."""
    context_parts: list[str] = []
    for chapter in paper.get("outline", []):
        chapter_title = chapter.get("title", "")
        for section in chapter.get("sections", []):
            if chapter.get("id") == chapter_id and section.get("id") == section_id:
                continue
            content = (section.get("content") or "").strip()
            if not content:
                continue
            section_title = section.get("title", "")
            context_parts.append(f"[{chapter_title} - {section_title}]\n{content}")

    if not context_parts:
        return ""

    full_context = "\n\n".join(context_parts)
    if len(full_context) <= max_chars:
        return full_context

    return full_context[-max_chars:]


def utc_now_iso() -> str:
    return datetime.now().isoformat()


def keyword_score(text: str, keywords: List[str]) -> int:
    lower_text = text.lower()
    return sum(lower_text.count(k.lower()) for k in keywords)


def build_description_chart(description: str) -> Dict[str, Any]:
    buckets = [
        ("财务", ["财务", "资金", "成本", "预算", "收益", "利润", "现金流", "融资"]),
        ("市场", ["市场", "用户", "增长", "运营", "营销", "品牌"]),
        ("风控", ["风险", "合规", "审计", "监管", "安全"]),
        ("技术", ["系统", "平台", "算法", "数据", "模型", "自动化"]),
        ("执行", ["落地", "实施", "流程", "管理", "协同", "效率"])
    ]
    categories = []
    values = []
    for name, keys in buckets:
        categories.append(name)
        values.append(max(keyword_score(description, keys), 1))

    return {
        "type": "bar",
        "title": "描述要点分析",
        "categories": categories,
        "series": values
    }


def parse_csv_for_chart(file_content: str) -> Dict[str, Any]:
    rows = list(csv.DictReader(io.StringIO(file_content)))
    if not rows:
        raise ValueError("CSV没有可用数据")

    numeric_columns: Dict[str, List[float]] = {}
    for col in rows[0].keys():
        values = []
        for row in rows:
            raw = (row.get(col) or "").strip()
            if raw == "":
                continue
            try:
                values.append(float(raw))
            except ValueError:
                values = []
                break
        if values:
            numeric_columns[col] = values

    if not numeric_columns:
        raise ValueError("CSV中未找到数值列")

    top_columns = list(numeric_columns.keys())[:5]
    categories = top_columns
    series = [round(sum(numeric_columns[col]) / len(numeric_columns[col]), 2) for col in top_columns]

    return {
        "type": "bar",
        "title": "上传文件均值分析",
        "categories": categories,
        "series": series,
        "summary": {
            "rows": len(rows),
            "numeric_columns": len(numeric_columns)
        }
    }

@app.get("/")
async def root():
    return {"message": "YiziPaper API is running", "version": "1.0.0"}

@app.post("/api/papers", response_model=Paper)
async def create_paper(paper: PaperCreate):
    paper_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    new_paper = {
        "id": paper_id,
        "title": paper.title,
        "paper_type": paper.paper_type,
        "direction": paper.direction,
        "major": paper.major,
        "keywords": paper.keywords,
        "word_count": paper.word_count,
        "target_word_count": paper.word_count,
        "generated_word_count": 0,
        "custom_prompt": paper.custom_prompt,
        "outline": [],
        "status": "draft",
        "created_at": now,
        "updated_at": now
    }
    papers_db[paper_id] = new_paper
    save_papers(papers_db)
    return new_paper

@app.get("/api/papers")
async def get_papers():
    return list(papers_db.values())

@app.get("/api/papers/{paper_id}")
async def get_paper(paper_id: str):
    if paper_id not in papers_db:
        raise HTTPException(status_code=404, detail="Paper not found")
    return papers_db[paper_id]

@app.put("/api/papers/{paper_id}")
async def update_paper(paper_id: str, paper: Paper):
    if paper_id not in papers_db:
        raise HTTPException(status_code=404, detail="Paper not found")
    paper.updated_at = datetime.now().isoformat()
    papers_db[paper_id] = paper.model_dump()
    save_papers(papers_db)
    return papers_db[paper_id]

@app.delete("/api/papers/{paper_id}")
async def delete_paper(paper_id: str):
    if paper_id in papers_db:
        del papers_db[paper_id]
        save_papers(papers_db)
        return {"message": "Paper deleted"}
    raise HTTPException(status_code=404, detail="Paper not found")

@app.post("/api/papers/{paper_id}/outline")
async def generate_outline(paper_id: str, request: OutlineGenerateRequest = None, api_key: Optional[str] = None):
    if paper_id not in papers_db:
        raise HTTPException(status_code=404, detail="Paper not found")

    lock = get_paper_lock(paper_id)
    async with lock:
        paper = papers_db[paper_id]
        target_word_count = int(
            paper.get("target_word_count")
            or paper.get("word_count")
            or 10000
        )
        word_count = request.word_count if request else target_word_count
        direction = paper.get('direction', 'finance')
        custom_prompt = paper.get('custom_prompt', '')
        
        outline = generate_outline_with_minimax(
            paper["title"],
            paper["paper_type"],
            direction,
            paper["major"],
            paper["keywords"],
            word_count,
            custom_prompt,
            api_key
        )
        
        paper["outline"] = outline
        paper["target_word_count"] = word_count
        paper["word_count"] = word_count
        paper["status"] = "outline_generated"
        paper["updated_at"] = datetime.now().isoformat()
        save_papers(papers_db)
        return paper

@app.put("/api/papers/{paper_id}/outline")
async def update_outline(paper_id: str, outline_data: OutlineUpdate):
    if paper_id not in papers_db:
        raise HTTPException(status_code=404, detail="Paper not found")

    lock = get_paper_lock(paper_id)
    async with lock:
        paper = papers_db[paper_id]
        paper["outline"] = [chapter.model_dump() for chapter in outline_data.outline]
        refresh_paper_metadata(paper)
        save_papers(papers_db)
        return paper

@app.post("/api/papers/{paper_id}/sections/{chapter_id}/{section_id}/generate")
async def generate_section(paper_id: str, chapter_id: str, section_id: str, api_key: Optional[str] = None):
    if paper_id not in papers_db:
        raise HTTPException(status_code=404, detail="Paper not found")

    async def generate_stream():
        lock = get_paper_lock(paper_id)
        async with lock:
            paper = papers_db[paper_id]
            target_chapter = None
            target_section = None
            for chapter in paper.get("outline", []):
                if chapter.get("id") != chapter_id:
                    continue
                target_chapter = chapter
                for section in chapter.get("sections", []):
                    if section.get("id") == section_id:
                        target_section = section
                        break
                break

            if target_chapter is None or target_section is None:
                yield f"data: {json.dumps({'error': 'Section not found'}, ensure_ascii=False)}\n\n"
                return

            # Use all generated sections in the same paper as context memory.
            context_before = build_paper_context(paper, chapter_id, section_id)

            target_total_words = int(
                paper.get("target_word_count")
                or paper.get("word_count")
                or 10000
            )

            generated_without_target = 0
            remaining_sections = 0
            for chapter in paper.get("outline", []):
                for section in chapter.get("sections", []):
                    if section.get("id") == section_id and chapter.get("id") == chapter_id:
                        continue
                    section_text = (section.get("content") or "").strip()
                    generated_without_target += len(section_text)
                    if not section_text:
                        remaining_sections += 1

            target_current_text = (target_section.get("content") or "").strip()
            if target_current_text or remaining_sections == 0:
                remaining_sections += 1

            remaining_words = max(target_total_words - generated_without_target, 250)
            section_word_count = 300
            direction = paper.get('direction', 'finance')
            custom_prompt = paper.get('custom_prompt', '')

            full_content = ""
            for chunk in generate_section_content_stream(
                paper["title"],
                target_chapter["title"],
                target_section["title"],
                context_before,
                paper["keywords"],
                section_word_count,
                direction,
                custom_prompt,
                api_key
            ):
                full_content += chunk
                yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"
            
            full_content = strip_think_content(full_content)
            target_section["content"] = full_content
            refresh_paper_metadata(paper)
            save_papers(papers_db)
            
            yield f"data: {json.dumps({'done': True, 'word_count': len(full_content)}, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(generate_stream(), media_type="text/event-stream")

@app.post("/api/papers/{paper_id}/sections/{chapter_id}/{section_id}/refine")
async def refine_section(paper_id: str, chapter_id: str, section_id: str, request: RefineRequest, api_key: Optional[str] = None):
    if paper_id not in papers_db:
        raise HTTPException(status_code=404, detail="Paper not found")

    lock = get_paper_lock(paper_id)
    async with lock:
        paper = papers_db[paper_id]
        
        for chapter in paper["outline"]:
            if chapter["id"] == chapter_id:
                for section in chapter["sections"]:
                    if section["id"] == section_id:
                        original_content = request.original_content if request.original_content else section.get("content", "")
                        
                        refined_content = refine_content_with_minimax(
                            original_content,
                            request.instruction,
                            paper["title"],
                            api_key
                        )
                        
                        section["content"] = strip_think_content(refined_content)
                        refresh_paper_metadata(paper)
                        save_papers(papers_db)
                        return paper
    
    raise HTTPException(status_code=404, detail="Section not found")

@app.put("/api/papers/{paper_id}/sections/{chapter_id}/{section_id}")
async def update_section(paper_id: str, chapter_id: str, section_id: str, section: Section):
    if paper_id not in papers_db:
        raise HTTPException(status_code=404, detail="Paper not found")

    lock = get_paper_lock(paper_id)
    async with lock:
        paper = papers_db[paper_id]
        
        for chapter in paper["outline"]:
            if chapter["id"] == chapter_id:
                for i, section_item in enumerate(chapter["sections"]):
                    if section_item["id"] == section_id:
                        chapter["sections"][i] = section.model_dump()
                        refresh_paper_metadata(paper)
                        save_papers(papers_db)
                        return paper
    
    raise HTTPException(status_code=404, detail="Section not found")

@app.get("/api/papers/{paper_id}/export")
async def export_paper(paper_id: str):
    if paper_id not in papers_db:
        raise HTTPException(status_code=404, detail="Paper not found")
    
    paper = papers_db[paper_id]
    
    doc = create_word_document(paper)
    
    file_stream = io.BytesIO()
    doc.save(file_stream)
    file_stream.seek(0)
    
    filename = f"{paper['title']}.docx"
    
    return StreamingResponse(
        file_stream,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


@app.get("/api/community/posts")
async def list_posts():
    posts = sorted(community_db.get("posts", []), key=lambda x: x.get("created_at", ""), reverse=True)
    return posts


@app.post("/api/community/posts")
async def create_post(payload: CommunityPostCreate):
    post = {
        "id": str(uuid.uuid4()),
        "title": payload.title.strip(),
        "content": payload.content.strip(),
        "author": payload.author.strip() or "匿名用户",
        "tags": payload.tags,
        "likes": 0,
        "comments": 0,
        "created_at": utc_now_iso()
    }
    community_db["posts"].append(post)
    save_community_data(community_db)
    return post


@app.get("/api/community/templates")
async def list_templates():
    templates = sorted(community_db.get("templates", []), key=lambda x: x.get("created_at", ""), reverse=True)
    return templates


@app.post("/api/community/templates")
async def create_template(payload: CommunityTemplateCreate):
    template = {
        "id": str(uuid.uuid4()),
        "name": payload.name.strip(),
        "description": payload.description.strip(),
        "content": payload.content.strip(),
        "author": payload.author.strip() or "匿名用户",
        "category": payload.category.strip() or "通用",
        "uses": 0,
        "created_at": utc_now_iso()
    }
    community_db["templates"].append(template)
    save_community_data(community_db)
    return template


@app.get("/api/community/commissions")
async def list_commissions():
    commissions = sorted(community_db.get("commissions", []), key=lambda x: x.get("created_at", ""), reverse=True)
    return commissions


@app.post("/api/community/commissions")
async def create_commission(payload: CommissionCreate):
    commission = {
        "id": str(uuid.uuid4()),
        "title": payload.title.strip(),
        "description": payload.description.strip(),
        "requester": payload.requester.strip() or "匿名用户",
        "deadline": payload.deadline,
        "status": "OPEN",
        "applications": 0,
        "created_at": utc_now_iso()
    }
    community_db["commissions"].append(commission)
    save_community_data(community_db)
    return commission


@app.post("/api/community/analysis/description")
async def analyze_description(payload: AnalysisTextRequest):
    chart = build_description_chart(payload.description or "")
    return {
        "summary": "已根据描述提取核心维度，并生成可视化分析。",
        "chart": chart
    }


@app.post("/api/community/analysis/file")
async def analyze_file(file: UploadFile = File(...)):
    filename = file.filename or ""
    if not filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="当前仅支持CSV文件分析")

    content = (await file.read()).decode("utf-8", errors="ignore")
    if not content.strip():
        raise HTTPException(status_code=400, detail="上传文件内容为空")

    try:
        chart = parse_csv_for_chart(content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {
        "summary": f"文件分析完成：共{chart['summary']['rows']}行，识别出{chart['summary']['numeric_columns']}个数值列。",
        "chart": chart
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
