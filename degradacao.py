"""
Degradação acumulada de cada escada rolante com Programação Dinâmica.

Dados: notas de falha (tipo Z1) da planilha da Motiva, últimos 12 meses.
Cada nota de falha é uma "leitura" da escada, em ordem de data.

Recorrência (D = degradação acumulada depois da leitura i):

    D(0) = 0
    D(1) = peso(1)
    D(i) = D(i-1) + peso(i)                                  se a falha NÃO é reincidente
    D(i) = D(i-1) + peso(i) + FATOR * (D(i-1) - D(i-2))      se a falha É reincidente

- peso(i) = 2 se a escada ficou indisponível na falha, 1 caso contrário
- reincidente = a falha aconteceu até 7 dias depois da anterior
- D(i-1) - D(i-2) é o impacto da falha anterior: se o problema voltou
  em menos de 7 dias, ele não foi resolvido, e a falha nova herda
  parte (FATOR) do impacto da anterior.

Como D(i) depende de D(i-1) E de D(i-2), a recursão pura recalcula os
mesmos subproblemas muitas vezes (como Fibonacci). Memoização e tabulação
calculam cada D(i) uma única vez.
"""

import sys
from pathlib import Path
from time import perf_counter

import pandas as pd

PESO_NORMAL = 1
PESO_INDISPONIVEL = 2
DIAS_REINCIDENCIA = 7
FATOR = 0.5

ARQUIVO_MOTIVA = Path("dados") / "ecr_09-26.XLSX"
ARQUIVO_FALHAS = Path("dados") / "falhas_12m.csv"


# ============================================================
# 1. PREPARAÇÃO DOS DADOS
# ============================================================

def preparar_falhas(arquivo_excel=ARQUIVO_MOTIVA, arquivo_csv=ARQUIVO_FALHAS):
    """
    Lê a planilha da Motiva e salva um CSV só com as falhas dos últimos
    12 meses. A planilha é grande; o CSV evita ler o Excel toda vez.

    Colunas do CSV: id_escada, estacao, data_hora, peso
    """
    if arquivo_csv.exists():
        return pd.read_csv(arquivo_csv, parse_dates=["data_hora"])

    print("Lendo a planilha da Motiva (pode levar 1-2 minutos)...")
    notas = pd.read_excel(
        arquivo_excel,
        sheet_name="ZMM_ANALISE_NOTAS",
        usecols=["Tipo de Nota", "Local de Instalação", "Início avaria",
                 "Hora início avaria", "Indisponível"],
        dtype=str,
    )

    # Z1 = nota de falha
    falhas = notas[notas["Tipo de Nota"] == "Z1"].copy()

    # SP04-6-ECR-PTA-ER15 -> id_escada = PTA-ER15, estacao = PTA
    falhas["id_escada"] = falhas["Local de Instalação"].str.extract(
        r"ECR-([A-Z]+-ER\d+)")[0]
    falhas = falhas.dropna(subset=["id_escada"])  # notas sem escada específica
    falhas["estacao"] = falhas["id_escada"].str.split("-").str[0]

    falhas["data_hora"] = pd.to_datetime(
        falhas["Início avaria"] + " " + falhas["Hora início avaria"].fillna("00:00:00"),
        dayfirst=True, errors="coerce",
    )
    falhas = falhas.dropna(subset=["data_hora"])

    # Mesma janela do grupo de Data Science: 365 dias até a última nota
    inicio = falhas["data_hora"].max().normalize() - pd.Timedelta(days=365)
    falhas = falhas[falhas["data_hora"] >= inicio]

    falhas["peso"] = falhas["Indisponível"].eq("X").map(
        {True: PESO_INDISPONIVEL, False: PESO_NORMAL})

    falhas = falhas[["id_escada", "estacao", "data_hora", "peso"]]
    falhas = falhas.sort_values(["id_escada", "data_hora"])

    arquivo_csv.parent.mkdir(exist_ok=True)
    falhas.to_csv(arquivo_csv, index=False)
    return falhas


def montar_leituras(falhas):
    """
    Monta, para cada escada, as listas de leituras em ordem de data:
        {id_escada: (pesos, reincidentes)}
    reincidentes[i] = True se a falha i veio até 7 dias depois da i-1.
    """
    leituras = {}
    for id_escada, grupo in falhas.groupby("id_escada"):
        grupo = grupo.sort_values("data_hora")
        pesos = grupo["peso"].tolist()
        intervalo = grupo["data_hora"].diff()
        reincidentes = (intervalo <= pd.Timedelta(days=DIAS_REINCIDENCIA)).tolist()
        leituras[id_escada] = (pesos, reincidentes)
    return leituras


# ============================================================
# 2. VERSÃO 1 - RECURSIVA PURA
# ============================================================

contador = {"chamadas": 0}


def degradacao_recursiva(pesos, reinc, i):
    """
    Aplica a recorrência diretamente. Recalcula D(i-2) dentro de D(i-1)
    e de novo em D(i): o número de chamadas cresce exponencialmente.
    """
    contador["chamadas"] += 1
    if i == 0:
        return 0
    if i == 1:
        return pesos[0]

    anterior = degradacao_recursiva(pesos, reinc, i - 1)
    d = anterior + pesos[i - 1]
    if reinc[i - 1]:
        d += FATOR * (anterior - degradacao_recursiva(pesos, reinc, i - 2))
    return d


# ============================================================
# 3. VERSÃO 2 - RECURSIVA COM MEMOIZAÇÃO (DICIONÁRIO)
# ============================================================

def degradacao_memoizada(pesos, reinc, i, memo=None):
    """
    Mesma recursão, mas guarda cada D(i) num dicionário.
    Se já foi calculado, devolve na hora: cada D(i) é calculado uma vez.
    """
    if memo is None:
        memo = {}
    contador["chamadas"] += 1
    if i in memo:
        return memo[i]
    if i == 0:
        return 0
    if i == 1:
        return pesos[0]

    anterior = degradacao_memoizada(pesos, reinc, i - 1, memo)
    d = anterior + pesos[i - 1]
    if reinc[i - 1]:
        d += FATOR * (anterior - degradacao_memoizada(pesos, reinc, i - 2, memo))
    memo[i] = d
    return d


# ============================================================
# 4. VERSÃO 3 - ITERATIVA COM TABULAÇÃO
# ============================================================

def degradacao_tabular(pesos, reinc, n):
    """
    Preenche uma tabela de baixo para cima: D[0], D[1], ..., D[n].
    Sem recursão (não estoura a pilha) e cada posição é calculada uma vez.
    Também devolve a tabela inteira: é a curva de degradação da escada.
    """
    D = [0.0] * (n + 1)
    if n >= 1:
        D[1] = pesos[0]
    for i in range(2, n + 1):
        D[i] = D[i - 1] + pesos[i - 1]
        if reinc[i - 1]:
            D[i] += FATOR * (D[i - 1] - D[i - 2])
    return D[n], D


# ============================================================
# 5. MEDIÇÃO DAS TRÊS VERSÕES
# ============================================================

def medir(funcao, *args, repeticoes=3):
    """Executa a função algumas vezes; devolve (resultado, menor tempo, chamadas)."""
    melhor = float("inf")
    for _ in range(repeticoes):
        contador["chamadas"] = 0
        inicio = perf_counter()
        resultado = funcao(*args)
        melhor = min(melhor, perf_counter() - inicio)
    return resultado, melhor, contador["chamadas"]


def comparar_versoes(pesos, reinc, tamanhos):
    """
    Mede as três versões para vários tamanhos n (primeiras n leituras).
    A recursiva pura só é medida até n=25, depois fica lenta demais.
    """
    linhas = []
    for n in tamanhos:
        r_mem, t_mem, c_mem = medir(degradacao_memoizada, pesos, reinc, n)
        (r_tab, _), t_tab, _ = medir(degradacao_tabular, pesos, reinc, n)

        if n <= 25:
            r_rec, t_rec, c_rec = medir(degradacao_recursiva, pesos, reinc, n)
            assert abs(r_rec - r_mem) < 1e-9
        else:
            r_rec, t_rec, c_rec = None, None, None

        assert abs(r_mem - r_tab) < 1e-9  # as versões dão o mesmo valor

        linhas.append({
            "n": n,
            "degradacao": round(r_tab, 2),
            "tempo_recursiva_ms": None if t_rec is None else t_rec * 1000,
            "chamadas_recursiva": c_rec,
            "tempo_memoizada_ms": t_mem * 1000,
            "chamadas_memoizada": c_mem,
            "tempo_tabular_ms": t_tab * 1000,
        })
    return pd.DataFrame(linhas)


# ============================================================
# 6. RANKING DE CRITICIDADE
# ============================================================

def gerar_ranking(leituras):
    """Calcula a degradação de todas as escadas (tabulação) e ordena."""
    linhas = []
    for id_escada, (pesos, reinc) in leituras.items():
        d, _ = degradacao_tabular(pesos, reinc, len(pesos))
        linhas.append({
            "id_escada": id_escada,
            "estacao": id_escada.split("-")[0],
            "falhas_12m": len(pesos),
            "reincidentes": sum(reinc),
            "degradacao": round(d, 2),
        })
    ranking = pd.DataFrame(linhas).sort_values("degradacao", ascending=False)
    ranking.insert(0, "posicao", range(1, len(ranking) + 1))
    return ranking.reset_index(drop=True)


# ============================================================
# 7. EXECUÇÃO
# ============================================================

if __name__ == "__main__":
    sys.setrecursionlimit(5000)  # a memoizada desce até n níveis

    falhas = preparar_falhas()
    leituras = montar_leituras(falhas)
    print(f"Falhas nos últimos 12 meses: {len(falhas)} | escadas: {len(leituras)}")
    print(f"Período: {falhas['data_hora'].min():%d/%m/%Y} "
          f"a {falhas['data_hora'].max():%d/%m/%Y}")

    # Exemplo pequeno, fácil de conferir à mão
    pesos = [1, 2, 1, 1]
    reinc = [False, True, False, True]
    print("\nExemplo à mão:", degradacao_tabular(pesos, reinc, 4)[1])

    # Medição com a escada que mais falhou
    escada = max(leituras, key=lambda e: len(leituras[e][0]))
    p, r = leituras[escada]
    print(f"\n=== MEDIÇÃO - {escada} ({len(p)} leituras) ===")
    tamanhos = [5, 10, 15, 20, 25, 50, 100, len(p)]
    print(comparar_versoes(p, r, tamanhos).to_string(index=False))

    ranking = gerar_ranking(leituras)
    print("\n=== TOP 15 - RANKING DE CRITICIDADE ===")
    print(ranking.head(15).to_string(index=False))
    ranking.to_csv("ranking_criticidade.csv", index=False)