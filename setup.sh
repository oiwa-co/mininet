#!/bin/bash
set -e

echo "Instalando Python uv..."
curl -LsSf https://astral.sh/uv/install.sh | sh

# Anade ~/.local/bin al PATH solo si no esta ya
PROFILE_LINE='if [ -d "$HOME/.local/bin" ] && [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then PATH="$HOME/.local/bin:$PATH"; fi'
echo "$PROFILE_LINE" >> ~/.profile
source ~/.profile

echo "Clonando repositorio..."
git clone https://github.com/oiwa-co/mininet.git redes
cd redes

echo "Creando entorno virtual .modules..."
uv venv .modules
source .modules/bin/activate

echo "Instalando dependencias..."
uv pip install mininet os-ken

echo "Entorno activado y dependencias instaladas."
