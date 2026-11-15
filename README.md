# gerador-casos-de-teste
Projeto IA builder para uso de Q/A
# Gerador de Casos de Teste com IA

App que recebe a descrição de uma tarefa com critérios de aceite e gera casos de teste em Gherkin (cenários positivos, negativos e de borda). Feito por um profissional de QA para acelerar a criação de casos e **medir** a qualidade do que a IA gera.

## Como funciona
- Interface em Streamlit; a chamada à IA fica isolada em `gerador.py` (trocar de provedor é simples).
- API gratuita do Gemini (modelo `gemini-3.1-flash-lite`), saída em JSON estruturado.
- O prompt define o papel de analista de QA, o formato e regras de cobertura.

## Avaliação (`eval/`)
10 tarefas inventadas (login, cupom, transferência, cadastro, upload etc.), cada uma com critérios de aceite e palavras-chave esperadas nos casos gerados. Cada tarefa rodou 3 vezes por prompt, com 3 prompts diferentes. Três critérios subjetivos (ex.: "formulário simples e intuitivo") ficaram fora da nota por não serem testáveis por palavra-chave, restando 35 critérios medidos.

| Prompt | Cobertura média |
|---|---|
| Básico | 92% |
| Elaborado | 92% |
| v2 (um caso por critério + casos de borda) | 94% |

### O que aprendi
- **A métrica importa tanto quanto o prompt.** Na primeira rodada, o v2 parecia muito melhor (82% → 93%). Ao revisar, vi que a métrica contava o campo `criterio`, que o v2 preenche copiando o texto do critério, e que várias palavras-chave eram estreitas demais. Corrigi a métrica e a diferença praticamente sumiu.
- **Os três prompts ficaram equivalentes** nesta amostra (a diferença de 2 pontos está dentro do ruído).
- **Falso negativo na métrica:** o critério "transferência rejeitada não debita o saldo" aparecia como não coberto em todas as rodadas e prompts. Ao abrir os casos, vi que a IA o cobria ("o saldo deve permanecer inalterado em R$ 500,00"), mas com palavras que minha lista não previa. Corrigi a lista depois, sem rodar a avaliação de novo; por isso os números abaixo estão um pouco subestimados.
- Critérios subjetivos de aceite não são testáveis; a avaliação ajudou a identificá-los.

## Limitações
- Amostra pequena (10 tarefas, 3 rodadas, um modelo); a diferença é um indício, não uma prova.
- A cobertura é medida por palavras-chave, que é uma aproximação; o ideal seria revisão humana dos casos.
- Tarefas inventadas, e o plano gratuito da API tem limites e pode usar os dados enviados para melhorar produtos do Google.
-As palavras-chave foram ampliadas depois da primeira rodada, o que pode ter elevado a nota de todos os prompts
- A checagem por palavra-chave gera falsos negativos (a IA acerta com outro vocabulário) e falsos positivos. Uma próxima melhoria seria usar um segundo modelo como juiz, ou revisão humana de uma amostra dos casos.

## Como rodar
```
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
# crie um arquivo .env com GEMINI_API_KEY=sua_chave
streamlit run app.py
python eval/avaliar.py
```