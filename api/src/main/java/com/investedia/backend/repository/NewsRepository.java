package com.investedia.backend.repository;

import com.investedia.backend.model.NewsSnapshot;

public interface NewsRepository {
    NewsSnapshot latest();
}
