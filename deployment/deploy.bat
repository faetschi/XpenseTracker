@echo off
pushd "%~dp0.."
echo Building and Pushing to GitHub Packages (GHCR) for Raspberry Pi...
docker buildx build --platform linux/arm64 -t ghcr.io/faetschi/xpensetracker:latest --push .
echo Done! Watchtower will update the Pi within 5 minutes.
popd
pause