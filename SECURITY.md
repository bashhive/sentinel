# Security Policy

## Reporting a vulnerability

Email **contact@bashhive.eu** with `SECURITY` in the subject. Include the
component, the input needed to reproduce, and what you observed.

Do not open a public GitHub issue for an unfixed vulnerability.

We will acknowledge within **3 working days**. This is a small operation, not a
funded programme: there is no bounty, and the fix timeline depends on severity.

## What this is

HiveSec Sentinel builds a verified vulnerability feed from public advisory
sources and publishes it to the BASH/HiveSec sites. It reads public data, writes
a bounded JSON feed, and holds no customer data.

## Scope

In scope:

- The advisory ingestion and verification pipeline — in particular anything that
  lets untrusted feed content change what gets published, or reach a shell,
  a filesystem path or a template.
- The Cloudflare Worker intake channel and its shared-secret authentication.
- The publication path into the website repository, and the delivery receipts.
- Anything that would let the feed publish an alert we did not verify, or
  suppress one we did.

Out of scope:

- The upstream advisory sources themselves — report those to their maintainers.
- Findings that need write access to this repository or to the deployment
  credentials.
- Reports produced solely by automated tooling, with no demonstrated impact.
- Denial of service, and anything requiring physical access.

## Design notes worth knowing before you report

- **Feed content is untrusted input by design.** The pipeline treats advisory
  text as data, never as instructions, and the publisher requires an explicit
  `public_brand` execution profile before anything leaves the machine. A bypass
  of either is exactly the kind of report we want.
- The intake authenticates with a **shared secret**, not Cloudflare Access — that
  changed on 2026-09-10 and was deliberate.
- Dependencies are pinned in `uv.lock`. As of 2026-09-10 a `syft` SBOM scanned
  with `grype --only-fixed` reports no known fixable vulnerabilities in the
  installed tree.

## Handling

Confirmed issues are fixed on a branch, released through the normal path, and
recorded in the changelog. We will credit you if you want to be credited.
