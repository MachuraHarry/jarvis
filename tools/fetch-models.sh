#!/bin/sh
# Lädt die Sprachmodelle nach models/ (nicht im Repo, zu groß).
set -eu
cd "$(dirname "$0")/.."
mkdir -p models/voices
if [ ! -d models/vosk-model-small-de-0.15 ]; then
  curl -fL -o /tmp/vosk-de.zip https://alphacephei.com/vosk/models/vosk-model-small-de-0.15.zip
  unzip -q /tmp/vosk-de.zip -d models && rm -f /tmp/vosk-de.zip
fi
B=https://huggingface.co/rhasspy/piper-voices/resolve/main/de/de_DE/karlsson/low
for f in de_DE-karlsson-low.onnx de_DE-karlsson-low.onnx.json; do
  [ -f "models/voices/$f" ] || curl -fL -o "models/voices/$f" "$B/$f"
done
echo "Modelle vorhanden:"; ls models models/voices
