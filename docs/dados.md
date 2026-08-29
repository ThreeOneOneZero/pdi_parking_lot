# Conjunto de Imagens — PKLot

Documento de caracterização do conjunto de dados adotado no projeto.
Complementa a [proposta técnica](proposta.md), seção 6.

---

## 1. Identificação e origem

| Campo | Valor |
|---|---|
| Nome | PKLot — A Robust Dataset for Parking Lot Classification |
| Instituições | Universidade Federal do Paraná (UFPR) e Pontifícia Universidade Católica do Paraná (PUCPR) |
| Página oficial | <https://web.inf.ufpr.br/vri/databases/parking-lot-database/> |
| Publicação associada | Almeida et al., *Expert Systems with Applications*, 42(11):4937–4949, 2015 |
| Ano de coleta | 2012–2013 |
| Forma de obtenção | Download direto do arquivo `PKLot.tar.gz` a partir do site do laboratório VRI/UFPR |

## 2. Licença e condições de uso

O conjunto é distribuído sob **Creative Commons Attribution 4.0 International (CC BY 4.0)**.

O uso para pesquisa é permitido, **condicionado à citação** do artigo original:

> ALMEIDA, P.; OLIVEIRA, L. S.; SILVA JR., E.; BRITTO JR., A.; KOERICH, A.
> PKLot — A robust dataset for parking lot classification.
> *Expert Systems with Applications*, 42(11):4937–4949, 2015.

**Redistribuição neste repositório:** as imagens **não são versionadas**. O arquivo completo tem
aproximadamente 4,9 GB compactado, o que é incompatível com um repositório Git. O diretório `data/`
está no `.gitignore` e as instruções de obtenção estão na seção 6 deste documento. Apenas figuras
derivadas selecionadas (painéis de recortes, histogramas) são versionadas em `images/results/`,
com atribuição.

## 3. Organização

O conjunto vem em duas formas complementares:

**`PKLot/`** — frames completos com anotação.

```text
PKLot/
└── <estacionamento>/        PUCPR | UFPR04 | UFPR05
    └── <clima>/             Sunny | Cloudy | Rainy
        └── <AAAA-MM-DD>/
            ├── <AAAA-MM-DD_HH_MM_SS>.jpg     frame 1280x720
            └── <AAAA-MM-DD_HH_MM_SS>.xml     anotacao de todas as vagas
```

**`PKLotSegmented/`** — recortes de vaga já extraídos pelos autores, separados por classe.

```text
PKLotSegmented/
└── <estacionamento>/        PUC | UFPR04 | UFPR05
    └── <clima>/
        └── <AAAA-MM-DD>/
            ├── Empty/       recortes de vaga livre
            └── Occupied/    recortes de vaga ocupada
```

O projeto usa **`PKLot/`** como fonte primária, porque a etapa de recorte com correção de
perspectiva é parte do pipeline sob investigação. O `PKLotSegmented/` é usado como referência de
verificação: comparar os recortes próprios com os dos autores valida a implementação da homografia.

## 4. Contagens verificadas na cópia local

Contagens obtidas por inspeção direta dos arquivos em 2026-08-29.

### 4.1 Frames completos (`PKLot/`)

| Estacionamento | Sunny | Cloudy | Rainy | Total | Dias distintos |
|---|---:|---:|---:|---:|---:|
| PUCPR  | 488 | 277 | 162 | **927** | 43 |
| UFPR04 | 431 | 284 |  62 | **777** | 49 |
| UFPR05 | 513 | 283 |  41 | **837** | 51 |
| **Total** | **1.432** | **844** | **265** | **2.541** | **143** |

Arquivos XML de anotação: **2.553**.

### 4.2 Recortes de vaga (`PKLotSegmented/`)

| Estacionamento | Clima | Ocupadas | Livres | Total | % ocupadas |
|---|---|---:|---:|---:|---:|
| PUC    | Sunny  | 19.799 | 22.902 | 42.701 | 46,4% |
| PUC    | Cloudy |  8.709 | 18.435 | 27.144 | 32,1% |
| PUC    | Rainy  | 11.358 |  5.704 | 17.062 | 66,6% |
| UFPR04 | Sunny  |  6.613 |  5.353 | 11.966 | 55,3% |
| UFPR04 | Cloudy |  2.399 |  5.702 |  8.101 | 29,6% |
| UFPR04 | Rainy  |    490 |  1.145 |  1.635 | 30,0% |
| UFPR05 | Sunny  | 11.879 |  8.682 | 20.561 | 57,8% |
| UFPR05 | Cloudy |  6.984 |  4.753 | 11.737 | 59,5% |
| UFPR05 | Rainy  |  1.275 |    575 |  1.850 | 68,9% |
| **Total** | | **69.506** | **73.251** | **142.757** | **48,7%** |

### 4.3 Observações sobre o balanceamento

O conjunto está globalmente equilibrado (48,7% ocupadas), mas **cada célula individual não está**.
A proporção de vagas ocupadas varia de 29,6% (UFPR04 nublado) a 68,9% (UFPR05 chuvoso) — uma faixa
de quase 40 pontos percentuais.

Isso tem consequência experimental direta: um classificador avaliado apenas pela acurácia agregada
pode parecer bom explorando o desbalanceamento em vez de reconhecer veículos. Por isso o protocolo
de avaliação exige métricas desagregadas por clima e matriz de confusão (critérios C3 e C4 da
proposta).

O desbalanceamento também não é aleatório — é interpretável. Dias chuvosos concentram mais vagas
ocupadas, o que é plausível: com chuva, mais pessoas vão de carro. Isso significa que clima e
ocupação são variáveis **correlacionadas** no conjunto, e essa correlação precisa ser considerada
ao interpretar os resultados.

### 4.4 Divergência em relação ao artigo original — **verificar**

> O artigo original descreve **12.417 frames**; a cópia local contém **2.541**. Da mesma forma, a
> literatura reporta cerca de 695 mil recortes, contra os 142.757 verificados localmente.
>
> A hipótese mais provável é extração incompleta do `PKLot.tar.gz`. Há também 2.553 XMLs para
> 2.541 JPGs — 12 anotações sem imagem correspondente —, o que reforça essa hipótese.
>
> **Ação pendente:** reextrair o arquivo e reconferir as contagens; atualizar esta seção com os
> números finais. O subconjunto atual já é suficiente para os experimentos da M1, portanto isso não
> bloqueia o andamento.

## 5. Características técnicas

| Propriedade | Valor |
|---|---|
| Resolução dos frames | 1280 × 720 px |
| Formato | JPEG (com perdas) |
| Espaço de cor | RGB |
| Aquisição | Câmera fixa em ponto elevado, com sobrevoo em perspectiva do pátio |
| Intervalo entre capturas | Aproximadamente 5 minutos |
| Período | Diurno apenas — **não há imagens noturnas** |
| Anotação | XML por frame, uma entrada por vaga |

### 5.1 Formato da anotação

```xml
<parking id="ufpr04">
  <space id="1" occupied="1">
    <rotatedRect>
      <center x="724" y="623" />
      <size w="93" h="154" />
      <angle d="-31" />
    </rotatedRect>
    <contour>
      <point x="720" y="549" />
      <point x="805" y="665" />
      <point x="715" y="698" />
      <point x="644" y="582" />
    </contour>
  </space>
  ...
</parking>
```

- `occupied` — verdade de referência: `1` ocupada, `0` livre.
- `contour` — quatro vértices do quadrilátero da vaga em coordenadas de imagem. **É esta a entrada
  usada para a homografia** do pipeline.
- `rotatedRect` — representação alternativa (centro, dimensões, ângulo). Redundante com o contorno
  para os fins deste projeto; mantida como verificação cruzada.

Nem toda vaga aparece em todos os frames de um mesmo estacionamento — a anotação acompanha a
configuração vigente na data.

## 6. Como obter os dados

O repositório não inclui as imagens. Para reproduzir os experimentos:

```bash
# 1. Baixar o arquivo a partir do laboratorio VRI/UFPR
#    https://web.inf.ufpr.br/vri/databases/parking-lot-database/
#    (arquivo PKLot.tar.gz, ~4,9 GB)

# 2. Extrair para data/ na raiz do repositorio
mkdir -p data
tar -xzf PKLot.tar.gz -C data/

# 3. Conferir a estrutura resultante
ls data/PKLot/PKLot        # deve listar: PUCPR  UFPR04  UFPR05
```

Estrutura esperada após a extração:

```text
data/
└── PKLot/
    ├── PKLot/              frames + anotacoes XML
    ├── PKLotSegmented/     recortes ja extraidos pelos autores
    └── PklotInfo.pdf       documentacao dos autores
```

## 7. Adequação ao problema

O conjunto foi escolhido por três propriedades que o tornam adequado à pergunta central da
proposta, e não apenas por estar disponível:

1. **Três estacionamentos distintos** com pontos de vista, geometrias e pavimentos diferentes.
   É o que viabiliza diretamente o experimento de generalização inter-estacionamento.
2. **Estratificação climática explícita**, permitindo medir robustez a variação fotométrica sem
   necessidade de simulação artificial de condições.
3. **Verdade de referência completa e por vaga**, eliminando o custo de anotação manual e tornando
   possível medir desempenho desde a primeira semana.

### 7.1 Limitações reconhecidas

- **Sem imagens noturnas.** Qualquer conclusão do projeto vale apenas para condições diurnas. Uma
  aplicação real precisaria estender a análise para iluminação artificial.
- **Coleta de 2012–2013.** Os veículos refletem a frota da época; a qualidade de sensor é inferior
  à de câmeras atuais. Isso tende a tornar o problema mais difícil, não mais fácil, o que é
  aceitável para os fins do projeto.
- **Apenas três pontos de vista.** Generalização inter-estacionamento é medida sobre uma amostra
  pequena de geometrias; conclusões devem ser apresentadas com essa ressalva.
- **Compressão JPEG.** Introduz artefatos que podem interferir em descritores de textura de escala
  fina. Ponto a observar durante a análise de erros.
