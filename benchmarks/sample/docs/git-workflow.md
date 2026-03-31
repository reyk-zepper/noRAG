# Git Workflow Guide

## Branching Strategy

A good branching strategy is essential for team collaboration. The most common approach is Git Flow:

- **main** — production-ready code, always stable
- **develop** — integration branch for features
- **feature/** — individual feature branches
- **hotfix/** — urgent production fixes
- **release/** — release preparation branches

## Common Commands

### Creating and switching branches

```bash
git checkout -b feature/new-login
git switch -c feature/new-login  # modern syntax
```

### Committing changes

```bash
git add -p              # stage interactively
git commit -m "feat: add login page"
git commit --amend      # modify last commit
```

### Merging and rebasing

```bash
git merge feature/new-login
git rebase main         # replay commits on top of main
git rebase -i HEAD~3    # interactive rebase last 3 commits
```

## Pull Request Best Practices

1. Keep PRs small — under 400 lines of changes
2. Write descriptive titles and descriptions
3. Include test coverage for new functionality
4. Request reviews from relevant team members
5. Address all review comments before merging

## Conflict Resolution

When merge conflicts occur:

1. Open the conflicted files
2. Look for conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`)
3. Choose the correct version or combine both
4. Stage the resolved files and complete the merge

## Git Hooks

Git hooks automate tasks at various points in the workflow:

- **pre-commit** — run linters, formatters before committing
- **commit-msg** — validate commit message format
- **pre-push** — run tests before pushing
- **post-merge** — install dependencies after merging
