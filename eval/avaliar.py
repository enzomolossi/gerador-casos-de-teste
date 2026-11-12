import json
import sys
import time
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from gerador import SYSTEM, SYSTEM_BASICO, gerar_casos

PAUSA = 8  # segundos entre chamadas, por causa do limite do plano gratuito
PAUSA_RETRY = 20
MAX_RETRIES = 3
CODIGOS_RETRY = {429, 503, 504}
REPETICOES = 3


def codigo_http(erro):
    codigo = getattr(erro, "code", None)
    if codigo is None:
        codigo = getattr(erro, "status_code", None)
    try:
        return int(codigo)
    except (TypeError, ValueError):
        return None


def avaliar_tarefa(item, system, repeticao):
    texto = item["tarefa"] + " Critérios: " + "; ".join(c["descricao"] for c in item["criterios"])
    for tentativa in range(MAX_RETRIES + 1):
        try:
            casos = gerar_casos(texto, system=system)
            break
        except Exception as erro:
            codigo = codigo_http(erro)
            if codigo not in CODIGOS_RETRY or tentativa == MAX_RETRIES:
                resultado = {"id": item["id"], "repeticao": repeticao, "erro": str(erro)}
                if codigo is not None:
                    resultado["codigo_http"] = codigo
                return resultado
            print(
                f"HTTP {codigo} em {item['id']} ({repeticao}/{REPETICOES}); "
                f"nova tentativa em {PAUSA_RETRY}s ({tentativa + 1}/{MAX_RETRIES})"
            )
            time.sleep(PAUSA_RETRY)

    formato_ok = len(casos) > 0 and all(
        all(k in c for k in ("titulo", "tipo", "criterio", "gherkin"))
        and any(p in c["gherkin"] for p in ("Então", "Entao"))
        and "Dado" in c["gherkin"]
        and "Quando" in c["gherkin"]
        for c in casos
    )
    tem_negativo = any(c.get("tipo") == "negativo" for c in casos)
    texto_casos = " ".join(
        f'{c.get("titulo", "")} {c.get("criterio", "")} {c.get("gherkin", "")}'.lower()
        for c in casos
    )
    criterios_nao_cobertos = [
        criterio["descricao"]
        for criterio in item["criterios"]
        if not any(palavra.lower() in texto_casos for palavra in criterio["palavras"])
    ]
    return {
        "id": item["id"],
        "repeticao": repeticao,
        "qtd_casos": len(casos),
        "formato_ok": formato_ok,
        "tem_negativo": tem_negativo,
        "cobertura": (len(item["criterios"]) - len(criterios_nao_cobertos)) / len(item["criterios"]),
        "criterios_nao_cobertos": criterios_nao_cobertos,
    }


def resumir_tarefa(item, execucoes):
    sucesso = [execucao for execucao in execucoes if "erro" not in execucao]
    completa = len(sucesso) == REPETICOES
    media = None
    if completa:
        media = {
            "qtd_casos": sum(execucao["qtd_casos"] for execucao in sucesso) / REPETICOES,
            "formato_ok": sum(execucao["formato_ok"] for execucao in sucesso) / REPETICOES,
            "tem_negativo": sum(execucao["tem_negativo"] for execucao in sucesso) / REPETICOES,
            "cobertura": sum(execucao["cobertura"] for execucao in sucesso) / REPETICOES,
        }

    criterios_nao_cobertos = []
    for criterio in item["criterios"]:
        repeticoes = [
            execucao["repeticao"]
            for execucao in sucesso
            if criterio["descricao"] in execucao["criterios_nao_cobertos"]
        ]
        if repeticoes:
            criterios_nao_cobertos.append(
                {"descricao": criterio["descricao"], "repeticoes": repeticoes}
            )

    return {
        "sucesso": completa,
        "execucoes_sucesso": len(sucesso),
        "media": media,
        "criterios_nao_cobertos": criterios_nao_cobertos,
        "execucoes": execucoes,
    }


def resumir_comparacao(pares):
    comparaveis = [par for par in pares if par["comparavel"]]
    resumo = {"tarefas_comparadas": len(comparaveis)}
    for nome in ("system_basico", "system"):
        medias = [par[nome]["media"] for par in comparaveis]
        resumo[nome.upper()] = {
            "formato_valido": (
                sum(media["formato_ok"] for media in medias) / len(medias) if medias else None
            ),
            "com_cenario_negativo": (
                sum(media["tem_negativo"] for media in medias) / len(medias) if medias else None
            ),
            "cobertura_media": (
                sum(media["cobertura"] for media in medias) / len(medias) if medias else None
            ),
        }
    return resumo


if __name__ == "__main__":
    tarefas = json.loads(Path(__file__).with_name("tarefas.json").read_text(encoding="utf-8"))
    prompts = {"SYSTEM_BASICO": SYSTEM_BASICO, "SYSTEM": SYSTEM}
    pares = []
    total_chamadas = len(tarefas) * len(prompts) * REPETICOES
    chamada_atual = 0

    for item in tarefas:
        par = {"id": item["id"]}
        for nome, system in prompts.items():
            execucoes = []
            for repeticao in range(1, REPETICOES + 1):
                resultado = avaliar_tarefa(item, system, repeticao)
                print(f"{nome} | {resultado}")
                execucoes.append(resultado)
                chamada_atual += 1
                if chamada_atual < total_chamadas:
                    time.sleep(PAUSA)
            par[nome.lower()] = resumir_tarefa(item, execucoes)
        par["comparavel"] = par["system_basico"]["sucesso"] and par["system"]["sucesso"]
        pares.append(par)

    resumo = resumir_comparacao(pares)

    print("\n=== COMPARAÇÃO DOS PROMPTS ===")
    print(f"{'Métrica':<30}{'SYSTEM_BASICO':>18}{'SYSTEM':>18}")
    print(f"{'Tarefas comparáveis':<30}{resumo['tarefas_comparadas']:>18}{resumo['tarefas_comparadas']:>18}")
    for chave, rotulo in (
        ("formato_valido", "Formato válido"),
        ("com_cenario_negativo", "Com cenário negativo"),
        ("cobertura_media", "Cobertura média"),
    ):
        valores = [resumo[nome][chave] for nome in ("SYSTEM_BASICO", "SYSTEM")]
        textos = [f"{valor:.0%}" if valor is not None else "N/D" for valor in valores]
        print(
            f"{rotulo:<30}"
            f"{textos[0]:>18}{textos[1]:>18}"
        )

    Path(__file__).with_name("resultados.json").write_text(
        json.dumps({"por_tarefa": pares, "resumo": resumo}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )