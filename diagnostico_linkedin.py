#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Diagnostico do canal LinkedIn. NAO publica nada.

Descobre qual caminho de API o app tem direito de usar:
  - API versionada /rest/images (varias versoes do cabecalho LinkedIn-Version)
  - API antiga /v2/assets?action=registerUpload

Grava tudo em diagnostico-linkedin.txt, que o workflow commita no repositorio.
"""
import datetime as dt
import os

import requests

LI = "https://api.linkedin.com"
TOK = os.environ["LI_TOKEN"].strip()
linhas = []


def p(s):
    print(s, flush=True)
    linhas.append(s)


p(f"== diagnostico LinkedIn — {dt.datetime.utcnow():%Y-%m-%d %H:%M:%S} UTC ==")
p("")

# 1) quem sou eu
r = requests.get(f"{LI}/v2/userinfo", headers={"Authorization": f"Bearer {TOK}"}, timeout=30)
p(f"[userinfo] {r.status_code} :: {r.text[:300]}")
urn = None
if r.status_code == 200:
    urn = f"urn:li:person:{r.json().get('sub')}"
p(f"[urn] {urn}")
p("")

# 2) API versionada, varias versoes
p("-- /rest/images?action=initializeUpload --")
for v in ["202509", "202508", "202507", "202506", "202505", "202504",
          "202503", "202501", "202411", "202408", "202405", "202401"]:
    h = {"Authorization": f"Bearer {TOK}",
         "X-Restli-Protocol-Version": "2.0.0",
         "LinkedIn-Version": v,
         "Content-Type": "application/json"}
    try:
        r = requests.post(f"{LI}/rest/images?action=initializeUpload", headers=h,
                          json={"initializeUploadRequest": {"owner": urn}}, timeout=30)
        p(f"  v{v}: {r.status_code} :: {r.text[:220]}")
    except Exception as e:
        p(f"  v{v}: EXCECAO {e}")
p("")

# 3) API antiga
p("-- /v2/assets?action=registerUpload (caminho antigo) --")
h = {"Authorization": f"Bearer {TOK}",
     "X-Restli-Protocol-Version": "2.0.0",
     "Content-Type": "application/json"}
body = {"registerUploadRequest": {
    "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
    "owner": urn,
    "serviceRelationships": [{"relationshipType": "OWNER",
                              "identifier": "urn:li:userGeneratedContent"}]}}
try:
    r = requests.post(f"{LI}/v2/assets?action=registerUpload", headers=h, json=body, timeout=30)
    p(f"  {r.status_code} :: {r.text[:500]}")
except Exception as e:
    p(f"  EXCECAO {e}")
p("")

# 4) o endpoint antigo de post existe para este token?
p("-- /v2/ugcPosts (so checa se responde, nao cria nada) --")
try:
    r = requests.get(f"{LI}/v2/ugcPosts?q=authors&authors=List({urn})&count=1",
                     headers=h, timeout=30)
    p(f"  {r.status_code} :: {r.text[:300]}")
except Exception as e:
    p(f"  EXCECAO {e}")

open("diagnostico-linkedin.txt", "w", encoding="utf-8").write("\n".join(linhas) + "\n")
print("\narquivo diagnostico-linkedin.txt gravado")
