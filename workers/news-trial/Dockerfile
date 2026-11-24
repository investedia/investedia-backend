FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUTF8=1 PYTHONDONTWRITEBYTECODE=1
COPY update_globe_news.py update_globe_news.py
COPY news_core.py news_core.py
COPY registry.py registry.py
COPY events.py events.py
COPY tools/news_library.py tools/news_library.py
COPY tools/globe-news/connections.py tools/globe-news/connections.py
COPY tools/globe-news/iso.json tools/globe-news/iso.json
COPY tools/globe-news/wb-countries.json tools/globe-news/wb-countries.json
COPY data/registry.json data/registry.json
COPY assets/quotes.js assets/quotes.js
COPY assets/globe/countries-50m.json assets/globe/countries-50m.json
COPY assets/globe/iso.json assets/globe/iso.json
COPY assets/globe/markets.json assets/globe/markets.json
COPY assets/globe/projects.json assets/globe/projects.json
COPY workers/news-trial/runner.py workers/news-trial/runner.py
COPY update_calendar.py update_calendar.py
COPY calendar_fred.py calendar_fred.py
COPY calendar_official.py calendar_official.py
COPY workers/news-trial/calendar_job.py workers/news-trial/calendar_job.py
COPY .local/cloudflare-frontend/ .local/cloudflare-frontend/
COPY tools/coverage/country_basics.py tools/coverage/country_basics.py
COPY assets/globe/economy.json assets/globe/economy.json
COPY data/market-country-facts.json data/market-country-facts.json
COPY tools/publish_library.py tools/publish_library.py
COPY tools/push-news-to-worker.py tools/push-news-to-worker.py
COPY tools/push-connections-to-worker.py tools/push-connections-to-worker.py
COPY workers/news-trial/index_job.py workers/news-trial/index_job.py
COPY .local/cloudflare-library-index/ .local/cloudflare-library-index/
USER 65532:65532
EXPOSE 8080
CMD ["python", "workers/news-trial/runner.py"]
