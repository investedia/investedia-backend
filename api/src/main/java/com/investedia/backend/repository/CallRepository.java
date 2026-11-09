package com.investedia.backend.repository;

import com.investedia.backend.model.LedgerDocument;

public interface CallRepository {
    LedgerDocument latest();
}
