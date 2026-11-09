package com.investedia.backend.model;

public record LedgerDocument(byte[] content, String etag) {
    public LedgerDocument {
        content = content.clone();
    }

    @Override
    public byte[] content() {
        return content.clone();
    }
}
