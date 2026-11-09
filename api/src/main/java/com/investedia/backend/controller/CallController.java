package com.investedia.backend.controller;

import com.investedia.backend.service.CallService;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.context.request.WebRequest;

@RestController
public class CallController {
    private final CallService service;
    public CallController(CallService service) { this.service = service; }

    @GetMapping("/v1/calls")
    public ResponseEntity<byte[]> calls(WebRequest request) {
        var ledger = service.latest();
        if (request.checkNotModified(ledger.etag())) {
            return ResponseEntity.status(304).eTag(ledger.etag())
                    .header(HttpHeaders.CACHE_CONTROL, "public, max-age=10").build();
        }
        return ResponseEntity.ok().contentType(MediaType.APPLICATION_JSON)
                .header(HttpHeaders.CACHE_CONTROL, "public, max-age=10")
                .eTag(ledger.etag()).body(ledger.content());
    }
}
