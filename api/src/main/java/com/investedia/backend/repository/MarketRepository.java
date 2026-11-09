package com.investedia.backend.repository;

import com.investedia.backend.model.PriceSnapshot;
import java.util.List;
import java.util.Map;

public interface MarketRepository {
    PriceSnapshot latest();
    Map<String, List<String>> symbolGroups();
}
