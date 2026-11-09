package com.investedia.backend.model;

import java.math.BigDecimal;

public record PriceRow(BigDecimal price, BigDecimal changePercent, long providerTimeMillis) {}
