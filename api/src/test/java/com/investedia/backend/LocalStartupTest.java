package com.investedia.backend;

import static org.assertj.core.api.Assertions.assertThat;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.test.context.SpringBootTest;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
class LocalStartupTest {
    @Value("${local.server.port}") int port;

    @Test
    void defaultRelativeRepositoryPathWorksInARealHttpServer() throws Exception {
        var client = HttpClient.newHttpClient();
        for (String route : new String[]{"/api/health", "/v1/prices", "/v1/news", "/v1/calls"}) {
            var response = client.send(HttpRequest.newBuilder(URI.create("http://127.0.0.1:" + port + route)).GET().build(),
                    HttpResponse.BodyHandlers.ofString());
            assertThat(response.statusCode()).as(route).isEqualTo(200);
            assertThat(response.headers().firstValue("X-Inv-Source")).contains("repository-snapshot");
        }
    }
}
