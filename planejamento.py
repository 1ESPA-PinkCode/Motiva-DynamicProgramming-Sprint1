"""
Plano de manutenção do turno.

planejar_turno(base, horas) usa:
- o ranking de criticidade (degradacao.py -> ranking_criticidade.csv)
- as rotas de menor tempo (Dijkstra, grafo.py)

Regra (algoritmo guloso):
1. A equipe sai da base.
2. Percorre o ranking do mais crítico para o menos crítico.
3. Para cada escada, calcula: ir da posição atual até a estação
   + tempo de manutenção + voltar dessa estação até a base.
4. Se couber no tempo do turno, a escada entra no plano e a equipe
   passa a estar naquela estação. Se não couber, pula para a próxima.
5. No fim, a equipe volta para a base.

Como a equipe sai da posição ATUAL (e não sempre da base), escadas
da mesma estação não gastam tempo de deslocamento entre si.
"""

from pathlib import Path

import pandas as pd

from grafo import BASE, ESTACOES, GRAFO, dijkstra, reconstruir_rota

TEMPO_MANUTENCAO = 30  # minutos por escada (estimativa do grupo)
ARQUIVO_RANKING = Path("ranking_criticidade.csv")


def calcular_todas_as_rotas():
    """
    Roda o Dijkstra a partir de cada vértice uma única vez.
    rotas[origem] = (tempos, anterior)
    """
    return {origem: dijkstra(origem)[:2] for origem in GRAFO}


ROTAS = calcular_todas_as_rotas()


def tempo_entre(origem, destino):
    tempos, _ = ROTAS[origem]
    return tempos[destino]


def caminho_entre(origem, destino):
    _, anterior = ROTAS[origem]
    return reconstruir_rota(anterior, destino)


def planejar_turno(base, horas, ranking=None):
    """
    Monta o plano do turno.

    Parâmetros:
        base: sigla da base de manutenção (ex.: "BASE")
        horas: duração do turno
        ranking: DataFrame do ranking; se não for passado, lê o CSV

    Retorna: (plano, minutos_usados), onde plano é uma lista de
    dicionários na ordem de atendimento.
    """
    if ranking is None:
        ranking = pd.read_csv(ARQUIVO_RANKING)

    limite = horas * 60
    usado = 0
    atual = base
    plano = []

    for _, escada in ranking.iterrows():
        estacao = escada["estacao"]
        if estacao not in GRAFO:
            continue  # estação fora da rede modelada

        ida = tempo_entre(atual, estacao)
        volta = tempo_entre(estacao, base)

        # Só aceita se ainda der tempo de voltar para a base depois
        if usado + ida + TEMPO_MANUTENCAO + volta <= limite:
            plano.append({
                "ordem": len(plano) + 1,
                "id_escada": escada["id_escada"],
                "estacao": estacao,
                "degradacao": escada["degradacao"],
                "deslocamento_min": ida,
                "rota": caminho_entre(atual, estacao),
            })
            usado += ida + TEMPO_MANUTENCAO
            atual = estacao

    # Volta para a base no fim do turno
    volta = tempo_entre(atual, base)
    plano.append({
        "ordem": len(plano) + 1,
        "id_escada": "(retorno)",
        "estacao": base,
        "degradacao": None,
        "deslocamento_min": volta,
        "rota": caminho_entre(atual, base),
    })
    usado += volta

    return plano, usado


def imprimir_plano(plano, usado, horas):
    """Mostra o plano do turno de forma legível."""
    print(f"=== PLANO DO TURNO ({horas} h = {horas * 60} min) ===")
    for item in plano:
        rota = " > ".join(item["rota"]) if len(item["rota"]) > 1 else "(mesma estação)"
        if item["id_escada"] == "(retorno)":
            print(f"{item['ordem']:>2}. Retorno à base | {item['deslocamento_min']} min | {rota}")
        else:
            nome = ESTACOES[item["estacao"]]["nome"]
            print(f"{item['ordem']:>2}. {item['id_escada']} ({nome}) | "
                  f"degradação {item['degradacao']} | "
                  f"deslocamento {item['deslocamento_min']} min + "
                  f"manutenção {TEMPO_MANUTENCAO} min | {rota}")

    escadas = len(plano) - 1
    deslocamento = sum(i["deslocamento_min"] for i in plano)
    print(f"\nEscadas atendidas: {escadas}")
    print(f"Tempo em manutenção: {escadas * TEMPO_MANUTENCAO} min")
    print(f"Tempo em deslocamento: {deslocamento} min")
    print(f"Total usado: {usado} de {horas * 60} min")


if __name__ == "__main__":
    for horas in [4, 8]:
        plano, usado = planejar_turno(BASE, horas)
        imprimir_plano(plano, usado, horas)
        print()