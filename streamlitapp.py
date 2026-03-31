import streamlit as st
import os
import re

st.set_page_config(page_title="TRÌNH TẠO TRUYỆN OFFLINE", page_icon="⚡", layout="wide")

BASE_DIR = "./truyen/"

# ==========================================
# CÁC HÀM XỬ LÝ DỮ LIỆU
# ==========================================
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
    
    # Tìm số trong tên file để làm tên dự phòng (VD: 001.txt -> Chương 001)
    num_match = re.search(r'\d+', filename)
    fallback_title = f"Chương {num_match.group()}" if num_match else filename.replace(".txt", "")
    
    if lines:
        first_line = lines[0].strip()
        # Nếu dòng đầu tiên có chữ, lấy làm tên chương. Nếu trống, lấy số file.
        if first_line:
            chapter_title = first_line
        else:
            chapter_title = fallback_title
            
        # Nội dung là các phần còn lại (từ dòng 2 trở đi)
        content_body = '\n'.join(lines[1:])
    else:
        chapter_title = fallback_title
        content_body = ""
        
    # Chuyển đổi xuống dòng thành thẻ <br>
    html_content = content_body.replace('\n', '<br>')
    return chapter_title, html_content

def get_local_novels():
    """Lấy danh sách thư mục truyện từ ./truyen/"""
    if not os.path.exists(BASE_DIR):
        os.makedirs(BASE_DIR)
    return [d for d in os.listdir(BASE_DIR) if os.path.isdir(os.path.join(BASE_DIR, d))]

# ==========================================
# HÀM TẠO FILE HTML OFFLINE (Lõi xử lý)
# ==========================================
def generate_offline_html(novel_title, metadata, chapters_data):
    """
    chapters_data: list các dict [{'title': '...', 'content': '...'}, ...]
    """
    # Xử lý ID lưu trữ độc nhất cho từng truyện để localStorage không bị đụng độ
    storage_key = f"reading_progress_{re.sub(r'[^a-zA-Z0-9]', '', novel_title)}"
    author_name = metadata.get("Tác giả", "Đang cập nhật")
    
    # --- CSS & CẤU TRÚC HTML ---
    html_head = f"""<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>{novel_title}</title>
    <style>
        :root {{
            --bg-color: #f4ecd8; /* Sepia dịu mắt */
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

        /* Thanh Sticky Header (neo trên cùng) */
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

        /* Sidebar ẩn hiện */
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
        
        /* Thông tin truyện trong Sidebar */
        .sidebar-info {{
            padding: 20px 15px;
            background-color: #f0f7f0;
            border-bottom: 2px solid var(--primary);
            text-align: center;
        }}
        .sidebar-info h3 {{ margin: 0; color: var(--primary); font-size: 20px; }}
        .sidebar-info p {{ margin: 8px 0 0 0; color: #555; font-size: 15px; font-style: italic; }}

        /* Lớp phủ màn hình khi mở sidebar */
        #overlay {{
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,0.5); z-index: 1000;
            display: none;
        }}
        #overlay.show {{ display: block; }}

        /* Menu chương trong Sidebar */
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

        /* Nội dung truyện */
        #content-area {{
            padding: 20px 15px;
            max-width: 800px;
            margin: 0 auto;
            min-height: 80vh;
        }}
        .chapter-content {{ display: none; }}
        .active-chapter {{ display: block; }}

        /* Nút bấm */
        button {{
            padding: 8px 12px;
            font-size: 16px;
            border: none; border-radius: 5px;
            background-color: var(--primary); color: white;
            cursor: pointer;
        }}
        button:disabled {{ background-color: #aaa; }}
        .btn-menu {{ background: transparent; color: #333; font-size: 24px; padding: 0 10px; border: none; }}
        
        /* Thanh điều hướng cuối bài */
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
    
    # Ghi nội dung vào thẻ div ẩn và chuẩn bị mảng dữ liệu cho JavaScript
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
        
        // Khôi phục vị trí đọc từ localStorage
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
            // Lưu trạng thái đọc vào bộ nhớ thiết bị
            localStorage.setItem(STORAGE_KEY, currentIdx);

            // 1. Ẩn tất cả nội dung, hiện nội dung chương hiện tại
            document.querySelectorAll('.chapter-content').forEach(el => el.classList.remove('active-chapter'));
            document.getElementById('chap-' + currentIdx).classList.add('active-chapter');
            
            // 2. Cập nhật tên chương trên Sticky Header
            document.getElementById('display-chap-name').innerText = chapterTitles[currentIdx];
            
            // 3. Cập nhật Sidebar Menu (đánh dấu chương đang đọc)
            document.querySelectorAll('.menu-item').forEach(el => el.classList.remove('active-menu'));
            const activeMenuItem = document.getElementById('menu-item-' + currentIdx);
            if(activeMenuItem) {{
                activeMenuItem.classList.add('active-menu');
                // Tự động cuộn menu sidebar đến vị trí chương đang đọc
                activeMenuItem.scrollIntoView({{block: "center"}}); 
            }}
            
            // 4. Bật/tắt nút Trước/Sau
            document.getElementById('btn-prev').disabled = (currentIdx === 0);
            document.getElementById('btn-next').disabled = (currentIdx === totalChapters - 1);
            
            // 5. Cuộn trang lên trên cùng (ngay dưới header)
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
            toggleSidebar(); // Đóng menu sau khi chọn
        }}

        // Khởi chạy khi load xong HTML
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
# GIAO DIỆN STREAMLIT
# ==========================================
st.title("⚡ Trình xuất truyện offline (HTML)")
st.write("Tạo ra một file HTML duy nhất chứa toàn bộ nội dung truyện. Ghi nhớ lịch sử đọc, giao diện tối ưu cho điện thoại.")

# Lựa chọn nguồn dữ liệu
source_option = st.radio("Chọn nguồn dữ liệu:", ["Chọn từ thư mục ./truyen/ (Local)", "Tải lên các file .txt (Upload)"], horizontal=True)

novel_title = ""
metadata = {}
chapters_data = [] # Lưu trữ dữ liệu các chương
ready_to_export = False

if source_option == "Chọn từ thư mục ./truyen/ (Local)":
    local_novels = get_local_novels()
    if not local_novels:
        st.warning(f"Không tìm thấy thư mục nào trong `{BASE_DIR}`.")
    else:
        selected_dir = st.selectbox("Chọn bộ truyện để xuất bản:", local_novels)
        novel_path = os.path.join(BASE_DIR, selected_dir)
        
        # Phân tích local files
        try:
            with open(os.path.join(novel_path, "000.txt"), "r", encoding="utf-8") as f:
                metadata = parse_metadata_content(f.read())
            novel_title = metadata.get("Tên truyện", selected_dir)
            
            # Quét files chương
            chap_files = [f for f in os.listdir(novel_path) if f.endswith(".txt") and f != "000.txt"]
            # Sắp xếp theo số
            chap_files.sort(key=lambda x: int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else 0)
            
            if chap_files:
                for cf in chap_files:
                    with open(os.path.join(novel_path, cf), "r", encoding="utf-8") as f:
                        c_title, c_html = parse_chapter_content(cf, f.read())
                        chapters_data.append({"title": c_title, "content": c_html})
                ready_to_export = True
            else:
                st.error("Không tìm thấy các file chương (001.txt, 002.txt...)")
        except Exception as e:
            st.error(f"Lỗi đọc file Local: {e}")

else:
    # Xử lý Upload files
    uploaded_files = st.file_uploader("Tải lên TẤT CẢ file .txt (Bao gồm file 000.txt và các file chương)", type=["txt"], accept_multiple_files=True)
    
    if uploaded_files:
        # Tách file 000.txt và các file khác
        meta_file = next((f for f in uploaded_files if f.name == "000.txt"), None)
        chap_files = [f for f in uploaded_files if f.name != "000.txt"]
        
        if not meta_file:
            st.error("⚠️ Bạn phải tải lên cả file `000.txt` chứa thông tin truyện.")
        elif not chap_files:
            st.error("⚠️ Bạn chưa tải lên các file chương (001.txt, ...).")
        else:
            # Đọc metadata
            content_000 = meta_file.getvalue().decode("utf-8")
            metadata = parse_metadata_content(content_000)
            novel_title = metadata.get("Tên truyện", "Truyện Upload")
            
            # Sắp xếp các file chương theo tên
            chap_files.sort(key=lambda x: int(re.search(r'\d+', x.name).group()) if re.search(r'\d+', x.name) else 0)
            
            for uf in chap_files:
                content_chap = uf.getvalue().decode("utf-8")
                c_title, c_html = parse_chapter_content(uf.name, content_chap)
                chapters_data.append({"title": c_title, "content": c_html})
            ready_to_export = True

# Hiển thị nút tải nếu dữ liệu đã sẵn sàng
if ready_to_export:
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
        for c in chapters_data[:10]: # Hiện 10 chương đầu
            st.write(f"- {c['title']}")
        if len(chapters_data) > 10:
            st.write("... và nhiều chương khác.")
