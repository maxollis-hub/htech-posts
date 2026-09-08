#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Diagnostico do canal WhatsApp do vigia — rodada 2.

Sintoma: HTTP 200, wa_id correto, e a mensagem NAO chega no WhatsApp Business
do Max (5532991434653).

Hipotese principal: o numero do Max esta registrado DENTRO da mesma WhatsApp
Business Account (WABA) do assistente. A Meta aceita (200) e descarta: numero da
conta nao entrega para numero da propria conta.
"""
import datetime as dt
import json
import os

import requests

GRAPH = "https://graph.facebook.com/v22.0"
TOK = os.environ.get("WA_TOKEN", "").strip()
PID = os.environ.get("WA_PHONE_ID", "").strip()
DEST = "".join(c for c in os.environ.get("WA_DESTINO", "") if c.isdigit())
WABA = os.environ.get("WA_WABA_ID", "1597874738563069").strip()
linhas = []


def p(s):
    print(s, flush=True)
    linhas.append(str(s))


p(f"== diagnostico WhatsApp (rodada 2) — {dt.datetime.utcnow():%Y-%m-%d %H:%M:%S} UTC ==")
p("")

# 1) TODOS os numeros dentro da WABA
p("-- numeros registrados nesta WhatsApp Business Account --")
r = requests.get(f"{GRAPH}/{WABA}/phone_numbers",
                 params={"access_token": TOK,
                         "fields": "display_phone_number,verified_name,id,quality_rating"},
                 timeout=30)
p(f"HTTP {r.status_code}")
numeros = []
try:
    for n in r.json().get("data", []):
        so_digitos = "".join(c for c in n.get("display_phone_number", "") if c.isdigit())
        numeros.append(so_digitos)
        marca = "   <<< ESTE E O DESTINO DO VIGIA" if so_digitos.endswith(DEST[-8:]) else ""
        p(f"   {n.get('display_phone_number')}  ({n.get('verified_name')})  id={n.get('id')}{marca}")
except Exception as e:
    p(f"   nao consegui ler: {e} :: {r.text[:300]}")

conflito = any(x.endswith(DEST[-8:]) for x in numeros)
p("")
if conflito:
    p("*** CONFIRMADO: o destino do vigia esta DENTRO da mesma WABA do remetente.")
    p("*** E por isso que a Meta responde 200 e nao entrega nada.")
    p("*** Solucao: usar um numero de destino que NAO pertenca a esta WABA.")
else:
    p("--- o destino NAO esta na WABA. A hipotese principal cai; ver abaixo.")

# 2) a conta esta com alguma restricao?
p("")
p("-- saude da conta --")
r2 = requests.get(f"{GRAPH}/{WABA}",
                  params={"access_token": TOK,
                          "fields": "name,account_review_status,business_verification_status,"
                                    "messaging_limit_tier,health_status"}, timeout=30)
p(f"HTTP {r2.status_code} :: {r2.text[:600]}")

# 3) o numero remetente consegue mesmo mandar?
p("")
p("-- saude do numero remetente --")
r3 = requests.get(f"{GRAPH}/{PID}",
                  params={"access_token": TOK,
                          "fields": "display_phone_number,verified_name,quality_rating,"
                                    "throughput,status,name_status,health_status"}, timeout=30)
try:
    p(json.dumps(r3.json(), indent=2, ensure_ascii=False))
except Exception:
    p(r3.text)

# 4) o que o Meta diz sobre ESTA conversa especifica
p("")
p("-- conversa com o destino --")
r4 = requests.get(f"{GRAPH}/{PID}/conversational_automation",
                  params={"access_token": TOK}, timeout=30)
p(f"[automacao] HTTP {r4.status_code} :: {r4.text[:300]}")

# 5) reenviar e guardar o id, para consulta de status
p("")
p("-- reenvio de teste --")
r5 = requests.post(f"{GRAPH}/{PID}/messages",
                   headers={"Authorization": f"Bearer {TOK}", "Content-Type": "application/json"},
                   json={"messaging_product": "whatsapp", "recipient_type": "individual",
                         "to": DEST, "type": "text",
                         "text": {"preview_url": False,
                                  "body": "HTECH: teste 3 do vigia. Responda OK se receber."}},
                   timeout=45)
p(f"HTTP {r5.status_code} :: {r5.text[:400]}")

open("diagnostico-whatsapp.txt", "w", encoding="utf-8").write("\n".join(linhas) + "\n")
print("\narquivo gravado")
