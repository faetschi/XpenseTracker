@echo off
pushd "%~dp0.."
echo Building and Pushing to GitHub Packages (GHCR) for Raspberry Pi...
:: Added --cache-from and --cache-to to store build layers on GHCR
docker buildx build --platform linux/arm64 ^
  --cache-from type=registry,ref=ghcr.io/faetschi/xpensetracker:buildcache ^
  --cache-to type=registry,ref=ghcr.io/faetschi/xpensetracker:buildcache,mode=max ^
  -t ghcr.io/faetschi/xpensetracker:latest --push .
echo Done! Watchtower will update the Pi within 5 minutes.
popd
pause