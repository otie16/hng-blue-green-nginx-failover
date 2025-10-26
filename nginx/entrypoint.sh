#!/usr/bin/env sh
set -e

TEMPLATE="/etc/nginx/nginx.template.conf"
OUT="/etc/nginx/nginx.conf"

# Export any variable(s) you’ll use in the template
export PORT

# Run envsubst properly (input via stdin)
envsubst '${PORT}' < $TEMPLATE > $OUT

echo "==== Generated nginx.conf ===="
cat $OUT
echo "=============================="

# Start nginx
nginx -g "daemon off;"
