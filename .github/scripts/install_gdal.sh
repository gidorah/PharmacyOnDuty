#!/usr/bin/env bash
# Install GDAL, which GeoDjango loads at startup, on a GitHub-hosted runner.
#
# The runner's Azure Ubuntu mirror sometimes trickles a download for over ten
# minutes. apt's own timeout only fires when no data arrives at all, so each
# attempt gets a time limit. A retry resumes the partly downloaded packages.
# After two stalled attempts the script switches to archive.ubuntu.com.
set -euo pipefail

apt_opts=(-q -o Acquire::Retries=3 -o Acquire::http::Timeout=20)

install() {
  sudo timeout 150 apt-get "${apt_opts[@]}" install -y --no-install-recommends gdal-bin
}

sudo apt-get "${apt_opts[@]}" update

for attempt in 1 2; do
  if install; then
    exit 0
  fi
  echo "::warning::apt-get install attempt $attempt stalled or failed; retrying."
done

echo "::warning::Switching from the runner's Ubuntu mirror to archive.ubuntu.com."
for file in /etc/apt/apt-mirrors.txt /etc/apt/sources.list.d/ubuntu.sources /etc/apt/sources.list; do
  if [ -f "$file" ]; then
    sudo sed -i 's|http://azure.archive.ubuntu.com/ubuntu|http://archive.ubuntu.com/ubuntu|g' "$file"
  fi
done
sudo apt-get "${apt_opts[@]}" update
install
