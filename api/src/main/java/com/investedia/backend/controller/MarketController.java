package com.investedia.backend.controller;

import com.investedia.backend.dto.ApiEnvelope;
import com.investedia.backend.service.MarketService;
import java.util.List;
import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class MarketController {
    private final MarketService service;
    public MarketController(MarketService service) { this.service = service; }

    @GetMapping("/v1/prices")
    public ApiEnvelope<Map<String, List<Number>>> prices(@RequestParam(defaultValue = "all") String group) {
        return service.prices(group);
    }

    @GetMapping("/v1/status")
    public Map<String, Object> status() { return service.status(); }
}
