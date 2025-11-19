import gradio as gr
import os, re
from .backend import SmartVideoNewsChatbot

chatbot = SmartVideoNewsChatbot()

def load_chat_sessions():
    try:
        sessions = chatbot.get_chat_sessions()
        if not sessions:
            return gr.update(choices=[], value=None), [], "📊 Chưa có phiên chat nào được lưu."

        choices = [
            (f"{s['title']} ({s['message_count']} tin) - {s['updated_at']}", s['id'])
            for s in sessions
        ]

        return gr.update(choices=choices, value=choices[0][1]), [], "📊 Danh sách phiên chat đã được cập nhật"

    except Exception as e:
        return gr.update(choices=[], value=None), [], f"❌ Lỗi khi tải danh sách phiên chat: {e}"

def on_session_selected(session_id):
    try:
        if not session_id:
            return [], "ℹ️ Chọn một phiên chat để xem nội dung"

        messages = chatbot.load_session(session_id)

        chat_display = []
        for msg in messages:
            if msg['role'] == 'user':
                chat_display.append([msg['content'], None])
            else:
                if chat_display:
                    chat_display[-1][1] = msg['content']

        session = chatbot.history_manager.get_session(session_id)
        session_info = f"📁 Đang xem: {session['title']} | {len(messages)//2} cuộc hội thoại | Cập nhật: {session['updated_at']}"

        return chat_display, session_info

    except Exception as e:
        return [], f"❌ Lỗi khi tải phiên chat: {e}"

def delete_selected_session(session_id):
    try:
        if session_id:
            chatbot.delete_session(session_id)
            result = load_chat_sessions()
            return result[0], [], "✅ Đã xóa phiên chat"

        return load_chat_sessions()[0], [], "ℹ️ Chọn phiên chat để xóa"

    except Exception as e:
        return load_chat_sessions()[0], [], f"❌ Lỗi khi xóa phiên chat: {e}"

def clear_all_sessions():
    try:
        chatbot.clear_all_history()
        chatbot.create_new_chat_session("Phiên làm việc mới")
        result = load_chat_sessions()
        return result[0], [], "✅ Đã xóa toàn bộ lịch sử"

    except Exception as e:
        return load_chat_sessions()[0], [], f"❌ {e}"

def refresh_sessions():
    try:
        result = load_chat_sessions()
        return result
    except Exception as e:
        return gr.update(choices=[], value=None), [], f"❌ {e}"


# ===== SCRIPT EDITING =====

def save_script_edits(script_editor, chat_history):
    if script_editor:
        chatbot.current_script = script_editor
        chat_history.append([
            "Lưu chỉnh sửa",
            f"✅ Script đã được cập nhật!\n\n{script_editor}"
        ])
        chatbot.add_to_history("Lưu chỉnh sửa", "Script đã được cập nhật")
    return chat_history, script_editor

def clear_script_edits(chat_history):
    chatbot.current_script = ""
    chat_history.append(["Xóa chỉnh sửa", "✅ Đã xóa script"])
    chatbot.add_to_history("Xóa chỉnh sửa", "Script đã xóa")
    return "", chat_history


# ===== VIDEO SELECTION =====

def handle_video_selection(video_choice, chat_history, current_script):
    try:
        if not video_choice:
            return chat_history, current_script

        idx = int(video_choice.split()[-1]) - 1
        response = chatbot.select_video_from_digest(idx)

        script_content = current_script

        if "✅" in response:
            script = chatbot.create_script("1 Cột")
            if not script.startswith("❌"):
                script_content = script

        chat_history.append([f"Chọn {video_choice}", response])
        chatbot.add_to_history(f"Chọn {video_choice}", response)

        return chat_history, script_content

    except Exception as e:
        err = f"❌ Lỗi khi chọn video: {e}"
        chat_history.append(["Chọn video", err])
        return chat_history, current_script


# ===== USER MESSAGE HANDLING =====

def handle_user_message(message, chat_history, current_script):
    try:
        if not message.strip():
            return "", chat_history, current_script, None

        msg = message.lower().strip()
        script_content = current_script

        # Select video: "chọn video X"
        if msg.startswith("chọn video"):
            match = re.search(r'chọn video\s+(\d+)', msg)
            if match:
                num = int(match.group(1)) - 1
                response = chatbot.select_video_from_digest(num)

                if "✅" in response:
                    script = chatbot.create_script("1 Cột")
                    if not script.startswith("❌"):
                        script_content = script

                chat_history.append([message, response])
                return "", chat_history, script_content, None

        # Detect export
        if "xuất" in msg or "tải" in msg or "pdf" in msg or "doc" in msg:
            format_type = "PDF"
            if "doc" in msg: format_type = "DOC"
            if "text" in msg or "txt" in msg: format_type = "TEXT"

            chat_history, reply, filepath = handle_export_action(format_type, chat_history)
            return "", chat_history, script_content, filepath

        category = chatbot.detect_category(message)

        if "tổng hợp" in msg:
            response = chatbot.create_video_digest(category, message)

        elif "lời dẫn" in msg or "script" in msg:
            if "2 cột" in msg:
                response = chatbot.create_script("2 Cột")
            elif "3 cột" in msg:
                response = chatbot.create_script("3 Cột")
            else:
                response = chatbot.create_script("1 Cột")

            if not response.startswith("❌"):
                script_content = response

        elif "video khác" in msg:
            response = chatbot.create_article_random_video(category, message)

        elif "bài báo" in msg:
            response = chatbot.create_article_with_image(category, message)

        else:
            response = chatbot.smart_content_creation(message, category)

        chat_history.append([message, response])
        chatbot.add_to_history(message, response)

        return "", chat_history, script_content, None

    except Exception as e:
        err = f"❌ Lỗi hệ thống: {e}"
        chat_history.append([message, err])
        return "", chat_history, current_script, None


# ===== CATEGORY ACTIONS =====

def handle_category_action(category, action, chat_history):
    try:
        if action == "Bài báo":
            response = chatbot.create_article_with_image(category)
        elif action == "Tổng hợp":
            response = chatbot.create_video_digest(category)
        elif action == "Video khác":
            response = chatbot.create_article_random_video(category)
        else:
            response = "❌ Thao tác không hợp lệ"

        chat_history.append([f"{action} - {category}", response])
        return chat_history, ""

    except Exception as e:
        err = f"❌ Lỗi: {e}"
        chat_history.append([f"{action} - {category}", err])
        return chat_history, ""


# ===== SCRIPT ACTIONS =====

def handle_script_action(action, chat_history, current_script):
    try:
        response = chatbot.create_script(action)
        script_content = response if not response.startswith("❌") else current_script

        chat_history.append([f"Tạo script {action}", response])
        return chat_history, script_content

    except Exception as e:
        err = f"❌ Lỗi: {e}"
        chat_history.append([f"Tạo script {action}", err])
        return chat_history, current_script


# ===== EXPORT =====

def handle_export_action(format_type, chat_history):
    try:
        filepath, msg = chatbot.export_content(format_type)

        if filepath and os.path.exists(filepath):
            chat_history.append(["Xuất file", f"✅ {msg}"])
            return chat_history, msg, filepath

        chat_history.append(["Xuất file", f"❌ {msg}"])
        return chat_history, msg, None

    except Exception as e:
        err = f"❌ {e}"
        chat_history.append(["Xuất file", err])
        return chat_history, err, None


# ===== CLEAR + NEW SESSION =====

def clear_chat():
    chatbot.current_video = None
    chatbot.current_script = ""
    chatbot.media_processor.cleanup_temp_files()
    chatbot.create_new_chat_session("Phiên mới")
    return [], ""

def create_new_session():
    chatbot.create_new_chat_session("Phiên mới")
    return [], ""
