package com.investedia.backend.controller;

import com.investedia.backend.dto.ApiEnvelope;
import com.investedia.backend.service.NewsService;
import java.util.List;
import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;
import tools.jackson.databind.JsonNode;

@RestController
public class NewsController {
    private final NewsService service;
    public NewsController(NewsService service) { this.service = service; }

    @GetMapping("/v1/news")
    public ApiEnvelope<Map<String, List<JsonNode>>> news() { return service.news(); }

    @GetMapping("/v1/globe")
    public ApiEnvelope<Map<String, List<Map<String, Object>>>> globe() { return service.globe(); }
}
