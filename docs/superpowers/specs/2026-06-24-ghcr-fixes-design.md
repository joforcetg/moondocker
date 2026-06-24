# GHCR Packaging Fixes Design

**Date:** 2026-06-24  
**Status:** Approved

## Problems

1. **Size N/A in GHCR** — multi-arch manifest list has an extra BuildKit SLSA provenance manifest injected by `build-push-action` default (`provenance: true`). GHCR can't compute size for an index containing an unknown manifest type.
2. **No badges** — provenance badge never appears because the BuildKit inline provenance (separate from `attest-build-provenance`) pollutes the index. The GitHub-native attestation gets created but the UI badge doesn't surface cleanly.
3. **137 versions** — every push accumulates: BuildKit provenance manifests + per-tag amd64/arm64 manifests + GitHub attestation artifacts, none pruned.
4. **Co-Authored-By in git history** — every commit carries `Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>` trailer; user wants this removed from all past commits and stopped going forward.

## Solution

### 1. ci.yml — three changes

**Change A: disable BuildKit inline provenance**

Add `provenance: false` to the `build-push-action` step. This removes the extra manifest that causes N/A size and version bloat. The GitHub-native attestation (`attest-build-provenance`) is separate and unaffected.

```yaml
- name: Build and push
  id: build
  uses: docker/build-push-action@...
  with:
    ...
    provenance: false      # add this line
```

**Change B: add cosign keyless signing**

Insert after the `attest-build-provenance` step. Uses GitHub OIDC — no secrets required. Signs the manifest list digest (covers both platforms). Permissions `id-token: write` already present.

```yaml
- name: Install cosign
  uses: sigstore/cosign-installer@<pinned-hash>  # v3 — resolve hash in implementation

- name: Sign image
  run: cosign sign --yes ghcr.io/${{ github.repository }}@${{ steps.build.outputs.digest }}
```

Both new actions (`cosign-installer`, `delete-package-versions`) must be pinned to commit hashes per existing workflow pattern (e.g. `uses: action@abc123 # v3`).

**Change C: prune old untagged versions**

Final step in the job. Keeps 5 newest untagged manifests (~2 recent builds' attestation artifacts), deletes all older ones. Chips away at accumulated 137 on every push.

```yaml
- name: Clean up old untagged versions
  uses: actions/delete-package-versions@v5
  with:
    package-name: moondocker
    package-type: container
    min-versions-to-keep: 5
    delete-only-untagged-versions: true
```

**Final step order in `build-and-push` job:**

1. checkout, QEMU, Buildx, login, meta (unchanged)
2. Build and push (`provenance: false` added)
3. Attest build provenance (unchanged)
4. **Install cosign** (new)
5. **Sign image** (new)
6. Scan image for CVEs (unchanged)
7. **Clean up old untagged versions** (new)

### 2. Git history — strip Co-Authored-By

Use `git filter-repo` to remove the `Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>` trailer from all commit messages, then force-push `main`.

```bash
git filter-repo --message-callback '
    import re
    return re.sub(rb"\nCo-[Aa]uthored-[Bb]y: Claude.*\n?", b"\n", message).rstrip() + b"\n"
'
git push --force origin main
```

Implications:
- All commit SHAs rewritten — anyone with a local clone needs to re-clone or `git fetch --all && git reset --hard origin/main`
- Existing `sha-XXXX` GHCR image tags become orphaned (stale, harmless — cleaned up by the new prune step over time)
- Branch protection on `main` must allow force-push temporarily; re-enable immediately after

### 3. ~/.claude/CLAUDE.md — stop future attribution

Remove the `Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>` line from the commit template in the global CLAUDE.md. No new commits will carry the trailer.

## Verification

After CI runs on the next push to `main`:
- GHCR package page shows numeric size (not N/A)
- Package page shows provenance badge (SLSA) and signed badge (cosign)
- Version count drops; stabilizes near `(tagged versions) + 5` after a few pushes
- `git log` shows no Co-Authored-By trailers on any commit
