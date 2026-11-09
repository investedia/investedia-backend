package com.investedia.backend.service;

import com.investedia.backend.model.LedgerDocument;
import com.investedia.backend.repository.CallRepository;
import org.springframework.stereotype.Service;

@Service
public class CallService {
    private final CallRepository repository;
    public CallService(CallRepository repository) { this.repository = repository; }

    public LedgerDocument latest() { return repository.latest(); }
}
