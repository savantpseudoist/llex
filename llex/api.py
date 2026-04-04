from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import os
import webview
from pydantic import BaseModel
from typing import List

app = FastAPI()

# Global services references
active_document = None
llm_bridge = None

def register_services(doc, bridge):
    global active_document, llm_bridge
    active_document = doc
    llm_bridge = bridge

# Get the path to the directory containing this file
base_dir = os.path.dirname(os.path.abspath(__file__))

# Mount static files
app.mount("/static", StaticFiles(directory=os.path.join(base_dir, "static")), name="static")

class SavePayload(BaseModel):
    html: str

@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    index_path = os.path.join(base_dir, "templates", "index.html")
    with open(index_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.get("/api/load")
def load_document():
    global active_document
    if active_document:
        return {"html": active_document.html_content}
    return {"html": ""}

@app.post("/api/save")
def save_document(payload: SavePayload):
    global active_document
    if active_document:
        active_document.html_content = payload.html
        if getattr(active_document, "path", None):
            active_document.save(active_document.path)
            return {"status": "saved"}
        else:
            return save_as_document(payload)
    return {"status": "error", "message": "No active document"}

@app.post("/api/save_as")
def save_as_document(payload: SavePayload):
    global active_document
    if active_document:
        active_document.html_content = payload.html
        try:
            window = webview.windows[0]
            try:
                dialog_type = webview.SAVE_DIALOG
            except AttributeError:
                dialog_type = 1 # Fallback integer for save dialog
            
            result = window.create_file_dialog(
                dialog_type, 
                save_filename=f"{active_document.title}.llex",
                file_types=('LLex Document (*.llex)', 'All files (*.*)')
            )
            if result and len(result) > 0:
                target_path = result[0]
                active_document.save(target_path)
                window.set_title(f"{active_document.path.name} - LLex")
                return {"status": "saved", "path": target_path}
            return {"status": "cancelled"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    return {"status": "error", "message": "No active document"}

class ScaffoldItem(BaseModel):
    id: int
    text: str
    instruction: str

class ScaffoldPayload(BaseModel):
    scaffolds: List[ScaffoldItem]

@app.post('/api/scaffold')
def execute_scaffolds(payload: ScaffoldPayload):
    if not llm_bridge:
        return {'status': 'error', 'message': 'LLM Bridge unavailable'}
    results = []
    for item in payload.scaffolds:
        result_text = llm_bridge.execute_instruction(item.text, item.instruction)
        results.append({'id': item.id, 'text': result_text})
    return {'status': 'success', 'results': results}

