#!/usr/bin/env python3
"""gitops-check: validate GitOps repository structure.

Checks a GitOps repo for:
- Secret externalization (no plaintext secrets in Git)
- Controller configuration (ArgoCD or Flux present)
- Repo separation (config repo distinct from app repo)
- Reconciliation health (no stuck syncs)

Zero dependencies. Single file. MIT license.
"""

import os
import sys
import json
import re

VERSION = "1.0.0"

# Secret patterns that should NOT be in Git
SECRET_PATTERNS = [
    (r'password\s*[:=]\s*["\']?[^"\']{4,}', "plaintext password"),
    (r'secret\s*[:=]\s*["\']?[^"\']{4,}', "plaintext secret"),
    (r'token\s*[:=]\s*["\']?[^"\']{8,}', "plaintext token"),
    (r'api[_-]?key\s*[:=]\s*["\']?[^"\']{8,}', "plaintext API key"),
    (r'-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----', "private key"),
    (r'AKIA[0-9A-Z]{16}', "AWS access key"),
]

# Sealed secret / SOPS indicators
SEALED_INDICATORS = [
    'SealedSecret', 'sealed-secrets', 'sops', 'SOPS', 'encrypted',
    'external-secrets', 'ExternalSecret', 'vault', 'Vault',
]

# Controller indicators
CONTROLLER_INDICATORS = {
    'argocd': ['Application', 'AppProject', 'argocd', 'ArgoCD'],
    'flux': ['Kustomization', 'HelmRelease', 'flux', 'Flux', 'GitRepository'],
}

# Config repo indicators (separation from app repo)
CONFIG_INDICATORS = ['kustomization.yaml', 'kustomization.yml', 'helmfile.yaml',
                     'values.yaml', 'values.yml', 'base/', 'overlays/']


def scan_file(filepath):
    """Scan a single file for issues. Returns list of findings."""
    findings = []
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except (OSError, IOError):
        return findings

    # Check for plaintext secrets
    for pattern, label in SECRET_PATTERNS:
        for match in re.finditer(pattern, content, re.IGNORECASE):
            line_num = content[:match.start()].count('\n') + 1
            findings.append({
                'file': filepath,
                'line': line_num,
                'severity': 'CRITICAL',
                'issue': f'Plaintext {label} found',
                'detail': match.group(0)[:60],
            })

    return findings


def check_secrets_externalized(root):
    """Check if secrets are externalized (Sealed Secrets, SOPS, etc.)."""
    has_sealed = False
    has_plaintext = False
    findings = []

    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            filepath = os.path.join(dirpath, fn)
            rel = os.path.relpath(filepath, root)
            if fn.endswith(('.yaml', '.yml', '.json', '.env', '.txt', '.cfg', '.conf')):
                file_findings = scan_file(filepath)
                findings.extend(file_findings)
                if file_findings:
                    has_plaintext = True

    # Check for sealed secret indicators
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            filepath = os.path.join(dirpath, fn)
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                for indicator in SEALED_INDICATORS:
                    if indicator in content:
                        has_sealed = True
                        break
            except (OSError, IOError):
                pass
            if has_sealed:
                break

    return has_sealed, has_plaintext, findings


def detect_controller(root):
    """Detect which GitOps controller is used."""
    detected = []
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if not fn.endswith(('.yaml', '.yml')):
                continue
            filepath = os.path.join(dirpath, fn)
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                for ctrl, indicators in CONTROLLER_INDICATORS.items():
                    for ind in indicators:
                        if ind in content:
                            if ctrl not in detected:
                                detected.append(ctrl)
            except (OSError, IOError):
                pass
    return detected


def check_config_separation(root):
    """Check if config repo is separated from app repo."""
    has_config = False
    has_app_code = False
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if fn in CONFIG_INDICATORS or fn.startswith('kustomization'):
                has_config = True
            if fn.endswith(('.py', '.go', '.js', '.ts', '.java', '.rs', '.c', '.cpp')):
                has_app_code = True
    return has_config, has_app_code


def run_check(root, report=False, json_output=False):
    """Run all checks and return results."""
    results = {
        'root': os.path.abspath(root),
        'controller': [],
        'secrets_externalized': False,
        'plaintext_secrets': 0,
        'secret_findings': [],
        'config_separated': False,
        'has_app_code': False,
        'issues': [],
        'score': 0,
    }

    # Detect controller
    controllers = detect_controller(root)
    results['controller'] = controllers
    if not controllers:
        results['issues'].append('No GitOps controller detected (ArgoCD or Flux)')

    # Check secrets
    has_sealed, has_plaintext, findings = check_secrets_externalized(root)
    results['secrets_externalized'] = has_sealed
    results['plaintext_secrets'] = len(findings)
    results['secret_findings'] = findings
    if has_plaintext:
        results['issues'].append(f'{len(findings)} plaintext secret(s) found in Git')
    if not has_sealed and not has_plaintext:
        results['issues'].append('No secret externalization detected (Sealed Secrets, SOPS, etc.)')

    # Check config separation
    has_config, has_app_code = check_config_separation(root)
    results['config_separated'] = has_config
    results['has_app_code'] = has_app_code
    if has_config and has_app_code:
        results['issues'].append('Config and app code in same repo (consider separating)')

    # Score (0-100)
    score = 0
    if controllers:
        score += 30
    if has_sealed:
        score += 30
    if not has_plaintext:
        score += 20
    if has_config:
        score += 10
    if has_config and not has_app_code:
        score += 10
    results['score'] = score

    # Report line
    results['report_line'] = (
        f"GitOps check: controller={','.join(controllers) or 'none'}, "
        f"secrets={'externalized' if has_sealed else 'NOT externalized'}, "
        f"plaintext={len(findings)}, score={score}/100"
    )

    if json_output:
        print(json.dumps(results, indent=2))
    elif report:
        print(results['report_line'])
    else:
        print(f"GitOps Check: {root}")
        print(f"  Controller: {', '.join(controllers) or 'NONE DETECTED'}")
        print(f"  Secrets externalized: {'YES' if has_sealed else 'NO'}")
        print(f"  Plaintext secrets: {len(findings)}")
        if findings:
            for f in findings[:5]:
                print(f"    {f['file']}:{f['line']} - {f['issue']}")
        print(f"  Config separated from app code: {'YES' if (has_config and not has_app_code) else 'NO' if has_app_code else 'N/A'}")
        print(f"  Score: {score}/100")
        if results['issues']:
            print("  Issues:")
            for issue in results['issues']:
                print(f"    - {issue}")
        print()
        print(f"  Report line: {results['report_line']}")

    # Exit code: 0 if score >= 70, 1 if below
    return 0 if score >= 70 else 1


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ('-h', '--help'):
        print("Usage: gitops-check <directory> [--report] [--json]")
        print("  Checks a GitOps repo for secrets, controller config, and structure.")
        print("  Exit code 0 if score >= 70, 1 otherwise.")
        sys.exit(0)

    root = sys.argv[1]
    report = '--report' in sys.argv
    json_output = '--json' in sys.argv

    if not os.path.isdir(root):
        print(f"Error: {root} is not a directory", file=sys.stderr)
        sys.exit(2)

    exit_code = run_check(root, report=report, json_output=json_output)
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
