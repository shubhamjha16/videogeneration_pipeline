# ─────────────────────────────────────────────────────────────────────────────
# EaseToLearn Custom SearXNG Research Engine
# Bakes in the JSON-enabled settings for industrial sidecar usage.
# ─────────────────────────────────────────────────────────────────────────────

FROM searxng/searxng:latest

# Overwrite the default config with our agent-optimized settings
COPY settings.yml /etc/searxng/settings.yml

# SearXNG uses UID 977 in its official image. 
# We ensure the config is readable by the app user.
USER root
RUN chown searxng:searxng /etc/searxng/settings.yml

# Generate a unique secret_key at build time and inject it into settings.yml.
# This keeps the secret out of the git-tracked settings.yml source file.
# SearXNG refuses to start if secret_key is missing or equals 'ultrasecretkey'.
RUN SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))") \
    && sed -i "/^server:/a\\  secret_key: \"$SECRET\"" /etc/searxng/settings.yml

USER searxng

EXPOSE 8080

LABEL org.opencontainers.image.title="EaseToLearn SearXNG"
LABEL org.opencontainers.image.description="Metasearch engine sidecar for AI video factory"
