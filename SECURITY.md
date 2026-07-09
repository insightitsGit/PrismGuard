# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| 0.1.x (latest on [PyPI](https://pypi.org/project/prismguard/)) | Yes |
| Older than latest patch on PyPI | Best effort — please upgrade |

## Reporting a vulnerability

Please **do not** open a public GitHub issue for security vulnerabilities.

Report privately to:

- **Email:** info@insightits.com  
- Subject line: `[PrismGuard Security]`

Include:

1. Description of the issue and impact
2. Steps to reproduce (PoC if available)
3. Affected version / commit
4. Whether the issue is already public elsewhere

We aim to acknowledge reports within **5 business days** and to provide a remediation plan or status update within **14 business days**.

## Scope

In scope examples:

- Remote code execution or arbitrary file write via the library / CLI / HTTP service
- Authentication / authorization bypass of license or HTTP controls
- Prompt-injection **bypass of PrismGuard itself** that is reproducible and high impact (with clear repro)
- Secrets accidentally shipped in the repository or package

Out of scope / lower priority examples:

- Theoretical attacks without a practical repro
- Issues that require already-compromised host credentials
- Social engineering of maintainers
- Vulnerabilities only in third-party dependencies with no PrismGuard-specific exploit path (please report upstream; we will upgrade when fixed)

## Safe harbor

We will not pursue legal action against researchers who:

- Make a good-faith effort to avoid privacy violations and service disruption
- Do not access data that is not their own
- Report findings promptly and privately
- Do not exploit the issue beyond what is needed to demonstrate it

## Hardening notes for operators

- Keep `PRISMGUARD_DEV_UNRESTRICTED` unset in production
- Use a production license public key before issuing paid licenses (see `docs/enterprise-product-model.md`)
- Prefer network isolation for `prismguard-serve` and authenticate at your edge
- Treat model artifacts and seed corpora as trusted inputs; verify downloads (`prismguard-model download`)
