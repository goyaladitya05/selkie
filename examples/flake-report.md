# Podman CI flake report

Generated 2026-08-16 14:13 UTC from `podman-container-tools/podman`.

Scanned **4** failed CI runs and found **16** distinct failure patterns across **16** occurrences.

## Patterns by frequency

| # | Count | Pattern | Dimensions | Category |
|---|-------|---------|------------|----------|
| 1 | 1 | [26-containersWait] POST containers/WaitTestingCtr/wait?condition=next-exit [-d  | **apiv2--rootless-fedora-current** | _uncategorized_ |
| 2 | 1 | [26-containersWait] POST containers/waitNextExit/wait?condition=next-exit [-d {} | **apiv2--rootless-fedora-current** | _uncategorized_ |
| 3 | 1 | [26-containersWait] Received headers from /wait | **apiv2--rootless-fedora-current** | _uncategorized_ |
| 4 | 1 | [26-containersWait] UNEXPECTED: curl on /wait returned results | **apiv2--rootless-fedora-current** | _uncategorized_ |
| 5 | 1 | [27-containersEvents] GET /v1.52/events?stream=false&since=(T) : status | **apiv2--rootless-fedora-current** | _uncategorized_ |
| 6 | 1 | [27-containersEvents] GET /v1.52/events?stream=false&since=(T)&type=remove : sta | **apiv2--rootless-fedora-current** | _uncategorized_ |
| 7 | 1 | [27-containersEvents] GET events?stream=false&since=(T) : status | **apiv2--rootless-fedora-current** | _uncategorized_ |
| 8 | 1 | [27-containersEvents] GET events?stream=false&since=(T)&type=remove : status | **apiv2--rootless-fedora-current** | _uncategorized_ |
| 9 | 1 | [27-containersEvents] GET events?stream=true: expected curl to time out; it did  | **apiv2--rootless-fedora-current** | _uncategorized_ |
| 10 | 1 | [27-containersEvents] GET libpod/events?stream=false&since=(T) : status | **apiv2--rootless-fedora-current** | _uncategorized_ |
| 11 | 1 | [27-containersEvents] Received headers from /events | **apiv2--rootless-fedora-current** | _uncategorized_ |
| 12 | 1 | [44-mounts] 'df' output includes tmpfs name | **apiv2--rootless-fedora-current** | _uncategorized_ |
| 13 | 1 | [44-mounts] GET containers/474126533bd3b399c5c39da23f2a603538f26bda535e443ba7284 | **apiv2--rootless-fedora-current** | _uncategorized_ |
| 14 | 1 | [44-mounts] compat mount subpath returns only selected subdir | **apiv2--rootless-fedora-current** | _uncategorized_ |
| 15 | 1 | podman build with a secret from file | **int**, **remote**, **root**, **fedora-prior** | _uncategorized_ |
| 16 | 1 | podman image rm - concurrent with shared layers | **int**, **local**, **root**, **fedora-rawhide** | _uncategorized_ |

## Details

### 1. [26-containersWait] POST containers/WaitTestingCtr/wait?condition=next-exit [-d {}] : status

- **Occurrences:** 1
- **Signature:** `59393b8bdf067847`
- **First seen:** 2026-08-15
- **Last seen:** 2026-08-15
- **Dimensions:** **apiv2--rootless-fedora-current**

<details><summary>Normalized signature</summary>

```
[<N>-containersWait] POST containers/WaitTestingCtr/wait?condition=next-exit [-d {}] : status|expected: <N> actual: <N> response: {"cause":"unable to open a handle to the library","message":"unable to open a handle to the library","response":<N>}
```

</details>

Recent runs:

- [apiv2--rootless-fedora-current](https://github.com/podman-container-tools/podman/actions/runs/31876401828) - pull_request, 2026-08-15

### 2. [26-containersWait] POST containers/waitNextExit/wait?condition=next-exit [-d {}] : status

- **Occurrences:** 1
- **Signature:** `dd98930571dc42df`
- **First seen:** 2026-08-15
- **Last seen:** 2026-08-15
- **Dimensions:** **apiv2--rootless-fedora-current**

<details><summary>Normalized signature</summary>

```
[<N>-containersWait] POST containers/waitNextExit/wait?condition=next-exit [-d {}] : status|expected: <N> actual: <N> response: {"cause":"unable to open a handle to the library","message":"unable to open a handle to the library","response":<N>}
```

</details>

Recent runs:

- [apiv2--rootless-fedora-current](https://github.com/podman-container-tools/podman/actions/runs/31876401828) - pull_request, 2026-08-15

### 3. [26-containersWait] Received headers from /wait

- **Occurrences:** 1
- **Signature:** `926566d90d191a6f`
- **First seen:** 2026-08-15
- **Last seen:** 2026-08-15
- **Dimensions:** **apiv2--rootless-fedora-current**

<details><summary>Normalized signature</summary>

```
[<N>-containersWait] Received headers from /wait|expected: ~ .*HTTP.* <N> OK.* actual: HTTP/<N>.<N> <N> Internal Server Error
```

</details>

Recent runs:

- [apiv2--rootless-fedora-current](https://github.com/podman-container-tools/podman/actions/runs/31876401828) - pull_request, 2026-08-15

### 4. [26-containersWait] UNEXPECTED: curl on /wait returned results

- **Occurrences:** 1
- **Signature:** `55f1be6291fa4bed`
- **First seen:** 2026-08-15
- **Last seen:** 2026-08-15
- **Dimensions:** **apiv2--rootless-fedora-current**

<details><summary>Normalized signature</summary>

```
[<N>-containersWait] UNEXPECTED: curl on /wait returned results|expected: actual:
```

</details>

Recent runs:

- [apiv2--rootless-fedora-current](https://github.com/podman-container-tools/podman/actions/runs/31876401828) - pull_request, 2026-08-15

### 5. [27-containersEvents] GET /v1.52/events?stream=false&since=(T) : status

- **Occurrences:** 1
- **Signature:** `f8070008ea120694`
- **First seen:** 2026-08-15
- **Last seen:** 2026-08-15
- **Dimensions:** **apiv2--rootless-fedora-current**

<details><summary>Normalized signature</summary>

```
[<N>-containersEvents] GET /v1.<N>/events?stream=false&since=(T) : status|expected: <N> actual: <N> response: {"cause":"unable to open a handle to the library","message":"unable to open a handle to the library","response":<N>}
```

</details>

Recent runs:

- [apiv2--rootless-fedora-current](https://github.com/podman-container-tools/podman/actions/runs/31876401828) - pull_request, 2026-08-15

### 6. [27-containersEvents] GET /v1.52/events?stream=false&since=(T)&type=remove : status

- **Occurrences:** 1
- **Signature:** `9f981bc85cc96cbe`
- **First seen:** 2026-08-15
- **Last seen:** 2026-08-15
- **Dimensions:** **apiv2--rootless-fedora-current**

<details><summary>Normalized signature</summary>

```
[<N>-containersEvents] GET /v1.<N>/events?stream=false&since=(T)&type=remove : status|expected: <N> actual: <N> response: {"cause":"unable to open a handle to the library","message":"unable to open a handle to the library","response":<N>}
```

</details>

Recent runs:

- [apiv2--rootless-fedora-current](https://github.com/podman-container-tools/podman/actions/runs/31876401828) - pull_request, 2026-08-15

### 7. [27-containersEvents] GET events?stream=false&since=(T) : status

- **Occurrences:** 1
- **Signature:** `a1d99abd8333add4`
- **First seen:** 2026-08-15
- **Last seen:** 2026-08-15
- **Dimensions:** **apiv2--rootless-fedora-current**

<details><summary>Normalized signature</summary>

```
[<N>-containersEvents] GET events?stream=false&since=(T) : status|expected: <N> actual: <N> response: {"cause":"unable to open a handle to the library","message":"unable to open a handle to the library","response":<N>}
```

</details>

Recent runs:

- [apiv2--rootless-fedora-current](https://github.com/podman-container-tools/podman/actions/runs/31876401828) - pull_request, 2026-08-15

### 8. [27-containersEvents] GET events?stream=false&since=(T)&type=remove : status

- **Occurrences:** 1
- **Signature:** `6b30b04ba1f68920`
- **First seen:** 2026-08-15
- **Last seen:** 2026-08-15
- **Dimensions:** **apiv2--rootless-fedora-current**

<details><summary>Normalized signature</summary>

```
[<N>-containersEvents] GET events?stream=false&since=(T)&type=remove : status|expected: <N> actual: <N> response: {"cause":"unable to open a handle to the library","message":"unable to open a handle to the library","response":<N>}
```

</details>

Recent runs:

- [apiv2--rootless-fedora-current](https://github.com/podman-container-tools/podman/actions/runs/31876401828) - pull_request, 2026-08-15

### 9. [27-containersEvents] GET events?stream=true: expected curl to time out; it did not

- **Occurrences:** 1
- **Signature:** `03cae67e227ff33c`
- **First seen:** 2026-08-15
- **Last seen:** 2026-08-15
- **Dimensions:** **apiv2--rootless-fedora-current**

<details><summary>Normalized signature</summary>

```
[<N>-containersEvents] GET events?stream=true: expected curl to time out; it did not|expected: actual:
```

</details>

Recent runs:

- [apiv2--rootless-fedora-current](https://github.com/podman-container-tools/podman/actions/runs/31876401828) - pull_request, 2026-08-15

### 10. [27-containersEvents] GET libpod/events?stream=false&since=(T) : status

- **Occurrences:** 1
- **Signature:** `6ab819339dd6300b`
- **First seen:** 2026-08-15
- **Last seen:** 2026-08-15
- **Dimensions:** **apiv2--rootless-fedora-current**

<details><summary>Normalized signature</summary>

```
[<N>-containersEvents] GET libpod/events?stream=false&since=(T) : status|expected: <N> actual: <N> response: {"cause":"unable to open a handle to the library","message":"unable to open a handle to the library","response":<N>}
```

</details>

Recent runs:

- [apiv2--rootless-fedora-current](https://github.com/podman-container-tools/podman/actions/runs/31876401828) - pull_request, 2026-08-15

### 11. [27-containersEvents] Received headers from /events

- **Occurrences:** 1
- **Signature:** `ef39090d54a8a666`
- **First seen:** 2026-08-15
- **Last seen:** 2026-08-15
- **Dimensions:** **apiv2--rootless-fedora-current**

<details><summary>Normalized signature</summary>

```
[<N>-containersEvents] Received headers from /events|expected: ~ .*HTTP.* <N> OK.* actual: HTTP/<N>.<N> <N> Internal Server Error
```

</details>

Recent runs:

- [apiv2--rootless-fedora-current](https://github.com/podman-container-tools/podman/actions/runs/31876401828) - pull_request, 2026-08-15

### 12. [44-mounts] 'df' output includes tmpfs name

- **Occurrences:** 1
- **Signature:** `c92c1c9634fbb6c2`
- **First seen:** 2026-08-15
- **Last seen:** 2026-08-15
- **Dimensions:** **apiv2--rootless-fedora-current**

<details><summary>Normalized signature</summary>

```
[<N>-mounts] 'df' output includes tmpfs name|expected: ~ .* /mytmpfs actual: {"cause":"unable to open a handle to the library","message":"failed to obtain logs for Container '<SHA256>': unable to open a handle to the library","response":<N>}
```

</details>

Recent runs:

- [apiv2--rootless-fedora-current](https://github.com/podman-container-tools/podman/actions/runs/31876401828) - pull_request, 2026-08-15

### 13. [44-mounts] GET containers/474126533bd3b399c5c39da23f2a603538f26bda535e443ba7284c0781f65ef5/logs?stdout=true : status

- **Occurrences:** 1
- **Signature:** `c7b9832deab9b030`
- **First seen:** 2026-08-15
- **Last seen:** 2026-08-15
- **Dimensions:** **apiv2--rootless-fedora-current**

<details><summary>Normalized signature</summary>

```
[<N>-mounts] GET containers/<SHA256>/logs?stdout=true : status|expected: <N> actual: <N> response: {"cause":"unable to open a handle to the library","message":"failed to obtain logs for Container '<SHA256>': unable to open a handle to the library","response":<N>}
```

</details>

Recent runs:

- [apiv2--rootless-fedora-current](https://github.com/podman-container-tools/podman/actions/runs/31876401828) - pull_request, 2026-08-15

### 14. [44-mounts] compat mount subpath returns only selected subdir

- **Occurrences:** 1
- **Signature:** `3542ec553dacc701`
- **First seen:** 2026-08-15
- **Last seen:** 2026-08-15
- **Dimensions:** **apiv2--rootless-fedora-current**

<details><summary>Normalized signature</summary>

```
[<N>-mounts] compat mount subpath returns only selected subdir|expected: ~ .*hello1$ actual: {"cause":"unable to open a handle to the library","message":"failed to obtain logs for Container '<SHA256>': unable to open a handle to the library","response":<N>}
```

</details>

Recent runs:

- [apiv2--rootless-fedora-current](https://github.com/podman-container-tools/podman/actions/runs/31876401828) - pull_request, 2026-08-15

### 15. podman build with a secret from file

- **Occurrences:** 1
- **Signature:** `4f7bbf3deb36f4a2`
- **First seen:** 2026-08-15
- **Last seen:** 2026-08-15
- **Dimensions:** **int**, **remote**, **root**, **fedora-prior**

<details><summary>Normalized signature</summary>

```
podman build with a secret from file|Command failed with exit status <N>. See above for error message.
```

</details>

Recent runs:

- [int-remote-root-fedora-prior](https://github.com/podman-container-tools/podman/actions/runs/31906086101) - pull_request, 2026-08-15

### 16. podman image rm - concurrent with shared layers

- **Occurrences:** 1
- **Signature:** `aa519083241a99f0`
- **First seen:** 2026-08-15
- **Last seen:** 2026-08-15
- **Dimensions:** **int**, **local**, **root**, **fedora-rawhide**

<details><summary>Normalized signature</summary>

```
podman image rm - concurrent with shared layers|BuildImage session output: "STEP <N>/<N>: FROM quay.io/libpod/cirros:latest STEP <N>/<N>: RUN touch rmtest:<N> COMMIT rmtest:<N>" Expected <int>: <N> to match exit code: <int>: <N>
```

</details>

Recent runs:

- [int-local-root-fedora-rawhide](https://github.com/podman-container-tools/podman/actions/runs/31876401828) - pull_request, 2026-08-15


## Skip markers with no recent matching failure

These tests are skipped for a tracked flake that was not observed in the scanned window. They may be candidates for re-enabling, but note that a skipped test cannot produce the failures this tool detects, so each needs a human check before removal.

| Issue | File | Line |
|-------|------|------|
| #7371 | `test/system/120-load.bats` | 76 |
| #8342 | `test/system/070-build.bats` | 795 |
| #8343 | `test/system/070-build.bats` | 796 |
| #11871 | `test/system/500-networking.bats` | 266 |
| #14536 | `test/system/070-build.bats` | 563 |
| #14873 | `test/system/130-kill.bats` | 143 |
| #15464 | `test/system/200-pod.bats` | 554 |
| #20196 | `test/e2e/restart_test.go` | 248 |
| #20196 | `test/e2e/run_test.go` | 1843 |
| #24230 | `test/e2e/checkpoint_test.go` | 1057 |
| #24571 | `test/e2e/checkpoint_test.go` | 1214 |
| #27264 | `test/system/702-artifact.bats` | 8 |
| #27759 | `test/system/161-volume-quotas.bats` | 45 |
| #28576 | `test/system/520-checkpoint.bats` | 137 |
