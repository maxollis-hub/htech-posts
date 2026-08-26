# O padrão de publicação da HTECH

Processo validado em 26/08/2026. Substitui a automação por navegador (Meta Business
Suite e Canva Planner), que quebrava toda semana. **Custo zero.**

Se você é o Claude de uma sessão futura: leia este arquivo inteiro antes de
publicar qualquer coisa. Ele existe para você não reconstruir o caminho do zero
nem repetir os erros já mapeados.

---

## Como funciona, em uma frase

Eu preparo as peças e ponho na fila do GitHub; um robô do próprio GitHub publica
no horário, sozinho, sem depender do computador do Max estar ligado.

## Divisão de trabalho

| Etapa | Quem | Esforço |
|---|---|---|
| Pauta, roteiro, slides, legendas | Claude | — |
| Converter mídia, montar e validar a fila, enviar | Claude | 1 comando |
| Publicar Instagram e LinkedIn do Max no horário | robô do GitHub | automático |
| Facebook (espelhado do Instagram) | Instagram, sozinho | automático |
| Publicar na **página** do LinkedIn | **Max** | 2 min, 2× por semana* |
| Story com link e Reel | **Max** | no celular |
| Colar token novo do LinkedIn | **Max** | 2 min a cada 60 dias |

\* até a aprovação da Community Management API sair. Depois disso, some da lista.

---

## O ritual de cada ciclo

### 1. Produzir (como sempre)
Slides em PNG 1080×1350 pelo script de PIL, legendas no `_legenda-e-instrucoes.md`
da peça. Nada muda aqui.

### 2. Montar a fila
Um arquivo JSON por peça em `fila/agendados/`, nomeado `AAAA-MM-DD-Pn.json`:

```json
{
  "id": "P9",
  "titulo": "Motorredutor superaquecendo",
  "quando": "2026-09-01T08:30:00",
  "destinos": ["instagram", "linkedin_perfil"],
  "midia_origem": [
    "criacoes/2026-09-01-nord/slides/01.png",
    "criacoes/2026-09-01-nord/slides/02.png"
  ],
  "legendas": {
    "instagram": "texto com hashtags",
    "linkedin": "texto do LinkedIn"
  }
}
```

Caminhos em `midia_origem` são relativos à raiz do projeto. Se `legendas.facebook`
não existir, o Facebook herda a do Instagram.

### 3. Preparar e enviar
```bash
cd automacao
python3 preparar.py            # converte, valida e mostra os erros
python3 preparar.py --push     # só depois que estiver limpo
```
`preparar.py` converte PNG→JPEG, grava em `midia/`, troca `midia_origem` por
`midia` e barra o envio se qualquer validação falhar.

### 4. Avisar o Max
Um resumo do que foi agendado, com data, hora e canais. **Janela de 24 h para
vetar** — decisão dele em 26/08. Silêncio significa aprovado.

### 5. Conferir depois
- Fila: os arquivos saem de `fila/agendados/` e aparecem em `fila/publicados/`
  com o resultado de cada canal.
- Execuções: aba **Actions** do repositório `htech-posts`.
- Falha: o GitHub manda e-mail automático para o Max, e o post **fica na fila**
  com só os canais que falharam — a próxima rodada tenta de novo.

---

## Armadilhas já pagas — não descobrir de novo

- **O Instagram só aceita JPEG.** PNG é recusado. `preparar.py` converte; nunca
  colocar PNG em `midia/` na mão.
- **Carrossel: no máximo 10 itens**, e todos são cortados na proporção do primeiro.
  Os nossos são 1080×1350 — manter assim.
- **Limites de texto:** Instagram 2.200, LinkedIn 3.000, Facebook 16.192 caracteres.
  `preparar.py` checa.
- **Deixe pelo menos 15 min de folga** entre o envio e o horário do post. O cron do
  GitHub roda a cada 10 min e costuma atrasar alguns minutos.
- **Atraso é normal, perda não.** O robô publica tudo que já venceu, não só o do
  minuto. Se uma execução falhar, a seguinte recupera.
- **Token do LinkedIn morre em 60 dias.** É limite deles. O do Facebook, se gerado
  com os cinco escopos certos, não expira (`expires_at: 0` no debug_token).
- **Nunca usar automação de navegador no LinkedIn.** Proteção anti-bot ativa; já
  causou logout forçado e há risco real de restrição da conta do Max.
- **NÃO incluir `facebook` nos destinos da fila** enquanto a Verificação Comercial
  não sair. A Meta exige `pages_manage_posts`, que só é liberada depois disso —
  o erro é `(#200) The permission(s) pages_manage_posts are not available`.
  Hoje o Facebook é alimentado pelo **compartilhamento automático do Instagram**,
  configurado na conta, fora do nosso código. Pôr `facebook` na fila só produz
  falha e post preso na fila.
- **Nada é reportado como publicado sem conferir** o arquivo em `fila/publicados/`
  ou a aba Actions. "Parece que funcionou" foi o que gerou o retrabalho de agosto.

## Quando algo falha

1. Abrir a aba **Actions** no GitHub e ler o log da execução vermelha.
2. Erro de token → gerar de novo (seção 2 ou 3 do `SETUP-UMA-VEZ.md`) e atualizar
   o secret.
3. Erro de mídia → quase sempre a URL não está pública: conferir se o `midia/`
   foi mesmo enviado no push.
4. Erro em `linkedin_pagina` → a aprovação ainda não saiu. Tirar esse destino da
   fila e publicar à mão.
