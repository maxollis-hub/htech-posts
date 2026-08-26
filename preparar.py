#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
preparar.py — prepara a fila antes de subir para o GitHub.

Eu (Claude) rodo isto no computador do Max, uma vez por ciclo. Ele nao roda nada.

O que faz:
  1. le os posts em fila/agendados/ que ainda tem `midia_origem`
  2. converte os slides PNG para JPEG (o Instagram so aceita JPEG)
  3. grava em midia/ com nome previsivel e troca `midia_origem` por `midia`
  4. valida tudo que costuma quebrar em producao
  5. opcionalmente faz commit e push (--push)

Uso:
    python3 preparar.py            # prepara e valida
    python3 preparar.py --push     # prepara, valida e envia para o GitHub
    python3 preparar.py --conferir # so mostra a fila, sem tocar em nada
"""

import datetime as dt
import json
import shutil
import subprocess
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    sys.exit("Falta Pillow: pip install Pillow")

RAIZ = Path(__file__).resolve().parent
PROJETO = RAIZ.parent
AGENDADOS = RAIZ / "fila" / "agendados"
MIDIA = RAIZ / "midia"
TZ = dt.timezone(dt.timedelta(hours=-3))

LIMITES = {"instagram": 2200, "facebook": 16192, "linkedin": 3000}
DESTINOS_VALIDOS = {"instagram", "facebook", "linkedin_perfil", "linkedin_pagina"}

erros, avisos = [], []


def erro(msg):
    erros.append(msg)
    print(f"  ERRO   {msg}")


def aviso(msg):
    avisos.append(msg)
    print(f"  aviso  {msg}")


def converter(origem: Path, destino: Path):
    """PNG -> JPEG de alta qualidade, fundo branco onde houver transparencia."""
    img = Image.open(origem)
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        fundo = Image.new("RGB", img.size, (255, 255, 255))
        fundo.paste(img, mask=img.split()[-1])
        img = fundo
    else:
        img = img.convert("RGB")
    img.save(destino, "JPEG", quality=92, optimize=True, subsampling=0)
    return img.size


def preparar_post(caminho: Path):
    post = json.loads(caminho.read_text(encoding="utf-8"))
    pid = post.get("id", caminho.stem)
    print(f"\n[{pid}] {post.get('titulo','')}")

    # ---- data
    try:
        quando = dt.datetime.fromisoformat(post["quando"]).replace(tzinfo=TZ)
    except Exception:
        erro(f"{pid}: campo 'quando' invalido (use 2026-09-01T08:30:00)")
        return
    minutos = (quando - dt.datetime.now(TZ)).total_seconds() / 60
    if minutos < 15 and not post.get("imediato"):
        erro(f"{pid}: agendado para daqui a {minutos:.0f} min — deixe pelo menos 15 min de folga "
             f'(para publicar na hora, ponha "imediato": true no JSON)')
    elif post.get("imediato"):
        print("  data   PUBLICACAO IMEDIATA — sai assim que o robo rodar")
    else:
        print(f"  data   {quando:%d/%m/%Y %H:%M} (em {minutos/60:.1f} h)")

    # ---- destinos
    for d in post.get("destinos", []):
        if d not in DESTINOS_VALIDOS:
            erro(f"{pid}: destino desconhecido '{d}'")
    if not post.get("destinos"):
        erro(f"{pid}: sem destinos")
    if "linkedin_pagina" in post.get("destinos", []):
        aviso(f"{pid}: destino linkedin_pagina exige a aprovacao da Community Management API — "
              "se ainda nao saiu, este destino vai falhar e o post fica na fila")

    # ---- legendas
    for d in post.get("destinos", []):
        chave = "linkedin" if d.startswith("linkedin") else d
        texto = post.get("legendas", {}).get(chave)
        if not texto:
            if chave == "facebook" and post.get("legendas", {}).get("instagram"):
                continue  # o Facebook herda a legenda do Instagram
            erro(f"{pid}: falta a legenda '{chave}'")
            continue
        lim = LIMITES.get(chave)
        if lim and len(texto) > lim:
            erro(f"{pid}: legenda de {chave} com {len(texto)} caracteres (limite {lim})")
        else:
            print(f"  texto  {chave}: {len(texto)} caracteres")

    # ---- midia
    if post.get("midia") and not post.get("midia_origem"):
        print("  midia  ja preparada")
        faltando = [m for m in post["midia"] if not (MIDIA / m).exists()]
        if faltando:
            erro(f"{pid}: arquivos ausentes em midia/: {faltando}")
        return

    origens = post.get("midia_origem") or []
    if not origens:
        erro(f"{pid}: sem 'midia_origem' nem 'midia'")
        return
    if len(origens) > 10:
        erro(f"{pid}: {len(origens)} slides — o Instagram aceita no maximo 10")
        return

    MIDIA.mkdir(exist_ok=True)
    finais, tamanhos = [], set()
    for i, rel in enumerate(origens, start=1):
        origem = (PROJETO / rel).resolve()
        if not origem.exists():
            erro(f"{pid}: slide nao encontrado: {rel}")
            continue
        nome = f"{pid.lower()}-{i:02d}.jpg"
        tamanhos.add(converter(origem, MIDIA / nome))
        finais.append(nome)

    if len(finais) == len(origens):
        if len(tamanhos) > 1:
            aviso(f"{pid}: slides com tamanhos diferentes {tamanhos} — "
                  "o Instagram corta todos pela proporcao do primeiro")
        post["midia"] = finais
        post.pop("midia_origem", None)
        caminho.write_text(json.dumps(post, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  midia  {len(finais)} slide(s) convertido(s) para JPEG {tamanhos.pop()}")


CLONE = Path.home() / "htech-posts"
CONFIG_REPO = RAIZ / "repo.json"
COPIAR = ["publicar.py", "preparar.py", "credenciais.py", "secrets_github.py",
           "requirements.txt", ".github", "fila", "midia"]


def _repo():
    if not CONFIG_REPO.exists():
        sys.exit("falta repo.json — crie com {\"repo\": \"usuario/htech-posts\", \"token\": \"...\"}")
    c = json.loads(CONFIG_REPO.read_text(encoding="utf-8"))
    return c["repo"], c["token"]


def _git(*args, cwd=None):
    r = subprocess.run(["git", *args], cwd=str(cwd or CLONE), capture_output=True, text=True)
    if r.returncode and "nothing to commit" not in (r.stdout + r.stderr):
        sys.exit(f"git {' '.join(args)} falhou:\n{r.stdout}{r.stderr}")
    return r


def enviar():
    """Sincroniza com um clone fora da pasta montada.

    O git nao consegue apagar arquivos temporarios dentro de $HOME/mnt (a pasta
    do Max e montada sem permissao de delete), o que deixa locks presos. Por isso
    o clone de trabalho mora no $HOME da VM: descartavel, o canonico e o GitHub.
    """
    repo, token = _repo()
    url = f"https://x-access-token:{token}@github.com/{repo}.git"

    if not (CLONE / ".git").exists():
        print(f"clonando {repo} em {CLONE} ...")
        r = subprocess.run(["git", "clone", url, str(CLONE)], capture_output=True, text=True)
        if r.returncode:
            sys.exit(f"clone falhou (repositorio existe? token tem Contents: write?):\n{r.stderr}")
    else:
        _git("remote", "set-url", "origin", url)
        _git("fetch", "origin")

    # repositorio recem-criado ainda nao tem commit nenhum
    tem_remoto = subprocess.run(["git", "rev-parse", "--verify", "origin/main"],
                                cwd=str(CLONE), capture_output=True).returncode == 0
    if tem_remoto:
        _git("reset", "--hard", "origin/main")
    else:
        subprocess.run(["git", "checkout", "-B", "main"], cwd=str(CLONE),
                       capture_output=True, text=True)
        print("repositorio vazio — este sera o primeiro commit")

    for item in COPIAR:
        origem = RAIZ / item
        if not origem.exists():
            continue
        destino = CLONE / item
        if origem.is_dir():
            shutil.copytree(origem, destino, dirs_exist_ok=True)
        else:
            shutil.copy2(origem, destino)
    for extra in ("README.md", "SETUP-UMA-VEZ.md"):
        if (RAIZ / extra).exists():
            shutil.copy2(RAIZ / extra, CLONE / extra)

    _git("add", "-A")
    _git("commit", "-m", f"fila atualizada em {dt.datetime.now(TZ):%d/%m/%Y %H:%M}")
    _git("push", "origin", "main")
    print(f"enviado para github.com/{repo} — o robo assume a partir daqui")


def main():
    if not AGENDADOS.exists():
        sys.exit("pasta fila/agendados nao existe")

    pendentes = sorted(AGENDADOS.glob("*.json"))
    if not pendentes:
        print("fila vazia — nada a preparar")
        if "--push" in sys.argv:
            print("enviando mesmo assim (estrutura e scripts)")
            enviar()
        return

    if "--conferir" in sys.argv:
        for f in pendentes:
            p = json.loads(f.read_text(encoding="utf-8"))
            print(f"{p['quando']}  {p['id']:6s}  {', '.join(p.get('destinos', []))}  "
                  f"{len(p.get('midia') or p.get('midia_origem') or [])} slide(s)")
        return

    for f in pendentes:
        preparar_post(f)

    print("\n" + "=" * 60)
    if erros:
        print(f"{len(erros)} erro(s) — nada foi enviado:")
        for e in erros:
            print(f"  · {e}")
        sys.exit(1)
    if avisos:
        print(f"{len(avisos)} aviso(s):")
        for a in avisos:
            print(f"  · {a}")
    print(f"fila validada: {len(pendentes)} post(s) prontos")

    if "--push" in sys.argv:
        enviar()


if __name__ == "__main__":
    main()
