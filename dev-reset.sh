#!/usr/bin/env bash
set -e

echo "=== Desktop-2FA DEV RESET ==="

# 1. Remove old entry-points
echo "[1/6] Removing old entry-points..."
rm -f ~/.local/bin/d2fa
rm -f ~/.local/bin/desktop-2fa

# 2. Remove old site-packages metadata
echo "[2/6] Removing old site-packages..."
rm -rf ~/.local/lib/python*/site-packages/desktop_2fa*
rm -rf ~/.local/lib/python*/site-packages/desktop-2fa*

# 3. Remove vault config (optional but recommended for clean tests)
echo "[3/6] Removing old vault..."
rm -rf ~/.config/desktop-2fa

# 4. Clear Bash command hash cache
echo "[4/6] Clearing Bash hash..."
hash -r || true

# 5. Reinstall project
echo "[5/6] Installing project..."
pip install . --break-system-packages

# 6. Show results
echo "[6/6] Installation complete."
echo
echo "Installed entry-points:"
which d2fa || echo "d2fa not found"
which desktop-2fa || echo "desktop-2fa not found"
echo
echo "Version check:"
desktop-2fa --version || true
d2fa --version || true

echo
echo "=== DONE ==="
