"""知识库构建脚本（可选）。

将 knowledge_base/raw/ 下的示例文档解析、切分、向量化，写入向量库。
默认情况下应用启动时会自动加载内置知识库；如需从 raw 目录导入，运行本脚本：

    cd backend
    python ../knowledge_base/scripts/build_knowledge.py

依赖应用代码路径，需在 backend 目录下运行（或设置 PYTHONPATH）。
"""
import sys
from pathlib import Path

# 将 backend 目录加入 sys.path，以便 import app 模块
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.rag.parser import parse_document  # noqa: E402
from app.rag.chunker import chunk_text  # noqa: E402
from app.rag.vector_store import vector_store  # noqa: E402
from app.rag.hybrid_search import hybrid_retriever  # noqa: E402
from app.utils.logger import logger  # noqa: E402

RAW_DIR = Path(__file__).resolve().parent.parent / "raw"


def main() -> None:
    """导入 raw 目录下的所有知识文档。"""
    if not RAW_DIR.exists():
        logger.error(f"raw 目录不存在：{RAW_DIR}")
        return

    texts = []
    metadatas = []

    for doc_path in sorted(RAW_DIR.glob("*.md")):
        logger.info(f"解析文档：{doc_path.name}")
        content = parse_document(str(doc_path))
        # 按段落切分（语义切分）
        chunks = chunk_text(content, max_len=400)
        source = doc_path.stem
        for chunk in chunks:
            texts.append(chunk)
            metadatas.append({"source": source, "category": "knowledge"})

    if not texts:
        logger.warning("未找到可导入的知识文档")
        return

    ids = vector_store.add(texts, metadatas)
    hybrid_retriever.index(texts, metadatas, ids=ids)
    logger.info(f"知识库构建完成，共导入 {len(texts)} 个切片")


if __name__ == "__main__":
    main()
