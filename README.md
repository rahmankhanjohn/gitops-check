# gitops-check

![Tests](https://github.com/rahmankhanjohn/gitops-check/actions/workflows/test.yml/badge.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![XERJ Corpus Hub contributor](https://hub.xerj.org/contributors/rahmankhanjohn/badge.svg)
![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)
![Dependencies: 0](https://img.shields.io/badge/dependencies-0-brightgreen.svg)
![Tests: 10](https://img.shields.io/badge/tests-10%20passing-brightgreen.svg)
![GitHub stars](https://img.shields.io/github/stars/rahmankhanjohn/gitops-check?style=social)
![Last commit](https://img.shields.io/github/last-commit/rahmankhanjohn/gitops-check)


Validate GitOps repository structure before the reconciliation loop runs.

Most teams call their deployment process GitOps. What they have is a Git repository with a deploy script. The reconciliation loop, secret externalization, and controller configuration are the parts that make it real. This tool checks whether they exist.

## What it checks

- **Controller detection** â€” ArgoCD or Flux present in the repo
- **Secret externalization** â€” Sealed Secrets, SOPS, or External Secrets (not plaintext)
- **Plaintext secret scan** â€” passwords, tokens, API keys, private keys in Git
- **Config separation** â€” config repo distinct from app code repo

## Usage

```bash
python gitops_check.py /path/to/gitops-repo
python gitops_check.py /path/to/gitops-repo --report
python gitops_check.py /path/to/gitops-repo --json
```

## Output

```
GitOps Check: /path/to/repo
  Controller: argocd
  Secrets externalized: YES
  Plaintext secrets: 0
  Config separated from app code: YES
  Score: 90/100
  Report line: GitOps check: controller=argocd, secrets=externalized, plaintext=0, score=90/100
```

## Exit codes

- 0: score >= 70 (pass)
- 1: score < 70 (fail)
- 2: error (bad path)

## Recognition

Indexed on the [XERJ Corpus Hub](https://hub.xerj.org/contributors/rahmankhanjohn) - the open reference memory AI coding agents search before they write code.

## Requirements

Python 3.9+, no dependencies.

## License

MIT

## Who is this for?

No telemetry in this tool. If you use it, plan to, or rejected it, tell us your environment in [the discussion thread](https://github.com/rahmankhanjohn/gitops-check/discussions/1). Operator replies steer the roadmap.
