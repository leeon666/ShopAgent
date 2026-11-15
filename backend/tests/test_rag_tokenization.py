"""Tests for mixed Chinese/ASCII BM25 tokenization."""

from app.services.rag.retrieval import tokenize_for_bm25


def test_chinese_policy_query_keeps_unigrams_and_bigrams() -> None:
    tokens = tokenize_for_bm25("质量问题退货运费")
    assert "质" in tokens
    assert "质量" in tokens
    assert "退货" in tokens


def test_mixed_text_keeps_ascii_words() -> None:
    tokens = tokenize_for_bm25("订单ORD-123退款")
    assert "ord" in tokens
    assert "123" in tokens
    assert "退款" in tokens
