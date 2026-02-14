#!/bin/bash
# Calculate SRI (Subresource Integrity) hash for files
# Usage: ./calculate-sri.sh <file1> [file2] [file3] ...
# Example: ./calculate-sri.sh main.js style.css

if [ $# -eq 0 ]; then
    echo "Usage: $0 <file1> [file2] [file3] ..."
    echo "Example: $0 main.js style.css"
    echo ""
    echo "Calculates SHA-384 SRI hashes for the given files."
    exit 1
fi

for file in "$@"; do
    if [ ! -f "$file" ]; then
        echo "Error: File not found: $file" >&2
        continue
    fi
    
    # Calculate SHA-384 hash and encode as base64
    hash=$(openssl dgst -sha384 -binary "$file" | openssl enc -base64 | tr -d '\n')
    
    # Output with filename and SRI format
    echo "$file:"
    echo "  sha384-$hash"
    echo ""
done
