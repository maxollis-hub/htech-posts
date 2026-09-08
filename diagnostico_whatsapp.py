#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Diagnostico do canal WhatsApp do vigia.

HTTP 200 da Cloud API significa ACEITO, nao ENTREGUE. Este script mostra a
resposta INTEIRA da Meta — inclusive o `contacts[0].wa_id`, que e o numero para
onde a mensagem realmente foi. No Brasil o wa_id costuma perder o 9 extra
(5532991434653 -> 553291434653), e mandar para o numero errado devolve 200 e
nao entrega nada.

Grava tudo em diagnostico-whatsapp.txt, commitado pelo workflow.
"""
import datetime as dt
import json
import os

import requests

GRAPH = "https://graph.facebook.com/v22.0"
TOK = os.environ.get("WA_TOKEN", "").strip()
PID = os.environ.get("WA_PHONE_ID", "").strip()
DEST = "".join(c for c in os.environ.get("WA_DESTINO", "") if c.isdigit())
linhas = []


def p(s):
    print(s, flush=True)
    linhas.append(str(s))


p(f"== diagnostico WhatsApp — {dt.datetime.utcnow():%Y-%m-%d %H:%M:%S} UTC ==")
p(f"phone_number_id configurado: {PID}")
p(f"destino configurado:         {DEST}")
p("")

# 1) que numero e esse phone_number_id?
r = requests.get(f"{GRAPH}/{PID}",
                 params={"fields": "display_phone_number,verified_name,quality_rating,platform_type",
                         "access_token": TOK}, timeout=30)
p(f"[quem sou eu] {r.status_code} :: {r.text[:400]}")
p("")

# 2) o destino e o proprio remetente? (mandar para si mesmo nao entrega)
try:
    meu = "".join(c for c in r.json().get("display_phone_number", "") if c.isdigit())
    if meu and (meu.endswith(DEST[-8:]) or DEST.endswith(meu[-8:])):
        p("*** ATENCAO: o destino parece ser O PROPRIO NUMERO do remetente.")
        p("*** A Meta aceita (200) e nao entrega. Precisa mandar para outro numero.")
        p("")
except Exception:
    pass

# 3) envio de teste, mostrando a resposta inteira
p("-- envio de teste (texto livre) --")
r2 = requests.post(f"{GRAPH}/{PID}/messages",
                   headers={"Authorization": f"Bearer {TOK}",
                            "Content-Type": "application/json"},
                   json={"messaging_product": "whatsapp",
                         "recipient_type": "individual",
                         "to": DEST,
                         "type": "text",
                         "text": {"preview_url": False,
                                  "body": "Teste do vigia da HTECH. Se voce recebeu isto, o canal esta funcionando."}},
                   timeout=45)
p(f"  HTTP {r2.status_code}")
p(f"  resposta: {r2.text[:800]}")
try:
    d = r2.json()
    cont = (d.get("contacts") or [{}])[0]
    entrada, waid = cont.get("input"), cont.get("wa_id")
    p("")
    p(f"  input (o que mandamos): {entrada}")
    p(f"  wa_id (para onde foi):  {waid}")
    if entrada and waid and entrada != waid:
        p("  *** DIFERENTE — a Meta normalizou o numero. Se nao chegou, use o wa_id")
        p(f"  *** como WA_DESTINO: {waid}")
    msg = (d.get("messages") or [{}])[0]
    p(f"  message id: {msg.get('id')}")
    p(f"  status:     {msg.get('message_status', '(nao informado)')}")
except Exception as e:
    p(f"  (nao consegui ler o JSON: {e})")

p("")
p("-- tentativa com o numero SEM o nono digito --")
if len(DEST) == 13 and DEST[4] == "9":
    alt = DEST[:4] + DEST[5:]
    p(f"  testando {alt}")
    r3 = requests.post(f"{GRAPH}/{PID}/messages",
                       headers={"Authorization": f"Bearer {TOK}",
                                "Content-Type": "application/json"},
                       json={"messaging_product": "whatsapp",
                             "recipient_type": "individual", "to": alt,
                             "type": "text",
                             "text": {"preview_url": False,
                                      "body": "Teste 2 do vigia da HTECH (numero sem o nono digito)."}},
                       timeout=45)
    p(f"  HTTP {r3.status_code} :: {r3.text[:500]}")
else:
    p("  (destino nao tem o formato 55 + DDD + 9 + 8 digitos; pulei)")

open("diagnostico-whatsapp.txt", "w", encoding="utf-8").write("\n".join(linhas) + "\n")
print("\narquivo gravado")
