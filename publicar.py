#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
publicar.py — publica os posts da fila cujo horario ja chegou.

Roda no GitHub Actions (a cada 10 min) e tambem na mao, para teste.
Nao depende do computador do Max ligado, nem de nenhuma assinatura.

Regra central: publica TUDO que esta vencido, nao so o do minuto exato.
Se uma execucao atrasar ou falhar, a proxima recupera. Nada se perde.

Credenciais, via variaveis de ambiente (GitHub Secrets):
    META_TOKEN        token de pagina do Facebook (nao expira)
    FB_PAGE_ID        id da pagina do Facebook
    IG_USER_ID        id da conta Instagram Business
    LI_TOKEN          access token do LinkedIn (perfil do Max, 60 dias)
    LI_PERSON_URN     urn:li:person:xxxx
    LI_ORG_URN        urn:li:organization:xxxx  (opcional, so quando sair a aprovacao)
    MEDIA_BASE_URL    base publica da midia, ex.: https://raw.githubusercontent.com/user/repo/main
"""

import datetime as dt
import json
import os
import sys
import time
from pathlib import Path

import requests

RAIZ = Path(__file__).resolve().parent
AGENDADOS = RAIZ / "fila" / "agendados"
PUBLICADOS = RAIZ / "fila" / "publicados"
GRAPH = "https://graph.facebook.com/v23.0"
LI = "https://api.linkedin.com"
TZ = dt.timezone(dt.timedelta(hours=-3))  # America/Sao_Paulo


def env(nome, obrigatorio=True):
    v = os.environ.get(nome, "").strip()
    if obrigatorio and not v:
        raise RuntimeError(f"variavel de ambiente ausente: {nome}")
    return v


def log(msg):
    print(f"[{dt.datetime.now(TZ):%d/%m %H:%M:%S}] {msg}", flush=True)


def url_midia(arquivo):
    return f"{env('MEDIA_BASE_URL').rstrip('/')}/midia/{arquivo}"


# ------------------------------------------------------------------ Instagram

def publicar_instagram(post):
    ig = env("IG_USER_ID")
    tok = env("META_TOKEN")
    arquivos = post["midia"]
    legenda = post["legendas"]["instagram"]

    if len(arquivos) == 1:
        r = requests.post(f"{GRAPH}/{ig}/media",
                          data={"image_url": url_midia(arquivos[0]),
                                "caption": legenda, "access_token": tok}, timeout=90)
        r.raise_for_status()
        container = r.json()["id"]
    else:
        filhos = []
        for arq in arquivos:
            r = requests.post(f"{GRAPH}/{ig}/media",
                              data={"image_url": url_midia(arq),
                                    "is_carousel_item": "true",
                                    "access_token": tok}, timeout=90)
            r.raise_for_status()
            filhos.append(r.json()["id"])
            time.sleep(1)
        r = requests.post(f"{GRAPH}/{ig}/media",
                          data={"media_type": "CAROUSEL",
                                "children": ",".join(filhos),
                                "caption": legenda,
                                "access_token": tok}, timeout=90)
        r.raise_for_status()
        container = r.json()["id"]

    # espera o container ficar pronto antes de publicar
    for _ in range(20):
        s = requests.get(f"{GRAPH}/{container}",
                         params={"fields": "status_code", "access_token": tok}, timeout=30)
        estado = s.json().get("status_code", "")
        if estado == "FINISHED":
            break
        if estado == "ERROR":
            raise RuntimeError(f"container do Instagram falhou: {s.text[:300]}")
        time.sleep(5)

    r = requests.post(f"{GRAPH}/{ig}/media_publish",
                      data={"creation_id": container, "access_token": tok}, timeout=90)
    r.raise_for_status()
    return {"id": r.json().get("id"), "permalink": None}


# ------------------------------------------------------------------ Facebook

def publicar_facebook(post):
    page = env("FB_PAGE_ID")
    tok = env("META_TOKEN")
    legenda = post["legendas"].get("facebook") or post["legendas"]["instagram"]

    ids = []
    for arq in post["midia"]:
        r = requests.post(f"{GRAPH}/{page}/photos",
                          data={"url": url_midia(arq), "published": "false",
                                "access_token": tok}, timeout=90)
        r.raise_for_status()
        ids.append(r.json()["id"])
        time.sleep(1)

    dados = {"message": legenda, "access_token": tok}
    for i, mid in enumerate(ids):
        dados[f"attached_media[{i}]"] = json.dumps({"media_fbid": mid})
    r = requests.post(f"{GRAPH}/{page}/feed", data=dados, timeout=90)
    r.raise_for_status()
    return {"id": r.json().get("id")}


# ------------------------------------------------------------------ LinkedIn

def _li_headers():
    return {"Authorization": f"Bearer {env('LI_TOKEN')}",
            "X-Restli-Protocol-Version": "2.0.0",
            "LinkedIn-Version": "202506",
            "Content-Type": "application/json"}


def _li_subir_imagem(owner_urn, arquivo):
    r = requests.post(f"{LI}/rest/images?action=initializeUpload",
                      headers=_li_headers(),
                      json={"initializeUploadRequest": {"owner": owner_urn}}, timeout=60)
    r.raise_for_status()
    v = r.json()["value"]
    caminho = RAIZ / "midia" / arquivo
    up = requests.put(v["uploadUrl"], data=caminho.read_bytes(),
                      headers={"Authorization": f"Bearer {env('LI_TOKEN')}"}, timeout=120)
    if up.status_code not in (200, 201):
        raise RuntimeError(f"upload de imagem no LinkedIn falhou: {up.status_code} {up.text[:200]}")
    return v["image"]


def publicar_linkedin(post, owner_urn):
    texto = post["legendas"]["linkedin"]
    arquivos = post["midia"]

    urns = []
    for arq in arquivos:
        urns.append(_li_subir_imagem(owner_urn, arq))
        time.sleep(1)

    corpo = {
        "author": owner_urn,
        "commentary": texto,
        "visibility": "PUBLIC",
        "distribution": {"feedDistribution": "MAIN_FEED",
                         "targetEntities": [], "thirdPartyDistributionChannels": []},
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }
    if len(urns) == 1:
        corpo["content"] = {"media": {"id": urns[0], "title": post.get("titulo", "")[:200]}}
    else:
        corpo["content"] = {"multiImage": {
            "images": [{"id": u, "altText": post.get("titulo", "")[:200]} for u in urns]}}

    r = requests.post(f"{LI}/rest/posts", headers=_li_headers(), json=corpo, timeout=120)
    if r.status_code not in (200, 201):
        raise RuntimeError(f"LinkedIn recusou: {r.status_code} {r.text[:400]}")
    return {"id": r.headers.get("x-restli-id") or r.headers.get("X-RestLi-Id")}


# ------------------------------------------------------------------ orquestrador

DESTINOS = {
    "instagram": lambda p: publicar_instagram(p),
    "facebook": lambda p: publicar_facebook(p),
    "linkedin_perfil": lambda p: publicar_linkedin(p, env("LI_PERSON_URN")),
    "linkedin_pagina": lambda p: publicar_linkedin(p, env("LI_ORG_URN")),
}


def vencidos(agora):
    AGENDADOS.mkdir(parents=True, exist_ok=True)
    PUBLICADOS.mkdir(parents=True, exist_ok=True)
    saida = []
    for f in sorted(AGENDADOS.glob("*.json")):
        post = json.loads(f.read_text(encoding="utf-8"))
        quando = dt.datetime.fromisoformat(post["quando"]).replace(tzinfo=TZ)
        if quando <= agora:
            saida.append((f, post, quando))
    return saida


def main():
    somente_listar = "--listar" in sys.argv
    forcar = "--forcar" in sys.argv
    agora = dt.datetime.now(TZ)
    fila = vencidos(agora) if not forcar else [
        (f, json.loads(f.read_text(encoding="utf-8")), None) for f in sorted(AGENDADOS.glob("*.json"))]

    if not fila:
        log("nada vencido na fila")
        return

    if somente_listar:
        for f, post, quando in fila:
            log(f"pendente: {post['id']} · {post['quando']} · {', '.join(post['destinos'])}")
        return

    houve_erro = False
    for arquivo, post, _ in fila:
        log(f"=== {post['id']} — {post.get('titulo','')}")
        resultado = {"publicado_em": agora.isoformat(), "destinos": {}}
        todos_ok = True

        for destino in post["destinos"]:
            if destino not in DESTINOS:
                log(f"  destino desconhecido, ignorado: {destino}")
                continue
            try:
                r = DESTINOS[destino](post)
                resultado["destinos"][destino] = {"ok": True, **r}
                log(f"  OK  {destino}")
            except Exception as e:
                todos_ok = False
                houve_erro = True
                resultado["destinos"][destino] = {"ok": False, "erro": str(e)[:500]}
                log(f"  ERRO {destino}: {str(e)[:300]}")

        post["resultado"] = resultado
        if todos_ok:
            destino_final = PUBLICADOS / arquivo.name
            destino_final.write_text(json.dumps(post, indent=2, ensure_ascii=False), encoding="utf-8")
            arquivo.unlink()
            log(f"  movido para publicados/")
        else:
            # mantem na fila para a proxima rodada tentar de novo os que falharam
            post["destinos"] = [d for d, v in resultado["destinos"].items() if not v["ok"]]
            arquivo.write_text(json.dumps(post, indent=2, ensure_ascii=False), encoding="utf-8")
            log(f"  mantido na fila com os destinos que falharam: {post['destinos']}")

    if houve_erro:
        sys.exit(1)


if __name__ == "__main__":
    main()
