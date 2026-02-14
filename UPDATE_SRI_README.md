# SRI Hash Update Automation

This repository includes automated Subresource Integrity (SRI) hash management for static assets.

## What It Does

- Automatically calculates SHA-384 hashes for `main.js` and `style.css`
- Updates all HTML files with the new integrity attributes when CSS/JS files change
- Runs automatically via GitHub Actions when changes are pushed to the main branch

## Components

### `update_sri.py`

Python script that:
- Calculates SHA-384 SRI hashes for static assets
- Updates all HTML files with new integrity attributes
- Uses regex pattern matching to find and replace hash values

### `calculate-sri.sh`

Bash script for manually calculating SRI hashes:
```bash
./calculate-sri.sh main.js style.css
```

### `.github/workflows/update-sri.yml`

GitHub Actions workflow that:
- Triggers on pushes to main branch when `main.js` or `style.css` change
- Runs `update_sri.py` to update HTML files
- Commits and pushes updated HTML files automatically

## Manual Usage

To manually update SRI hashes:

```bash
python3 update_sri.py
```

This will:
1. Calculate new hashes for `main.js` and `style.css`
2. Update all `*.html` files in the repository root
3. Display which files were modified

## How It Works

1. When you modify `main.js` or `style.css` and push to main:
2. GitHub Actions workflow is triggered
3. Script calculates new SHA-384 hashes
4. All HTML files are updated with new integrity attributes
5. Changes are committed and pushed automatically with `[skip ci]` flag

## Requirements

- Python 3.x (standard library only - uses hashlib, base64, re, pathlib)
- Git (for the GitHub Actions workflow)

## Security Benefits

SRI (Subresource Integrity) provides:
- Protection against compromised CDNs or file modifications
- Ensures browsers only execute expected file content
- Prevents tampering with CSS/JS files
- Adds an extra layer of security for static assets

## Testing

To test the automation locally:

```bash
# Make a change to main.js or style.css
echo "/* test */" >> main.js

# Run the update script
python3 update_sri.py

# Check the updated HTML files
git diff *.html

# Revert your test changes
git checkout main.js *.html
```

## Notes

- The workflow uses `[skip ci]` in commit messages to prevent infinite loops
- Only HTML files in the repository root are updated
- The script safely handles missing files and provides clear output
- SHA-384 is used (recommended over SHA-256 for stronger security)
