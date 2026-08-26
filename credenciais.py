#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
credenciais.py — transforma o pouco que o Max cola em tudo que o robo precisa.

Ele so precisa me dar tres coisas:
  · App ID e App Secret do app do Facebook
  · um token curto gerado no Graph API Explorer (com os escopos da lista abaixo)
  · um token do LinkedIn gerado no Token Generator

Este script faz o resto: troca por token longo, descobre a pagina, o Instagram
e o URN do LinkedIn, confere se o token de pagina realmente nao expira, e
imprime o bloco pronto de secrets para colar no GitHub.

Uso:
    python3 credenciais.py --app-id 123 --app-secret abc --token-curto EAAG... \
                           --linkedin-token AQV...
"""

import argparse
import json
import sys

import requests

GRAPH = "https://graph.facebook.com/v23.0"

ESCOPOS = ["pages_show_list", "pages_read_engagement", "pages_manage_posts",
           "instagram_basic", "instagram_content_publish"]


def passo(txt):
    print(f"\n>> {txt}")


def meta(app_id, app_secret, token_curto):
    passo("trocando o token curto por um token longo (60 dias)")
    r = requests.get(f"{GRAPH}/oauth/access_token", params={
        "grant_type": "fb_exchange_token", "client_id": app_id,
        "client_secret": app_secret, "fb_exchange_token": token_curto}, timeout=30)
    if r.status_code != 200:
        sys.exit(f"falhou: {r.text[:400]}")
    user_token = r.json()["access_token"]
    print("   ok")

    passo("procurando as paginas que voce administra")
    r = requests.get(f"{GRAPH}/me/accounts", params={
        "fields": "id,name,access_token,tasks", "access_token": user_token}, timeout=30)
    r.raise_for_status()
    paginas = r.json().get("data", [])
    if not paginas:
        sys.exit("nenhuma pagina encontrada — confira se o app tem as permissoes de pagina")
    for i, p in enumerate(paginas):
        marca = "CREATE_CONTENT" in (p.get("tasks") or [])
        print(f"   [{i}] {p['name']}  (id {p['id']})  pode publicar: {'sim' if marca else 'NAO'}")
    escolha = 0 if len(paginas) == 1 else int(input("   qual pagina e a da HTECH? numero: "))
    pagina = paginas[escolha]
    page_token = pagina["access_token"]

    passo("conferindo se o token de pagina expira")
    r = requests.get(f"{GRAPH}/debug_token", params={
        "input_token": page_token, "access_token": f"{app_id}|{app_secret}"}, timeout=30)
    d = r.json().get("data", {})
    expira = d.get("expires_at", None)
    if expira == 0:
        print("   PERFEITO: expires_at = 0, este token nao expira")
    else:
        print(f"   ATENCAO: expires_at = {expira} — o token vai expirar. "
              "Refaca o passo do token curto conferindo os escopos.")

    passo("descobrindo a conta do Instagram ligada a pagina")
    r = requests.get(f"{GRAPH}/{pagina['id']}", params={
        "fields": "instagram_business_account{id,username}", "access_token": page_token}, timeout=30)
    ig = (r.json().get("instagram_business_account") or {})
    if not ig:
        print("   nao achei o Instagram vinculado. Confira em Meta Business Suite se "
              "@htechmotionsolutions esta ligado a esta pagina e e conta Business.")
    else:
        print(f"   ok: @{ig.get('username')} (id {ig.get('id')})")

    return {"META_TOKEN": page_token, "FB_PAGE_ID": pagina["id"], "IG_USER_ID": ig.get("id", "")}


def linkedin(token):
    passo("descobrindo o seu URN no LinkedIn")
    r = requests.get("https://api.linkedin.com/v2/userinfo",
                     headers={"Authorization": f"Bearer {token}"}, timeout=30)
    if r.status_code != 200:
        sys.exit(f"falhou: {r.status_code} {r.text[:300]}")
    sub = r.json().get("sub")
    print(f"   ok: {r.json().get('name')} — urn:li:person:{sub}")
    return {"LI_TOKEN": token, "LI_PERSON_URN": f"urn:li:person:{sub}"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--app-id")
    ap.add_argument("--app-secret")
    ap.add_argument("--token-curto")
    ap.add_argument("--linkedin-token")
    ap.add_argument("--org-urn", help="urn:li:organization:xxx, so quando a aprovacao sair")
    a = ap.parse_args()

    print("Escopos que o token curto do Facebook precisa ter:")
    for e in ESCOPOS:
        print(f"   · {e}")

    segredos = {}
    if a.app_id and a.app_secret and a.token_curto:
        segredos.update(meta(a.app_id, a.app_secret, a.token_curto))
    if a.linkedin_token:
        segredos.update(linkedin(a.linkedin_token))
    if a.org_urn:
        segredos["LI_ORG_URN"] = a.org_urn

    print("\n" + "=" * 64)
    print("COLE ESTES SECRETS NO GITHUB")
    print("Settings > Secrets and variables > Actions > New repository secret")
    print("=" * 64)
    for k, v in segredos.items():
        print(f"\n{k}\n{v}")
    print("\n" + "=" * 64)


if __name__ == "__main__":
    main()
