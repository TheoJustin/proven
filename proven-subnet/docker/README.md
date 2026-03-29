# Docker Fixtures

The validator evaluates miner-generated tests against two local web-app fixtures:

- `reference/`: the clean application
- `mutant/`: the intentionally changed application

Both directories build simple Nginx images that serve the bundled static assets.

## Recommended Local Ports

- Reference app: `127.0.0.1:8080`
- Mutant app: `127.0.0.1:8081`

The validator code assumes those endpoints by default.

## Operational Notes

- Bind these containers to localhost on a VPS unless you explicitly need public access.
- The media bundles here are large and may have licensing implications if the repo becomes public-facing. Re-audit the asset set before public release or commercialization.
