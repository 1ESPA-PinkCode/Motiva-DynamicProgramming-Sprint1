from pathlib import Path
import pandas as pd
 
arquivo = Path("dados") / "ecr_09-26.XLSX"
 
tabela = pd.read_excel(
    arquivo,
    sheet_name="ZMM_ANALISE_NOTAS",
    usecols=[
        "Local de Instalação",
        "Início avaria",
        "Sintoma"
    ]
)
 
print("=== QUALIDADE DOS DADOS ===")
print("Total de registros:", len(tabela))
 
print("\nValores vazios:")
print(tabela.isna().sum())
 
print("\nQuantidade de locais diferentes:")
print(tabela["Local de Instalação"].nunique())
 
print("\nPeríodo das avarias:")
datas = pd.to_datetime(
    tabela["Início avaria"],
    dayfirst=True,
    errors="coerce"
)
 
print("Data mais antiga:", datas.min())
print("Data mais recente:", datas.max())
print("Datas inválidas ou vazias:", datas.isna().sum())