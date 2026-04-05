import asyncio

# Fix for Vercel's outdated sqlite3 version (required by CrewAI/ChromaDB)
try:
    __import__('pysqlite3')
    import sys
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
except ImportError:
    pass
import json
import os
import re
import random
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from crewai import Agent, Task, Crew, Process
from langchain_groq import ChatGroq
from dotenv import load_dotenv

load_dotenv()

# ==========================================
# LAYOUT ENGINE
# ==========================================

MANGA_TEMPLATES = {
    1: [[{"x": 0, "y": 0, "w": 1.0, "h": 1.0}]],
    2: [
        [{"x": 0, "y": 0, "w": 1.0, "h": 0.5}, {"x": 0, "y": 0.5, "w": 1.0, "h": 0.5}],
        [{"x": 0, "y": 0, "w": 0.5, "h": 1.0}, {"x": 0.5, "y": 0, "w": 0.5, "h": 1.0}],
    ],
    3: [
        [{"x": 0, "y": 0, "w": 1.0, "h": 0.4}, {"x": 0, "y": 0.4, "w": 0.5, "h": 0.6}, {"x": 0.5, "y": 0.4, "w": 0.5, "h": 0.6}],
        [{"x": 0, "y": 0, "w": 0.6, "h": 0.5}, {"x": 0.6, "y": 0, "w": 0.4, "h": 0.5}, {"x": 0, "y": 0.5, "w": 1.0, "h": 0.5}],
        [{"x": 0, "y": 0, "w": 0.5, "h": 0.55}, {"x": 0.5, "y": 0, "w": 0.5, "h": 0.55}, {"x": 0, "y": 0.55, "w": 1.0, "h": 0.45}],
    ],
    4: [
        [{"x": 0, "y": 0, "w": 0.5, "h": 0.45}, {"x": 0.5, "y": 0, "w": 0.5, "h": 0.45}, {"x": 0, "y": 0.45, "w": 0.6, "h": 0.55}, {"x": 0.6, "y": 0.45, "w": 0.4, "h": 0.55}],
        [{"x": 0, "y": 0, "w": 1.0, "h": 0.35}, {"x": 0, "y": 0.35, "w": 0.5, "h": 0.3}, {"x": 0.5, "y": 0.35, "w": 0.5, "h": 0.3}, {"x": 0, "y": 0.65, "w": 1.0, "h": 0.35}],
        [{"x": 0, "y": 0, "w": 0.6, "h": 0.5}, {"x": 0.6, "y": 0, "w": 0.4, "h": 0.25}, {"x": 0.6, "y": 0.25, "w": 0.4, "h": 0.25}, {"x": 0, "y": 0.5, "w": 1.0, "h": 0.5}],
    ],
    5: [
        [{"x": 0, "y": 0, "w": 1.0, "h": 0.3}, {"x": 0, "y": 0.3, "w": 0.5, "h": 0.35}, {"x": 0.5, "y": 0.3, "w": 0.5, "h": 0.35}, {"x": 0, "y": 0.65, "w": 0.4, "h": 0.35}, {"x": 0.4, "y": 0.65, "w": 0.6, "h": 0.35}],
        [{"x": 0, "y": 0, "w": 0.55, "h": 0.4}, {"x": 0.55, "y": 0, "w": 0.45, "h": 0.4}, {"x": 0, "y": 0.4, "w": 0.35, "h": 0.3}, {"x": 0.35, "y": 0.4, "w": 0.65, "h": 0.3}, {"x": 0, "y": 0.7, "w": 1.0, "h": 0.3}],
    ],
    6: [
        [{"x": 0, "y": 0, "w": 0.6, "h": 0.33}, {"x": 0.6, "y": 0, "w": 0.4, "h": 0.33}, {"x": 0, "y": 0.33, "w": 0.35, "h": 0.34}, {"x": 0.35, "y": 0.33, "w": 0.65, "h": 0.34}, {"x": 0, "y": 0.67, "w": 0.5, "h": 0.33}, {"x": 0.5, "y": 0.67, "w": 0.5, "h": 0.33}],
        [{"x": 0, "y": 0, "w": 0.5, "h": 0.33}, {"x": 0.5, "y": 0, "w": 0.5, "h": 0.33}, {"x": 0, "y": 0.33, "w": 0.5, "h": 0.34}, {"x": 0.5, "y": 0.33, "w": 0.5, "h": 0.34}, {"x": 0, "y": 0.67, "w": 0.5, "h": 0.33}, {"x": 0.5, "y": 0.67, "w": 0.5, "h": 0.33}],
    ],
    7: [
        [{"x": 0, "y": 0, "w": 1.0, "h": 0.25}, {"x": 0, "y": 0.25, "w": 0.33, "h": 0.25}, {"x": 0.33, "y": 0.25, "w": 0.34, "h": 0.25}, {"x": 0.67, "y": 0.25, "w": 0.33, "h": 0.25}, {"x": 0, "y": 0.5, "w": 0.5, "h": 0.25}, {"x": 0.5, "y": 0.5, "w": 0.5, "h": 0.25}, {"x": 0, "y": 0.75, "w": 1.0, "h": 0.25}],
    ],
}

EMPHASIS_MAP = {
    "SPLASH PAGE": "dominant",
    "DOUBLE SPREAD": "dominant",
    "ACTION": "high",
    "CLOSE-UP": "high",
    "EXTREME CLOSE-UP": "high",
    "WIDE SHOT": "medium",
    "ESTABLISHING": "medium",
    "MEDIUM SHOT": "standard",
    "REACTION": "standard",
    "OVER-THE-SHOULDER": "standard",
    "BIRDS EYE": "medium",
    "WORMS EYE": "medium",
}

def get_template_for_panels(panel_count, style="manga"):
    count = min(panel_count, 7)
    count = max(count, 1)
    templates = MANGA_TEMPLATES.get(count, MANGA_TEMPLATES[4])
    return random.choice(templates)

def adjust_for_emphasis(panels, template):
    adjusted = []
    for i, panel in enumerate(panels):
        if i >= len(template):
            break
        layout = template[i].copy()
        panel_type = panel.get("type", "MEDIUM SHOT").upper()
        emphasis = EMPHASIS_MAP.get(panel_type, "standard")
        if panel_type in ("SPLASH PAGE", "DOUBLE SPREAD"):
            layout = {"x": 0, "y": 0, "w": 1.0, "h": 1.0}
        adjusted.append({**panel, "layout": layout, "emphasis": emphasis})
    return adjusted

def generate_layouts(script_data, style="manga", reading_direction="rtl"):
    if not script_data or "pages" not in script_data: return []
    layouts = []
    for page_data in script_data["pages"]:
        panels = page_data.get("panels", [])
        panel_count = len(panels)
        if panel_count == 0:
            layouts.append({"id": page_data.get("page_number", len(layouts) + 1), "panels": []})
            continue
        has_splash = any(p.get("type", "").upper() in ("SPLASH PAGE", "DOUBLE SPREAD") for p in panels)
        if has_splash and panel_count == 1:
            template = [{"x": 0, "y": 0, "w": 1.0, "h": 1.0}]
        else:
            template = get_template_for_panels(panel_count, style)
        adjusted_panels = adjust_for_emphasis(panels, template)
        if reading_direction == "rtl" and style == "manga":
            for p in adjusted_panels:
                if "layout" in p:
                    p["layout"]["x"] = 1.0 - p["layout"]["x"] - p["layout"]["w"]
        layouts.append({
            "id": page_data.get("page_number", len(layouts) + 1),
            "title": page_data.get("title", ""),
            "panels": adjusted_panels,
        })
    return layouts

# ==========================================
# AGENTS
# ==========================================

def create_agents(llm):
    lead_writer = Agent(
        role="Lead Writer — Master Storyteller & Script Architect",
        goal="Transform a raw story outline into a richly detailed, professionally paced manga script.",
        backstory="You are a veteran manga writer. You specialize in breaking stories into page-by-page scene structures that translate perfectly to visual panels.",
        llm=llm, verbose=False, allow_delegation=False,
    )
    pacing_editor = Agent(
        role="Pacing & Panel Editor — Visual Layout Specialist",
        goal="Convert scene breakdowns into precise panel-by-panel layouts with exact panel types and sizes.",
        backstory="You are an expert manga editor. Your specialty is visual pacing and panel composition.",
        llm=llm, verbose=False, allow_delegation=False,
    )
    dialogue_polisher = Agent(
        role="Dialogue & SFX Polisher — Language & Sound Specialist",
        goal="Refine all dialogue. Add sound effects (SFX) text, ensuring all text fits within typical manga speech bubble constraints.",
        backstory="You are a dialogue specialist and letterer. You know that manga dialogue must be radically concise.",
        llm=llm, verbose=False, allow_delegation=False,
    )
    return lead_writer, pacing_editor, dialogue_polisher

# ==========================================
# TASKS
# ==========================================

def create_tasks(lead_writer, pacing_editor, dialogue_polisher, outline, genre, style, pages, reading_direction):
    genre_context = {"shonen": "action", "seinen": "thriller", "shoujo": "drama"}.get(genre, genre)
    story_task = Task(
        description=f"Break down this outline into a {pages}-page scene structure.\nOUTLINE: {outline}\nGENRE: {genre}\n",
        agent=lead_writer,
        expected_output=f"A detailed page-by-page scene breakdown for {pages} pages.",
    )
    panel_task = Task(
        description=f"Convert the scene breakdown into a panel-by-panel script for exactly {pages} pages. OUTPUT JSON.",
        agent=pacing_editor,
        expected_output=f"Valid JSON with exactly {pages} pages and panel layouts.",
        context=[story_task],
    )
    dialogue_task = Task(
        description="Add polished dialogue, SFX, and text elements to the panels. OUTPUT COMPLETE MATCHING JSON.",
        agent=dialogue_polisher,
        expected_output="A complete, valid JSON manga script over all pages.",
        context=[story_task, panel_task],
    )
    return [story_task, panel_task, dialogue_task]

# ==========================================
# CREW PIPELINE
# ==========================================

def get_llm():
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key or api_key == "your_groq_api_key_here":
        raise ValueError("GROQ_API_KEY not set. Get one at https://console.groq.com")
    return ChatGroq(temperature=0.7, model_name="llama-3.3-70b-versatile", groq_api_key=api_key)

def extract_json_from_text(text):
    try: return json.loads(text)
    except: pass
    json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if json_match:
        try: return json.loads(json_match.group(1))
        except: pass
    json_match = re.search(r'\{[\s\S]*\}', text)
    if json_match:
        try: return json.loads(json_match.group(0))
        except: pass
    return None

def create_fallback_script(raw_text, num_pages):
    return {"pages": [{"page_number": i+1, "panels": [{"type": "WIDE SHOT", "size": "full", "description": "Page " + str(i+1), "dialogue": [], "sfx": [], "notes": ""}]} for i in range(num_pages)]}

async def run_generation_pipeline(outline, genre, style, chapters, pages, reading_direction):
    llm = get_llm()
    lead_writer, pacing_editor, dialogue_polisher = create_agents(llm)
    tasks = create_tasks(lead_writer, pacing_editor, dialogue_polisher, outline, genre, style, pages, reading_direction)
    agent_map = {0: ("writer", "Lead Writer"), 1: ("pacer", "Pacing Editor"), 2: ("polisher", "Dialogue Polisher")}
    crew = Crew(agents=[lead_writer, pacing_editor, dialogue_polisher], tasks=tasks, process=Process.sequential, verbose=False)

    for idx, (agent_id, agent_name) in agent_map.items():
        yield f"data: {json.dumps({'event': 'agent_start', 'agent_id': agent_id, 'agent_name': agent_name, 'status': 'waiting'})}\n\n"

    try:
        yield f"data: {json.dumps({'event': 'agent_start', 'agent_id': 'writer', 'agent_name': 'Lead Writer', 'status': 'thinking'})}\n\n"
        result = crew.kickoff()
        raw_output = str(result)
        
        task_outputs = [str(task.output) if hasattr(task, 'output') and task.output else "" for task in tasks]
        for idx, output in enumerate(task_outputs):
            agent_id, agent_name = agent_map.get(idx, ("unknown", "Unknown"))
            yield f"data: {json.dumps({'event': 'agent_start', 'agent_id': agent_id, 'agent_name': agent_name, 'status': 'thinking'})}\n\n"
            chunk_size = 80
            for i in range(0, len(output), chunk_size):
                yield f"data: {json.dumps({'event': 'agent_chunk', 'agent_id': agent_id, 'content': output[i:i + chunk_size]})}\n\n"
            yield f"data: {json.dumps({'event': 'agent_complete', 'agent_id': agent_id})}\n\n"

        final_output = task_outputs[-1] if task_outputs else raw_output
        script_data = extract_json_from_text(final_output) or create_fallback_script(raw_output, pages)
        layout_data = generate_layouts(script_data, style, reading_direction)

        yield f"data: {json.dumps({'event': 'script', 'script': script_data})}\n\n"
        yield f"data: {json.dumps({'event': 'panel_layout', 'pages': layout_data})}\n\n"
        yield f"data: {json.dumps({'event': 'complete', 'script': script_data, 'pages': layout_data})}\n\n"

    except Exception as e:
        yield f"data: {json.dumps({'event': 'error', 'message': str(e)})}\n\n"

async def run_edit_pipeline(prompt, current_script, genre, style):
    llm = get_llm()
    _, _, dialogue_polisher = create_agents(llm)
    edit_task = Task(description=f"USER REQUEST: {prompt}\nCURRENT SCRIPT JSON: {json.dumps(current_script)}\nUpdate script to match request. OUTPUT JSON.", agent=dialogue_polisher, expected_output="A complete updated JSON script.")
    crew = Crew(agents=[dialogue_polisher], tasks=[edit_task], process=Process.sequential, verbose=False)

    yield f"data: {json.dumps({'event': 'agent_start', 'agent_id': 'polisher', 'agent_name': 'Dialogue Polisher', 'status': 'thinking'})}\n\n"
    try:
        result = crew.kickoff()
        output = str(result)
        for i in range(0, len(output), 80):
            yield f"data: {json.dumps({'event': 'agent_chunk', 'agent_id': 'polisher', 'content': output[i:i + 80]})}\n\n"
        yield f"data: {json.dumps({'event': 'agent_complete', 'agent_id': 'polisher'})}\n\n"

        script_data = extract_json_from_text(output)
        if script_data:
            layout_data = generate_layouts(script_data, style, "rtl")
            yield f"data: {json.dumps({'event': 'complete', 'script': script_data, 'pages': layout_data})}\n\n"
        else:
            yield f"data: {json.dumps({'event': 'error', 'message': 'Could not parse edited script'})}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'event': 'error', 'message': str(e)})}\n\n"

# ==========================================
# FASTAPI SERVER
# ==========================================

app = FastAPI(title="MangaPost API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

class GenerateRequest(BaseModel):
    outline: str
    genre: str = "shonen"
    style: str = "manga"
    chapters: int = 1
    pages_per_chapter: int = 20
    reading_direction: str = "rtl"

class EditRequest(BaseModel):
    prompt: str
    current_script: Optional[dict] = None
    genre: str = "shonen"
    style: str = "manga"

@app.get("/api/health")
async def health_check():
    return {"status": "ok"}

@app.post("/api/generate")
async def generate_script(request: GenerateRequest):
    if not request.outline.strip(): raise HTTPException(status_code=400, detail="Empty outline")
    async def event_stream():
        async for event in run_generation_pipeline(request.outline, request.genre, request.style, request.chapters, request.pages_per_chapter, request.reading_direction):
            yield event
            await asyncio.sleep(0.01)
    return StreamingResponse(event_stream(), media_type="text/event-stream")

@app.post("/api/edit")
async def edit_script(request: EditRequest):
    if not request.prompt.strip(): raise HTTPException(status_code=400, detail="Empty prompt")
    async def event_stream():
        async for event in run_edit_pipeline(request.prompt, request.current_script, request.genre, request.style):
            yield event
            await asyncio.sleep(0.01)
    return StreamingResponse(event_stream(), media_type="text/event-stream")

# Note: Vercel hooks directly into `app`, starting uvicorn is only for local
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("index:app", host="0.0.0.0", port=8000, reload=True)
