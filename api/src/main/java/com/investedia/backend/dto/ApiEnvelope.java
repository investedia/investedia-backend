package com.investedia.backend.dto;

import java.util.Map;

// Endpoint-specific metadata retains the existing snake_case wire keys.
public record ApiEnvelope<T>(T data, Map<String, Object> meta) {}
