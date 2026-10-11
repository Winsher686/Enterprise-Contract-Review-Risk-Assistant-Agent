"""文本切分模块单元测试。"""
from app.rag.chunker import split_clauses, chunk_text


class TestSplitClauses:
    def test_split_by_article_number(self):
        """按「第X条」切分。"""
        text = "第一条 合同目的\n内容一\n第二条 付款\n内容二"
        clauses = split_clauses(text)
        assert len(clauses) == 2
        assert clauses[0]["title"] == "第一条 合同目的"
        assert "内容一" in clauses[0]["content"]

    def test_split_by_chinese_number(self):
        """按「一、二、」切分。"""
        text = "一、甲方义务\n义务内容\n二、乙方义务\n义务内容2"
        clauses = split_clauses(text)
        assert len(clauses) == 2

    def test_split_by_digit(self):
        """按「1. 2.」切分。"""
        text = "1. 第一项\n内容\n2. 第二项\n内容2"
        clauses = split_clauses(text)
        assert len(clauses) == 2

    def test_single_paragraph(self):
        """无条款标记时整体作为一个条款。"""
        text = "这是一段没有条款标记的合同正文。"
        clauses = split_clauses(text)
        assert len(clauses) == 1
        # 无条款标题时归入「其他条款」
        assert clauses[0]["content"] == text

    def test_empty_text(self):
        """空文本返回空列表。"""
        assert split_clauses("") == []
        assert split_clauses("\n\n  \n") == []

    def test_preamble_becomes_other_clause(self):
        """条款标记之前的内容归入「其他条款」。"""
        text = "合同标题\n编号\n第一条 正文\n内容"
        clauses = split_clauses(text)
        # 标题+编号归入其他条款，正文是第一条
        assert clauses[0]["title"] == "其他条款"
        assert clauses[-1]["title"].startswith("第一条")


class TestChunkText:
    def test_short_text_single_chunk(self):
        """短文本返回单个 chunk。"""
        assert chunk_text("短文本") == ["短文本"]

    def test_empty_text(self):
        """空/空白文本返回空列表。"""
        assert chunk_text("") == []
        assert chunk_text("   ") == []

    def test_long_text_split(self):
        """长文本按 max_len 切分。"""
        text = "a" * 1000
        chunks = chunk_text(text, max_len=500)
        assert len(chunks) == 2
        assert len(chunks[0]) == 500

    def test_overlap(self):
        """验证 overlap 生效（相邻 chunk 有重叠）。"""
        text = "abcdefghij"
        chunks = chunk_text(text, max_len=6, overlap=2)
        assert len(chunks) >= 2
        # 前一个 chunk 的结尾与后一个 chunk 的开头重叠
        assert chunks[0][-2:] == chunks[1][:2]
