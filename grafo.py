"""
Rede de estações da Linha 4-Amarela como grafo.

Vértices: estações (identificadas pela sigla do dataset) + base de manutenção.
Arestas: trechos, com peso em minutos de deslocamento.

Algoritmos:
- BFS: caminho com menos trechos
- Dijkstra: caminho com menor tempo
- A*: menor tempo, usando uma heurística de distância em linha reta
"""

import heapq
import json
import math
from collections import deque
from pathlib import Path


# ============================================================
# 1. LEITURA DA REDE (JSON -> LISTA DE ADJACÊNCIA)
# ============================================================

def carregar_rede(arquivo):
    """
    Lê a rede de estações do arquivo JSON.

    Retorna:
        grafo: {sigla: {vizinho: minutos}}   (lista de adjacência)
        estacoes: {sigla: {"nome", "lat", "lon"}}
        base: sigla da base de manutenção
    """
    with open(arquivo, encoding="utf-8") as f:
        dados = json.load(f)

    estacoes = {e["sigla"]: e for e in dados["estacoes"]}
    grafo = {sigla: {} for sigla in estacoes}

    # Grafo não direcionado: o trecho vale nos dois sentidos
    for t in dados["trechos"]:
        grafo[t["de"]][t["para"]] = t["minutos"]
        grafo[t["para"]][t["de"]] = t["minutos"]

    return grafo, estacoes, dados["base"]


GRAFO, ESTACOES, BASE = carregar_rede(
    Path(__file__).parent / "rede" / "rede_estacoes.json"
)


# ============================================================
# 2. FUNÇÕES AUXILIARES
# ============================================================

def reconstruir_rota(anterior, destino):
    """Volta do destino até a origem seguindo o 'anterior' de cada vértice."""
    if destino not in anterior:
        return []
    rota = []
    atual = destino
    while atual is not None:
        rota.append(atual)
        atual = anterior[atual]
    return rota[::-1]


def tempo_da_rota(rota):
    """Soma os minutos de todos os trechos da rota."""
    return sum(GRAFO[a][b] for a, b in zip(rota, rota[1:]))


# ============================================================
# 3. BFS - MENOS TRECHOS
# ============================================================

def bfs(origem, destino):
    """
    Busca em largura: encontra a rota com MENOS TRECHOS.
    Não olha o tempo de cada trecho.
    """
    fila = deque([origem])
    anterior = {origem: None}

    while fila:
        atual = fila.popleft()
        if atual == destino:
            break
        for vizinho in GRAFO[atual]:
            if vizinho not in anterior:
                anterior[vizinho] = atual
                fila.append(vizinho)

    return reconstruir_rota(anterior, destino)


# ============================================================
# 4. DIJKSTRA - MENOR TEMPO
# ============================================================

def dijkstra(origem, destino=None):
    """
    Menor tempo da origem até cada vértice.

    Se 'destino' for informado, para quando chegar nele
    (usado para comparar com o A*).

    Retorna: (tempos, anterior, nos_visitados)
    """
    tempos = {v: math.inf for v in GRAFO}
    tempos[origem] = 0
    anterior = {origem: None}
    fila = [(0, origem)]
    visitados = 0

    while fila:
        tempo_atual, atual = heapq.heappop(fila)
        if tempo_atual > tempos[atual]:
            continue  # entrada antiga da fila, já achamos caminho melhor
        visitados += 1
        if atual == destino:
            break
        for vizinho, minutos in GRAFO[atual].items():
            novo_tempo = tempo_atual + minutos
            if novo_tempo < tempos[vizinho]:
                tempos[vizinho] = novo_tempo
                anterior[vizinho] = atual
                heapq.heappush(fila, (novo_tempo, vizinho))

    return tempos, anterior, visitados


# ============================================================
# 5. A* - MENOR TEMPO COM HEURÍSTICA
# ============================================================

def distancia_km(a, b):
    """
    Distância aproximada em linha reta entre duas estações.
    1 grau de latitude ≈ 111 km; a longitude encolhe com o cosseno da latitude.
    """
    lat_media = math.radians((ESTACOES[a]["lat"] + ESTACOES[b]["lat"]) / 2)
    dy = (ESTACOES[a]["lat"] - ESTACOES[b]["lat"]) * 111
    dx = (ESTACOES[a]["lon"] - ESTACOES[b]["lon"]) * 111 * math.cos(lat_media)
    return math.sqrt(dx ** 2 + dy ** 2)


# Velocidade do trecho mais rápido da rede (km por minuto)
VELOCIDADE_MAXIMA = max(
    distancia_km(a, b) / minutos
    for a in GRAFO
    for b, minutos in GRAFO[a].items()
)


def heuristica(estacao, destino):
    """
    Estimativa otimista do tempo restante:
    distância em linha reta / velocidade do trecho mais rápido.

    Nunca passa do tempo real (heurística ADMISSÍVEL), porque
    nenhum caminho é mais curto que a linha reta e nenhum trecho
    é mais rápido que VELOCIDADE_MAXIMA. Por isso o A* acha
    sempre o mesmo tempo ótimo que o Dijkstra.
    """
    return distancia_km(estacao, destino) / VELOCIDADE_MAXIMA


def astar(origem, destino):
    """
    A*: igual ao Dijkstra, mas a fila é ordenada por
    tempo_ate_aqui + heuristica (estimativa do que falta).

    Retorna: (tempo, rota, nos_visitados)
    """
    tempos = {origem: 0}
    anterior = {origem: None}
    fila = [(heuristica(origem, destino), origem)]
    visitados = 0

    while fila:
        _, atual = heapq.heappop(fila)
        visitados += 1
        if atual == destino:
            return tempos[destino], reconstruir_rota(anterior, destino), visitados
        for vizinho, minutos in GRAFO[atual].items():
            novo_tempo = tempos[atual] + minutos
            if novo_tempo < tempos.get(vizinho, math.inf):
                tempos[vizinho] = novo_tempo
                anterior[vizinho] = atual
                prioridade = novo_tempo + heuristica(vizinho, destino)
                heapq.heappush(fila, (prioridade, vizinho))

    return math.inf, [], visitados


# ============================================================
# 6. TESTES
# ============================================================

if __name__ == "__main__":
    print("=== LISTA DE ADJACÊNCIA ===")
    for v, vizinhos in GRAFO.items():
        print(f"{v:>5}: {vizinhos}")

    print("\n=== BFS x DIJKSTRA (SAINDO DA BASE) ===")
    tempos, anterior, _ = dijkstra(BASE)
    for est in GRAFO:
        if est == BASE:
            continue
        r_bfs = bfs(BASE, est)
        r_dij = reconstruir_rota(anterior, est)
        print(f"{est}: BFS {len(r_bfs)-1} trechos/{tempo_da_rota(r_bfs)} min "
              f"({' > '.join(r_bfs)}) | Dijkstra {len(r_dij)-1} trechos/"
              f"{tempos[est]} min ({' > '.join(r_dij)})")

    print("\n=== DIJKSTRA x A* (SAINDO DE PAULISTA) ===")
    total_dij = total_astar = 0
    for est in GRAFO:
        if est == "PTA":
            continue
        t_dij, _, vis_dij = dijkstra("PTA", est)
        t_astar, _, vis_astar = astar("PTA", est)
        assert t_astar == t_dij[est]  # mesmo tempo ótimo
        total_dij += vis_dij
        total_astar += vis_astar
        print(f"{est}: {t_astar} min | visitados Dijkstra={vis_dij}  A*={vis_astar}")
    print(f"TOTAL visitados: Dijkstra={total_dij}  A*={total_astar}")