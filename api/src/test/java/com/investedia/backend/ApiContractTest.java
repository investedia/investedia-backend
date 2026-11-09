package com.investedia.backend;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.options;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.LinkedHashSet;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Import;
import org.springframework.context.annotation.Primary;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.servlet.MockMvc;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

@SpringBootTest
@AutoConfigureMockMvc
@Import(ApiContractTest.TimeConfiguration.class)
class ApiContractTest {
    static final Path ROOT = repositoryRoot();
    static final Instant CONTRACT_NOW = Instant.parse("2026-11-07T15:00:00Z");
    @Autowired MockMvc mvc;
    @Autowired ObjectMapper mapper;
    @Autowired Clock clock;

    static Path repositoryRoot() {
        Path current = Path.of("").toAbsolutePath();
        while (current != null && !Files.exists(current.resolve("workers/live/index.js"))) current = current.getParent();
        if (current == null) throw new IllegalStateException("Tests require the Investedia repository");
        return current;
    }

    @DynamicPropertySource
    static void properties(DynamicPropertyRegistry properties) {
        properties.add("investedia.repository-root", ROOT::toString);
    }

    @TestConfiguration
    static class TimeConfiguration {
        @Bean @Primary Clock contractClock() {
            // Must match the fixed now in api/tools/worker-contracts.mjs.
            return Clock.fixed(CONTRACT_NOW, ZoneOffset.UTC);
        }
    }

    @Test
    void readResponsesMatchExistingWorkerForTheSameRealSnapshots() throws Exception {
        assertThat(clock.instant()).isEqualTo(CONTRACT_NOW);
        assertThat(Files.readString(ROOT.resolve("api/tools/worker-contracts.mjs")))
                .contains("const now = Date.parse('" + CONTRACT_NOW + "');");
        var process = new ProcessBuilder("node", ROOT.resolve("api/tools/worker-contracts.mjs").toString(), ROOT.toString())
                .redirectError(ProcessBuilder.Redirect.INHERIT).start();
        byte[] output = process.getInputStream().readAllBytes();
        assertThat(process.waitFor()).isZero();
        var cases = mapper.readTree(output);
        assertThat(cases.size()).isEqualTo(8);
        for (var entry : cases.properties()) {
            var result = mvc.perform(get(entry.getKey())).andReturn().getResponse();
            assertThat(result.getStatus()).as(entry.getKey()).isEqualTo(entry.getValue().path("status").asInt());
            assertEquivalent(entry.getValue().path("body"), mapper.readTree(result.getContentAsString()), entry.getKey());
            assertThat(result.getHeader("X-Inv-Source")).isEqualTo("repository-snapshot");
        }
    }

    private void assertEquivalent(JsonNode expected, JsonNode actual, String path) {
        if (expected.isNumber()) {
            assertThat(actual.isNumber()).as(path).isTrue();
            assertThat(actual.decimalValue()).as(path).isEqualByComparingTo(expected.decimalValue());
        } else if (expected.isObject()) {
            assertThat(actual.isObject()).as(path).isTrue();
            var expectedKeys = new LinkedHashSet<String>();
            var actualKeys = new LinkedHashSet<String>();
            expected.properties().forEach(entry -> expectedKeys.add(entry.getKey()));
            actual.properties().forEach(entry -> actualKeys.add(entry.getKey()));
            assertThat(actualKeys).as(path).containsExactlyInAnyOrderElementsOf(expectedKeys);
            expected.properties().forEach(entry -> assertEquivalent(entry.getValue(), actual.get(entry.getKey()), path + "/" + entry.getKey()));
        } else if (expected.isArray()) {
            assertThat(actual.isArray()).as(path).isTrue();
            assertThat(actual.size()).as(path).isEqualTo(expected.size());
            for (int i = 0; i < expected.size(); i++) assertEquivalent(expected.get(i), actual.get(i), path + "/" + i);
        } else assertThat(actual).as(path).isEqualTo(expected);
    }

    @Test
    void callsAreTheExactSavedLedgerAndSupportConditionalRequests() throws Exception {
        byte[] original = Files.readAllBytes(ROOT.resolve("assets/globe/v5-ledger.json"));
        var response = mvc.perform(get("/v1/calls")).andExpect(status().isOk()).andReturn().getResponse();
        assertThat(response.getContentAsByteArray()).containsExactly(original);
        String etag = response.getHeader("ETag");
        assertThat(etag).isNotBlank();
        mvc.perform(get("/v1/calls").header("If-None-Match", etag))
                .andExpect(status().isNotModified()).andExpect(header().string("ETag", etag));
        assertThat(Files.readAllBytes(ROOT.resolve("assets/globe/v5-ledger.json"))).containsExactly(original);
    }

    @Test
    void localFrontendCorsWorksButUnapprovedOriginsDoNot() throws Exception {
        mvc.perform(options("/v1/news").header("Origin", "http://127.0.0.1:8765")
                .header("Access-Control-Request-Method", "GET"))
                .andExpect(status().isOk()).andExpect(header().string("Access-Control-Allow-Origin", "http://127.0.0.1:8765"));
        mvc.perform(options("/v1/news").header("Origin", "https://unapproved.example")
                .header("Access-Control-Request-Method", "GET")).andExpect(status().isForbidden());
    }

    @Test
    void ingestionIsExplicitlyUnavailableAndDoesNotWrite() throws Exception {
        var news = Files.readAllBytes(ROOT.resolve("assets/globe/news-live.json"));
        var calls = Files.readAllBytes(ROOT.resolve("assets/globe/v5-ledger.json"));
        for (String route : new String[]{"news", "calls"}) {
            var response = mvc.perform(post("/v1/ingest/" + route).contentType("application/json").content("{}"))
                    .andExpect(status().isServiceUnavailable()).andReturn().getResponse();
            assertThat(mapper.readTree(response.getContentAsString()).path("error").asText()).isEqualTo("ingest not configured");
        }
        assertThat(Files.readAllBytes(ROOT.resolve("assets/globe/news-live.json"))).containsExactly(news);
        assertThat(Files.readAllBytes(ROOT.resolve("assets/globe/v5-ledger.json"))).containsExactly(calls);
    }

    @Test
    void healthAndStatusDescribeSnapshotModeWithoutInventingCloudflareStatistics() throws Exception {
        var health = mapper.readTree(mvc.perform(get("/api/health")).andExpect(status().isOk()).andReturn().getResponse().getContentAsString());
        assertThat(health.path("mode").asText()).isEqualTo("read-only-snapshots");
        var info = mapper.readTree(mvc.perform(get("/v1/status")).andExpect(status().isOk()).andReturn().getResponse().getContentAsString());
        assertThat(info.path("backend").asText()).isEqualTo("spring");
        assertThat(info.path("kv").isNull()).isTrue();
        assertThat(info.path("cron").isNull()).isTrue();
        mvc.perform(get("/ticker")).andExpect(status().isServiceUnavailable());
    }
}
