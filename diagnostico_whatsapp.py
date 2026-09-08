#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Teste do TEMPLATE — o caminho que funciona fora da janela de 24 h.

Descoberta: a Cloud API responde 200 para texto livre mesmo com a janela de 24 h
FECHADA, e falha depois, em silencio, por webhook. Ou seja: 200 nao prova nada, e
o fallback do vigia (que so caia no template quando o texto era RECUSADO) nunca
era acionado. Template funciona fora da janela — e isso e o que este teste prova.
"""
import datetime as dt
import json
import os

import requests

GRAPH = "https://graph.facebook.com/v22.0"
TOK = os.environ["WA_TOKEN"].strip()
PID = os.environ["WA_PHONE_ID"].strip()
DEST = "".join(c for c in os.environ["WA_DESTINO"] if c.isdigit())
NOME = os.environ.get("WA_TEMPLATE", "lembrete_agenda").strip()
IDIOMA = os.environ.get("WA_TEMPLATE_LANG", "pt_BR").strip()
linhas = []


def p(s):
    print(s, flush=True)
    linhas.append(str(s))


p(f"== teste do template — {dt.datetime.utcnow():%Y-%m-%d %H:%M:%S} UTC ==")
p(f"template: {NOME} ({IDIOMA})  destino: {DEST}")
p("")

# como o template esta cadastrado (quantas variaveis ele espera?)
WABA = os.environ.get("WA_WABA_ID", "1597874738563069")
r = requests.get(f"{GRAPH}/{WABA}/message_templates",
                 params={"access_token": TOK, "name": NOME, "limit": 5}, timeout=30)
p("-- como o template esta cadastrado --")
try:
    for t in r.json().get("data", []):
        p(f"   nome={t.get('name')} status={t.get('status')} idioma={t.get('language')} categoria={t.get('category')}")
        for c in t.get("components", []):
            p(f"      [{c.get('type')}] {json.dumps(c.get('text',''), ensure_ascii=False)[:220]}")
except Exception as e:
    p(f"   erro: {e} :: {r.text[:300]}")
p("")

p("-- envio do template --")
corpo = {"messaging_product": "whatsapp", "recipient_type": "individual",
         "to": DEST, "type": "template",
         "template": {"name": NOME, "language": {"code": IDIOMA},
                      "components": [{"type": "body", "parameters": [
                          {"type": "text", "text": "Teste do vigia HTECH"},
                          {"type": "text", "text": dt.datetime.utcnow().strftime("%d/%m/%Y %H:%M")},
                          {"type": "text", "text": "Se voce recebeu isto, o canal de aviso funciona fora da janela de 24h"}]}]}}
r2 = requests.post(f"{GRAPH}/{PID}/messages",
                   headers={"Authorization": f"Bearer {TOK}", "Content-Type": "application/json"},
                   json=corpo, timeout=45)
p(f"HTTP {r2.status_code}")
p(f"resposta: {r2.text[:600]}")

open("diagnostico-whatsapp.txt", "w", encoding="utf-8").write("\n".join(linhas) + "\n")
print("\ngravado")
