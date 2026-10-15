# Escadas Rolantes: Manutenção Orientada por Dados

**Challenge Motiva + FIAP 2026/2027 · Dynamic Programming · Sprint 1**

Squad **PinkCode** – 2ESPR

| Integrante | RM |
|---|---|
| Lara Mofid Essa Alssabak | _RM567947_ |
| Maria Luisa Boucinhas Franco | _RM567355_ |
| Maria Luiza Kochnoff da Matta | _RM568459_ |
| Roberta Moreira dos Santos | _RM567825_ |

## Sobre o projeto

A partir do histórico de falhas das escadas rolantes da Linha 4-Amarela (ViaQuatro/Motiva), o projeto:

1. calcula a **degradação acumulada** de cada escada com Programação Dinâmica (três versões);
2. gera um **ranking de criticidade**;
3. modela a rede de estações como **grafo** e calcula rotas com **BFS, Dijkstra e A\***;
4. monta o **plano do turno** de manutenção com `planejar_turno(base, horas)`.

O `notebook.ipynb` executa tudo do início ao fim e já está salvo com os resultados.

## Estrutura

```
├── notebook.ipynb          # execução completa com resultados e interpretações
├── degradacao.py           # preparação dos dados, 3 versões da degradação, medição e ranking
├── grafo.py                # leitura da rede, BFS, Dijkstra e A*
├── planejamento.py         # planejar_turno(base, horas)
├── rede/
│   └── rede_estacoes.json  # rede de estações (vértices e trechos)
└── dados/                  # dataset da Motiva (não enviado ao GitHub)
    ├── ecr_09-26.XLSX
    └── falhas_12m.csv      # gerado na primeira execução
```

## Como executar

1. Coloque a planilha da Motiva em `dados/ecr_09-26.XLSX`.
2. Instale as dependências: `pip install pandas openpyxl matplotlib`
3. Abra e execute o `notebook.ipynb`.

Também é possível rodar cada parte separadamente: `python degradacao.py`, `python grafo.py`, `python planejamento.py` (nessa ordem, porque o planejamento usa o ranking gerado pela degradação).

> O dataset da Motiva não está no repositório por ser material fornecido pela empresa. Os resultados podem ser conferidos no notebook já executado.

## 1. Dados

O dataset fornecido não traz leituras de sensores (vibração, temperatura etc.). Ele traz as **notas de manutenção** de cada escada (aba `ZMM_ANALISE_NOTAS`). Por isso adaptamos o conceito de "leitura":

- usamos as notas do tipo **Z1 (falha)**;
- cada falha é uma **leitura** da escada, em ordem de data;
- janela dos **últimos 12 meses** (22/09/2025 a 22/09/2026): 8.591 falhas em 197 escadas;
- `peso = 2` se a escada ficou indisponível na falha, `peso = 1` caso contrário.

## 2. Degradação acumulada (Programação Dinâmica)

```
D(0) = 0
D(1) = peso(1)
D(i) = D(i-1) + peso(i)                              falha normal
D(i) = D(i-1) + peso(i) + 0,5 · (D(i-1) − D(i-2))    falha reincidente (até 7 dias após a anterior)
```

Se a falha volta em menos de 7 dias, o problema não foi resolvido: a falha nova herda metade do impacto da anterior (`D(i-1) − D(i-2)`).

Como `D(i)` depende de `D(i-1)` e `D(i-2)`, há subproblemas sobrepostos, como em Fibonacci.

| Versão | Como funciona | Complexidade |
|---|---|---|
| `degradacao_recursiva` | aplica a fórmula direto, recalcula valores repetidos | exponencial |
| `degradacao_memoizada` | recursão + dicionário com os valores já calculados | linear |
| `degradacao_tabular` | preenche a tabela `D[0..n]` com um laço | linear, sem recursão |

### Resultados da medição (escada LUZ-ER04, 147 leituras)

| n | chamadas recursiva | chamadas memoizada |
|---|---|---|
| 10 | 177 | 19 |
| 15 | 1.973 | 29 |
| 20 | 21.891 | 39 |
| 25 | 242.785 | 49 |
| 147 | inviável | 286 |

**Interpretação:** a recursiva pura multiplica as chamadas por cerca de 11 a cada 5 leituras, por isso só foi medida até n = 25. Memoização e tabulação crescem de forma linear; a tabulação é a mais rápida e não corre risco de estourar a pilha, então foi a usada no ranking. As três versões dão o mesmo resultado.

## 3. Ranking de criticidade

| Posição | Escada | Falhas (12 meses) | Degradação |
|---|---|---|---|
| 1 | LUZ-ER04 | 147 | 537,52 |
| 2 | VSO-ER08 | 136 | 500,50 |
| 3 | PIN-ER28 | 138 | 496,12 |
| 4 | PIN-ER24 | 131 | 473,00 |
| 5 | PTA-ER17 | 127 | 431,87 |

**Interpretação:**
- Pinheiros tem 6 das 15 escadas mais críticas.
- A degradação acompanha de perto o número de falhas (correlação de Spearman ≈ 1). A reincidência em até 7 dias é comum em quase todas as escadas, então aumenta a degradação de todas de forma parecida; testamos janelas de 1 e 2 dias e o ranking quase não mudou. Neste dataset, **o volume de falhas é o principal fator de criticidade**.

## 4. Rede de estações (grafo)

Arquivo `rede/rede_estacoes.json`, carregado como **lista de adjacência**.

- **Vértices:** 11 estações da Linha 4-Amarela, o Terminal Vila Sônia (`TVS`) e a base de manutenção (Pátio Vila Sônia). As siglas são as mesmas do dataset, então cada escada se liga à sua estação pelo código (`PIN-ER24` → `PIN`).
- **Arestas:** trechos com peso em minutos. Trem entre estações, a pé até a base e dois trechos de viatura (base → Butantã, base → Pinheiros).
- Os tempos são **estimativas do grupo** e as coordenadas são aproximadas.

### BFS × Dijkstra

| Destino | BFS | Dijkstra |
|---|---|---|
| Pinheiros | 1 trecho, 22 min (viatura) | 4 trechos, 13 min (trem) |
| Luz | 8 trechos, 36 min | 11 trechos, 27 min |

**Interpretação:** o BFS minimiza trechos e escolhe a viatura; o Dijkstra minimiza tempo e escolhe o trem. Para planejar a manutenção usamos o Dijkstra.

### A\* × Dijkstra

Heurística: `h(n) = distância em linha reta até o destino / velocidade do trecho mais rápido da rede`.

É **admissível**: nenhum caminho é mais curto que a linha reta e nenhum trecho é mais rápido que a velocidade máxima, então `h(n)` nunca passa do tempo real. Por isso o A\* encontra sempre o mesmo tempo ótimo do Dijkstra.

**Resultado (saindo de Paulista para todos os destinos):** mesmo tempo em todos, com **66 estações visitadas pelo A\* contra 90 do Dijkstra** (cerca de 27% a menos). Saindo da base, que fica numa ponta da linha, a vantagem é pequena, porque quase todas as estações já estão no caminho.

## 5. Plano do turno: `planejar_turno(base, horas)`

Algoritmo guloso: percorre o ranking do mais crítico para o menos crítico e aceita a escada se couber no turno o tempo de ida **a partir da posição atual**, mais 30 min de manutenção, mais a volta para a base.

**Turno de 8 h:** 12 escadas atendidas, 360 min de manutenção, 118 min de deslocamento (478 de 480 min).

**Interpretação:**
- Escadas da mesma estação são atendidas em sequência, sem deslocamento.
- O tempo de volta é reservado antes de aceitar cada escada.
- **Limitação:** seguir o ranking à risca às vezes faz a equipe atravessar a linha (Luz → Vila Sônia). Escolhemos priorizar a criticidade em vez da distância.

## Limitações e próximos passos

- O dataset tem notas de falha, não leituras de sensores; quando houver dados de sensores, eles podem entrar como peso de cada leitura.
- Tempos de deslocamento e de manutenção são estimativas.
- No plano do turno, entre escadas com criticidade parecida, escolher a mais próxima reduziria o deslocamento.