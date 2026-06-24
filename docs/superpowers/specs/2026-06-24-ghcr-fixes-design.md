# GHCR Packaging Fixes Design

**Date:** 2026-06-24  
**Status:** Approved

## Problems

1. **Size N/A in GHCR:** The multi-arch manifest list has an extra BuildKit SLSA provenance manifest injected by the `build-push-action` default (`provenance: true`). GHCR can't compute size for an index containing an unknown manifest type.
2. **No badges:** The provenance badge never appears because the BuildKit inline provenance (separate from `attest-build-provenance`) pollutes the index. The GitHub-native attestation gets created, but the UI badge doesn't surface cleanly.
3. **137 versions:** Every push accumulates BuildKit provenance manifests, per-tag amd64/arm64 manifests, and GitHub attestation artifacts, none of them pruned.
4. **Co-Authored-By in git history:** Every commit carries `Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>`. The goal is to remove it from all past commits and stop adding it going forward.

## Solution

### 1. ci.yml: three changes

**Change A: disable BuildKit inline provenance**

Add `provenance: false` to the `build-push-action` step. This removes the extra manifest that causes the N/A size and version bloat. The GitHub-native attestation (`attest-build-provenance`) is separate and unaffected.

```yaml
- name: Build and push
  id: build
  uses: docker/build-push-action@...
  with:
    ...
    provenance: false      # add this line
```

**Change B: add cosign keyless signing**

Goes after the `attest-build-provenance` step. It uses GitHub OIDC, so no secrets are needed. It signs the manifest list digest, which covers both platforms. The `id-token: write` permission is already in the job.

```yaml
- name: Install cosign
  uses: sigstore/cosign-installer@<pinned-hash>  # v3 - resolve hash in implementation

- name: Sign image
  run: cosign sign --yes ghcr.io/${{ github.repository }}@${{ steps.build.outputs.digest }}
```

Both new actions (`cosign-installer`, `delete-package-versions`) must be pinned to commit hashes per the existing workflow pattern (e.g. `uses: action@abc123 # v3`).

**Change C: prune old untagged versions**

Last step in the job. Keeps the 5 newest untagged manifests (roughly 2 recent builds worth of attestation artifacts) and deletes everything older. Runs on every push, so it gradually chips away at the accumulated 137.

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

### 2. Git history: strip Co-Authored-By

Use `git filter-repo` to remove the `Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>` trailer from all commit messages, then force-push `main`.

```bash
git filter-repo --message-callback '
    import re
    return re.sub(rb"\nCo-[Aa]uthored-[Bb]y: Claude.*\n?", b"\n", message).rstrip() + b"\n"
'
git push --force origin main
```

Implications:
- All commit SHAs are rewritten. Anyone with a local clone needs to re-clone or run `git fetch --all && git reset --hard origin/main`.
- Existing `sha-XXXX` GHCR image tags become orphaned. They're harmless, and the new prune step will clean them up over time.
- Branch protection on `main` must allow force-push temporarily. Re-enable it immediately after.

### 3. ~/.claude/CLAUDE.md: stop future attribution

Remove the `Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>` line from the commit template in the global CLAUDE.md. No new commits will carry the trailer.

## Verification

After CI runs on the next push to `main`:
- GHCR package page shows a numeric size (not N/A)
- Package page shows the provenance badge (SLSA) and signed badge (cosign)
- Version count drops and stabilizes near `(tagged versions) + 5` after a few pushes
- `git log` shows no Co-Authored-By trailers on any commit
