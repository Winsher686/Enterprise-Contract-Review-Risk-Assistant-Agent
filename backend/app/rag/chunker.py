"""文本切分模块。

合同场景采用「章节 + 条款」语义切分，而非固定长度切分，
避免切断「违约责任条款 + 免责条件」导致风险判断错误。
"""
import re
from typing import List, Dict


def split_clauses(text: str) -> List[Dict]:
    """将合同文本按条款切分。

    识别常见的条款标记：
    - 第X条 / 第X款
    - 一、二、三、 等中文序号
    - 数字序号 1. 2. 3.
    """
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if not lines:
        return []

    # 条款起始模式
    clause_pattern = re.compile(
        r"^(第[一二三四五六七八九十百千万\d]+[条款]|[一二三四五六七八九十]+、|\d+[.、])"
    )

    clauses = []
    current_title = None
    current_content = []

    def flush():
        nonlocal current_title, current_content
        if current_content:
            content = "".join(current_content)
            clauses.append({
                "title": current_title or "其他条款",
                "content": content,
            })
        current_content = []

    for line in lines:
        if clause_pattern.match(line):
            flush()
            current_title = line
            current_content = [line]
        else:
            current_content.append(line)

    flush()

    # 如果没切分出任何条款，整体作为一个条款
    if not clauses:
        clauses = [{"title": "合同全文", "content": text}]

    return clauses


def chunk_text(text: str, max_len: int = 500, overlap: int = 0) -> List[str]:
    """通用长度切分（用于知识库文档）。"""
    if len(text) <= max_len:
        return [text] if text.strip() else []
    chunks = []
    start = 0
    while start < len(text):
        end = start + max_len
        chunks.append(text[start:end])
        start = end - overlap
    return chunks
