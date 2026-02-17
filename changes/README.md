# Changelog Fragments

This directory contains changelog fragments for [Towncrier](https://towncrier.readthedocs.io/).

## Usage

For each change (feature, bugfix, etc.), create a file in this directory:

```bash
# Format: <issue_or_pr_number>.<type>.md
# Examples:
echo "Added new feature for XYZ." > changes/123.feature.md
echo "Fixed bug in ABC." > changes/124.bugfix.md
echo "Improved documentation for DEF." > changes/125.doc.md
```

## Available Types

- `feature` - New features
- `bugfix` - Bug fixes
- `doc` - Documentation changes
- `removal` - Removed or deprecated features
- `misc` - Miscellaneous (will not appear in changelog)

## Generating Changelog

To update the changelog:

```bash
# Preview (without changes)
uv run towncrier build --draft

# Create changelog and delete fragments
uv run towncrier build --version X.Y.Z

# Create changelog without deleting fragments (for testing)
uv run towncrier build --version X.Y.Z --keep
```

## Example Fragment

Filename: `42.feature.md`
```
Added support for nullable annotations in Android SDK.
```

The fragment will then appear in the changelog as follows:
```
### Features

- Added support for nullable annotations in Android SDK. (#42)
```
