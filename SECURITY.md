# Security Policy

## Supported Versions

| Version         | Supported                    |
| --------------- | ---------------------------- |
| `main` branch   | ✅ Active support            |
| Tagged releases | ✅ Security fixes backported |
| Older branches  | ❌ No support                |

## Reporting a Vulnerability

We take security seriously, even in a research platform. If you discover a vulnerability, please **do not open a public GitHub Issue**.

### How to Report

**Email**: bishal.ghimire@gmail.com
**Subject Line**: `[SECURITY] Brief description`

### What to Include

1. Description of the vulnerability
2. Steps to reproduce (proof of concept if possible)
3. Potential impact
4. Your name/handle (for credit in the fix, if you wish)

### Response Timeline

| Action                        | Timeline                                      |
| ----------------------------- | --------------------------------------------- |
| Acknowledgment of your report | Within 48 hours                               |
| Initial assessment            | Within 7 days                                 |
| Fix or mitigation             | Within 30 days (critical); 90 days (moderate) |
| Public disclosure             | After fix is released                         |

We will credit you in the release notes unless you prefer to remain anonymous.

## Scope

### In Scope

- Injection vulnerabilities in the Flask web app (`application/web/app.py`)
- Insecure deserialization of research data files
- Path traversal vulnerabilities in file I/O code
- API authentication/authorization issues (`application/api/api.py`)
- Dependency vulnerabilities (please also open a `dependabot` PR if applicable)

### Out of Scope

- Vulnerabilities in third-party dependencies not related to this project
- Issues that require physical access to a server
- Social engineering attacks
- Theoretical vulnerabilities with no practical exploit path

## Security Best Practices for Contributors

When contributing code, please:

- **Never commit secrets**: API keys, tokens, passwords must be environment variables
- **Validate all file paths**: Prevent directory traversal in any code that reads user-supplied paths
- **Sanitize inputs**: Especially in the Flask web app and API endpoint handlers
- **Use parameterized queries**: If database integration is added in the future
- **Pin dependency versions**: Use exact versions in `requirements*.txt` files to prevent supply-chain attacks
