from fastapi import FastAPI, WebSocket, Body, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Optional
import json
import sys
import os
import ast
from pydantic import BaseModel
import asyncio

# Add root directory to Python path to import core modules
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(ROOT_DIR)

from chat import CodeChat
from code_analyzer import CodeAnalyzer

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class CreateIndexRequest(BaseModel):
    repo_path: str

class IndexProgress:
    def __init__(self):
        self.current_file: str = ""
        self.total_files: int = 0
        self.processed_files: int = 0
        self.status: str = "idle"

# Global progress tracker
index_progress = IndexProgress()

# Store active WebSocket connections and their chat instances
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[WebSocket, str] = {}  # WebSocket -> index_id
        self.chat_instances: Dict[str, CodeChat] = {}  # index_id -> chat instance
        self.progress_subscribers: List[WebSocket] = []  # WebSockets subscribed to progress updates

    async def connect(self, websocket: WebSocket, index_id: str):
        await websocket.accept()
        self.active_connections[websocket] = index_id
        if index_id not in self.chat_instances:
            chat = CodeChat()
            if chat.load_index(index_id):
                self.chat_instances[index_id] = chat
            else:
                await websocket.close(code=1000, reason="Failed to load index")
                return False
        return True

    async def connect_progress(self, websocket: WebSocket):
        await websocket.accept()
        self.progress_subscribers.append(websocket)
        return True

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            del self.active_connections[websocket]
        if websocket in self.progress_subscribers:
            self.progress_subscribers.remove(websocket)

    async def broadcast_progress(self):
        progress_data = {
            "type": "progress",
            "current_file": index_progress.current_file,
            "total_files": index_progress.total_files,
            "processed_files": index_progress.processed_files,
            "status": index_progress.status
        }
        disconnected = []
        for ws in self.progress_subscribers:
            try:
                await ws.send_text(json.dumps(progress_data))
            except WebSocketDisconnect:
                disconnected.append(ws)
            except Exception as e:
                print(f"Error broadcasting progress: {str(e)}")
                disconnected.append(ws)
        
        # Clean up disconnected websockets
        for ws in disconnected:
            self.disconnect(ws)

    async def process_message(self, websocket: WebSocket, message: str):
        try:
            index_id = self.active_connections.get(websocket)
            if not index_id or index_id not in self.chat_instances:
                await websocket.close(code=1011, reason="Invalid session")
                return
            
            chat = self.chat_instances[index_id]
            similar_chunks = chat.search_similar(message)
            
            response_data = {
                "type": "response",
                "message": "No relevant code found." if not similar_chunks else chat.get_chat_response(message, similar_chunks),
                "chunks": [
                    {
                        "content": chunk["content"],
                        "file": chunk.get("file", "unknown"),
                        "start_line": chunk.get("start_line", 0),
                        "end_line": chunk.get("end_line", 0)
                    } 
                    for chunk in (similar_chunks or [])
                ]
            }
            await websocket.send_text(json.dumps(response_data))
        except Exception as e:
            print(f"Error processing message: {str(e)}")
            try:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "An error occurred while processing your message"
                }))
            except:
                pass

    async def heartbeat(self, websocket: WebSocket):
        """Send periodic heartbeat to keep connection alive"""
        while True:
            try:
                if websocket not in self.active_connections:
                    break
                await websocket.send_json({"type": "ping"})
                await asyncio.sleep(30)  # Send heartbeat every 30 seconds
            except WebSocketDisconnect:
                self.disconnect(websocket)
                break
            except Exception as e:
                print(f"Heartbeat error: {str(e)}")
                self.disconnect(websocket)
                break

manager = ConnectionManager()

@app.get("/api/indices")
async def get_indices():
    chat = CodeChat()
    indices = chat.list_available_indices()
    return [{"id": idx, "name": idx} for idx in indices]

@app.post("/api/indices/create")
async def create_index(request: CreateIndexRequest):
    try:
        # Convert relative path to absolute path relative to ROOT_DIR
        if request.repo_path == "." or not os.path.isabs(request.repo_path):
            repo_path = os.path.abspath(os.path.join(ROOT_DIR, request.repo_path))
        else:
            repo_path = request.repo_path

        # Update progress
        index_progress.status = "starting"
        index_progress.current_file = ""
        index_progress.processed_files = 0
        await manager.broadcast_progress()

        chat = CodeChat()
        name = os.path.basename(os.path.abspath(repo_path))
        success = chat.create_new_index(repo_path, name)
        
        # Update final progress
        index_progress.status = "completed" if success else "failed"
        await manager.broadcast_progress()

        if success:
            return {"id": name, "success": True}
        else:
            return {"success": False, "error": "Failed to create index"}, 500
    except Exception as e:
        index_progress.status = "failed"
        await manager.broadcast_progress()
        return {"success": False, "error": str(e)}, 500

@app.websocket("/ws/chat/{index_id}")
async def websocket_endpoint(websocket: WebSocket, index_id: str):
    manager = ConnectionManager()
    try:
        if await manager.connect(websocket, index_id):
            # Start heartbeat task
            heartbeat_task = asyncio.create_task(manager.heartbeat(websocket))
            
            try:
                while True:
                    message = await websocket.receive_text()
                    await manager.process_message(websocket, message)
            except WebSocketDisconnect:
                manager.disconnect(websocket)
            finally:
                heartbeat_task.cancel()
    except Exception as e:
        print(f"WebSocket error: {str(e)}")
        await websocket.close(code=1011)

@app.websocket("/ws/progress")
async def progress_endpoint(websocket: WebSocket):
    if not await manager.connect_progress(websocket):
        return
        
    # Start heartbeat in the background
    heartbeat_task = asyncio.create_task(manager.heartbeat(websocket))
    
    try:
        while True:
            await websocket.receive_text()  # Keep connection alive
            await asyncio.sleep(0.1)  # Prevent tight loop
    except WebSocketDisconnect:
        print("Progress client disconnected normally")
    except Exception as e:
        print(f"Progress WebSocket Error: {str(e)}")
    finally:
        heartbeat_task.cancel()
        manager.disconnect(websocket)

class CodeStructureAnalyzer(ast.NodeVisitor):
    def __init__(self):
        self.nodes = []
        self.links = []
        self.current_class = None
        self.current_function = None
        self.imports = {}
        self.node_id = 0
        self.base_classes = {}
        self.module_nodes = set()  # Track created module nodes

    def get_id(self) -> int:
        self.node_id += 1
        return self.node_id

    def add_module_node(self, module_name: str) -> str:
        if module_name not in self.module_nodes:
            module_id = f"module_{self.get_id()}"
            self.nodes.append({
                "id": module_id,
                "name": module_name,
                "type": "module"
            })
            self.module_nodes.add(module_name)
            self.imports[module_name] = module_id
            return module_id
        return self.imports[module_name]

    def visit_ClassDef(self, node):
        class_id = f"class_{self.get_id()}"
        class_name = node.name
        self.nodes.append({
            "id": class_id,
            "name": class_name,
            "type": "class"
        })
        self.base_classes[class_name] = class_id
        
        # Handle inheritance
        for base in node.bases:
            if isinstance(base, ast.Name):
                base_name = base.id
                # Check if base class is imported
                if base_name in self.imports:
                    self.links.append({
                        "source": class_id,
                        "target": self.imports[base_name],
                        "type": "inherits"
                    })
                # Check if base class is defined in the codebase
                elif base_name in self.base_classes:
                    self.links.append({
                        "source": class_id,
                        "target": self.base_classes[base_name],
                        "type": "inherits"
                    })

        old_class = self.current_class
        self.current_class = class_id
        self.generic_visit(node)
        self.current_class = old_class

    def visit_Import(self, node):
        for name in node.names:
            module_name = name.name.split('.')[0]  # Get root module name
            module_id = self.add_module_node(module_name)
            self.imports[name.asname or name.name] = module_id

    def visit_ImportFrom(self, node):
        if node.module:
            module_name = node.module.split('.')[0]  # Get root module name
            module_id = self.add_module_node(module_name)
            for name in node.names:
                if name.asname:
                    self.imports[name.asname] = module_id
                else:
                    self.imports[name.name] = module_id

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name) and self.current_function:
            func_name = node.func.id
            if func_name in self.imports:
                self.links.append({
                    "source": self.current_function,
                    "target": self.imports[func_name],
                    "type": "calls"
                })
        elif isinstance(node.func, ast.Attribute) and self.current_function:
            # Handle method calls on imported modules
            if isinstance(node.func.value, ast.Name):
                module_name = node.func.value.id
                if module_name in self.imports:
                    self.links.append({
                        "source": self.current_function,
                        "target": self.imports[module_name],
                        "type": "calls"
                    })
        self.generic_visit(node)

@app.get("/api/code-structure/{index_id}")
async def get_code_structure(index_id: str):
    try:
        chat = CodeChat()
        if not chat.load_index(index_id):
            return {"error": "Failed to load index"}, 404

        # Get all Python files in the indexed codebase
        code_files = []
        for root, _, files in os.walk(ROOT_DIR):
            for file in files:
                if file.endswith('.py'):
                    code_files.append(os.path.join(root, file))

        # Analyze code structure
        analyzer = CodeStructureAnalyzer()
        for file_path in code_files:
            with open(file_path, 'r') as f:
                try:
                    tree = ast.parse(f.read())
                    analyzer.visit(tree)
                except:
                    continue

        return {
            "nodes": analyzer.nodes,
            "links": analyzer.links
        }
    except Exception as e:
        return {"error": str(e)}, 500 