import streamlit as st
from bs4 import BeautifulSoup
import re
import os

# ==========================================
# CẤU HÌNH TRANG (Khai báo 1 lần duy nhất)
# ==========================================
st.set_page_config(page_title="XỬ LÝ VÀ ĐỌC TRUYỆN", page_icon="📚", layout="wide")

BASE_DIR = "./truyen/"

# ==========================================
# CÁC HÀM XỬ LÝ DỮ LIỆU (Dùng chung & Tạo truyện)
# ==========================================
def convert_html_to_plaintext(html_content):
    """Hàm chuyển đổi HTML sang Text thuần"""
    if not html_content:
        return ""
    
    soup = BeautifulSoup(html_content, 'html.parser')
    text = soup.get_text(separator='\n')
    
    lines = text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        line = line.strip()
        # Xóa dấu '+' đứng ngay đầu dòng (kèm khoảng trắng nếu có)
        line = re.sub(r'^\+\s*', '', line)
        cleaned_lines.append(line)
    
    final_text = '\n'.join(cleaned_lines)
    # Dọn dẹp: giảm bớt các dòng trống liên tiếp thành tối đa 2 dòng (1 khoảng trắng)
    final_text = re.sub(r'\n{3,}', '\n\n', final_text)
    
    return final_text.strip()

def parse_metadata_content(content):
    """Đọc nội dung text của file 000.txt theo thứ tự từng dòng"""
    lines = [line.strip() for line in content.strip().split('\n')]
    
    metadata = {
        "Tên truyện": lines[0] if len(lines) > 0 and lines[0] else "Truyện chưa đặt tên",
        "Tác giả": lines[1] if len(lines) > 1 and lines[1] else "Đang cập nhật",
        "Link": lines[2] if len(lines) > 2 else "",
        "Tổng số chương": int(lines[3]) if len(lines) > 3 and lines[3].isdigit() else 0,
        "Chương đang đọc": int(lines[4]) if len(lines) > 4 and lines[4].isdigit() else 0
    }
    return metadata

def parse_chapter_content(filename, content):
    """Phân tích nội dung chương: Dòng 1 là tên chương, còn lại là nội dung"""
    lines = content.split('\n')
    
    # Tìm số trong tên file để làm tên dự phòng
    num_match = re.search(r'\d+', filename)
    fallback_title = f"Chương {num_match.group()}" if num_match else filename.replace(".txt", "")
    
    if lines:
        first_line = lines[0].strip()
        if first_line:
            chapter_title = first_line
        else:
            chapter_title = fallback_title
        content_body = '\n'.join(lines[1:])
    else:
        chapter_title = fallback_title
        content_body = ""
        
    html_content = content_body.replace('\n', '<br>')
    return chapter_title, html_content

def get_local_novels():
    """Lấy danh sách thư mục truyện từ ./truyen/"""
    if not os.path.exists(BASE_DIR):
        os.makedirs(BASE_DIR)
    return [d for d in os.listdir(BASE_DIR) if os.path.isdir(os.path.join(BASE_DIR, d))]

def generate_offline_html(novel_title, metadata, chapters_data):
    """Hàm tạo file HTML Offline"""
    storage_key = f"reading_progress_{re.sub(r'[^a-zA-Z0-9]', '', novel_title)}"
    author_name = metadata.get("Tác giả", "Đang cập nhật")
    
    html_head = f"""<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>{novel_title}</title>
    <style>
        :root {{
            --bg-color: #f4ecd8;
            --text-color: #2c2c2c;
            --primary: #4CAF50;
            --sidebar-bg: #fff;
            --header-bg: #e8dfc7;
        }}
        
        body {{
            background-color: var(--bg-color);
            color: var(--text-color);
            font-family: 'Segoe UI', Tahoma, Verdana, sans-serif;
            font-size: 18px;
            line-height: 1.6;
            margin: 0;
            padding: 0;
            overflow-x: hidden;
        }}

        #sticky-header {{
            position: sticky;
            top: 0;
            background-color: var(--header-bg);
            padding: 10px 15px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            display: flex;
            justify-content: space-between;
            align-items: center;
            z-index: 1000;
        }}
        
        .header-title-wrapper {{
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }}
        
        .header-novel-name {{ font-size: 14px; font-weight: bold; color: #555; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
        .header-chap-name {{ font-size: 16px; font-weight: bold; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}

        #sidebar {{
            position: fixed;
            top: 0; left: -300px;
            width: 280px;
            height: 100%;
            background-color: var(--sidebar-bg);
            box-shadow: 2px 0 5px rgba(0,0,0,0.2);
            transition: left 0.3s ease;
            z-index: 1001;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
        }}
        #sidebar.open {{ left: 0; }}
        
        .sidebar-info {{
            padding: 20px 15px;
            background-color: #f0f7f0;
            border-bottom: 2px solid var(--primary);
            text-align: center;
        }}
        .sidebar-info h3 {{ margin: 0; color: var(--primary); font-size: 20px; }}
        .sidebar-info p {{ margin: 8px 0 0 0; color: #555; font-size: 15px; font-style: italic; }}

        #overlay {{
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,0.5); z-index: 1000;
            display: none;
        }}
        #overlay.show {{ display: block; }}

        #menu-list {{ padding: 10px 0; overflow-y: auto; flex-grow: 1; }}
        .menu-item {{
            padding: 12px 15px;
            border-bottom: 1px solid #eee;
            cursor: pointer;
            font-size: 16px;
        }}
        .menu-item:hover, .menu-item.active-menu {{
            background-color: #eef7ee;
            color: var(--primary);
            font-weight: bold;
        }}

        #content-area {{
            padding: 20px 15px;
            max-width: 800px;
            margin: 0 auto;
            min-height: 80vh;
        }}
        .chapter-content {{ display: none; }}
        .active-chapter {{ display: block; }}

        button {{
            padding: 8px 12px;
            font-size: 16px;
            border: none; border-radius: 5px;
            background-color: var(--primary); color: white;
            cursor: pointer;
        }}
        button:disabled {{ background-color: #aaa; }}
        .btn-menu {{ background: transparent; color: #333; font-size: 24px; padding: 0 10px; border: none; }}
        
        .bottom-nav {{
            display: flex; justify-content: space-between;
            max-width: 800px; margin: 20px auto; padding: 0 15px 40px 15px;
        }}
    </style>
</head>
<body>

    <div id="overlay" onclick="toggleSidebar()"></div>
    <div id="sidebar">
        <div class="sidebar-info">
            <h3>{novel_title}</h3>
            <p>Tác giả: {author_name}</p>
        </div>
        <div style="padding: 10px 15px; font-weight: bold; color: #333; background: #fafafa; border-bottom: 1px solid #ddd;">
            Danh sách chương:
        </div>
        <div id="menu-list"></div>
    </div>

    <div id="sticky-header">
        <button class="btn-menu" onclick="toggleSidebar()">☰</button>
        <div class="header-title-wrapper">
            <span class="header-novel-name">{novel_title}</span>
            <span class="header-chap-name" id="display-chap-name">Đang tải...</span>
        </div>
        <div style="width: 44px;"></div>
    </div>

    <div id="content-area">
"""
    
    html_body = ""
    js_chapters_array = []
    
    for idx, chap in enumerate(chapters_data):
        chap_title_escaped = chap['title'].replace("'", "\\'").replace('"', '\\"')
        js_chapters_array.append(f"'{chap_title_escaped}'")
        
        html_body += f"""
        <div id="chap-{idx}" class="chapter-content">
            <h2 style="text-align: center; margin-bottom: 30px;">{chap['title']}</h2>
            <div>{chap['content']}</div>
        </div>
        """
        
    js_chapters_str = "[" + ", ".join(js_chapters_array) + "]"
        
    html_tail = f"""
    </div>

    <div class="bottom-nav">
        <button id="btn-prev" onclick="changeChapter(-1)">⬅️ Chương Trước</button>
        <button id="btn-next" onclick="changeChapter(1)">Chương Sau ➡️</button>
    </div>

    <script>
        const totalChapters = {len(chapters_data)};
        const chapterTitles = {js_chapters_str};
        const STORAGE_KEY = '{storage_key}';
        
        let currentIdx = parseInt(localStorage.getItem(STORAGE_KEY)) || 0;
        if(currentIdx >= totalChapters || currentIdx < 0) currentIdx = 0;

        function toggleSidebar() {{
            document.getElementById('sidebar').classList.toggle('open');
            document.getElementById('overlay').classList.toggle('show');
        }}

        function buildSidebarMenu() {{
            const menuList = document.getElementById('menu-list');
            let html = '';
            for(let i = 0; i < totalChapters; i++) {{
                html += `<div class="menu-item" id="menu-item-${{i}}" onclick="jumpToChapter(${{i}})">${{chapterTitles[i]}}</div>`;
            }}
            menuList.innerHTML = html;
        }}

        function updateUI() {{
            localStorage.setItem(STORAGE_KEY, currentIdx);

            document.querySelectorAll('.chapter-content').forEach(el => el.classList.remove('active-chapter'));
            document.getElementById('chap-' + currentIdx).classList.add('active-chapter');
            
            document.getElementById('display-chap-name').innerText = chapterTitles[currentIdx];
            
            document.querySelectorAll('.menu-item').forEach(el => el.classList.remove('active-menu'));
            const activeMenuItem = document.getElementById('menu-item-' + currentIdx);
            if(activeMenuItem) {{
                activeMenuItem.classList.add('active-menu');
                activeMenuItem.scrollIntoView({{block: "center"}}); 
            }}
            
            document.getElementById('btn-prev').disabled = (currentIdx === 0);
            document.getElementById('btn-next').disabled = (currentIdx === totalChapters - 1);
            
            window.scrollTo(0, 0);
        }}

        function changeChapter(step) {{
            const newIdx = currentIdx + step;
            if(newIdx >= 0 && newIdx < totalChapters) {{
                currentIdx = newIdx;
                updateUI();
            }}
        }}

        function jumpToChapter(idx) {{
            currentIdx = idx;
            updateUI();
            toggleSidebar();
        }}

        window.onload = () => {{
            buildSidebarMenu();
            updateUI();
        }};
    </script>
</body>
</html>
"""
    return html_head + html_body + html_tail

# ==========================================
# SIDEBAR ĐIỀU HƯỚNG
# ==========================================
st.sidebar.title("📌 MENU")
page_selection = st.sidebar.radio(
    "Vui lòng chọn chức năng:", 
    ["1. Công cụ xóa HTML", "2. Trình tạo truyện offline"]
)
st.sidebar.markdown("---")
st.sidebar.info("Công cụ hỗ trợ tải, dọn dẹp và xuất file HTML truyện offline siêu nhẹ.")

# ==========================================
# TRANG 1: CÔNG CỤ XÓA MÃ HTML (TRANG CHỦ)
# ==========================================
if page_selection == "1. Công cụ xóa HTML":
    st.title("📝 Trình chuyển đổi HTML sang văn bản thuần")
    st.markdown("Công cụ này giúp bạn gỡ bỏ mọi mã HTML (`<br>`, `<p>`, `<div>`, `<span>`...) và trả về văn bản nguyên gốc, tự động ngắt dòng hợp lý.")

    col1, col2 = st.columns(2)
    html_input = ""

    with col1:
        st.subheader("1. Nhập hoặc tải nội dung lên")
        
        uploaded_file = st.file_uploader("Tải file .txt lên (Chứa mã HTML):", type=["txt"], key="html_uploader")
        
        st.markdown("**HOẶC**")
        
        pasted_text = st.text_area(
            "Dán trực tiếp nội dung HTML vào đây:", 
            height=350, 
            help="Khung nhập văn bản.",
            kwargs={"spellcheck": "false"} 
        )
        
        if uploaded_file is not None:
            html_input = uploaded_file.getvalue().decode("utf-8")
        elif pasted_text:
            html_input = pasted_text

    with col2:
        st.subheader("2. Nội dung đã chuyển đổi")
        
        if st.button("Chuyển Đổi Sang Text 🚀", type="primary"):
            if not html_input.strip():
                st.warning("Vui lòng nhập nội dung hoặc tải file lên trước khi chuyển đổi!")
            else:
                with st.spinner("Đang xử lý..."):
                    converted_text = convert_html_to_plaintext(html_input)
                    st.success("Chuyển đổi thành công!")
                    
                    st.markdown("**Kết quả (Nhấn biểu tượng 📋 ở góc phải khung dưới để Copy):**")
                    st.code(converted_text, language="text", wrap_lines=True)
                    
                    st.download_button(
                        label="⬇️ Tải Xuống File .txt",
                        data=converted_text,
                        file_name="van_ban_da_loc_html.txt",
                        mime="text/plain",
                        type="primary"
                    )

# ==========================================
# TRANG 2: TRÌNH TẠO TRUYỆN OFFLINE + ĐÁNH DẤU
# ==========================================
elif page_selection == "2. Trình Tạo Truyện Offline":
    st.title("⚡ Trình xuất truyện offline (HTML)")
    st.write("Tạo ra một file HTML duy nhất chứa toàn bộ nội dung truyện. Ghi nhớ lịch sử đọc, giao diện tối ưu cho điện thoại.")

    source_option = st.radio("Chọn nguồn dữ liệu:", ["Chọn từ thư mục ./truyen/ (Github)", "Tải lên các file .txt (Upload)"], horizontal=True)

    novel_title = ""
    metadata = {}
    chapters_data = [] 
    ready_to_export = False

    if source_option == "Chọn từ thư mục ./truyen/ (Local)":
        local_novels = get_local_novels()
        
        # Tạo danh sách phân loại truyện
        unfinished_novels = []
        finished_novels = []
        unfinished_options = {}
        finished_options = {}
        
        # Quét trước thông tin từ file 000.txt của từng truyện để phân loại
        for d in local_novels:
            n_path = os.path.join(BASE_DIR, d)
            f_000 = os.path.join(n_path, "000.txt")
            t_title = d
            c_chap = 0
            t_chap = 0
            
            if os.path.exists(f_000):
                try:
                    with open(f_000, "r", encoding="utf-8") as f:
                        meta_temp = parse_metadata_content(f.read())
                    t_title = meta_temp.get("Tên truyện", d)
                    t_chap = meta_temp.get("Tổng số chương", 0)
                    c_chap = meta_temp.get("Chương đang đọc", 0)
                except:
                    pass
            
            item = {"dir": d, "title": t_title, "current": c_chap, "total": t_chap}
            
            # Điều kiện ĐÃ ĐỌC XONG: Chương đang đọc >= Tổng số chương (và Tổng chương phải > 0)
            if t_chap > 0 and c_chap >= t_chap:
                finished_novels.append(item)
                finished_options[d] = f"📘 {t_title} (Hoàn thành: {c_chap}/{t_chap})"
            else:
                unfinished_novels.append(item)
                unfinished_options[d] = f"📖 {t_title} (Đang đọc: {c_chap}/{t_chap})"
                
        if not local_novels:
            st.warning(f"Không tìm thấy thư mục nào trong `{BASE_DIR}`.")
        else:
            st.markdown("### 🗂️ Chọn bộ truyện từ thư mục máy tính")
            
            # --- KHỞI TẠO CÁC BIẾN STATE CHỐNG XUNG ĐỘT SELECTBOX ---
            if "sel_unif" not in st.session_state:
                st.session_state.sel_unif = "-- Chọn truyện --"
            if "sel_fin" not in st.session_state:
                st.session_state.sel_fin = "-- Chọn truyện --"
            if "selected_dir" not in st.session_state:
                st.session_state.selected_dir = None

            # Đồng bộ hóa danh sách chọn hợp lệ để tránh lỗi Crash của Streamlit khi chuyển trạng thái truyện
            unif_list_opts = ["-- Chọn truyện --"] + [item["dir"] for item in unfinished_novels]
            fin_list_opts = ["-- Chọn truyện --"] + [item["dir"] for item in finished_novels]
            
            if st.session_state.sel_unif not in unif_list_opts:
                st.session_state.sel_unif = "-- Chọn truyện --"
            if st.session_state.sel_fin not in fin_list_opts:
                st.session_state.sel_fin = "-- Chọn truyện --"

            # Các hàm Callback điều hướng khi click chọn truyện
            def on_change_unif():
                if st.session_state.sel_unif != "-- Chọn truyện --":
                    st.session_state.selected_dir = st.session_state.sel_unif
                    st.session_state.sel_fin = "-- Chọn truyện --" # Reset selectbox còn lại
                else:
                    if st.session_state.selected_dir == st.session_state.sel_unif:
                        st.session_state.selected_dir = None

            def on_change_fin():
                if st.session_state.sel_fin != "-- Chọn truyện --":
                    st.session_state.selected_dir = st.session_state.sel_fin
                    st.session_state.sel_unif = "-- Chọn truyện --" # Reset selectbox còn lại
                else:
                    if st.session_state.selected_dir == st.session_state.sel_fin:
                        st.session_state.selected_dir = None

            # --- CHIA LÀM 2 SELECTBOX SONG SONG ---
            col_sel1, col_sel2 = st.columns(2)
            
            with col_sel1:
                st.selectbox(
                    "⏳ 1. Danh sách truyện CHƯA đọc xong:",
                    options=unif_list_opts,
                    format_func=lambda x: unfinished_options.get(x, x),
                    key="sel_unif",
                    on_change=on_change_unif
                )
                
            with col_sel2:
                st.selectbox(
                    "✅ 2. Danh sách truyện ĐÃ ĐỌC XONG:",
                    options=fin_list_opts,
                    format_func=lambda x: finished_options.get(x, x),
                    key="sel_fin",
                    on_change=on_change_fin
                )
                
            selected_dir = st.session_state.selected_dir
            
            # --- XỬ LÝ TRUYỆN ĐÃ CHỌN ---
            if selected_dir and selected_dir != "-- Chọn truyện --":
                novel_path = os.path.join(BASE_DIR, selected_dir)
                try:
                    # Phân tích file 000.txt
                    with open(os.path.join(novel_path, "000.txt"), "r", encoding="utf-8") as f:
                        metadata = parse_metadata_content(f.read())
                    novel_title = metadata.get("Tên truyện", selected_dir)
                    
                    # Quét files chương
                    chap_files = [f for f in os.listdir(novel_path) if f.endswith(".txt") and f != "000.txt"]
                    chap_files.sort(key=lambda x: int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else 0)
                    
                    if chap_files:
                        for cf in chap_files:
                            with open(os.path.join(novel_path, cf), "r", encoding="utf-8") as f:
                                c_title, c_html = parse_chapter_content(cf, f.read())
                                chapters_data.append({"title": c_title, "content": c_html})
                        ready_to_export = True
                    else:
                        st.error("Không tìm thấy các file chương (001.txt, 002.txt...)")
                        
                    # CẬP NHẬT TRẠNG THÁI TIẾN ĐỘ VÀO 000.txt
                    st.markdown("---")
                    st.subheader(f"🔖 Cập nhật tiến độ đọc cho: {novel_title}")
                    col_mark1, col_mark2 = st.columns([1, 2])
                    
                    with col_mark1:
                        current_chap = metadata.get("Chương đang đọc", 0)
                        new_progress = st.number_input("Chương đang đọc hiện tại:", min_value=0, value=int(current_chap), step=1)
                    
                    with col_mark2:
                        st.write("") 
                        st.write("") 
                        if st.button("💾 Lưu tiến độ vào file 000.txt", type="secondary"):
                            file_000_path = os.path.join(novel_path, "000.txt")
                            try:
                                with open(file_000_path, "r", encoding="utf-8") as file:
                                    lines = [line.strip("\n") for line in file.readlines()]
                                
                                while len(lines) < 5:
                                    lines.append("")
                                    
                                lines[4] = str(new_progress) # Dòng số 5 trong file
                                
                                with open(file_000_path, "w", encoding="utf-8") as file:
                                    file.write("\n".join(lines))
                                    
                                st.success(f"✅ Đã lưu tiến độ mới: Chương {new_progress}. Hệ thống tự động phân loại lại nhóm!")
                                
                                # Reset lại lựa chọn cũ để ứng dụng quét và chuyển nhóm ngay lập tức
                                st.session_state.selected_dir = None
                                st.session_state.sel_unif = "-- Chọn truyện --"
                                st.session_state.sel_fin = "-- Chọn truyện --"
                                st.rerun()
                            except Exception as e:
                                st.error(f"Lỗi ghi file 000.txt: {e}")

                except Exception as e:
                    st.error(f"Lỗi đọc dữ liệu truyện này: {e}")
            else:
                st.info("💡 Vui lòng lựa chọn một bộ truyện từ 1 trong 2 danh sách phía trên để xử lý.")

    else:
        # Xử lý Upload files (Giữ nguyên gốc)
        uploaded_files = st.file_uploader("Tải lên TẤT CẢ file .txt (Bao gồm file 000.txt và các file chương)", type=["txt"], accept_multiple_files=True, key="novel_uploader")
        
        if uploaded_files:
            meta_file = next((f for f in uploaded_files if f.name == "000.txt"), None)
            chap_files = [f for f in uploaded_files if f.name != "000.txt"]
            
            if not meta_file:
                st.error("⚠️ Bạn phải tải lên cả file `000.txt` chứa thông tin truyện.")
            elif not chap_files:
                st.error("⚠️ Bạn chưa tải lên các file chương (001.txt, ...).")
            else:
                content_000 = meta_file.getvalue().decode("utf-8")
                metadata = parse_metadata_content(content_000)
                novel_title = metadata.get("Tên truyện", "Truyện Upload")
                
                chap_files.sort(key=lambda x: int(re.search(r'\d+', x.name).group()) if re.search(r'\d+', x.name) else 0)
                
                for uf in chap_files:
                    content_chap = uf.getvalue().decode("utf-8")
                    c_title, c_html = parse_chapter_content(uf.name, content_chap)
                    chapters_data.append({"title": c_title, "content": c_html})
                ready_to_export = True

    # Hiển thị nút tải nếu dữ liệu đã sẵn sàng (Giữ nguyên gốc)
    if ready_to_export:
        st.markdown("---")
        st.success(f"✅ Đã quét thành công **{len(chapters_data)}** chương truyện.")
        
        html_output = generate_offline_html(novel_title, metadata, chapters_data)
        
        st.download_button(
            label=f"⬇️ TẢI FILE OFFLINE ({novel_title}).html",
            data=html_output,
            file_name=f"{novel_title}_Offline.html",
            mime="text/html",
            use_container_width=True,
            type="primary"
        )
        
        with st.expander("Xem trước danh sách chương đã nhận diện"):
            for c in chapters_data[:10]:
                st.write(f"- {c['title']}")
            if len(chapters_data) > 10:
                st.write("... và nhiều chương khác.")
