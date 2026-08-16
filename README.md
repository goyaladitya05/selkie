# Selkie

Flake triage for Podman's GitHub Actions CI.

Selkie fetches failed CI runs from the GitHub Actions API, parses the log
artifacts Podman already produces, collapses failures into stable signatures,
and keeps a persistent record of every distinct flake pattern it has seen. An
optional analysis layer categorizes each pattern with an LLM.

This is a proof of concept built while preparing an LFX Mentorship proposal for
[podman-container-tools/podman](https://github.com/podman-container-tools/podman).
It runs against the real repository today.

## Why this shape

**Deterministic first, agentic second.** Fetching, parsing, de-duplication and
counting are plain code. The model is used for exactly one thing code cannot do:
reading a failure and explaining why it happened. That keeps the system
debuggable, keeps model cost proportional to *unique* failures rather than total
CI volume, and means the pipeline still produces a useful de-duplicated report
when no model is configured at all.

**Podman's logs are already structured.** Every test job pipes through
`hack/ci/logformatter`, which converts Ginkgo (`test/e2e`) and BATS
(`test/system`) output into HTML. Selkie parses that rather than grepping raw
text.

**Artifact names carry the analysis axes.** Logs are uploaded as
`{test}-{mode}-{priv}-{distro}.logs`, so every failure arrives tagged with
suite, local/remote, root/rootless and distro. Grouping along those axes answers
the first question a maintainer asks: *is this rootless-only? debian-only?*

**No new infrastructure.** State is JSON files intended to live on a dedicated
git branch. No database, no service, nothing to operate. `git log` is the audit
trail.

## Install

Python 3.10+ and a GitHub token. No dependencies.

```
git clone <this repo> && cd selkie
export GITHUB_TOKEN=...      # or just have `gh auth login` done
```

## Use

```bash
# Fetch the last 20 failed CI runs and fingerprint every failure.
python3 -m selkie.cli ingest --runs 20

# Post-merge runs only. A failure on main is near-certainly a flake or an
# infrastructure problem, because that code just passed the identical suite
# on its pull request.
python3 -m selkie.cli ingest --runs 20 --event push

# Cross-reference against in-tree skip markers in a podman checkout.
python3 -m selkie.cli link ~/src/podman

# Categorize patterns with a locally served model (optional).
export SELKIE_LLM_BASE_URL=http://localhost:8080/v1
python3 -m selkie.cli analyze

# Render the report.
python3 -m selkie.cli report -o flake-report.md --podman ~/src/podman
```

See [`examples/flake-report.md`](examples/flake-report.md) for real output.

## How deduplication works

The same flake looks different every time it fires: different timestamps,
container IDs, ports, durations, temp directories and scheduler addresses. Before
hashing, those tokens are normalized away:

```
podman logs c-ltfu-t93-uxvehj2c failed at 08/15/26 20:38:15.857 in 10466ms
podman logs c-ltfu-t93-pp42aakz failed at 08/16/26 03:02:11.004 in  9871ms
                    |
                    v
podman logs c-ltfu-t<N>-<RAND> failed at <TIME> in <DUR>
```

Both collapse to one signature hash. The test identity is hashed alongside the
error, so a generic message such as `exit status 125` occurring in two unrelated
tests does not merge them.

The normalization rules are Podman-specific on purpose: the random resource-name
suffixes, BATS scratch directories and CI checkout prefixes handled here are the
noise these logs actually contain.

## The skip-marker loop

Podman tracks known flakes in the source tree:

```
skip "FIXME #27759: There is a selinux problem with this test"
skip_if_aarch64 "FIXME #28576: selinux problem only on aarch64"
```

and `hack/ci/pr-removes-fixed-skips` enforces that a PR closing an issue also
removes the matching skip. Reading those markers lets Selkie answer two
questions a log-only view cannot:

1. Is a newly seen pattern already tracked? If so, annotate it rather than
   filing a duplicate.
2. Has a tracked flake stopped firing? Then its skip may be removable, which
   turns the report into a tool for *shrinking* the skip list.

A skipped test cannot produce the failures this tool detects, so stale-skip
findings are reported as candidates for a human to confirm, never acted on
automatically.

## Local-first inference

Model access goes through an OpenAI-compatible endpoint, so a locally served
model works unchanged:

```bash
ramalama serve qwen2.5-coder
export SELKIE_LLM_BASE_URL=http://localhost:8080/v1
python3 -m selkie.cli analyze
```

Hosted APIs are opt-in via `SELKIE_LLM_API_KEY`. CI logs can contain hostnames,
infrastructure details and tokens leaked into error output, so they should not
silently transit a third-party service. With no endpoint configured, everything
except categorization still works.

Categories are grounded in Podman's actual flake history rather than invented:
`test-race`, `product-race`, `network-registry`, `platform-specific`,
`storage-environment`, `infrastructure`, and `deterministic-regression`.

That last one is deliberate. A triage system that cannot say *"this one is real,
do not re-run it"* trains people to ignore it.

## Layout

```
selkie/
  github.py       GitHub Actions API client (stdlib only)
  parse.py        Ginkgo and BATS parsers over logformatter HTML
  fingerprint.py  normalization and signature hashing
  store.py        pattern knowledge base (JSON, git-branch friendly)
  skipmarkers.py  in-tree skip/FIXME cross-referencing
  analyze.py      optional LLM categorization
  report.py       Markdown report
  cli.py          entry point
tests/            unit tests, fixtures captured from real failed CI runs
```

## Tests

```
python3 -m unittest discover -s tests
```

Fixtures are real trimmed logformatter output from failed runs of
podman-container-tools/podman, so the parsers are exercised against the exact
shapes CI produces.

## Status and known limitations

Proof of concept. Working end to end against the live repository; not yet
deployed as a scheduled workflow.

- Categorization accuracy has not been measured against a labeled corpus yet.
  The intended ground truth is the `flakes`-labeled issues plus the in-tree skip
  markers.
- Suites other than `int` and `sys` (apiv2, compose, docker-py) are parsed on a
  best-effort basis: both parsers are tried, and the TAP-style output of several
  of them is picked up by the BATS parser.
- Artifact retention bounds how far back ingestion can reach, so scheduled runs
  need to keep pace with expiry.
- Issue filing, PR comments and scheduled execution are designed but not built.
