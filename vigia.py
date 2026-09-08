#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""vigia.py — confere se a fila esta realmente publicando e avisa o Max.

Existe por causa de 01–07/09/2026: o LinkedIn quebrou, TODA execucao ficou
vermelha por sete dias e ninguem viu, porque Instagram e Facebook continuaram
publicando e a aba Actions nao e vigiada por ninguem.

Roda no GitHub Actions (sempre ligado, nao depende do PC do Max):
    python vigia.py --diario    avisa SO se houver problema
    python vigia.py --semanal   manda o panorama sempre, mesmo tudo em ordem

O resumo semanal e de proposito: vigia silencioso e indistinguivel de vigia morto.

Canais de aviso, nesta ordem:
  1. WhatsApp pela Cloud API (texto na janela de 24h; fora dela, template).
  2. Issue no repositorio — o GitHub manda e-mail sozinho. Rede de seguranca
     para quando o WhatsApp falhar, que e justamente quando o aviso importa.

Variaveis de ambiente:
    WA_TOKEN, WA_PHONE_ID, WA_DESTINO, WA_TEMPLATE (opcional), WA_TEMPLATE_LANG
    GITHUB_TOKEN, GITHUB_REPOSITORY   (o proprio Actions fornece)
    LI_TOKEN_VALIDO_ATE               AAAA-MM-DD, para avisar antes de vencer
"""
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
AGENDADOS = RAIZ / "fila" / "agendados"
PUBLICADOS = RAIZ / "fila" / "publicados"
TZ = dt.timezone(dt.timedelta(hours=-3))
GRAPH = "https://graph.facebook.com/v22.0"

# O cron do GitHub e estrangulado: na pratica roda uma vez a cada 2-3 h, nao a
# cada 10 min. So considerar atrasada a peca que passou desta folga.
FOLGA_HORAS = 4


def http(url, dados=None, cabecalhos=None, metodo=None):
    req = urllib.request.Request(
        url, data=json.dumps(dados).encode() if dados is not None else None,
        headers=cabecalhos or {}, method=metodo)
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return 0, str(e)


# ------------------------------------------------------------------ o que olhar

def ler_fila():
    pecas = []
    for f in sorted(AGENDADOS.glob("*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        try:
            quando = dt.datetime.fromisoformat(d["quando"]).replace(tzinfo=TZ)
        except Exception:
            continue
        pecas.append({"arquivo": f.name, "id": d.get("id", f.stem),
                      "titulo": d.get("titulo", ""), "quando": quando,
                      "destinos": d.get("destinos", []),
                      "erros": {k: v.get("erro") for k, v in
                                (d.get("resultado") or {}).get("destinos", {}).items()
                                if not v.get("ok")}})
    return pecas


def ultimas_execucoes(n=8):
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    tok = os.environ.get("GITHUB_TOKEN", "")
    if not (repo and tok):
        return []
    s, corpo = http(f"https://api.github.com/repos/{repo}/actions/workflows/publicar.yml/runs?per_page={n}",
                    cabecalhos={"Authorization": f"Bearer {tok}",
                                "Accept": "application/vnd.github+json"})
    if s != 200:
        return []
    return [(r["created_at"], r["conclusion"]) for r in json.loads(corpo).get("workflow_runs", [])]


def publicados_recentes(dias=7):
    limite = dt.datetime.now(TZ) - dt.timedelta(days=dias)
    saida = []
    for f in sorted(PUBLICADOS.glob("*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
            quando = dt.datetime.fromisoformat(
                d.get("resultado", {}).get("publicado_em", ""))
        except Exception:
            continue
        if quando >= limite:
            canais = ", ".join(k for k, v in d["resultado"]["destinos"].items() if v.get("ok"))
            saida.append((d.get("id", f.stem), quando, canais))
    return saida


# ------------------------------------------------------------------ avisar

def whatsapp(assunto, quando_txt, detalhe, texto_completo):
    tok = os.environ.get("WA_TOKEN", "").strip()
    pid = os.environ.get("WA_PHONE_ID", "").strip()
    para = "".join(c for c in os.environ.get("WA_DESTINO", "") if c.isdigit())
    if not (tok and pid and para):
        return False, "WhatsApp nao configurado (faltam WA_TOKEN/WA_PHONE_ID/WA_DESTINO)"

    cab = {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}
    s, corpo = http(f"{GRAPH}/{pid}/messages", {
        "messaging_product": "whatsapp", "recipient_type": "individual",
        "to": para, "type": "text",
        "text": {"preview_url": False, "body": texto_completo[:4000]}}, cab)
    if s == 200:
        return True, "texto entregue (janela de 24h aberta)"

    # fora da janela de 24h o texto livre e recusado (#131047): vai de template
    nome = os.environ.get("WA_TEMPLATE", "").strip()
    if not nome:
        return False, f"texto recusado ({s}) e nenhum WA_TEMPLATE configurado :: {corpo[:200]}"
    idioma = os.environ.get("WA_TEMPLATE_LANG", "pt_BR").strip()

    def limpar(t):
        # variavel de template nao aceita quebra de linha nem espaco duplo
        return " ".join(str(t).split())[:900]

    s2, corpo2 = http(f"{GRAPH}/{pid}/messages", {
        "messaging_product": "whatsapp", "recipient_type": "individual",
        "to": para, "type": "template",
        "template": {"name": nome, "language": {"code": idioma},
                     "components": [{"type": "body", "parameters": [
                         {"type": "text", "text": limpar(assunto)},
                         {"type": "text", "text": limpar(quando_txt)},
                         {"type": "text", "text": limpar(detalhe)}]}]}}, cab)
    if s2 == 200:
        return True, f"template '{nome}' entregue"
    return False, f"texto {s} e template {s2} :: {corpo2[:250]}"


def abrir_issue(titulo, corpo):
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    tok = os.environ.get("GITHUB_TOKEN", "")
    if not (repo and tok):
        return False, "sem GITHUB_TOKEN"
    s, r = http(f"https://api.github.com/repos/{repo}/issues",
                {"title": titulo, "body": corpo, "labels": ["vigia"]},
                {"Authorization": f"Bearer {tok}",
                 "Accept": "application/vnd.github+json",
                 "Content-Type": "application/json"}, "POST")
    return s == 201, f"issue HTTP {s}"


# ------------------------------------------------------------------ principal

def main():
    semanal = "--semanal" in sys.argv
    agora = dt.datetime.now(TZ)
    fila = ler_fila()
    limite = agora - dt.timedelta(hours=FOLGA_HORAS)

    atrasadas = [p for p in fila if p["quando"] <= limite]
    proximas = sorted([p for p in fila if p["quando"] > limite], key=lambda p: p["quando"])
    execucoes = ultimas_execucoes()
    # so importa se a execucao MAIS RECENTE falhou: o robo reprocessa o que ficou
    # para tras, entao falha antiga com verde depois ja esta resolvida
    ultima = execucoes[0][1] if execucoes else None
    seguidas = 0
    for _, c in execucoes:
        if c in (None, "success"):
            break
        seguidas += 1

    problemas = []
    if atrasadas:
        for p in atrasadas:
            motivo = "; ".join(f"{k}: {v}" for k, v in p["erros"].items()) or "nenhuma tentativa registrada"
            problemas.append(f"{p['id']} venceu {p['quando']:%d/%m %H:%M} e nao publicou "
                             f"em {', '.join(p['destinos'])} — {motivo}")
    if ultima not in (None, "success"):
        problemas.append(f"a ultima execucao do robo falhou ({seguidas} seguida(s)) — ver a aba Actions")
    if not fila:
        problemas.append("a fila esta VAZIA — nenhuma peca agendada")
    elif not proximas:
        problemas.append("nao ha nenhuma peca agendada para os proximos dias")

    venc = os.environ.get("LI_TOKEN_VALIDO_ATE", "").strip()
    if venc:
        try:
            dias = (dt.date.fromisoformat(venc) - agora.date()).days
            if dias <= 15:
                problemas.append(f"o token do LinkedIn vence em {dias} dia(s) ({venc}) — renovar")
        except ValueError:
            pass

    # ---- monta o texto
    linhas = ["*HTECH — vigia da publicacao*", f"{agora:%d/%m/%Y %H:%M}", ""]
    if problemas:
        linhas.append("*ATENCAO*")
        linhas += [f"- {t}" for t in problemas]
        linhas.append("")
    else:
        linhas.append("Tudo em ordem: nada vencido na fila.")
        linhas.append("")

    if semanal:
        recentes = publicados_recentes()
        linhas.append(f"*Publicado nos ultimos 7 dias:* {len(recentes)}")
        for pid, q, canais in recentes:
            linhas.append(f"- {pid} · {q:%d/%m %H:%M} · {canais}")
        linhas.append("")
        linhas.append(f"*Na fila:* {len(proximas)}")
        for p in proximas[:6]:
            linhas.append(f"- {p['id']} · {p['quando']:%d/%m %H:%M} · {', '.join(p['destinos'])}")
        if not proximas:
            linhas.append("- nada agendado")
        linhas.append("")
        linhas.append("Lembrete: stories, reels e a pagina do LinkedIn continuam manuais.")
    texto = "\n".join(linhas)

    print(texto)
    print()

    # grava o relatorio no repositorio: os logs do Actions nao sao acessiveis
    # daqui e ninguem abre a aba Actions — este arquivo e o registro consultavel
    rodape = [""]
    if execucoes:
        rodape.append("Ultimas execucoes do robo: " +
                      ", ".join(f"{d[:16].replace('T',' ')} {c}" for d, c in execucoes[:5]))
    Path(RAIZ / "vigia-ultimo-relatorio.txt").write_text(
        texto + "\n".join(rodape) + "\n", encoding="utf-8")

    if not problemas and not semanal:
        print("nada a avisar (modo diario, tudo em ordem)")
        return

    assunto = ("Publicacao HTECH: " + problemas[0][:80]) if problemas else "Publicacao HTECH: tudo em ordem"
    detalhe = " | ".join(problemas)[:900] if problemas else \
        f"{len(publicados_recentes())} peca(s) publicadas nos ultimos 7 dias, {len(proximas)} na fila."
    ok, como = whatsapp(assunto, f"{agora:%d/%m/%Y %H:%M}", detalhe, texto)
    print(f"WhatsApp: {'OK' if ok else 'FALHOU'} — {como}")

    if problemas and not ok:
        feito, det = abrir_issue(f"[vigia] {assunto}", texto)
        print(f"Issue de seguranca: {'criada' if feito else 'falhou'} — {det}")

    # nunca derrubar a execucao por causa do canal de aviso: vermelho aqui seria
    # exatamente o sinal que ninguem olha
    return


if __name__ == "__main__":
    main()
