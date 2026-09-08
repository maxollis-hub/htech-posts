#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cria o template proprio do vigia na WABA da HTECH. Aprovado pelo Max em 08/09/2026."""
import datetime as dt
import json
import os

import requests

GRAPH = "https://graph.facebook.com/v22.0"
TOK = os.environ["WA_TOKEN"].strip()
WABA = os.environ.get("WA_WABA_ID", "1597874738563069").strip()
L = []


def p(s):
    print(s, flush=True)
    L.append(str(s))


NOME = "aviso_publicacao"
CORPO = ("HTECH · vigia da publicação\n\n"
         "Situação: {{1}}\n"
         "Verificado em: {{2}}\n\n"
         "{{3}}\n\n"
         "Relatório completo em vigia-ultimo-relatorio.txt, no repositório htech-posts.")
EXEMPLO = ["tudo em ordem",
           "15/09/2026 07:50",
           "3 peças publicadas nos últimos 7 dias, 1 na fila."]

p(f"== criar template — {dt.datetime.utcnow():%Y-%m-%d %H:%M:%S} UTC ==")
p("")

# ja existe?
r0 = requests.get(f"{GRAPH}/{WABA}/message_templates",
                  params={"access_token": TOK, "name": NOME, "limit": 5}, timeout=30)
existentes = [t for t in r0.json().get("data", []) if t.get("name") == NOME]
if existentes:
    p(f"-- ja existe um template '{NOME}':")
    for t in existentes:
        p(f"   status={t.get('status')} idioma={t.get('language')} id={t.get('id')}")
    p("   nao vou criar de novo.")
else:
    p(f"-- criando '{NOME}' --")
    r = requests.post(f"{GRAPH}/{WABA}/message_templates",
                      headers={"Authorization": f"Bearer {TOK}",
                               "Content-Type": "application/json"},
                      json={"name": NOME, "language": "pt_BR", "category": "UTILITY",
                            "components": [{"type": "BODY", "text": CORPO,
                                            "example": {"body_text": [EXEMPLO]}}]},
                      timeout=45)
    p(f"HTTP {r.status_code}")
    p(f"resposta: {r.text[:600]}")

p("")
p("-- estado atual --")
r2 = requests.get(f"{GRAPH}/{WABA}/message_templates",
                  params={"access_token": TOK, "name": NOME, "limit": 5}, timeout=30)
try:
    for t in r2.json().get("data", []):
        p(f"   nome={t.get('name')}  STATUS={t.get('status')}  categoria={t.get('category')}  id={t.get('id')}")
        if t.get("status") == "REJECTED":
            p(f"      motivo: {t.get('rejected_reason')}")
except Exception as e:
    p(f"   {e} :: {r2.text[:300]}")

open("diagnostico-whatsapp.txt", "w", encoding="utf-8").write("\n".join(L) + "\n")
print("gravado")
