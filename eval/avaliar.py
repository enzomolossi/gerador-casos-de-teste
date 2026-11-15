import json
import sys
import time
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from gerador import gerar_casos, SYSTEM, SYSTEM_BASICO, SYSTEM_V2

PROMPTS = {"basico": SYSTEM_BASICO, "atual": SYSTEM, "v2": SYSTEM_V2}
RODADAS = 3        # quantas vezes roda cada tarefa por prompt
PAUSA = 6          # segundos entre chamadas (limite do plano gratuito)
TENTATIVAS = 3     # tentativas em caso de erro temporário
ESPERA_ERRO = 20   # segundos de espera antes de tentar de novo


def chamar(texto, system):
    for t in range(TENTATIVAS):
        try:
            return gerar_casos(texto, system)
        except Exception as e:
            temporario = any(c in str(e) for c in ("503", "429", "504")) or isinstance(
                e, (ValueError, KeyError)
            )
            if temporario and t < TENTATIVAS - 1:
                time.sleep(ESPERA_ERRO)
                continue
            raise


def avaliar_rodada(item, system):
    texto = item["tarefa"] + " Critérios: " + "; ".join(c["descricao"] for c in item["criterios"])
    casos = chamar(texto, system)
    formato_ok = len(casos) > 0 and all(
        all(k in c for k in ("titulo", "tipo", "criterio", "gherkin"))
        and "Dado" in c["gherkin"]
        and "Quando" in c["gherkin"]
        and ("Então" in c["gherkin"] or "Entao" in c["gherkin"])
        for c in casos
    )
    tem_negativo = any(c.get("tipo") == "negativo" for c in casos)
    # Só título e Gherkin: o campo "criterio" repete o texto do critério (principalmente no v2)
    # e inflaria a cobertura.
    texto_casos = " ".join(
        f'{c.get("titulo", "")} {c.get("gherkin", "")}'.lower() for c in casos
    )
    medidos = [c for c in item["criterios"] if c.get("testavel", True)]
    faltou = [
        crit["descricao"]
        for crit in medidos
        if not any(p.lower() in texto_casos for p in crit["palavras"])
    ]
    return {
        "qtd_casos": len(casos),
        "formato_ok": formato_ok,
        "tem_negativo": tem_negativo,
        "cobertura": 1 - len(faltou) / len(medidos),
        "nao_cobertos": faltou,
    }


def media(valores):
    return sum(valores) / len(valores) if valores else 0


if __name__ == "__main__":
    tarefas = json.loads(Path(__file__).with_name("tarefas.json").read_text(encoding="utf-8"))
    resultados = {}

    for item in tarefas:
        resultados[item["id"]] = {}
        for nome, system in PROMPTS.items():
            rodadas, erros = [], 0
            for _ in range(RODADAS):
                try:
                    rodadas.append(avaliar_rodada(item, system))
                except Exception as e:
                    erros += 1
                    print(f"  erro ({item['id']}, {nome}): {str(e)[:80]}")
                time.sleep(PAUSA)
            resultados[item["id"]][nome] = {"rodadas": rodadas, "erros": erros}
            if rodadas:
                cob = media([r["cobertura"] for r in rodadas])
                print(f"{item['id']:28} {nome:7} cobertura {cob:.0%} ({len(rodadas)}/{RODADAS} rodadas ok)")

    # Comparação justa: só tarefas em que TODOS os prompts tiveram pelo menos 1 rodada ok
    ids_validos = [
        i for i, por_prompt in resultados.items()
        if all(por_prompt[p]["rodadas"] for p in PROMPTS)
    ]
    print(f"\n=== COMPARAÇÃO ({len(ids_validos)}/{len(tarefas)} tarefas válidas em todos os prompts) ===")
    print(f"{'Métrica':26}" + "".join(f"{p:>10}" for p in PROMPTS))

    def linha(titulo, campo):
        valores = []
        for p in PROMPTS:
            por_tarefa = [
                media([float(r[campo]) for r in resultados[i][p]["rodadas"]]) for i in ids_validos
            ]
            valores.append(media(por_tarefa))
        print(f"{titulo:26}" + "".join(f"{v:>10.0%}" for v in valores))

    linha("Formato válido", "formato_ok")
    linha("Com cenário negativo", "tem_negativo")
    linha("Cobertura média", "cobertura")

    print("\n=== CRITÉRIOS NÃO COBERTOS (quantas rodadas falharam) ===")
    for i in ids_validos:
        for p in PROMPTS:
            contagem = {}
            for r in resultados[i][p]["rodadas"]:
                for d in r["nao_cobertos"]:
                    contagem[d] = contagem.get(d, 0) + 1
            for d, n in contagem.items():
                print(f"{i} | {p} | {d} ({n}/{len(resultados[i][p]['rodadas'])} rodadas)")

    Path(__file__).with_name("resultados.json").write_text(
        json.dumps(resultados, ensure_ascii=False, indent=2), encoding="utf-8"
    )