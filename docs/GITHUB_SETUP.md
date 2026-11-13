# Private GitHub setup

The connected GitHub account was verified as `amirpvry`; the target repository returned 404 and was absent from the account repository list. The connector has no create-repository operation, and the workspace CLI credential failed authentication. No remote was created or modified. No employer files or history were opened.

After authenticating the GitHub CLI on your machine, run from this project directory:

```bash
gh auth login
gh repo create amirpvry/ai-grading-portfolio --private --source=. --remote=origin --push \
  --description 'Independent Django backend demo: asynchronous AST grading, PostgreSQL transactions, Celery reliability, JWT and opt-in AI feedback'
gh repo edit amirpvry/ai-grading-portfolio \
  --add-topic python,django,django-rest-framework,postgresql,redis,celery,backend,ai,portfolio,docker
```

If a private repository already exists when you run this, inspect it before connecting or pushing. Do not force-push unrelated history. Do not change visibility until you have explicitly approved publication and reviewed the security audit. CI runs after push; its status has not been claimed here.

A profile README draft is provided locally in `docs/PROFILE_README_DRAFT.md`. No profile or unrelated repository was modified.
