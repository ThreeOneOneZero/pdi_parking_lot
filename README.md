# Classificação de Ocupação de Vagas de Estacionamento sob Variação de Iluminação e Ponto de Vista

Projeto Aplicado Longitudinal — **Processamento de Imagens**
Etapa atual: **M1 — definição do problema e estudo de viabilidade**

# PENDENTE VERIFICAÇÃO DESSE CONTEUDO, NAO FINAL!

---

## Integrantes

| Nome             | Participação                                                                     |
| ---------------- | -------------------------------------------------------------------------------- |
| Leonardo Pacheco | Definição do problema, obtenção e caracterização dos dados, documentação técnica |

> Composição da equipe ainda em definição. Aguardando email pois está dimensionado para uma pessoa.

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

**Pergunta técnica central:** quanto da queda de desempenho entre condições climáticas e entre
estacionamentos diferentes pode ser recuperada por pré-processamento fotométrico e escolha de
descritores de textura, em vez de simplesmente ampliar o conjunto de treino?

O classificador é mantido fixo durante todo o projeto; as etapas de processamento de imagem são a
variável experimental. É isso que torna o trabalho um estudo de PDI, e não um exercício de
aprendizado de máquina onde a imagem é apenas um vetor de entrada.

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
        ├─ normalizacao fotometrica     ← VARIAVEL EXPERIMENTAL
        ├─ descritor de textura         ← VARIAVEL EXPERIMENTAL
        ├─ classificador SVM            ← COMPONENTE FIXO
        └─→  { vaga: ocupada|livre + confianca }  ──→  contagem de vagas livres
```

**Entra:** frame RGB 1280×720 de câmera fixa + definição das vagas (polígonos de 4 pontos).
**Sai:** rótulo `ocupada`/`livre` com confiança por vaga, e a contagem agregada de vagas livres.

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

**M1 em andamento.**

Concluído: problema definido e delimitado · conjunto obtido, inspecionado e caracterizado · formato
da anotação validado · pipeline preliminar projetado com alternativas registradas · critérios de
sucesso e protocolo de avaliação definidos.

Experimentos realizados:

| | Experimento | Resultado |
|---|---|---|
| E1 | Extração de recortes com correção de perspectiva | Vagas variam **11×** em área no mesmo frame, justificando a normalização geométrica |
| E2 | Separabilidade por densidade de bordas | **94,0%** de acerto com Sobel + limiar, sem treinamento |

O E2 responde a pergunta que determina a viabilidade do projeto — *existe medida sobre os pixels que
separe vaga ocupada de livre?* Com o limiar calibrado no UFPR04 e aplicado sem alteração aos demais:
**94,0%** no próprio lote, **66,0%** no UFPR05, **85,1%** no PUCPR. A intensidade média, usada como
comparação, fica em 64,7% e cai a 32,9%.

Análise dos resultados, tabelas por clima e padrão dos erros em
[`docs/proposta.md`](docs/proposta.md), seção 7.2.

Pendente: vídeo de apresentação.

---

## Organização do repositório

```text
pdi_parking_lot/
├── README.md               este arquivo — sintese do projeto
├── AI_USAGE.md             declaracao de uso de IA generativa
├── docs/
│   ├── proposta.md         proposta tecnica completa
│   └── dados.md            caracterizacao do conjunto de imagens
├── src/parking/            modulos do pipeline
├── scripts/                experimentos E1-E4, executaveis por linha de comando
├── tests/                  testes das operacoes de src/
├── images/results/         figuras versionadas (paineis, histogramas)
├── results/                metricas geradas pelos experimentos
├── data/                   conjunto PKLot (NAO versionado — ver docs/dados.md)
├── requirements.txt
└── .gitignore
```

---

## Tecnologias

Python 3.11+ · OpenCV e scikit-image (homografia, normalização, descritores) · NumPy ·
scikit-learn (SVM) · Matplotlib (figuras).

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

| Parâmetro | Padrão | Descrição |
|---|---|---|
| `--data` | obrigatório | diretório `PKLot/` |
| `--calibrate-on` | `UFPR04` | estacionamento onde o limiar é calibrado |
| `--frames-per-weather` | `6` | frames amostrados por condição climática |
| `--patch-size` | `48x64` | tamanho canônico do recorte |

Saídas: `images/results/e2_edge_density_<lote>.png` (histogramas por clima, com o limiar marcado) e
`results/e2_measurements.csv` (uma linha por vaga, com as duas medidas e o rótulo).

---

## Vídeo da M1

> _A ser publicado no YouTube como não listado, com o link inserido aqui antes da entrega._

---

## Créditos do conjunto de dados

> ALMEIDA, P.; OLIVEIRA, L. S.; SILVA JR., E.; BRITTO JR., A.; KOERICH, A.
> **PKLot — A robust dataset for parking lot classification.**
> _Expert Systems with Applications_, 42(11):4937–4949, 2015.
