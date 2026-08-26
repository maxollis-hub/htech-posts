# Setup — uma vez só, ~35 min, custo zero

Nada aqui se repete toda semana. Depois disto, publicar um ciclo é um comando meu.

---

## 1. GitHub — a casa do robô (10 min)

1. `github.com` → criar conta, se ainda não tiver.
2. `github.com/new` → nome **`htech-posts`** → **Public** → Create.
   > Público porque o Instagram exige que a imagem esteja numa URL pública para
   > conseguir baixá-la. Só entram slides de carrossel — material que vira público
   > dias depois de qualquer jeito. Nada de cliente, nada interno. As senhas ficam
   > em *Secrets*, criptografados, que não aparecem no repositório.
3. Settings → Developer settings → Personal access tokens → **Fine-grained tokens**
   → Generate new token → acesso só ao `htech-posts` → permissão **Contents: Read and write**
   → copiar o token e me mandar.

## 2. Facebook e Instagram — token que não expira (15 min)

O app já existe desde julho (ID `3255146598207446`). Só falta gerar o token certo.

1. `developers.facebook.com/tools/explorer` → escolher o app HTECH.
2. Em **Permissions**, marcar exatamente estas cinco:
   `pages_show_list` · `pages_read_engagement` · `pages_manage_posts` ·
   `instagram_basic` · `instagram_content_publish`
3. **Generate Access Token** → autorizar → copiar o token (começa com `EAA...`).
4. Pegar também o **App ID** e o **App Secret** em Settings → Basic (o secret fica
   atrás de um botão "Show").
5. Me mandar os três.

> Esse token curto vale poucas horas — não tem problema. Eu troco por um token de
> página que, com os escopos certos, **não expira**. Eu confiro isso e te aviso.

## 3. LinkedIn — seu perfil (5 min, repete a cada 60 dias)

1. `linkedin.com/developers/tools/oauth/token-generator` → escolher o app HTECH.
2. Marcar os escopos `openid`, `profile`, `w_member_social`.
3. Autorizar → copiar o token → me mandar.

> 60 dias é limite do LinkedIn, não escolha nossa. Eu deixo um lembrete agendado
> para te avisar no dia 55 — é colar um token novo, dois minutos.

## 4. LinkedIn da página HTECH — pedir agora, usar depois (10 min)

Postar na **página** por programa exige aprovação do LinkedIn (Community Management
API). É gratuito, mas a análise leva de uma a quatro semanas e exige CNPJ e página
verificada — a HTECH tem os dois.

1. `developer.linkedin.com` → o app HTECH → Products → **Community Management API**
   → solicitar o **Development Tier**.
2. Me avisar quando a resposta chegar.

**Enquanto não sai, a página do LinkedIn é a única coisa que fica na sua mão:**
duas vezes por semana, ~2 min cada, com o PDF e a legenda já prontos na pasta.

## 5. Me mandar tudo

Token do GitHub · App ID · App Secret · token do Facebook · token do LinkedIn.
Eu monto os secrets, subo a estrutura e faço um teste com uma peça só.
