package com.investedia.backend.config;

import java.time.Clock;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

@Configuration
public class ApiConfiguration implements WebMvcConfigurer {
    @Bean
    Clock clock() {
        return Clock.systemUTC();
    }

    @Override
    public void addCorsMappings(CorsRegistry registry) {
        registry.addMapping("/**")
                .allowedOriginPatterns("https://investedia.com", "https://www.investedia.com",
                        "http://localhost:[*]", "http://127.0.0.1:[*]")
                .allowedMethods("GET", "HEAD", "OPTIONS")
                .allowedHeaders("If-None-Match")
                .exposedHeaders("ETag", "X-Inv-Source")
                .maxAge(86400);
    }
}
