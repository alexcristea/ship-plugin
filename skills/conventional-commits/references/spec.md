# Conventional Commits 1.0.0 — condensed reference

Source: https://www.conventionalcommits.org/en/v1.0.0/

## Structure

```
<type>[optional scope][!]: <description>

[optional body]

[optional footer(s)]
```

## The rules (paraphrased from the spec, numbered as in the spec)

1. Commits MUST be prefixed with a type (a noun such as `feat`, `fix`), followed by an OPTIONAL scope, OPTIONAL `!`, and a REQUIRED terminal colon and space.
2. `feat` MUST be used when a commit adds a new feature.
3. `fix` MUST be used when a commit represents a bug fix.
4. A scope MAY follow the type. It MUST be a noun describing a section of the codebase, in parentheses: `fix(parser):`.
5. A description MUST immediately follow the colon and space. It is a short summary of the change.
6. A longer body MAY follow, beginning one blank line after the description.
7. The body is free-form and MAY have any number of newline-separated paragraphs.
8. One or more footers MAY follow one blank line after the body. Each footer is a word token, then `: ` or ` #`, then a value (inspired by git trailers).
9. A footer token MUST use `-` instead of spaces (e.g. `Acked-by`), except `BREAKING CHANGE`, which may contain a space.
10. A footer value MAY contain spaces and newlines; parsing ends at the next valid token/separator pair.
11. Breaking changes MUST be indicated in the type/scope prefix with `!`, or as a footer.
12. As a footer, it MUST be uppercase `BREAKING CHANGE`, followed by a colon, space, and description: `BREAKING CHANGE: environment variables now take precedence over config files`.
13. If `!` is used in the prefix, the `BREAKING CHANGE:` footer MAY be omitted, and the description SHALL describe the breaking change.
14. Types other than `feat` and `fix` MAY be used (e.g. `docs:`).
15. The units of information MUST NOT be treated as case sensitive by implementors, except `BREAKING CHANGE`, which MUST be uppercase.
16. `BREAKING-CHANGE` is synonymous with `BREAKING CHANGE` as a footer token.

## SemVer mapping

- `fix` → PATCH
- `feat` → MINOR
- any commit with a breaking change (`!` or `BREAKING CHANGE` footer), of any type → MAJOR

## Reverts

The spec doesn't mandate a format. The common convention:

```
revert: let us never again speak of the noodle incident

Refs: 676104e, a215868
```

## Examples from the spec

```
feat: allow provided config object to extend other configs

BREAKING CHANGE: `extends` key in config file is now used for extending other config files
```

```
feat!: send an email to the customer when a product is shipped
```

```
feat(api)!: send an email to the customer when a product is shipped
```

```
chore!: drop support for Node 6

BREAKING CHANGE: use JavaScript features not available in Node 6.
```

```
docs: correct spelling of CHANGELOG
```

```
feat(lang): add Polish language
```

```
fix: prevent racing of requests

Introduce a request id and a reference to latest request. Dismiss
incoming responses other than from latest request.

Remove timeouts which were used to mitigate the racing issue but are
obsolete now.

Reviewed-by: Z
Refs: #123
```
