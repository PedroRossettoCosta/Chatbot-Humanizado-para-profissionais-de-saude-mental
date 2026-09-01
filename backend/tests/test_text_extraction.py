from app.services.text_extraction import chunk_text


def test_chunk_text_short_text_returns_single_chunk():
    text = "Texto curto de teste."
    chunks = chunk_text(text)
    assert chunks == [text]


def test_chunk_text_empty_returns_no_chunks():
    assert chunk_text("") == []
    assert chunk_text("   \n  ") == []


def test_chunk_text_splits_with_overlap():
    text = "abcdefghijklmnopqrstuvwxyz"
    chunks = chunk_text(text, chunk_size=10, overlap=3)

    assert chunks == ["abcdefghij", "hijklmnopq", "opqrstuvwx", "vwxyz"]
    # o fim de cada chunk deve reaparecer no começo do próximo (overlap)
    for previous, current in zip(chunks, chunks[1:]):
        assert previous[-3:] == current[:3]
