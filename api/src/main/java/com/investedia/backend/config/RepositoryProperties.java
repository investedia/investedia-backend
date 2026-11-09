package com.investedia.backend.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties("investedia")
public record RepositoryProperties(String repositoryRoot) {}
