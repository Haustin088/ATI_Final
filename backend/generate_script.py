import re, html
from datetime import datetime

class ScriptGenerator:

    def __init__(self):
        pass

    def format_time(self):
        return datetime.now().strftime("%d/%m/%Y")

    # ---------------------------------------------------------
    # TURN OUTLINE INTO SECTIONS
    # ---------------------------------------------------------
    def split_outline_sections(self, outline: str):
        outline = re.sub(r"<[^>]+>", "", outline)
        outline = html.unescape(outline)
        outline = re.sub(r"<[^>]+>", "", outline)
        outline = outline.replace("\xa0", " ").replace(" ", " ")
        lines = [l.strip() for l in outline.split("\n") if l.strip()]

        # Remove junk lines BEFORE grouping
        UNWANTED = [
            r"Dàn ý dưới đây nhằm hệ thống hóa",
            r"không thay thế",
            r"^Topic\s*:",
            r"^Thực thể quan trọng",
            r"^Từ khóa nổi bật",
            r"Các hoạt động thể chất được đề cập",
            r"^##",
            r"^🎬",
        ]

        cleaned = []
        for ln in lines:
            if any(re.search(pat, ln, flags=re.IGNORECASE) for pat in UNWANTED):
                continue
            cleaned.append(ln)

        # -----------------------------------------------------
        # NORMAL SECTION SPLITTING (no special-case hacks)
        # -----------------------------------------------------
        sections = []
        current = []

        for ln in cleaned:
            is_header = re.match(r"^\d+\.\s", ln) or ln.endswith(":")
            if is_header:
                if current:
                    sections.append(current)
                    current = []
            current.append(ln)

        if current:
            sections.append(current)

        # -----------------------------------------------------
        # Convert each section → paragraph
        # -----------------------------------------------------
        paragraphs = []

        for sec in sections:
            body = []
            for ln in sec:
                # skip headers ("1. ..." or "Bối cảnh:")
                if re.match(r"^\d+\.\s", ln) or ln.endswith(":"):
                    continue
                body.append(ln)

            paragraph = " ".join(re.sub(r"^[-•]\s*", "", l) for l in body)
            paragraph = re.sub(r"\s{2,}", " ", paragraph).strip()

            if paragraph:   # <-- THIS FIXES THE EMPTY FIRST ROW
                paragraphs.append(paragraph)

        return paragraphs

    # ---------------------------------------------------------
    # TURN WHOLE OUTLINE INTO ONE PARAGRAPH (1 COLUMN)
    # ---------------------------------------------------------
    def outline_to_paragraph(self, text: str) -> str:
        text = re.sub(r"^🎬.*?\n", "", text, flags=re.DOTALL)
        text = re.sub(r"^\d+\.\s*[^\n]+", "", text, flags=re.MULTILINE)
        text = re.sub(r"^[^:\n]+:\s*$", "", text, flags=re.MULTILINE)
        text = re.sub(r"^\s*[-•]\s*", "", text, flags=re.MULTILINE)
        text = "\n".join([l for l in text.split("\n") if l.strip()])
        text = text.replace("\n", " ")
        text = re.sub(r"\s{2,}", " ", text).strip()
        if not text.endswith("."):
            text += "."
        return text

    # ---------------------------------------------------------
    # 1 COLUMN FORMAT
    # ---------------------------------------------------------
    def make_one_column(self, title, category, outline):
        clean = self.outline_to_paragraph(outline)

        return f"""
# 🎤 LỜI DẪN BTV - {category.upper()}

**TIÊU ĐỀ:** {title}
**THỜI LƯỢNG:** 2–4 phút
**NGÀY PHÁT SÓNG:** {self.format_time()}
**BIÊN TẬP VIÊN:** [Tên BTV]

---

{clean}

---

**KẾT THÚC CHƯƠNG TRÌNH**
""".strip()

    # ---------------------------------------------------------
    # 2 COLUMN FORMAT
    # ---------------------------------------------------------
    def make_two_columns(self, title, category, outline):
        sections = self.split_outline_sections(outline)
        rows = ""

        for i, paragraph in enumerate(sections, 1):
            rows += f"""
<tr>
    <td style="width: 20%; font-weight: bold; background:#f6f7f8; border:1px solid #ddd;">Đoạn {i}</td>
    <td style="width: 80%; border:1px solid #ddd;">{paragraph}</td>
</tr>
"""

        return f"""
# 🎤 LỜI DẪN BTV - {category.upper()}

**TIÊU ĐỀ:** {title}
**ĐỊNH DẠNG:** 2 CỘT - PHÂN ĐOẠN

<table style="width:100%; border-collapse: collapse;">
{rows}
</table>

---
**KẾT THÚC CHƯƠNG TRÌNH**
""".strip()

    # ---------------------------------------------------------
    # 3 COLUMN FORMAT (TIMELINE)
    # ---------------------------------------------------------
    def make_three_columns(self, title, category, outline):
        sections = self.split_outline_sections(outline)
        rows = ""
        segment = 25  # seconds each

        for i, paragraph in enumerate(sections):
            start = i * segment
            end = start + segment
            t1 = f"{start//60:02d}:{start%60:02d}"
            t2 = f"{end//60:02d}:{end%60:02d}"
            guidance = self.get_guidance(i)

            rows += f"""
<tr>
    <td style="width:15%; border:1px solid #ddd; background:#eef6ff; font-weight:bold;">{t1} - {t2}</td>
    <td style="width:60%; border:1px solid #ddd;">{paragraph}</td>
    <td style="width:25%; border:1px solid #ddd; background:#fffbea;">{guidance}</td>
</tr>
"""

        return f"""
# 🎤 LỜI DẪN BTV - {category.upper()}

**TIÊU ĐỀ:** {title}
**ĐỊNH DẠNG:** 3 CỘT - TIMELINE

<table style="width:100%; border-collapse: collapse;">
{rows}
</table>

---
**KẾT THÚC CHƯƠNG TRÌNH**
""".strip()

    # ---------------------------------------------------------
    # VOICE GUIDANCE
    # ---------------------------------------------------------
    def get_guidance(self, idx):
        guide = [
            "Giọng mở đầu: ấm áp, chậm rãi.",
            "Giọng kể thông tin: rõ ràng, nhấn nhá.",
            "Giọng phân tích: đều, chắc, chậm.",
            "Giọng nhấn mạnh số liệu.",
            "Giọng kết nối & chuyển ý.",
            "Giọng tổng kết & cảm xúc nhẹ.",
        ]
        return guide[idx] if idx < len(guide) else "Giọng đọc ổn định, chuyên nghiệp."

if __name__ == "__main__":
    # Create a fake outline to test
    outline = """
🎬 DÀN Ý VIDEO (3–4 PHÚT)

1. Mở đầu (HOOK):
- Những thông tin dưới đây được tổng hợp từ các dữ liệu hiện có.
- Ngay trong buổi sáng hôm nay, Trung tâm Y học thực hành của Đại học Y Dược TP.

2. Các phần nội dung:
- Vận động nhẹ nhàng giúp cải thiện lưu lượng máu.
- Tập thể dục hỗ trợ giảm viêm.

3. Kết luận:
- Việc tiếp cận thông tin thận trọng luôn quan trọng.
- Chúng tôi sẽ tiếp tục cập nhật khi có dữ liệu mới.
"""

    gen = ScriptGenerator()

    print("\n=== TEST 1: ONE COLUMN ===\n")
    print(gen.make_one_column("Tiêu đề test", "Thời sự", outline))

    print("\n=== TEST 2: TWO COLUMNS ===\n")
    print(gen.make_two_columns("Tiêu đề test", "Thời sự", outline))

    print("\n=== TEST 3: THREE COLUMNS ===\n")
    print(gen.make_three_columns("Tiêu đề test", "Thời sự", outline))
