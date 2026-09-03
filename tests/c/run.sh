#!/usr/bin/env bash
#
# Compile and run the generated firmware header, as C and as C++.
#
# Warnings are errors on purpose: the Pico build treats them that way, and a
# header that only compiles cleanly at a laxer setting fails there instead.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
HEADER_DIR="$ROOT/gen/c"
OUT="$(mktemp -d)"
trap 'rm -rf "$OUT"' EXIT

echo "==> gcc (C11)"
gcc -std=c11 -Wall -Wextra -Werror -pedantic \
    -I "$HEADER_DIR" -o "$OUT/schema_keys_c" "$ROOT/tests/c/main.c"
"$OUT/schema_keys_c"

if command -v g++ >/dev/null 2>&1; then
    echo "==> g++ (C++17)"
    g++ -std=c++17 -Wall -Wextra -Werror -pedantic \
        -I "$HEADER_DIR" -o "$OUT/schema_keys_cpp" "$ROOT/tests/c/main.cpp"
    "$OUT/schema_keys_cpp"
else
    # Not silently skipped: the firmware is C++, so a runner without g++ is
    # running a weaker check than the one this suite claims to run.
    echo "::warning::g++ not found — the header's C++ face was NOT compiled." >&2
fi
