import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import gradio as gr
from .db import Base, engine
from .routers import crawl, rss_manager, users, system, generate_article, youtube_rss
from fastapi.staticfiles import StaticFiles

from chatbot.backend import SmartVideoNewsChatbot
from chatbot.chatbot_ui import build_ui

from chatbot.frontend import (
    handle_user_message,
    handle_video_selection,
    save_script_edits,
    clear_script_edits,
    handle_category_action,
    handle_script_action,
    handle_export_action,
    clear_chat,
    create_new_session,
    refresh_sessions,
    on_session_selected,
    delete_selected_session,
    clear_all_sessions,
)

Base.metadata.create_all(bind=engine)

app = FastAPI()

backend_data_dir = os.path.join(os.path.dirname(__file__), "data")
app.mount("/backend/data", StaticFiles(directory=backend_data_dir), name="backend-data")
app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
app.include_router(crawl.router)
app.include_router(users.router)
app.include_router(system.router)
app.include_router(generate_article.router, prefix="/api")
app.include_router(rss_manager.router)
app.include_router(youtube_rss.router)

# Initialize chatbot backend
chatbot = SmartVideoNewsChatbot()

# Build Gradio chatbot UI (IMPORTANT STEP)
demo = build_ui(
    handle_user_message,
    handle_video_selection,
    save_script_edits,
    clear_script_edits,
    handle_category_action,
    handle_script_action,
    handle_export_action,
    clear_chat,
    create_new_session,
    refresh_sessions,
    on_session_selected,
    delete_selected_session,
    clear_all_sessions,
    chatbot
)

# Mount chatbot at /chatbot
app = gr.mount_gradio_app(app, demo, path="/chatbot")
