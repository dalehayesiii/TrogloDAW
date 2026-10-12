# Owner setup for merge enforcement

The contributing account has WRITE, not ADMIN, permission. An owner must configure
these settings; workflows alone cannot prevent merging despite failed checks.

1. Enable GitHub Actions and allow the released actions in `ci.yml`, including
   amannn/action-semantic-pull-request, dorny/paths-filter and astral-sh/setup-uv.
   Dependabot proposes action version updates monthly.
2. Allow only squash merges. Set the squash subject to **Pull request title** and
   body to **Pull request body** to preserve conventional titles/breaking footers.
3. Protect main: require PRs and these five GitHub status checks:
   **PR title and docs**, **Python checks**, **Angular checks**,
   **Integration and specs**, **Windows build and installed app**.
   Remove the old aggregate **Required checks** requirement. Require the branch
   up to date, block force pushes/deletion, and apply to admins with no bypass.
   Valid docs changes intentionally skip Python/Angular/build; title and specs
   still run. GitHub enforces required statuses; there is no aggregate-check job.
4. Permit `contents: write` for the main publisher's `GITHUB_TOKEN`. Keep default
   tokens read-only; never add personal release tokens to PR jobs.
5. Create `openspec:proposal-only` only if proposal-only work is requested.

Owner-authenticated CLI for merge settings:
```powershell
gh auth status
gh api repos/dalehayesiii/music-maker --jq .permissions
gh repo edit dalehayesiii/music-maker --enable-squash-merge --enable-merge-commit=false --enable-rebase-merge=false
gh api --method PATCH repos/dalehayesiii/music-maker -f squash_merge_commit_title=PR_TITLE -f squash_merge_commit_message=PR_BODY
```
Configure protection in Settings > Rules > Rulesets (or Branches), preserving any
stronger existing policy. No merge queue is configured: add a tested `merge_group`
workflow/policy before enabling a merge queue with these checks.
