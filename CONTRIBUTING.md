# Contributing results

Reproduce the work. Show the conditions. Keep the failures.

## Required metadata

- Hardware and memory
- Operating system
- Model repository and exact serving artifact
- Quantization
- Runtime and version
- Context limit
- Concurrency
- Sampling settings
- Runner commit SHA
- Raw sanitized JSON result

## Submission

1. Fork the repository.
2. Run the public battery.
3. Sanitize the result.
4. Add it under `results/community/<github-user>/`.
5. Run the tests and sensitive-data scan.
6. Open a pull request using the result template.

Do not submit credentials, private network addresses, internal hostnames, personal paths, customer data, or proprietary prompts.
