# Distribuição do LTS CopaTruck para o Pérez — avaliação de opções

> Criado 2026-07-02 (sprint R$5k). Objetivo: Pérez roda e testa à vontade, salva
> dados/exports na máquina dele, e tem ZERO acesso ao código-fonte.

## Opções

| # | Opção | Proteção de IP | Esforço | Custo | Veredito |
|---|-------|----------------|---------|-------|----------|
| 1 | **Web hosted** — Streamlit em servidor SARU (VPS tipo Hetzner/Railway/Render), acesso via link + senha | **Máxima** — código nunca sai do servidor | Baixo (deploy do que já roda) | ~R$30-60/mês | **Recomendada** |
| 2 | **Executável Windows** — Nuitka standalone | Alta (compila p/ C; reversão difícil) | Médio-alto (build Windows, Streamlit empacotado é chato) | zero mensal | V2 se pista-sem-internet virar requisito |
| 3 | Executável Windows — PyInstaller | **Fraca** — fonte extraível trivialmente (pyinstxtractor) | Baixo | zero | Descartada p/ IP |
| 4 | Docker image entregue | Fraca — `docker cp` extrai tudo | Baixo | zero | Descartada p/ IP |
| 5 | API SARU + cliente fino | Máxima | Alto | mensal | Overkill p/ MVP |

## Recomendação (sprint)

**Opção 1 (hosted)**: zero trabalho de packaging dentro do prazo, IP 100% protegida,
e vira argumento de VENDA na proposta A — "acesso à plataforma SARU" soa maior que
"te mando um .exe". Bônus: dá visibilidade de uso (justifica retainer) e mantém
controle de versão. Export de resultados = botão de download CSV (Streamlit nativo).

## Prompt de validação — colar no Perplexity ou Gemini (Vitor executa)

```text
Preciso distribuir um app Python 3.12 + Streamlit para UM cliente não-técnico no
Windows, com estas restrições: (1) cliente NÃO pode ter acesso ao código-fonte
(proteção de IP real, não só ofuscação); (2) cliente precisa rodar simulações e
exportar CSVs; (3) sou dev solo, manutenção mínima, orçamento baixo.

Compare em 2026:
(a) Hospedar Streamlit com autenticação simples: VPS (Hetzner/Contabo), Railway,
    Render, Streamlit Community Cloud — custo mensal real, limites de RAM/CPU,
    e risco de exposição do código em cada um;
(b) PyInstaller onefile — quão fácil é extrair o fonte na prática
    (pyinstxtractor/decompiladores atuais);
(c) Nuitka standalone/onefile — nível real de proteção contra descompilação,
    esforço de build para Windows e problemas conhecidos com Streamlit;
(d) Alternativas não citadas (Cython compilado, PyArmor — status de segurança 2026).

Responda com: tabela comparativa (proteção IP real / esforço / custo / manutenção),
veredito para meu caso, e 2 fontes por afirmação técnica.
```

## Estado da decisão

- [ ] Vitor roda o prompt acima (Perplexity/Gemini) e cola resultado em `docs/research/`
- [ ] Cross-check com esta tabela (regra: ≥2 fontes antes de decidir)
- [ ] Default se Pérez fechar caminho A antes da pesquisa: **hosted** (opção 1)
