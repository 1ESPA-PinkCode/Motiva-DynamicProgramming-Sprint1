from pathlib import Path
from time import perf_counter
 
import pandas as pd
 
from grafo import BASE, REDE, dijkstra
 
 
# ============================================================
# 1. GERAR RANKING A PARTIR DOS DADOS DA MOTIVA
# ============================================================
 
def gerar_ranking(arquivo):
    print("Lendo a planilha da Motiva. Aguarde...")
 
    dados = pd.read_excel(
        arquivo,
        sheet_name="ZMM_ANALISE_NOTAS",
        usecols=["Local de Instalação", "Sintoma"],
        engine="openpyxl"
    )
 
    print("Planilha carregada. Gerando ranking...")
 
    ranking = (
        dados.groupby("Local de Instalação")
        .agg(
            total_ocorrencias=("Local de Instalação", "size"),
            sintomas_registrados=("Sintoma", "count")
        )
        .sort_values(
            by="total_ocorrencias",
            ascending=False
        )
        .reset_index()
    )
 
    ranking.insert(0, "posicao", range(1, len(ranking) + 1))
 
    # Exemplo: SP04-6-ECR-PTA-ER16 -> PTA
    ranking["sigla_estacao"] = (
        ranking["Local de Instalação"]
        .astype(str)
        .str.split("-")
        .str[3]
    )
 
    return ranking
 
 
# ============================================================
# 2. PROGRAMAÇÃO DINÂMICA: VERSÃO RECURSIVA
# ============================================================
 
def degradacao_recursiva(incrementos, n):
    if n == 0:
        return 0
 
    return (
        degradacao_recursiva(incrementos, n - 1)
        + incrementos[n - 1]
    )
 
 
# ============================================================
# 3. PROGRAMAÇÃO DINÂMICA: VERSÃO MEMOIZADA
# ============================================================
 
def degradacao_memoizada(incrementos, n):
    memo = {}
 
    def calcular(k):
        if k == 0:
            return 0
 
        if k not in memo:
            memo[k] = calcular(k - 1) + incrementos[k - 1]
 
        return memo[k]
 
    return calcular(n)
 
 
# ============================================================
# 4. PROGRAMAÇÃO DINÂMICA: TABULAÇÃO ITERATIVA
# ============================================================
 
def degradacao_tabular(incrementos, n):
    tabela = [0] * (n + 1)
 
    for i in range(1, n + 1):
        tabela[i] = tabela[i - 1] + incrementos[i - 1]
 
    return tabela[n]
 
 
# ============================================================
# 5. COMPARAR OS TRÊS ALGORITMOS
# ============================================================
 
def comparar_algoritmos(incrementos):
    n = len(incrementos)
 
    inicio = perf_counter()
    resultado_recursivo = degradacao_recursiva(incrementos, n)
    tempo_recursivo = perf_counter() - inicio
 
    inicio = perf_counter()
    resultado_memoizado = degradacao_memoizada(incrementos, n)
    tempo_memoizado = perf_counter() - inicio
 
    inicio = perf_counter()
    resultado_tabular = degradacao_tabular(incrementos, n)
    tempo_tabular = perf_counter() - inicio
 
    print(f"Recursiva: resultado={resultado_recursivo}, "
          f"tempo={tempo_recursivo:.8f}s")
 
    print(f"Memoizada: resultado={resultado_memoizado}, "
          f"tempo={tempo_memoizado:.8f}s")
 
    print(f"Tabulacao: resultado={resultado_tabular}, "
          f"tempo={tempo_tabular:.8f}s")
 
    assert resultado_recursivo == resultado_memoizado == resultado_tabular
 
    print("Validacao: as tres versoes retornaram o mesmo resultado.")
 
    return resultado_tabular
 
 
# ============================================================
# 6. COMPARAR COM OS DADOS DA MOTIVA
# ============================================================
 
def comparar_por_escada(ranking):
    ocorrencias = ranking["total_ocorrencias"].tolist()
 
    print("\n=== COMPARACAO COM DADOS DA MOTIVA ===")
    print(f"Quantidade de locais: {len(ranking)}")
 
    return comparar_algoritmos(ocorrencias)
 
 
# ============================================================
# 7. INTEGRAR O RANKING COMPLEMENTAR
# ============================================================
 
def integrar_ranking(ranking):
    arquivo_ranking = Path("dados") / "ranking_escadas_12m.csv"
 
    # Associação entre siglas e estações existentes no grafo.
    mapa_siglas = {
        "VSO": "Vila Sonia",
        "PIN": "Pinheiros",
        "BUT": "Butanta",
        "FAL": "Faria Lima",
        "LUZ": "Luz",
        "PTA": "Paulista",
        "HIG": "Higienopolis-Mackenzie",
        "REP": "Republica",
    }
 
    ranking = ranking.copy()
 
    # Extrai o identificador, por exemplo:
    # SP04-6-ECR-PTA-ER16 -> PTA-ER16
    ranking["id_escada"] = (
        ranking["Local de Instalação"]
        .astype(str)
        .str.extract(r"ECR-([A-Z]+-ER\d+)$", expand=False)
    )
 
    if arquivo_ranking.exists():
        ranking_extra = pd.read_csv(
            arquivo_ranking,
            encoding="utf-8-sig"
        )
 
        colunas_necessarias = {
            "id_escada",
            "indice_atencao",
            "falhas_12m"
        }
 
        faltantes = colunas_necessarias - set(ranking_extra.columns)
 
        if faltantes:
            raise ValueError(
                "Colunas ausentes no ranking complementar: "
                + ", ".join(sorted(faltantes))
            )
 
        # Evita duplicar equipamentos durante a junção.
        ranking_extra = ranking_extra[
            ["id_escada", "indice_atencao", "falhas_12m"]
        ].drop_duplicates(subset="id_escada")
 
        ranking = ranking.merge(
            ranking_extra,
            on="id_escada",
            how="left"
        )
 
        ranking["indice_atencao"] = pd.to_numeric(
            ranking["indice_atencao"],
            errors="coerce"
        )
 
        ranking["falhas_12m"] = pd.to_numeric(
            ranking["falhas_12m"],
            errors="coerce"
        )
 
        # Equipamentos com índice disponível ficam primeiro;
        # os demais continuam ordenados pelo histórico de ocorrências.
        ranking = ranking.sort_values(
            by=["indice_atencao", "total_ocorrencias"],
            ascending=[False, False],
            na_position="last"
        )
 
        encontrados = ranking["indice_atencao"].notna().sum()
 
        print("\n=== INTEGRACAO DOS RANKINGS ===")
        print(f"Equipamentos com índice complementar: {encontrados}")
        print(f"Equipamentos no ranking original: {len(ranking)}")
 
    else:
        print(
            "\nArquivo ranking_escadas_12m.csv não encontrado. "
            "Será usado o ranking da planilha original."
        )
 
    ranking["estacao"] = ranking["sigla_estacao"].map(mapa_siglas)
 
    return ranking
 
 
# ============================================================
# 8. PLANEJAMENTO DO TURNO DE MANUTENÇÃO
# ============================================================
 
def planejar_turno(base, horas, ranking):
    print(f"\n=== PLANEJAMENTO DO TURNO: {horas} HORAS ===")
 
    distancias, rotas = dijkstra(base)
    minutos_disponiveis = horas * 60
 
    selecionadas = []
    tempo_total = 0
 
    # Duração provisória: 30 minutos por equipamento.
    tempo_manutencao = 30
 
    for _, equipamento in ranking.iterrows():
        estacao = equipamento["estacao"]
 
        if pd.isna(estacao):
            continue
 
        if estacao not in distancias:
            continue
 
        distancia = distancias[estacao]
 
        if distancia == float("inf"):
            continue
 
        # Estimativa de ida e volta até a estação.
        tempo_deslocamento = distancia * 2
        tempo_necessario = tempo_deslocamento + tempo_manutencao
 
        if tempo_total + tempo_necessario <= minutos_disponiveis:
            selecionadas.append({
                "equipamento": equipamento["Local de Instalação"],
                "estacao": estacao,
                "ocorrencias": equipamento["total_ocorrencias"],
                "indice_atencao": equipamento.get("indice_atencao"),
                "rota": rotas[estacao],
                "tempo_deslocamento": tempo_deslocamento,
                "tempo_manutencao": tempo_manutencao,
                "tempo_total": tempo_necessario
            })
 
            tempo_total += tempo_necessario
 
    if not selecionadas:
        print("Nenhuma manutenção foi selecionada.")
        print("Verifique as siglas e as associações com as estações.")
        return
 
    for numero, item in enumerate(selecionadas, start=1):
        print(f"\n{numero}. Equipamento: {item['equipamento']}")
        print(f"   Estação: {item['estacao']}")
        print(f"   Ocorrências históricas: {item['ocorrencias']}")
 
        if pd.notna(item["indice_atencao"]):
            print(f"   Índice de atenção: {item['indice_atencao']}")
 
        print(f"   Rota: {' -> '.join(item['rota'])}")
        print(
            f"   Deslocamento estimado: "
            f"{item['tempo_deslocamento']} minutos"
        )
        print(f"   Manutenção estimada: {item['tempo_manutencao']} minutos")
        print(f"   Tempo total estimado: {item['tempo_total']} minutos")
 
    print(f"\nEquipamentos selecionados: {len(selecionadas)}")
    print(f"Tempo utilizado: {tempo_total} minutos")
    print(f"Tempo disponível: {minutos_disponiveis} minutos")
    print(f"Tempo restante: {minutos_disponiveis - tempo_total} minutos")
 
 
# ============================================================
# 9. EXECUÇÃO PRINCIPAL
# ============================================================
 
if __name__ == "__main__":
    arquivo = Path("dados") / "ecr_09-26.XLSX"
 
    if not arquivo.exists():
        raise FileNotFoundError(
            f"Planilha não encontrada: {arquivo.resolve()}"
        )
 
    ranking = gerar_ranking(arquivo)
 
    print("\n=== TOP 10 - RANKING DA PLANILHA ===")
    print(
        ranking[
            [
                "posicao",
                "Local de Instalação",
                "total_ocorrencias",
                "sintomas_registrados",
                "sigla_estacao"
            ]
        ].head(10).to_string(index=False)
    )
 
    print("\n=== CONFERÊNCIA DAS SIGLAS ===")
    print(
        ranking["sigla_estacao"]
        .value_counts(dropna=False)
        .to_string()
    )
 
    ranking = integrar_ranking(ranking)
 
    # Salva o ranking integrado para consulta.
    caminho_saida = Path("ranking_preliminar.csv")
    ranking.to_csv(
        caminho_saida,
        index=False,
        encoding="utf-8-sig"
    )
 
    print(f"\nRanking integrado salvo em: {caminho_saida}")
    print(f"Total de locais: {len(ranking)}")
 
    print("\n=== TESTE DOS ALGORITMOS ===")
    exemplo = [2, 3, 1, 4, 2]
    comparar_algoritmos(exemplo)
 
    comparar_por_escada(ranking)
 
    planejar_turno(BASE, 8, ranking)