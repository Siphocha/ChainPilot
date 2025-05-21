#!/bin/bash
# Install build tools and dependencies
apt-get update && apt-get install -y build-essential python3-dev libffi-dev libssl-dev
pip install --upgrade pip
pip install -r requirements.txt