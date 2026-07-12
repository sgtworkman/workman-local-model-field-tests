# Contributing

Reproduce the work. Show the conditions. Keep the failures.

## Result admission status

Community results are accepted only as `workman-field-tests.v2` public-battery artifacts that pass the provenance, comparability, and privacy validator. Historical or hand-authored result records are not admitted to rankings.

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

## Result submission flow

1. Fork the repository.
2. Run the public battery.
   Use `--admission-ready` and provide the required model/runtime/hardware metadata.
3. Sanitize the result.
4. Add it under `results/community/<github-user>/`.
5. Run the tests and sensitive-data scan.
6. Run `workman-field-admit <result> --verify-commit`.
7. Open a pull request using the result template.

Do not submit credentials, private network addresses, internal hostnames, personal paths, customer data, or proprietary prompts.
