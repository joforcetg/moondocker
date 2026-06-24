# GHCR Packaging Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix GHCR image size N/A, add provenance and signature badges, prune version count, and strip Co-Authored-By trailers from git history.

**Architecture:** Three isolated changes — update `~/.claude/CLAUDE.md` to stop future attribution, patch `.github/workflows/ci.yml` with `provenance: false` + cosign signing + version cleanup, then rewrite git history with `git filter-repo` and force-push.

**Tech Stack:** GitHub Actions, Docker Buildx, sigstore/cosign (keyless via GitHub OIDC), git-filter-repo

## Global Constraints

- All new action `uses:` pins must use full commit SHA + `# vX.Y.Z` comment, matching existing workflow pattern
- `cosign sign` uses keyless signing (GitHub OIDC) — no secrets added
- `git filter-repo` removes only `Co-Authored-By: Claude*` trailers, leaves all other trailers untouched
- Force-push to `main` requires temporarily disabling branch protection; re-enable immediately after
- No new Python dependencies, no new files beyond the workflow edit

---

### Task 1: Stop future Co-Authored-By attribution

**Files:**
- Modify: `~/.claude/CLAUDE.md` (global Claude Code config — outside the repo)

**Interfaces:**
- Produces: Claude Code no longer appends `Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>` to any commit

- [ ] **Step 1: Add no-attribution rule to CLAUDE.md**

The system prompt instructs Claude to append `Co-Authored-By` trailers. A CLAUDE.md rule overrides it (user instructions beat system prompt).

Open `~/.claude/CLAUDE.md`. Under the `## Humanizer & Commits` section, add this line:

```markdown
- Do not add Co-Authored-By trailers to commit messages.
```

The section should look like this after the edit:

```markdown
## Humanizer & Commits

- Humanizer skill installed at ~/.claude/skills/humanizer/.
- All commit messages, PR titles, PR descriptions, and GitHub content in ENGLISH.
- Commit style: direct, imperative, natural human tone. No refactor, enhance, leverage, utilize, robust, streamline. Short phrases like fix login redirect, add email validation, clean up dead code.
- Run humanizer on any text before pushing commits or opening PRs.
- Do not add Co-Authored-By trailers to commit messages.
```

- [ ] **Step 2: Verify**

```bash
grep "Co-Authored\|co-authored" ~/.claude/CLAUDE.md
```

Expected: no output (the rule prevents addition; it doesn't need the literal string in CLAUDE.md).

```bash
grep "Do not add Co-Authored" ~/.claude/CLAUDE.md
```

Expected: `- Do not add Co-Authored-By trailers to commit messages.`

> Note: No commit for this task — `~/.claude/CLAUDE.md` is outside the repo.

---

### Task 2: Fix ci.yml — provenance, cosign, cleanup

**Files:**
- Modify: `.github/workflows/ci.yml` (lines 66–93 of the `build-and-push` job)

**Interfaces:**
- Consumes: `${{ steps.build.outputs.digest }}` — the manifest list digest from the build step (already exists)
- Produces: CI pushes image without inline BuildKit provenance, attaches cosign signature, prunes old untagged versions after each run

- [ ] **Step 1: Add `provenance: false` to build step**

In `.github/workflows/ci.yml`, find the `Build and push` step (currently ends at `cache-to: type=gha,mode=max`). Add `provenance: false` as the last line of the `with` block:

```yaml
      - name: Build and push
        id: build
        uses: docker/build-push-action@f9f3042f7e2789586610d6e8b85c8f03e5195baf # v7
        with:
          context: .
          platforms: linux/amd64,linux/arm64
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
          provenance: false
```

- [ ] **Step 2: Add cosign steps after `Attest build provenance`**

After the existing `Attest build provenance` step, insert these two steps:

```yaml
      - name: Install cosign
        if: github.event.repository.visibility == 'public'
        uses: sigstore/cosign-installer@6f9f17788090df1f26f669e9d70d6ae9567deba6 # v4.1.2

      - name: Sign image
        if: github.event.repository.visibility == 'public'
        run: cosign sign --yes ghcr.io/${{ github.repository }}@${{ steps.build.outputs.digest }}
```

- [ ] **Step 3: Add cleanup step at end of job**

After the existing `Scan image for CVEs` step, append:

```yaml
      - name: Clean up old untagged versions
        uses: actions/delete-package-versions@e5bc658cc4c965c472efe991f8beea3981499c55 # v5.0.0
        with:
          package-name: moondocker
          package-type: container
          min-versions-to-keep: 5
          delete-only-untagged-versions: true
```

- [ ] **Step 4: Verify YAML syntax**

```bash
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml')); print('YAML OK')"
```

Expected: `YAML OK`

- [ ] **Step 5: Verify final step order in the job**

```bash
grep -n "name:" .github/workflows/ci.yml | tail -15
```

Expected order (last section of `build-and-push` job):
```
  - Set up QEMU
  - Set up Docker Buildx
  - Log in to GHCR
  - Extract metadata
  - Build and push
  - Attest build provenance
  - Install cosign
  - Sign image
  - Scan image for CVEs
  - Clean up old untagged versions
```

- [ ] **Step 6: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "fix(ci): disable BuildKit provenance, add cosign signing, prune old versions"
```

- [ ] **Step 7: Push and verify CI**

```bash
git push origin main
```

Watch the `build-and-push` job in GitHub Actions. After it completes:
- Go to the GHCR package page (`https://github.com/joforcetg/moondocker/pkgs/container/moondocker`)
- Size column should show a number (not N/A)
- Package page should show provenance and signed badges

---

### Task 3: Strip Co-Authored-By from git history

> **Warning:** This rewrites every commit SHA. Force-push to `main` required. Anyone with a local clone must re-clone or run `git fetch --all && git reset --hard origin/main` afterward.

**Files:**
- Destructive rewrite of git history (no files changed, all commit SHAs change)

**Interfaces:**
- Produces: `git log` shows zero `Co-Authored-By: Claude*` trailers across all commits; other trailers (dependabot, user) are preserved

- [ ] **Step 1: Install git-filter-repo**

```bash
sudo apt-get install -y git-filter-repo
```

If apt doesn't have it (Debian 13 should):

```bash
pip install --user git-filter-repo
```

Verify:

```bash
git filter-repo --version
```

Expected: a version string like `2.47.0` (any version is fine)

- [ ] **Step 2: Note the remote URL (filter-repo removes it)**

```bash
git remote get-url origin
```

Copy the output — you'll need it in Step 5. For this repo it should be:
`https://github.com/joforcetg/moondocker.git`

- [ ] **Step 3: Verify the filter before running it**

Check how many commits currently have the trailer:

```bash
git log --format="%H %s" | wc -l
git log --format="%B" | grep -c "Co-Authored-By: Claude"
```

Note both numbers — you'll verify they drop to 0 after filter-repo.

- [ ] **Step 4: Run git-filter-repo**

```bash
git filter-repo --message-callback '
import re
return re.sub(rb"\nCo-[Aa]uthored-[Bb]y: Claude[^\n]*", b"", message).rstrip() + b"\n"
' --force
```

This removes any line matching `Co-Authored-By: Claude…` (case-insensitive `A`/`a`, `B`/`b`). All other trailers (dependabot, user co-authors) are left intact.

- [ ] **Step 5: Verify the rewrite**

```bash
git log --format="%B" | grep -i "co-authored-by: claude"
```

Expected: no output.

```bash
git log --format="%B" | grep -i "co-authored-by"
```

Expected: only dependabot/user lines remain (if any).

```bash
git log --oneline | head -5
```

Confirm commit count looks right (same number as Step 3).

- [ ] **Step 6: Re-add the remote (filter-repo removes it)**

```bash
git remote add origin https://github.com/joforcetg/moondocker.git
git fetch origin
```

- [ ] **Step 7: Disable branch protection, force-push, re-enable**

> **Manual step:** In GitHub → Settings → Branches → main protection rule → temporarily uncheck "Require a pull request before merging" or enable "Allow force pushes". Then:

```bash
git push --force origin main
```

> **Immediately after push:** Re-enable branch protection.

- [ ] **Step 8: Verify on GitHub**

```bash
gh api repos/joforcetg/moondocker/commits --jq '.[0:3][].commit.message' | grep -i "co-authored-by: claude"
```

Expected: no output.

Also check a few older commits in the GitHub UI to confirm the trailers are gone.
