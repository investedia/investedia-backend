package com.investedia.backend;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.ConfigurationPropertiesScan;

@SpringBootApplication
@ConfigurationPropertiesScan
public class InvestediaApplication {
    public static void main(String[] args) {
        SpringApplication.run(InvestediaApplication.class, args);
    }
}
