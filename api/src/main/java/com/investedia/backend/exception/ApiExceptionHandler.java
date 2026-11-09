package com.investedia.backend.exception;

import jakarta.servlet.http.HttpServletRequest;
import java.util.Map;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@RestControllerAdvice
public class ApiExceptionHandler {
    @ExceptionHandler(UnknownGroupException.class)
    ResponseEntity<Map<String, Object>> unknownGroup(UnknownGroupException exception) {
        return ResponseEntity.badRequest().body(Map.of("error", "unknown group", "groups", exception.groups()));
    }

    @ExceptionHandler(SnapshotUnavailableException.class)
    ResponseEntity<Map<String, Object>> unavailable(HttpServletRequest request) {
        if (request.getRequestURI().equals("/v1/calls")) {
            return ResponseEntity.status(404).body(Map.of("error", "no live calls yet"));
        }
        String provider = request.getRequestURI().equals("/v1/prices") ? "yahoo-spark" : "rss+gemini";
        return ResponseEntity.status(503).body(Map.of("error", "no data yet",
                "meta", Map.of("state", "unavailable", "provider", provider, "version", 1)));
    }
}
