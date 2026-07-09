from prismguard.storage.blobs import InMemoryBlobStore, raw_text_sha256


def test_raw_text_sha256_stable() -> None:
    assert raw_text_sha256("hello") == raw_text_sha256("hello")
    assert raw_text_sha256("hello") != raw_text_sha256("world")


def test_in_memory_blob_store_roundtrip() -> None:
    store = InMemoryBlobStore()
    digest = store.put_raw_text("privileged memo text")
    assert digest == raw_text_sha256("privileged memo text")
    assert store.get_raw_text(digest) == "privileged memo text"
    # dedupe
    digest2 = store.put_raw_text("privileged memo text")
    assert digest2 == digest
