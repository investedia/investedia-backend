package com.investedia.backend;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.investedia.backend.config.RepositoryProperties;
import com.investedia.backend.controller.CallController;
import com.investedia.backend.controller.MarketController;
import com.investedia.backend.controller.NewsController;
import com.investedia.backend.exception.ApiExceptionHandler;
import com.investedia.backend.exception.SnapshotUnavailableException;
import com.investedia.backend.repository.file.FileCallRepository;
import com.investedia.backend.repository.file.FileMarketRepository;
import com.investedia.backend.repository.file.FileNewsRepository;
import com.investedia.backend.repository.file.JsonSnapshotReader;
import com.investedia.backend.service.CallService;
import com.investedia.backend.service.MarketService;
import com.investedia.backend.service.NewsService;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Clock;
import java.time.ZoneOffset;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import tools.jackson.databind.json.JsonMapper;

class SnapshotRepositoryTest {
    @TempDir Path root;
    final JsonMapper mapper = JsonMapper.builder().build();

    JsonSnapshotReader reader(Path directory) {
        return new JsonSnapshotReader(new RepositoryProperties(directory.toString()), mapper);
    }

    @Test
    void missingAndMalformedSnapshotsFailClosedWithoutLeakingPaths() throws Exception {
        var reader = reader(root);
        var mvc = MockMvcBuilders.standaloneSetup(
                new MarketController(new MarketService(new FileMarketRepository(reader, mapper), Clock.systemUTC())),
                new NewsController(new NewsService(new FileNewsRepository(reader), Clock.systemUTC())),
                new CallController(new CallService(new FileCallRepository(reader))))
                .setControllerAdvice(new ApiExceptionHandler()).build();
        for (String route : new String[]{"prices", "news", "globe"}) {
            var response = mvc.perform(get("/v1/" + route)).andExpect(status().isServiceUnavailable()).andReturn().getResponse();
            assertThat(response.getContentAsString()).doesNotContain(root.toString()).doesNotContain("Exception");
        }
        mvc.perform(get("/v1/calls")).andExpect(status().isNotFound());
        Files.createDirectories(root.resolve("assets/globe"));
        Files.writeString(root.resolve("assets/quotes.js"), "window.QUOTES={broken};");
        Files.writeString(root.resolve("assets/globe/news-live.json"), "{broken}");
        Files.writeString(root.resolve("assets/globe/v5-ledger.json"), "{}");
        mvc.perform(get("/v1/prices")).andExpect(status().isServiceUnavailable());
        mvc.perform(get("/v1/news")).andExpect(status().isServiceUnavailable());
        mvc.perform(get("/v1/calls")).andExpect(status().isNotFound());
    }

    @Test
    void corruptLedgerKeepsTheDocumentedWorkerCompatible404WithoutWrites() throws Exception {
        Path ledger = root.resolve("assets/globe/v5-ledger.json");
        Files.createDirectories(ledger.getParent());
        var mvc = MockMvcBuilders.standaloneSetup(
                new CallController(new CallService(new FileCallRepository(reader(root)))))
                .setControllerAdvice(new ApiExceptionHandler()).build();
        for (String corrupt : new String[]{"{broken}", "{}", "{\"calls\":null}"}) {
            Files.writeString(ledger, corrupt);
            var response = mvc.perform(get("/v1/calls")).andExpect(status().isNotFound())
                    .andReturn().getResponse();
            assertThat(mapper.readTree(response.getContentAsString()).path("error").asText())
                    .isEqualTo("no live calls yet");
            assertThat(response.getContentAsString()).doesNotContain(root.toString(), "Exception");
            assertThat(response.getHeader("ETag")).isNull();
            assertThat(Files.readString(ledger)).isEqualTo(corrupt);
        }
    }

    @Test
    void repositoryCannotReadOutsideItsConfiguredRoot() throws Exception {
        Files.createDirectories(root.resolve("allowed"));
        Files.writeString(root.resolve("outside.json"), "{}");
        assertThatThrownBy(() -> reader(root.resolve("allowed")).bytes("../outside.json"))
                .isInstanceOf(SnapshotUnavailableException.class);
    }

    @Test
    void snapshotsAreRefreshedFromFilesWithoutWritingBack() throws Exception {
        var original = Files.readAllBytes(ApiContractTest.ROOT.resolve("assets/globe/news-live.json"));
        Files.createDirectories(root.resolve("assets/globe"));
        Path file = root.resolve("assets/globe/news-live.json");
        Files.write(file, original);
        var repository = new FileNewsRepository(reader(root));
        assertThat(repository.latest().articles()).isNotEmpty();
        assertThat(Files.readAllBytes(file)).containsExactly(original);
        Files.writeString(file, "{}");
        assertThatThrownBy(repository::latest).isInstanceOf(SnapshotUnavailableException.class);
    }

    @Test
    void freshnessBoundaryUsesSavedTimestampsRatherThanPretendingDataIsLive() {
        var repository = new FileMarketRepository(reader(ApiContractTest.ROOT), mapper);
        var snapshot = repository.latest();
        var boundary = new MarketService(repository, Clock.fixed(snapshot.asOf().plusMillis(360_000), ZoneOffset.UTC));
        var stale = new MarketService(repository, Clock.fixed(snapshot.asOf().plusMillis(360_001), ZoneOffset.UTC));
        assertThat(boundary.prices("all").meta().get("state")).isEqualTo("delayed");
        assertThat(stale.prices("all").meta().get("state")).isEqualTo("stale");
        assertThat(stale.prices("all").meta().get("upstream_ok")).isEqualTo(false);
    }
}
