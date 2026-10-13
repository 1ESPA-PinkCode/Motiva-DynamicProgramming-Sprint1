from collections import deque
import heapq
 
 
# ============================================================
# 1. ESTACOES E BASE DE MANUTENCAO
# ============================================================
 
ESTACOES = [
    "Vila Sonia",
    "Sao Paulo-Morumbi",
    "Butanta",
    "Pinheiros",
    "Faria Lima",
    "Fradique Coutinho",
    "Oscar Freire",
    "Paulista",
    "Higienopolis-Mackenzie",
    "Republica",
    "Luz"
]
 
BASE = "Patio de Manutencao Vila Sonia"
 
# Tempos ilustrativos para testar os algoritmos.
# Substituir por tempos validados antes da entrega final.
TEMPOS_EXEMPLO = [4, 3, 5, 4, 3, 4, 5, 4, 4, 6]
TEMPO_BASE_VILA_SONIA = 5
 
# ============================================================
# 2. CRIACAO DO GRAFO
# ============================================================
 
REDE = {estacao: {} for estacao in ESTACOES}
REDE[BASE] = {}
 
REDE[BASE]["Vila Sonia"] = TEMPO_BASE_VILA_SONIA
REDE["Vila Sonia"][BASE] = TEMPO_BASE_VILA_SONIA
 
for i in range(len(ESTACOES) - 1):
    origem = ESTACOES[i]
    destino = ESTACOES[i + 1]
    tempo = TEMPOS_EXEMPLO[i]
 
    REDE[origem][destino] = tempo
    REDE[destino][origem] = tempo
 
 
# ============================================================
# 3. BFS - CAMINHO COM MENOS TRECHOS
# ============================================================
 
def bfs(origem, destino):
    """Retorna o caminho com menor quantidade de arestas."""
 
    if origem not in REDE or destino not in REDE:
        return []
 
    fila = deque([origem])
    anteriores = {origem: None}
 
    while fila:
        atual = fila.popleft()
 
        if atual == destino:
            break
 
        for vizinho in REDE[atual]:
            if vizinho not in anteriores:
                anteriores[vizinho] = atual
                fila.append(vizinho)
 
    if destino not in anteriores:
        return []
 
    caminho = []
    atual = destino
 
    while atual is not None:
        caminho.append(atual)
        atual = anteriores[atual]
 
    return caminho[::-1]
 
 
# ============================================================
# 4. DIJKSTRA - MENOR TEMPO DE DESLOCAMENTO
# ============================================================
 
def dijkstra(origem):
    """Calcula as menores distâncias e reconstrói todas as rotas."""
 
    if origem not in REDE:
        raise ValueError(f"Origem inexistente no grafo: {origem}")
 
    distancias = {
        estacao: float("inf")
        for estacao in REDE
    }
 
    anteriores = {
        estacao: None
        for estacao in REDE
    }
 
    distancias[origem] = 0
    fila = [(0, origem)]
 
    while fila:
        distancia, atual = heapq.heappop(fila)
 
        if distancia > distancias[atual]:
            continue
 
        for vizinho, tempo in REDE[atual].items():
            nova_distancia = distancia + tempo
 
            if nova_distancia < distancias[vizinho]:
                distancias[vizinho] = nova_distancia
                anteriores[vizinho] = atual
 
                heapq.heappush(
                    fila,
                    (nova_distancia, vizinho)
                )
 
    rotas = {}
 
    for destino in REDE:
        if distancias[destino] == float("inf"):
            rotas[destino] = []
            continue
 
        caminho = []
        atual = destino
 
        while atual is not None:
            caminho.append(atual)
            atual = anteriores[atual]
 
        rotas[destino] = caminho[::-1]
 
    return distancias, rotas
 
 
# ============================================================
# 5. A* - BUSCA COM HEURISTICA
# ============================================================
 
def astar(origem, destino):
    """
    Encontra uma rota de menor custo usando A*.
 
    A heuristica utiliza a distancia em numero de trechos
    ate o destino multiplicada pelo menor peso de aresta.
    Como o grafo atual e linear, ela e admissivel para as
    estacoes dessa linha.
    """
 
    if origem not in REDE or destino not in REDE:
        return float("inf"), []
 
    if origem == destino:
        return 0, [origem]
 
    menor_tempo = min(
        tempo
        for vizinhos in REDE.values()
        for tempo in vizinhos.values()
    )
 
    # Posicao das estacoes na linha.
    posicoes = {
        estacao: i
        for i, estacao in enumerate(ESTACOES)
    }
 
    def heuristica(estacao):
        # A base fica imediatamente antes de Vila Sonia
        # no modelo usado para este teste.
        if estacao == BASE:
            posicao_atual = -1
        else:
            posicao_atual = posicoes[estacao]
 
        if destino == BASE:
            posicao_destino = -1
        else:
            posicao_destino = posicoes[destino]
 
        quantidade_trechos = abs(
            posicao_atual - posicao_destino
        )
 
        return quantidade_trechos * menor_tempo
 
    fila = [(heuristica(origem), 0, origem)]
    anteriores = {origem: None}
    custos = {origem: 0}
 
    while fila:
        _, custo_atual, atual = heapq.heappop(fila)
 
        if custo_atual > custos.get(atual, float("inf")):
            continue
 
        if atual == destino:
            break
 
        for vizinho, tempo in REDE[atual].items():
            novo_custo = custo_atual + tempo
 
            if novo_custo < custos.get(vizinho, float("inf")):
                custos[vizinho] = novo_custo
                anteriores[vizinho] = atual
 
                prioridade = novo_custo + heuristica(vizinho)
 
                heapq.heappush(
                    fila,
                    (prioridade, novo_custo, vizinho)
                )
 
    if destino not in custos:
        return float("inf"), []
 
    caminho = []
    atual = destino
 
    while atual is not None:
        caminho.append(atual)
        atual = anteriores[atual]
 
    return custos[destino], caminho[::-1]
 
 
# ============================================================
# 6. TESTES E COMPARACAO DOS ALGORITMOS
# ============================================================
 
if __name__ == "__main__":
 
    print("=== DIJKSTRA: MENOR TEMPO DESDE A BASE ===")
 
    distancias, rotas = dijkstra(BASE)
 
    for estacao in ESTACOES:
        print(f"\nDestino: {estacao}")
        print(f"Tempo ilustrativo: {distancias[estacao]} minutos")
        print("Rota:", " -> ".join(rotas[estacao]))
 
    destino = "Luz"
 
    print("\n=== BFS: MENOR NUMERO DE TRECHOS ===")
 
    rota_bfs = bfs(BASE, destino)
    print("Rota:", " -> ".join(rota_bfs))
    print(f"Quantidade de trechos: {len(rota_bfs) - 1}")
 
    print("\n=== A*: ROTA ATE LUZ ===")
 
    custo_astar, rota_astar = astar(BASE, destino)
 
    print(f"Tempo ilustrativo: {custo_astar} minutos")
    print("Rota:", " -> ".join(rota_astar))
 
    print("\n=== COMPARACAO: DIJKSTRA X A* ===")
 
    print(f"Dijkstra: {distancias[destino]} minutos")
    print(f"A*: {custo_astar} minutos")
    print("Mesmo custo?", distancias[destino] == custo_astar)
 
    print("\n=== VALIDACAO DE TODAS AS ESTACOES ===")
 
    for estacao in ESTACOES:
        custo, rota = astar(BASE, estacao)
 
        correto = custo == distancias[estacao]
 
        print(
            f"{estacao}: "
            f"Dijkstra={distancias[estacao]} min | "
            f"A*={custo} min | "
            f"Correto={correto}"
        )
 
        assert correto, f"Divergencia entre algoritmos: {estacao}"
 
    print("\nTodos os testes de custo passaram.")