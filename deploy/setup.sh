#!/bin/bash
set -e

echo "=== Smart Podcast Finder - EC2 Setup ==="

# Update system
sudo yum update -y
sudo yum install -y git python3.11 python3.11-pip

# Install Temporal CLI
curl -sSf https://temporal.download/cli.sh | sh
export PATH="$HOME/.temporalio/bin:$PATH"
echo 'export PATH="$HOME/.temporalio/bin:$PATH"' >> ~/.bashrc

# Clone the repo
cd /home/ec2-user
git clone https://github.com/DeepikaSidda/Smart-Podcast-Finder.git
cd Smart-Podcast-Finder

# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .

# Create .env from example (user needs to fill in keys)
cp .env.example .env

echo ""
echo "=== Setup complete! ==="
echo "Next steps:"
echo "1. Edit /home/ec2-user/Smart-Podcast-Finder/.env with your API keys"
echo "2. Run: cd /home/ec2-user/Smart-Podcast-Finder && bash deploy/start.sh"
