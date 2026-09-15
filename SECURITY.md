# Security

Keep credentials in environment/secrets management, never Git. Raw source captures remain private. Public/client-safe outputs should contain normalized claims, metrics, provenance links and short quotations only where legally appropriate.

Do not expose PostgreSQL, Dagster, changedetection.io or acquisition workers publicly unless explicitly required and protected. Prefer Tailscale/private networking between Oracle and Hetzner services.
