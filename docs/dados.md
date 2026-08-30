# Conjunto de Imagens — PKLot

## Características

- **Frames:** 12.417, de 1280 × 720 px
- **Formato:** JPEG, RGB
- **Aquisição:** câmera fixa em ponto elevado, capturas a cada ~5 minutos, 2012–2013
- **Período:** diurno apenas
- **Anotação:** um arquivo XML por frame, descrevendo todas as vagas daquele frame

## Origem

- **Nome:** PKLot — A Robust Dataset for Parking Lot Classification
- **Instituições:** UFPR e PUCPR
- **Página:** <https://web.inf.ufpr.br/vri/databases/parking-lot-database/>
- **Licença:** CC BY 4.0
- **Obtenção:** download de `PKLot.tar.gz` (~4,9 GB) na página acima, extraído em `data/`

A licença exige citação do artigo dos autores em qualquer publicação sobre o trabalho:

> ALMEIDA, P.; OLIVEIRA, L. S.; SILVA JR., E.; BRITTO JR., A.; KOERICH, A.
> PKLot — A robust dataset for parking lot classification.
> *Expert Systems with Applications*, 42(11):4937–4949, 2015.

As imagens não são versionadas neste repositório.

## Organização

O conjunto vem em duas formas: **`PKLot/`** traz os frames completos com anotação e é a fonte
primária do projeto; **`PKLotSegmented/`** traz recortes de vaga já extraídos pelos autores e serve
como referência para verificar a nossa extração.

```text
PKLot/<estacionamento>/<clima>/<data>/<timestamp>.jpg + .xml
PKLotSegmented/<estacionamento>/<clima>/<data>/<Empty|Occupied>/<recorte>.jpg
```

## Contagens

### Frames

**PUCPR** — Sunny 2.315 · Cloudy 1.328 · Rainy 831 · **total 4.474**

**UFPR04** — Sunny 2.098 · Cloudy 1.408 · Rainy 285 · **total 3.791**

**UFPR05** — Sunny 2.500 · Cloudy 1.426 · Rainy 226 · **total 4.152**

**Total geral: 12.417 frames**

### Recortes de vaga (`PKLotSegmented/`)

**PUCPR** — Sunny 208.387 · Cloudy 132.780 · Rainy 83.056 · **total 424.223**

**UFPR04** — Sunny 58.500 · Cloudy 39.385 · Rainy 7.958 · **total 105.843**

**UFPR05** — Sunny 99.890 · Cloudy 56.966 · Rainy 8.929 · **total 165.785**

**Total geral: 695.851 recortes**, sendo 48,5% de vagas ocupadas.

### Balanceamento

O conjunto é globalmente equilibrado, mas a proporção de vagas ocupadas varia por estacionamento e
clima — de 29,5% (UFPR04 nublado) a 68,1% (UFPR05 chuvoso).

Por isso os resultados são sempre reportados desagregados por clima: uma média agregada permitiria
que um método parecesse bom apenas por explorar o desbalanceamento de uma célula específica.

## Formato da anotação

```xml
<parking id="ufpr04">
  <space id="1" occupied="1">              <!-- occupied: verdade de referencia, 1 ou 0 -->
    <rotatedRect>                          <!-- representacao alternativa, nao usada -->
      <center x="724" y="623" /><size w="93" h="154" /><angle d="-31" />
    </rotatedRect>
    <contour>                              <!-- 4 vertices da vaga; entrada da homografia -->
      <point x="720" y="549" /><point x="805" y="665" />
      <point x="715" y="698" /><point x="644" y="582" />
    </contour>
  </space>
</parking>
```

## Adequação e limitações

O conjunto atende ao problema por ter três estacionamentos com pontos de vista distintos, clima
rotulado e verdade de referência por vaga — as três condições necessárias para os experimentos
previstos na proposta.

Limitações:

- **Sem imagens noturnas.** Luz artificial poderia afetar os resultados, especialmente em dias de
  chuva e à noite; os dados não permitem afirmar nada a respeito.
- **Anotação parcial.** Apenas um subconjunto das vagas de cada câmera é anotado, então não há
  validação possível além do que está documentado.
