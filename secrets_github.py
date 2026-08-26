#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
secrets_github.py — grava os secrets no repositorio pela API, criptografados.

Evita que o Max tenha que colar seis valores um por um na interface do GitHub.
Cada valor e criptografado com a chave publica do repositorio antes de sair
daqui — e o mesmo que a interface do GitHub faz.

Uso:
    python3 secrets_github.py --de segredos.json
    python3 secrets_github.py --listar
"""

import argparse
import json
import sys
from base64 import b64encode
from pathlib import Path

import requests

try:
    from nacl import encoding, public
except ImportError:
    sys.exit("Falta pynacl: pip install pynacl")

RAIZ = Path(__file__).resolve().parent
API = "https://api.github.com"


def repo_token():
    cfg = RAIZ / "repo.json"
    if not cfg.exists():
        sys.exit("falta repo.json")
    c = json.loads(cfg.read_text(encoding="utf-8"))
    return c["repo"], c["token"]


def cabecalho(token):
    return {"Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"}


def criptografar(chave_publica_b64: str, valor: str) -> str:
    chave = public.PublicKey(chave_publica_b64.encode(), encoding.Base64Encoder())
    return b64encode(public.SealedBox(chave).encrypt(valor.encode())).decode()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--de", help="arquivo JSON com os pares NOME: valor")
    ap.add_argument("--listar", action="store_true")
    a = ap.parse_args()

    repo, token = repo_token()
    h = cabecalho(token)

    if a.listar:
        r = requests.get(f"{API}/repos/{repo}/actions/secrets", headers=h, timeout=30)
        if r.status_code != 200:
            sys.exit(f"nao consegui listar (o token tem permissao Secrets?): {r.status_code} {r.text[:200]}")
        nomes = [s["name"] for s in r.json().get("secrets", [])]
        print(f"secrets em {repo}: {', '.join(nomes) if nomes else '(nenhum)'}")
        return

    if not a.de:
        sys.exit("informe --de segredos.json ou --listar")

    valores = json.loads(Path(a.de).read_text(encoding="utf-8"))
    valores = {k: v for k, v in valores.items() if v and not k.startswith("_")}

    r = requests.get(f"{API}/repos/{repo}/actions/secrets/public-key", headers=h, timeout=30)
    if r.status_code != 200:
        sys.exit(f"nao consegui a chave publica do repositorio: {r.status_code} {r.text[:300]}")
    chave = r.json()

    for nome, valor in valores.items():
        payload = {"encrypted_value": criptografar(chave["key"], str(valor)),
                   "key_id": chave["key_id"]}
        rr = requests.put(f"{API}/repos/{repo}/actions/secrets/{nome}",
                          headers=h, json=payload, timeout=30)
        if rr.status_code in (201, 204):
            print(f"  OK   {nome}")
        else:
            print(f"  ERRO {nome}: {rr.status_code} {rr.text[:200]}")

    print("\npronto — os valores ficam criptografados no GitHub e nunca aparecem no repositorio")


if __name__ == "__main__":
    main()
