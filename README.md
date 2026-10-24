# Classificação de Ocupação de Vagas de Estacionamento sob Variação de Iluminação e Ponto de Vista

Projeto Aplicado Longitudinal — **Processamento de Imagens**
Etapa atual: **M2, implementação parcial e experimentos**

---

## Integrantes

| Nome             | Participação                                                         |
| ---------------- | -------------------------------------------------------------------- |
| Leonardo Pacheco | Todas as etapas: problema, dados, protocolo, código, experimentos e documentação |

Equipe de uma pessoa.

---

## Problema

Estacionamentos de grande porte precisam saber quantas vagas estão livres. Instrumentar cada vaga
com sensor tem custo que cresce linearmente com o número de vagas; uma câmera fixa em ponto elevado
cobre dezenas de vagas de uma vez, mas transfere o problema para a **interpretação da imagem**.

A dificuldade é específica: a aparência de uma vaga varia muito por razões que **nada têm a ver com
estar ocupada**. Sombras escurecem vagas vazias, chuva deixa o asfalto espelhado, a perspectiva faz
vagas distantes ficarem pequenas e obliquadas, carros brancos sobre asfalto claro têm contraste
quase nulo, e árvores ocluem fileiras inteiras. O sinal desejado está misturado com ruído
fotométrico e geométrico de magnitude comparável.

**Pergunta técnica central:** é possível processar a imagem de modo que a medida usada para decidir
deixe de depender do clima e do estacionamento — permitindo que a mesma regra funcione onde não foi
calibrada?

A decisão é uma regra explícita, `medida > limiar`, sem treinamento nem modelo. As etapas de
processamento aplicadas antes da medida são a variável experimental. É isso que torna o trabalho um
estudo de PDI, e não um exercício de aprendizado de máquina onde a imagem é apenas um vetor de
entrada.

→ Delimitação completa em **[`docs/proposta.md`](docs/proposta.md)**, seção 1.

## Contexto de aplicação

Campus universitário ou estacionamento corporativo que já possui câmeras de segurança em pontos
elevados e quer reaproveitá-las para publicar a contagem de vagas livres. O requisito de
generalização é real: quem instala o sistema num estacionamento quer instalar no seguinte sem
recomeçar a anotação.

## Objetivo geral

Investigar e avaliar experimentalmente um pipeline de PDI capaz de classificar a ocupação de vagas
a partir de frames de câmera fixa, **quantificando** o impacto das etapas de normalização
fotométrica e de representação por textura sobre a robustez a mudanças de clima e de
estacionamento.

→ Objetivos específicos e critérios de sucesso em **[`docs/proposta.md`](docs/proposta.md)**, seção 3.

---

## Solução proposta

```text
frame 1280x720  +  anotacao das vagas
        │
        ├─ recorte por vaga + correcao de perspectiva  ──→  patch canonico
        ├─ normalizacao fotometrica       ← VARIAVEL EXPERIMENTAL
        ├─ medida sobre os pixels (Sobel) ← VARIAVEL EXPERIMENTAL
        ├─ comparacao com limiar          ← REGRA FIXA, sem treinamento
        └─→  { vaga: ocupada|livre }  ──→  contagem de vagas livres
```

**Entra:** frame RGB 1280×720 de câmera fixa + definição das vagas (polígonos de 4 pontos).
**Sai:** rótulo `ocupada`/`livre` por vaga, e a contagem agregada de vagas livres.

→ Diagrama detalhado, finalidade de cada etapa, dúvidas em aberto e alternativas consideradas em
**[`docs/proposta.md`](docs/proposta.md)**, seção 4.

---

## Imagens

**PKLot** — UFPR / PUCPR, licença CC BY 4.0 com citação obrigatória.

|                       |                                                           |
| --------------------- | --------------------------------------------------------- |
| Estacionamentos       | 3 (PUCPR, UFPR04, UFPR05)                                 |
| Condições             | Sunny, Cloudy, Rainy                                      |
| Frames                | 12.417                                                    |
| Recortes de vaga      | 695.851 (48,5% ocupadas)                                  |
| Resolução             | 1280 × 720 px, JPEG                                       |
| Verdade de referência | XML por frame, com polígono e rótulo de ocupação por vaga |

O conjunto foi escolhido por três propriedades, não por conveniência: três pontos de vista
distintos (viabiliza o experimento inter-estacionamento), estratificação climática explícita
(viabiliza o experimento de robustez fotométrica) e anotação completa por vaga (permite medir
desempenho desde a primeira semana).

**As imagens não são versionadas** — ~5 GB é incompatível com Git e não será commitado.

→ Origem, licença, contagens verificadas, formato da anotação, limitações e **instruções de
download** em **[`docs/dados.md`](docs/dados.md)**.

---

## Estágio atual

M2 em andamento. Já funciona a divisão congelada por data, a medição dos 240 quadros, a calibração,
a avaliação e os experimentos abaixo. Falta o comando que recebe um quadro e devolve a contagem de
vagas livres (está no plano da M3).

|     | Experimento | Resultado |
| --- | --- | --- |
| E1  | Recorte com correção de perspectiva (M1) | Vagas variam 11× em área no mesmo quadro |
| E2  | Densidade de bordas + limiar (M1, reavaliado) | 90,7% de acurácia balanceada em outros dias do UFPR04, 80,2% no UFPR05 |
| E3  | Normalização fotométrica | CLAHE melhora o UFPR05 chuva (+5,8), mas piora no resto |
| E4  | Região segmentada (morfologia + maior componente) | Empate com a densidade de bordas |
| E5  | Erro por área, posição e vaga | Mais erro nas vagas distantes do UFPR05 e numa fileira de bloquete do PUCPR |

Os 94,0% da M1 foram medidos nas mesmas vagas da calibração, isso foi corrigido na M2. Detalhes em
[`docs/relatorio_m2.md`](docs/relatorio_m2.md).

---

## Organização do repositório

```text
pdi_parking_lot/
├── README.md               este arquivo — sintese do projeto
├── AI_USAGE.md             declaracao de uso de IA generativa
├── docs/
│   ├── proposta.md         proposta tecnica completa
│   ├── dados.md            caracterizacao do conjunto de imagens
│   └── relatorio_m2.md     relatorio parcial da M2
├── src/parking/            modulos do pipeline
├── scripts/                divisao, medicao, avaliacao e experimentos E1-E5
├── tests/                  testes das operacoes de src/
├── images/results/         figuras versionadas (paineis, histogramas)
├── results/                metricas geradas pelos experimentos
├── data/                   conjunto PKLot (NAO versionado — ver docs/dados.md)
├── requirements.txt
└── .gitignore
```

---

## Tecnologias

Python 3.11+ · OpenCV (homografia, Sobel) · NumPy · Matplotlib (figuras) · pytest.

As escolhas não estão fechadas e poderão ser revistas conforme a investigação avançar.

---

## Reprodução

Preparação do ambiente:

```bash
python -m venv .venv
```

Ativação — **necessária em todo terminal novo**, senão o `python` usado será o do sistema e as
dependências não serão encontradas:

```bash
source .venv/Scripts/activate
```

Em Linux e macOS o caminho é `source .venv/bin/activate`. Com o ambiente ativo, o prompt mostra
`(.venv)`.

```bash
python -m pip install -r requirements.txt
```

Obtenção dos dados: **[`docs/dados.md`](docs/dados.md)**, seção 6.

### Testes

```bash
python -m pytest tests/ -q
```

### E1 — extração de recortes com correção de perspectiva

```bash
python -m scripts.e1_extract_patches --data ../PKLot/PKLot --lot UFPR04
```

Ajuste `--data` para onde o conjunto foi extraído. Parâmetros disponíveis:

| Parâmetro              | Padrão      | Descrição                                      |
| ---------------------- | ----------- | ---------------------------------------------- |
| `--data`               | obrigatório | diretório `PKLot/` com os três estacionamentos |
| `--lot`                | `UFPR04`    | `PUCPR`, `UFPR04` ou `UFPR05`                  |
| `--weather`            | `all`       | `Sunny`, `Cloudy`, `Rainy` ou `all`            |
| `--frames-per-weather` | `2`         | frames processados por condição climática      |
| `--samples-per-cell`   | `8`         | recortes por célula da grade                   |
| `--patch-size`         | `48x64`     | tamanho canônico do recorte                    |
| `--seed`               | `42`        | semente da amostragem                          |

Saídas: `images/results/overlay_*.png` (frame com as vagas anotadas),
`images/results/grid_<lote>.png` (grade de recortes por clima e classe) e
`results/e1_inventory.csv` (uma linha por vaga extraída).

### E2 — separabilidade por densidade de bordas

```bash
python -m scripts.e2_edge_density --data ../PKLot/PKLot
```

Mede densidade de bordas (Sobel) e intensidade média de cada vaga **usando apenas os pixels**,
calibra um limiar em um estacionamento e o aplica sem alteração aos demais. Os rótulos de ocupação
são lidos só depois, para pontuar.

| Parâmetro              | Padrão      | Descrição                                |
| ---------------------- | ----------- | ---------------------------------------- |
| `--data`               | obrigatório | diretório `PKLot/`                       |
| `--calibrate-on`       | `UFPR04`    | estacionamento onde o limiar é calibrado |
| `--frames-per-weather` | `6`         | frames amostrados por condição climática |
| `--patch-size`         | `48x64`     | tamanho canônico do recorte              |

Saídas: `images/results/e2_edge_density_<lote>.png` (histogramas por clima, com o limiar marcado) e
`results/e2_measurements.csv` (uma linha por vaga, com as duas medidas e o rótulo).

### M2: exemplo mínimo, sem o conjunto de dados

As medidas da M2 estão versionadas em `results/measurements.csv`, então a avaliação roda sem
baixar o PKLot:

```bash
python -m scripts.evaluate
```

Deve gerar o mesmo `results/evaluation.csv` do repositório. A primeira linha impressa é o UFPR04
com 1674 vagas e 90,7% de acurácia balanceada.

### M2: cadeia completa

Na ordem. A divisão já está no repositório, o primeiro comando fica só pra mostrar como foi feita
(ele não sobrescreve sem `--force`).

```bash
python -m scripts.make_split --data ../PKLot/PKLot
python -m scripts.measure --data ../PKLot/PKLot
python -m scripts.evaluate
python -m scripts.evaluate --baseline clahe+edge_density --pipelines clahe+edge_density,clahe+region_fraction --output results/evaluation_clahe_base.csv
python -m scripts.e4_sweep --data ../PKLot/PKLot
python -m scripts.e3_figures --data ../PKLot/PKLot
python -m scripts.e4_figures --data ../PKLot/PKLot
python -m scripts.e5_errors --data ../PKLot/PKLot
```

| Script | Faz | Saída |
| --- | --- | --- |
| `make_split` | divide os quadros por data entre calibração e teste | `results/split.csv` |
| `measure` | mede cada vaga com cada configuração | `results/measurements.csv`, `results/timing.csv` |
| `evaluate` | calibra no UFPR04 e pontua o teste, comparando com o baseline | `results/evaluation.csv` |
| `e4_sweep` | escolhe os tamanhos da morfologia só na calibração | `results/e4_sweep.csv` |
| `e3_figures`, `e4_figures` | figuras dos experimentos | `images/results/e3_*.png`, `e4_*.png` |
| `e5_errors` | erro por área, posição e vaga | `results/e5_*.csv`, `images/results/e5_*.png` |

Rodando de novo os arquivos saem iguais, menos o `timing.csv`, que é tempo de relógio.

---

## Vídeos

- M1: <https://www.youtube.com/watch?v=BaTaY7yU4uY>
- M2: <https://youtu.be/ykyUDydEANM>

---

## Créditos do conjunto de dados

> ALMEIDA, P.; OLIVEIRA, L. S.; SILVA JR., E.; BRITTO JR., A.; KOERICH, A.
> **PKLot — A robust dataset for parking lot classification.**
> _Expert Systems with Applications_, 42(11):4937–4949, 2015.
