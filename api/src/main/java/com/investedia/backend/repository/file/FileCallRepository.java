package com.investedia.backend.repository.file;

import com.investedia.backend.exception.SnapshotUnavailableException;
import com.investedia.backend.model.LedgerDocument;
import com.investedia.backend.repository.CallRepository;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;
import org.springframework.stereotype.Repository;

@Repository
public class FileCallRepository implements CallRepository {
    private final JsonSnapshotReader reader;
    public FileCallRepository(JsonSnapshotReader reader) { this.reader = reader; }

    @Override
    public LedgerDocument latest() {
        byte[] content = reader.bytes("assets/globe/v5-ledger.json");
        if (!reader.parse(content).path("calls").isArray()) throw new SnapshotUnavailableException();
        try {
            // Hash the exact representation served; never recalculate or edit prediction records.
            String etag = '"' + HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(content)) + '"';
            return new LedgerDocument(content, etag);
        } catch (NoSuchAlgorithmException exception) {
            throw new IllegalStateException(exception);
        }
    }
}
