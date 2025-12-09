#!/usr/bin/env bash
# SSH Tunnel Script for AWS Database Access
#
# Ports:
#   15432 -> PostgreSQL (5432)
#   17687 -> Neo4j Bolt (7687)
#   17474 -> Neo4j HTTP (7474)

KEY="${SSH_KEY_PATH:-$HOME/.ssh/server.pem}"
USER_HOST="ubuntu@ec2-3-115-78-26.ap-northeast-1.compute.amazonaws.com"

# Check if key exists
if [ ! -f "$KEY" ]; then
    echo "ERROR: SSH key not found at: $KEY"
    echo "Set SSH_KEY_PATH environment variable or copy key to ~/.ssh/server.pem"
    exit 1
fi

# Set correct permissions
chmod 600 "$KEY"

echo "Starting SSH tunnels..."
echo "  PostgreSQL: localhost:15432"
echo "  Neo4j Bolt: localhost:17687"
echo "  Neo4j HTTP: localhost:17474"
echo ""
echo "Press Ctrl+C to stop"
echo ""

while true; do
    echo "$(date '+%Y-%m-%d %H:%M:%S') Connecting..."

    ssh -i "$KEY" \
        -L 15432:localhost:5432 \
        -L 17687:localhost:7687 \
        -L 17474:localhost:7474 \
        -o ServerAliveInterval=60 \
        -o ServerAliveCountMax=3 \
        -o ExitOnForwardFailure=yes \
        -o TCPKeepAlive=yes \
        -o StrictHostKeyChecking=no \
        -N \
        "$USER_HOST"

    EXIT_CODE=$?
    echo "$(date '+%Y-%m-%d %H:%M:%S') SSH exited (code ${EXIT_CODE}). Reconnecting in 5s..."
    sleep 5
done
