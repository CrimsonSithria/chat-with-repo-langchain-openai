from fastapi import FastAPI, WebSocket, Body, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Optional
import json
import sys
import os
import ast
from pydantic import BaseModel
import asyncio
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

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
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.progress_connections: List[WebSocket] = []
        self.chats: Dict[str, CodeChat] = {}

    async def send_log(self, websocket: WebSocket, message: str):
        """Send a log message to the client."""
        await websocket.send_json({
            "type": "log",
            "content": message
        })

    async def process_message(self, websocket: WebSocket, message: str):
        """Process a chat message and send the response."""
        index_id = next((k for k, v in self.active_connections.items() if websocket in v), None)
        if not index_id or index_id not in self.chats:
            await websocket.send_json({
                "type": "error",
                "content": "Chat session not found"
            })
            return

        chat = self.chats[index_id]
        try:
            # Send log that we're processing
            await self.send_log(websocket, "Processing your message...")
            
            # Get similar chunks first
            similar_chunks = chat.search_similar(message)
            
            # Log chunk information
            chunk_info = "\nRelevant code chunks found:"
            total_tokens = 0
            for i, chunk in enumerate(similar_chunks, 1):
                chunk_tokens = chat.count_tokens(chunk["content"])
                total_tokens += chunk_tokens
                chunk_info += f"\n{i}. File: {chunk.get('file', 'unknown')}"
                chunk_info += f"\n   Lines {chunk.get('start_line', '?')}-{chunk.get('end_line', '?')}"
                chunk_info += f"\n   Tokens: {chunk_tokens}"
                chunk_info += f"\n   Distance: {chunk.get('distance', '?'):.3f}"
            
            chunk_info += f"\nTotal tokens from chunks: {total_tokens}"
            await self.send_log(websocket, chunk_info)
            
            # Get response from chat
            response, token_usage = await chat.get_response(message)
            
            # Send token usage log
            if token_usage:
                usage_log = f"\nToken Usage Summary:"
                usage_log += f"\n- Prompt tokens: {token_usage.get('prompt', 0)}"
                usage_log += f"\n- Completion tokens: {token_usage.get('completion', 0)}"
                usage_log += f"\n- Total tokens: {token_usage.get('total', 0)}"
                usage_log += f"\n- Reasoning tokens: {token_usage.get('reasoning', 0)}"
                await self.send_log(websocket, usage_log)
            
            # Send the actual response
            await websocket.send_json({
                "type": "chat",
                "role": "assistant",
                "content": response,
                "token_usage": token_usage,
                "chunks_info": {
                    "count": len(similar_chunks),
                    "total_tokens": total_tokens,
                    "chunks": [{"file": c.get("file"), 
                              "start_line": c.get("start_line"),
                              "end_line": c.get("end_line"),
                              "tokens": chat.count_tokens(c["content"]),
                              "distance": c.get("distance")} 
                             for c in similar_chunks]
                }
            })
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            await websocket.send_json({
                "type": "error",
                "content": str(e)
            })

    async def connect(self, websocket: WebSocket, index_id: str):
        """Connect a WebSocket client."""
        try:
            await websocket.accept()
            
            # Create chat instance if needed
            if index_id not in self.chats:
                chat = CodeChat()
                logger.info(f"Loading index: {index_id}")
                if not chat.load_index(index_id):
                    logger.error(f"Failed to load index: {index_id}")
                    await websocket.send_json({
                        "type": "error",
                        "content": "Failed to load index. Please try again."
                    })
                    return False
                self.chats[index_id] = chat
            
            self.active_connections[index_id] = [websocket]
            logger.info(f"Client connected to index: {index_id}")
            
            # Send ready message
            await websocket.send_json({
                "type": "status",
                "content": "ready"
            })
            return True
            
        except Exception as e:
            logger.error(f"Error connecting client: {e}")
            try:
                await websocket.send_json({
                    "type": "error",
                    "content": f"Connection error: {str(e)}"
                })
            except:
                pass
            return False

    async def connect_progress(self, websocket: WebSocket):
        await websocket.accept()
        self.progress_connections.append(websocket)
        return True

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            del self.active_connections[websocket]
        if websocket in self.progress_connections:
            self.progress_connections.remove(websocket)

    async def broadcast_progress(self):
        progress_data = {
            "type": "progress",
            "current_file": index_progress.current_file,
            "total_files": index_progress.total_files,
            "processed_files": index_progress.processed_files,
            "status": index_progress.status
        }
        disconnected = []
        for ws in self.progress_connections:
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
    """Get list of available indices."""
    try:
        chat = CodeChat()
        indices = chat.list_available_indices()
        return [{"id": idx, "name": idx} for idx in indices]
    except Exception as e:
        logger.error(f"Error listing indices: {e}")
        return {"error": str(e)}, 500

@app.post("/api/indices/create")
async def create_index(request: CreateIndexRequest):
    """Create a new index."""
    try:
        # Use the provided path directly if it's absolute
        repo_path = request.repo_path

        # Validate the path exists
        if not os.path.exists(repo_path):
            logger.error(f"Path does not exist: {repo_path}")
            return {"success": False, "error": f"Path does not exist: {repo_path}"}, 404

        # Update progress
        index_progress.status = "starting"
        index_progress.current_file = ""
        index_progress.processed_files = 0
        await manager.broadcast_progress()

        chat = CodeChat()
        # Use the last directory name as the index name
        name = os.path.basename(os.path.normpath(repo_path))
        
        logger.info(f"Creating index for path: {repo_path} with name: {name}")
        
        # Check if index already exists
        if name in chat.list_available_indices():
            logger.warning(f"Index already exists: {name}")
            return {"success": False, "error": f"Index already exists: {name}"}, 400
            
        success = chat.create_new_index(repo_path, name)
        
        # Update final progress
        index_progress.status = "completed" if success else "failed"
        await manager.broadcast_progress()

        if success:
            logger.info(f"Successfully created index: {name}")
            return {"id": name, "success": True}
        else:
            logger.error("Failed to create index")
            return {"success": False, "error": "Failed to create index"}, 500
    except Exception as e:
        logger.error(f"Error creating index: {e}")
        index_progress.status = "failed"
        await manager.broadcast_progress()
        return {"success": False, "error": str(e)}, 500

@app.websocket("/ws/chat/{index_id}")
async def websocket_endpoint(websocket: WebSocket, index_id: str):
    try:
        if await manager.connect(websocket, index_id):
            # Start heartbeat task
            heartbeat_task = asyncio.create_task(manager.heartbeat(websocket))
            
            try:
                while True:
                    data = await websocket.receive_json()
                    if data.get("type") == "chat":
                        await manager.process_message(websocket, data.get("content", ""))
                    elif data.get("type") == "pong":
                        continue  # Ignore pong responses
            except WebSocketDisconnect:
                logger.info(f"Client disconnected from index: {index_id}")
                manager.disconnect(websocket)
            except Exception as e:
                logger.error(f"Error processing message: {e}")
            finally:
                heartbeat_task.cancel()
                manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.close(code=1011)
        except:
            pass

@app.websocket("/ws/progress")
async def progress_endpoint(websocket: WebSocket):
    try:
        if await manager.connect_progress(websocket):
            # Start heartbeat task
            heartbeat_task = asyncio.create_task(manager.heartbeat(websocket))
            
            try:
                while True:
                    await websocket.receive_text()  # Keep connection alive
                    await asyncio.sleep(0.1)  # Prevent tight loop
            except WebSocketDisconnect:
                logger.info("Progress client disconnected normally")
            except Exception as e:
                logger.error(f"Progress WebSocket error: {e}")
            finally:
                heartbeat_task.cancel()
                manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"Progress WebSocket error: {e}")
        try:
            await websocket.close(code=1011)
        except:
            pass

class CodeStructureAnalyzer(ast.NodeVisitor):
    def __init__(self):
        self.nodes = []
        self.links = []
        self.current_class = None
        self.current_function = None
        self.imports = {}
        self.node_id = 0
        self.base_classes = {}
        self.module_nodes = {}  # Track module nodes by full path
        self.current_module = None
        self.function_nodes = {}  # Track function nodes
        self.module_path = None  # Current module path
        
    def get_id(self) -> int:
        self.node_id += 1
        return self.node_id
        
    def add_module_node(self, module_path: str, module_name: str) -> str:
        """Add a module node if it doesn't exist."""
        if module_path not in self.module_nodes:
            module_id = f"module_{self.get_id()}"
            self.nodes.append({
                "id": module_id,
                "name": module_name,
                "type": "module",
                "path": module_path
            })
            self.module_nodes[module_path] = module_id
            return module_id
        return self.module_nodes[module_path]
        
    def visit_Module(self, node):
        """Process module-level nodes."""
        if not self.current_module:
            module_name = os.path.basename(self.module_path) if self.module_path else "unknown"
            self.current_module = self.add_module_node(self.module_path, module_name)
        self.generic_visit(node)
        
    def visit_ClassDef(self, node):
        """Process class definitions."""
        # Only process classes that:
        # 1. Have methods
        # 2. Are inherited from
        # 3. Have base classes
        has_methods = any(isinstance(item, ast.FunctionDef) for item in node.body)
        has_base_classes = len(node.bases) > 0
        
        if not (has_methods or has_base_classes):
            return
            
        class_id = f"class_{self.get_id()}"
        class_name = node.name
        
        # Add class node
        self.nodes.append({
            "id": class_id,
            "name": class_name,
            "type": "class",
            "module": os.path.basename(self.module_path) if self.module_path else "unknown"
        })
        self.base_classes[class_name] = class_id
        
        # Link class to its module
        if self.current_module:
            self.links.append({
                "source": class_id,
                "target": self.current_module,
                "type": "belongs_to"
            })
        
        # Handle inheritance
        for base in node.bases:
            if isinstance(base, ast.Name):
                base_name = base.id
                if base_name in self.base_classes:
                    self.links.append({
                        "source": class_id,
                        "target": self.base_classes[base_name],
                        "type": "inherits"
                    })
        
        # Process class body
        old_class = self.current_class
        self.current_class = class_id
        self.generic_visit(node)
        self.current_class = old_class
        
    def visit_FunctionDef(self, node):
        """Process function definitions."""
        # Only process functions that:
        # 1. Are class methods
        # 2. Have significant complexity (calls other functions or has complex logic)
        # 3. Are called by other functions
        
        # Skip simple getter/setter methods
        if len(node.body) <= 2 and not any(isinstance(n, ast.Call) for n in ast.walk(node)):
            return
            
        func_id = f"function_{self.get_id()}"
        func_name = f"{node.name}"
        if self.current_class:
            func_name = f"{self.base_classes[self.current_class]}.{node.name}"
        
        # Add function node
        self.nodes.append({
            "id": func_id,
            "name": func_name,
            "type": "function",
            "module": os.path.basename(self.module_path) if self.module_path else "unknown"
        })
        self.function_nodes[func_name] = func_id
        
        # Link function to its class or module
        if self.current_class:
            self.links.append({
                "source": func_id,
                "target": self.current_class,
                "type": "belongs_to"
            })
        elif self.current_module:
            self.links.append({
                "source": func_id,
                "target": self.current_module,
                "type": "belongs_to"
            })
        
        # Process function body
        old_function = self.current_function
        self.current_function = func_id
        self.generic_visit(node)
        self.current_function = old_function
        
    def visit_Call(self, node):
        """Process function calls."""
        if isinstance(node.func, ast.Name) and self.current_function:
            func_name = node.func.id
            if func_name in self.function_nodes:
                self.links.append({
                    "source": self.current_function,
                    "target": self.function_nodes[func_name],
                    "type": "calls"
                })
        elif isinstance(node.func, ast.Attribute) and self.current_function:
            # Handle method calls
            if isinstance(node.func.value, ast.Name):
                class_name = node.func.value.id
                method_name = node.func.attr
                full_name = f"{class_name}.{method_name}"
                if full_name in self.function_nodes:
                    self.links.append({
                        "source": self.current_function,
                        "target": self.function_nodes[full_name],
                        "type": "calls"
                    })
        self.generic_visit(node)

@app.get("/api/code-structure/{index_id}")
async def get_code_structure(index_id: str):
    try:
        logger.info(f"Fetching code structure for index: {index_id}")
        chat = CodeChat()
        if not chat.load_index(index_id):
            logger.error("Failed to load index")
            return {"error": "Failed to load index"}, 404

        # Get files from the loaded index's metadata
        code_files = set()
        logger.info(f"Scanning metadata with {len(chat.ingester.metadata)} entries")
        for metadata in chat.ingester.metadata:
            logger.info(f"Metadata entry: {metadata.keys()}")
            if 'file' in metadata:
                file_path = metadata['file']
                logger.info(f"Found file in metadata: {file_path}")
                if os.path.exists(file_path):
                    code_files.add(file_path)
                    logger.info(f"File exists: {file_path}")
                else:
                    logger.warning(f"File does not exist: {file_path}")

        if not code_files:
            logger.warning("No code files found in metadata")
            return {"nodes": [], "links": []}

        # Analyze code structure
        analyzer = CodeStructureAnalyzer()
        for file_path in code_files:
            if not file_path.endswith('.py'):
                logger.info(f"Skipping non-Python file: {file_path}")
                continue
            try:
                logger.info(f"Analyzing file: {file_path}")
                with open(file_path, 'r') as f:
                    content = f.read()
                    logger.info(f"File content length: {len(content)} characters")
                    analyzer.module_path = file_path
                    tree = ast.parse(content)
                    analyzer.visit(tree)
                logger.info(f"Successfully analyzed {file_path}")
                logger.info(f"Current nodes: {len(analyzer.nodes)}")
                logger.info(f"Current links: {len(analyzer.links)}")
            except Exception as e:
                logger.error(f"Error analyzing {file_path}: {e}")
                continue

        # Log analysis results
        logger.info(f"Found {len(analyzer.nodes)} nodes and {len(analyzer.links)} links")
        logger.info("Node types:")
        node_types = {}
        for node in analyzer.nodes:
            node_type = node.get("type", "unknown")
            node_types[node_type] = node_types.get(node_type, 0) + 1
        for node_type, count in node_types.items():
            logger.info(f"- {node_type}: {count}")

        # Filter out nodes with too many connections
        node_connections = {}
        for link in analyzer.links:
            source = link["source"]
            target = link["target"]
            node_connections[source] = node_connections.get(source, 0) + 1
            node_connections[target] = node_connections.get(target, 0) + 1

        logger.info("Connection counts:")
        for node_id, count in sorted(node_connections.items(), key=lambda x: x[1], reverse=True)[:10]:
            logger.info(f"- Node {node_id}: {count} connections")

        # Keep nodes with reasonable number of connections
        MAX_CONNECTIONS = 20
        important_nodes = set(node_id for node_id, count in node_connections.items() 
                            if count <= MAX_CONNECTIONS)

        filtered_nodes = [node for node in analyzer.nodes 
                         if node["id"] in important_nodes]
        filtered_links = [link for link in analyzer.links 
                         if link["source"] in important_nodes 
                         and link["target"] in important_nodes]

        logger.info(f"Filtered to {len(filtered_nodes)} nodes and {len(filtered_links)} links")

        result = {
            "nodes": filtered_nodes,
            "links": filtered_links
        }
        
        logger.info("Successfully generated code structure")
        return result
    except Exception as e:
        logger.error(f"Error generating code structure: {e}")
        return {"error": str(e)}, 500

@app.get("/api/indices/{index_id}/load")
async def load_index(index_id: str):
    """Load an index and prepare it for chat."""
    try:
        chat = CodeChat()
        success = chat.load_index(index_id)
        if success:
            return {"success": True}
        return {"success": False, "error": "Failed to load index"}, 404
    except Exception as e:
        logger.error(f"Error loading index: {e}")
        return {"success": False, "error": str(e)}, 500 