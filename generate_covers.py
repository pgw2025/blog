# generate_covers.py
import os
import re
import sys
from pathlib import Path

# ================= 动态自适应配置项 =================
SCRIPT_DIR = Path(__file__).resolve().parent

HUGO_POSTS_DIR = "/opt/blog/content/posts"  # Hugo 文章目录
OUTPUT_COVER_FILENAME = "featured.svg"      # 生成的封面文件名
DEFAULT_CATEGORY = "tech"

# 1. 默认模板文件名
DEFAULT_TEMPLATE = "template_default.svg"

# 2. 建立【分类】到【专属模板文件】的映射表
# 未在此配置的分类会自动使用 DEFAULT_TEMPLATE
CATEGORY_TEMPLATES = {
    "运维技术": "template_linux.svg",

}
# ==========================================


def parse_front_matter(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if not match:
        return None

    yaml_block = match.group(1)
    meta = {}
    for line in yaml_block.split("\n"):
        if ":" in line:
            key, val = line.split(":", 1)
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            val = re.sub(r"[\[\]\"]", "", val) 
            meta[key] = val
    return meta


def split_title(title, max_chars=14):
    """
    优先根据冒号（中文'：'或英文':'）将标题拆分为两行。
    如果标题中无冒号，则使用原有的字数/单词安全切分逻辑。
    """
    # 1. 优先尝试寻找冒号
    for colon in ["：", ":"]:
        if colon in title:
            # split(colon, 1) 表示仅在第一个出现的冒号处进行切分，防止标题中有多个冒号时报错
            parts = title.split(colon, 1)
            line1 = parts[0].strip()
            line2 = parts[1].strip()
            return line1, line2

    # 2. 如果没有冒号，则执行原有的安全切分逻辑
    if len(title) <= max_chars:
        return title, ""
        
    if " " in title:
        words = title.split(" ")
        line1, line2 = "", ""
        for word in words:
            if len(line1 + word) <= max_chars * 1.5:
                line1 += word + " "
            else:
                line2 += word + " "
        return line1.strip(), line2.strip()
        
    return title[:max_chars], title[max_chars:]


def generate_svg(meta, output_path):
    # 解析分类
    category_raw = meta.get("categories", DEFAULT_CATEGORY).strip()
    category = category_raw.split(",")[0].strip() if "," in category_raw else category_raw
    category_lower = category.lower()

    # 1. 动态选择模板文件
    template_filename = CATEGORY_TEMPLATES.get(category_lower, DEFAULT_TEMPLATE)
    template_file_path = SCRIPT_DIR / template_filename

    # 安全降级：如果指定的专属模板文件不存在，则自动使用默认模板
    if not template_file_path.exists():
        template_file_path = SCRIPT_DIR / DEFAULT_TEMPLATE

    with open(template_file_path, "r", encoding="utf-8") as f:
        template = f.read()

    # 2. 文字排版与时间
    title = meta.get("title", "无标题")
    subtitle = meta.get("subtitle", meta.get("description", ""))
    title_1, title_2 = split_title(title)
    date = meta.get("date", "")[:10]

    # 3. 仅替换文本占位符
    output_content = template.replace("{TITLE_LINE_1}", title_1)
    output_content = output_content.replace("{TITLE_LINE_2}", title_2)
    output_content = output_content.replace("{SUBTITLE}", subtitle)
    output_content = output_content.replace(
        "{DESCRIPTION}", f"Published on {date}" if date else ""
    )
    output_content = output_content.replace("{CATEGORY}", category.upper())

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(output_content)


def clean_covers():
    """
    清理函数：递归遍历文章目录，删除所有生成的封面文件
    """
    posts_path = Path(HUGO_POSTS_DIR)
    if not posts_path.exists():
        print(f"[错误] 未找到目录: {HUGO_POSTS_DIR}")
        return

    # 递归查找所有匹配配置中文件名的文件
    cover_files = list(posts_path.glob(f"**/{OUTPUT_COVER_FILENAME}"))

    if not cover_files:
        print("未找到任何已生成的封面文件，无需清理。")
        return

    print(f"找到 {len(cover_files)} 个封面文件，准备开始清理...")
    deleted_count = 0

    for file_path in cover_files:
        try:
            file_path.unlink()  # 删除文件
            print(f"🗑️ 已删除: {file_path}")
            deleted_count += 1
        except Exception as e:
            print(f"❌ 无法删除文件 {file_path.name}: {e}")
            
    print(f"\n清理完毕。共成功删除 {deleted_count} 张封面图。")


def main():
    posts_path = Path(HUGO_POSTS_DIR)

    if not posts_path.exists():
        print(f"[错误] 未找到目录: {HUGO_POSTS_DIR}")
        return

    md_files = list(posts_path.glob("**/*.md"))
    print(f"找到 {len(md_files)} 篇文章，正在读取专属模板并替换标题...")

    for md_file in md_files:
        try:
            meta = parse_front_matter(md_file)
            if not meta or "title" not in meta:
                continue

            bundle_dir = md_file.parent
            output_path = bundle_dir / OUTPUT_COVER_FILENAME

            generate_svg(meta, output_path)
            print(f"✔️ 生成成功 -> {output_path}")
        except Exception as e:
            print(f"❌ 处理失败 {md_file.name}: {e}")


if __name__ == "__main__":
    # 解析命令行参数
    if len(sys.argv) > 1 and sys.argv[1].lower() in ["clean", "-clean", "--clean"]:
        clean_covers()
    else:
        main()