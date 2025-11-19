import gradio as gr

def build_ui(
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
):
    with gr.Blocks(
        title="Chatbot Tin Tức Video Thông Minh - Giao diện trò chuyện",
        theme=gr.themes.Soft(),
        css="""
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; border-radius: 10px; color: white; margin-bottom: 20px; text-align: center; }
        .section { background: #f8f9fa; padding: 15px; border-radius: 10px; margin: 10px 0; border: 1px solid #e9ecef; }
        .success { background: #d4edda; padding: 10px; border-radius: 5px; border: 1px solid #c3e6cb; }
        .warning { background: #fff3cd; padding: 10px; border-radius: 5px; border: 1px solid #ffeaa7; }
        .danger { background: #f8d7da; padding: 10px; border-radius: 5px; border: 1px solid #f5c6cb; }
        .image-container { text-align: center; margin: 20px 0; }
        .image-container img { border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); max-width: 100%; }
        .history-panel { background: #f5f5f5; padding: 15px; border-radius: 10px; border: 1px solid #ddd; }
        .guide-dropdown { background: #e3f2fd; border: 1px solid #90caf9; border-radius: 5px; padding: 10px; margin: 10px 0; }
        """
    ) as demo:

        # ==============================
        # HEADER
        # ==============================
        gr.HTML("""
        <style>
        .header-container {
            background: linear-gradient(90deg, #6a85f1 0%, #836ce8 50%, #b779f2 100%);
            padding: 18px 28px;
            border-radius: 14px;
            color: white;
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 22px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.12);
        }

        .header-title {
            text-align: center;
            flex: 1;
        }

        .header-title h1 {
            margin: 0;
            font-size: 2rem;
            font-weight: 800;
            letter-spacing: -0.5px;
            color: white !important;
        }

        .header-title p {
            margin: 4px 0 0 0;
            font-size: 1.1rem;
            font-weight: 500;
            opacity: 0.95;
            color: white !important;
        }

        .back-btn {
            background: white;
            padding: 8px 14px;
            border-radius: 8px;
            text-decoration: none !important;
            font-weight: 600;
            font-size: 0.9rem;
            box-shadow: 0 2px 5px rgba(0,0,0,0.12);
            display: inline-flex;
            align-items: center;
            gap: 4px;
            border: 1px solid #e5e7eb;
        }

        .gradient-text {
            background: linear-gradient(to right, #6366f1, #a855f7);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .back-btn:hover {
            background: #f9f9f9;
        }
        </style>

        <div class="header-container">

            <a href="http://127.0.0.1:8000/frontend/editor.html" 
               class="back-btn">
                ← <span class="gradient-text">Quay về Editor</span>
            </a>

            <div class="header-title">
                <h1>🎬 CHATBOT TIN TỨC VIDEO THÔNG MINH</h1>
                <p>🤖 Giao diện trò chuyện thông minh — Tạo bài báo tự động từ video</p>
            </div>

            <div style="width: 150px;"></div>
        </div>
        """)

        # ==============================
        # QUICK GUIDE
        # ==============================
        with gr.Column(elem_classes="guide-dropdown"):
            with gr.Accordion("📚 HƯỚNG DẪN SỬ DỤNG NHANH (Bấm để mở/rút gọn)", open=False):
                gr.HTML("""
                <style>
                    .guide-wrapper {
                        background: #ffffff;
                        border: 1px solid #e5e7eb;
                        border-radius: 16px;
                        padding: 24px;
                        margin-bottom: 14px;
                        box-shadow: 0 4px 10px rgba(0,0,0,0.04);
                    }

                    .guide-title {
                        background: linear-gradient(to right, #6366f1, #a855f7);
                        color: white;
                        padding: 12px 18px;
                        border-radius: 12px;
                        font-size: 1.25rem;
                        font-weight: 700;
                        margin-bottom: 22px;
                        display: flex;
                        align-items: center;
                        gap: 10px;
                    }

                    /* 🟣 FIXED 3-COLUMN LAYOUT — NO RESPONSIVE */
                    .guide-grid {
                        display: grid;
                        grid-template-columns: 1fr 1fr 1fr !important;
                        gap: 28px;
                    }

                    .guide-block h3 {
                        font-size: 1.05rem;
                        font-weight: 700;
                        color: #4f46e5;
                        margin-bottom: 6px;
                    }

                    .guide-block ul {
                        margin: 0;
                        padding-left: 20px;
                    }

                    .guide-block li {
                        margin: 6px 0;
                        font-size: 0.93rem;
                        line-height: 1.45rem;
                    }
                </style>

                <div class="guide-wrapper">
                    <div class="guide-grid">

                        <div class="guide-block">
                            <h3>🎯 1. TÌM KIẾM THÔNG MINH</h3>
                            <ul>
                                <li>Gõ chủ đề: “thời sự”, “công nghệ”, “giáo dục”, “thể thao”</li>
                                <li>Tìm kiếm cụ thể: “tuyển sinh đại học 2025”, “AI và robot”, “VR”</li>
                                <li>Hệ thống tự động tìm video phù hợp nhất</li>
                            </ul>

                            <h3>📝 2. TẠO NỘI DUNG</h3>
                            <ul>
                                <li><b>Bài báo:</b> Tạo bài báo >600 từ</li>
                                <li><b>Tổng hợp:</b> Xem 5 video cùng chủ đề</li>
                                <li><b>Video khác:</b> Chọn video ngẫu nhiên</li>
                            </ul>

                            <h3>🎤 3. TẠO LỜI DẪN BTV</h3>
                            <ul>
                                <li>1 Cột: đơn giản</li>
                                <li>2 Cột: chi tiết</li>
                                <li>3 Cột: timeline + hướng dẫn</li>
                            </ul>
                        </div>

                        <div class="guide-block">
                            <h3>🎞️ 4. CHỌN VIDEO TỪ TỔNG HỢP</h3>
                            <ul>
                                <li>Tạo tổng hợp video trước</li>
                                <li>Chọn video từ danh sách (1 → 5)</li>
                                <li>Tự động tạo script BTV</li>
                            </ul>

                            <h3>📤 5. XUẤT FILE</h3>
                            <ul>
                                <li><b>TEXT</b>: File văn bản</li>
                                <li><b>DOC</b>: File Word</li>
                                <li><b>PDF</b>: File PDF đẹp</li>
                            </ul>

                            <h3>📁 6. QUẢN LÝ LỊCH SỬ</h3>
                            <ul>
                                <li>Lưu tự động mọi cuộc trò chuyện</li>
                                <li>Xem lại các phiên chat cũ</li>
                                <li>Tải lại phiên để tiếp tục</li>
                            </ul>
                        </div>

                        <div class="guide-block">
                            <h3>🎛️ 7. THAO TÁC NHANH</h3>
                            <ul>
                                <li>Dùng các nút chức năng</li>
                                <li>Chọn chủ đề từ dropdown</li>
                                <li>Tạo script với 1 click</li>
                            </ul>

                            <h3>🔌 8. KẾT NỐI VỚI ADMIN</h3>
                            <ul>
                                <li>Tự động cập nhật nguồn tin</li>
                                <li>Đồng bộ realtime RSS + YouTube</li>
                                <li>Không cần khởi động lại</li>
                            </ul>

                            <h3>💡 9. MẸO HAY</h3>
                            <ul>
                                <li>Dùng từ khóa tiếng Việt tự nhiên</li>
                                <li>Kết hợp nhiều chức năng</li>
                                <li>Xuất file sau khi hài lòng</li>
                                <li>Admin chỉnh gì → chatbot cập nhật ngay</li>
                            </ul>
                        </div>

                    </div>
                </div>
                """)

        with gr.Tabs():

            # ===== TAB: CHAT =====
            with gr.TabItem("💬 Trò chuyện"):
                with gr.Row():
                    # LEFT SIDE
                    with gr.Column(scale=2):
                        chatbot_display = gr.Chatbot(
                            label="Trò chuyện với Chatbot",
                            height=500,
                            show_copy_button=True
                        )

                        with gr.Row():
                            user_input = gr.Textbox(
                                label="Nhập yêu cầu của bạn...",
                                placeholder="Ví dụ: 'tin thể thao', 'tổng hợp công nghệ', ...",
                                scale=4
                            )
                            send_btn = gr.Button("🚀 Gửi", variant="primary", scale=1)

                        gr.Markdown("### 📝 Chỉnh sửa Script")
                        script_editor = gr.Textbox(
                            label="Nội dung script",
                            lines=6,
                            interactive=True
                        )

                        with gr.Row():
                            save_script_btn = gr.Button("💾 Lưu chỉnh sửa", variant="primary")
                            clear_script_btn = gr.Button("🗑️ Xóa chỉnh sửa", variant="secondary")

                    # RIGHT SIDE
                    with gr.Column(scale=1):
                        with gr.Column(elem_classes="section"):
                            gr.Markdown("### 🎯 Thao tác nhanh")

                            chatbot.refresh_data_from_admin()
                            categories = (
                                list(chatbot.rss_feeds.keys()) +
                                list(chatbot.youtube_channels.keys())
                            )

                            category_dropdown = gr.Dropdown(
                                choices=categories,
                                label="Chọn chủ đề",
                                value=categories[0] if categories else None
                            )

                            with gr.Row():
                                article_btn = gr.Button("📹 Bài báo", variant="primary")
                                digest_btn = gr.Button("📺 Tổng hợp")
                                random_video_btn = gr.Button("🎲 Video khác")

                        # VIDEO SELECTOR
                        with gr.Column(elem_classes="section"):
                            gr.Markdown("### 📋 Chọn video từ tổng hợp")
                            video_selector = gr.Dropdown(
                                choices=[f"Video {i+1}" for i in range(5)],
                                label="Chọn video để áp dụng"
                            )
                            select_video_btn = gr.Button("🎤 Áp dụng", variant="primary")

                        # SCRIPT TYPE
                        with gr.Column(elem_classes="section"):
                            gr.Markdown("### 🎤 Tạo Script BTV")
                            with gr.Row():
                                script_1col_btn = gr.Button("1 Cột")
                                script_2col_btn = gr.Button("2 Cột")
                                script_3col_btn = gr.Button("3 Cột")

                        # EXPORT
                        with gr.Column(elem_classes="section"):
                            gr.Markdown("### 📤 Xuất file")
                            export_format = gr.Radio(
                                choices=["TEXT", "DOC", "PDF"],
                                label="Định dạng",
                                value="TEXT"
                            )
                            export_btn = gr.Button("📥 Xuất file", variant="primary")
                            export_file = gr.File(label="Tải xuống", visible=True)

                        # CONTROLS
                        with gr.Column(elem_classes="section"):
                            gr.Markdown("### ⚙️ Điều khiển")
                            with gr.Row():
                                clear_btn = gr.Button("🗑️ Xóa chat", variant="secondary")
                                new_session_btn = gr.Button("🆕 Phiên mới", variant="primary")

            # ===== TAB: HISTORY =====
            with gr.TabItem("📊 Lịch sử chatbot"):
                with gr.Row():
                    with gr.Column(scale=1):
                        with gr.Column(elem_classes="history-panel"):
                            gr.Markdown("### 📁 QUẢN LÝ LỊCH SỬ")

                            with gr.Row():
                                refresh_history_btn = gr.Button("🔄 Làm mới danh sách")

                            session_dropdown = gr.Dropdown(
                                label="Chọn phiên chat",
                                info="Chọn một phiên chat để xem nội dung",
                                interactive=True
                            )

                            session_info = gr.Markdown("📊 Chọn phiên chat để xem nội dung")

                            with gr.Row():
                                load_session_btn = gr.Button("📂 Tải phiên", variant="primary")
                                delete_session_btn = gr.Button("🗑️ Xóa phiên", variant="secondary")

                            with gr.Row():
                                clear_all_history_btn = gr.Button("💥 Xóa tất cả", variant="stop")

                    with gr.Column(scale=2):
                        with gr.Column(elem_classes="history-panel"):
                            gr.Markdown("### 💬 NỘI DUNG PHIÊN CHAT")
                            history_chatbot = gr.Chatbot(
                                label="Lịch sử trò chuyện",
                                height=500,
                                show_copy_button=True
                            )

        # ==========================================
        # EVENT WIRING
        # ==========================================
        send_btn.click(
            handle_user_message,
            inputs=[user_input, chatbot_display, script_editor],
            outputs=[user_input, chatbot_display, script_editor, export_file]
        )
        user_input.submit(
            handle_user_message,
            inputs=[user_input, chatbot_display, script_editor],
            outputs=[user_input, chatbot_display, script_editor, export_file]
        )

        select_video_btn.click(
            handle_video_selection,
            inputs=[video_selector, chatbot_display, script_editor],
            outputs=[chatbot_display, script_editor]
        )

        save_script_btn.click(
            save_script_edits,
            inputs=[script_editor, chatbot_display],
            outputs=[chatbot_display, script_editor]
        )
        clear_script_btn.click(
            clear_script_edits,
            inputs=[chatbot_display],
            outputs=[script_editor, chatbot_display]
        )

        article_btn.click(
            lambda c, h: handle_category_action(c, "Bài báo", h),
            inputs=[category_dropdown, chatbot_display],
            outputs=[chatbot_display, script_editor]
        )
        digest_btn.click(
            lambda c, h: handle_category_action(c, "Tổng hợp", h),
            inputs=[category_dropdown, chatbot_display],
            outputs=[chatbot_display, script_editor]
        )
        random_video_btn.click(
            lambda c, h: handle_category_action(c, "Video khác", h),
            inputs=[category_dropdown, chatbot_display],
            outputs=[chatbot_display, script_editor]
        )

        script_1col_btn.click(
            lambda h, s: handle_script_action("1 Cột", h, s),
            inputs=[chatbot_display, script_editor],
            outputs=[chatbot_display, script_editor]
        )
        script_2col_btn.click(
            lambda h, s: handle_script_action("2 Cột", h, s),
            inputs=[chatbot_display, script_editor],
            outputs=[chatbot_display, script_editor]
        )
        script_3col_btn.click(
            lambda h, s: handle_script_action("3 Cột", h, s),
            inputs=[chatbot_display, script_editor],
            outputs=[chatbot_display, script_editor]
        )

        export_btn.click(
            handle_export_action,
            inputs=[export_format, chatbot_display],
            outputs=[chatbot_display, script_editor, export_file]
        )

        clear_btn.click(clear_chat, outputs=[chatbot_display, script_editor])
        new_session_btn.click(create_new_session, outputs=[chatbot_display, script_editor])

        refresh_history_btn.click(
            refresh_sessions,
            outputs=[session_dropdown, history_chatbot, session_info]
        )
        load_session_btn.click(
            on_session_selected,
            inputs=[session_dropdown],
            outputs=[history_chatbot, session_info]
        )
        session_dropdown.change(
            on_session_selected,
            inputs=[session_dropdown],
            outputs=[history_chatbot, session_info]
        )
        delete_session_btn.click(
            delete_selected_session,
            inputs=[session_dropdown],
            outputs=[session_dropdown, history_chatbot, session_info]
        )
        clear_all_history_btn.click(
            clear_all_sessions,
            outputs=[session_dropdown, history_chatbot, session_info]
        )

        demo.load(
            refresh_sessions,
            outputs=[session_dropdown, history_chatbot, session_info]
        )

    return demo
