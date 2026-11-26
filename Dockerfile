# SDLC360 hosted (deploy/gcp/site.sh): Cloud Run behind Identity-Aware Proxy. Stdlib-only Python plus git for the clones.
# runs/ is a Cloud Storage bucket mounted at /mnt/runs; the clone cache is the instance's own disk (memory).
FROM python:3.12-slim
RUN apt-get update -qq && apt-get install -y -qq --no-install-recommends git ca-certificates > /dev/null \
    && rm -rf /var/lib/apt/lists/* && useradd --create-home --uid 10001 sdlc
WORKDIR /srv/sdlc360
COPY --chown=sdlc sdlc.py ./
COPY --chown=sdlc src ./src
COPY --chown=sdlc assessment ./assessment
USER sdlc
ENV PYTHONUNBUFFERED=1 SDLC360_CLOUD=1 PORT=8080
EXPOSE 8080
CMD ["python", "sdlc.py", "serve", "--runs-dir", "/mnt/runs", "--cache-dir", "/tmp/repos"]
