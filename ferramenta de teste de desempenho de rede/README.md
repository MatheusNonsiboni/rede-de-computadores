# Ferramenta de Teste de Desempenho de Rede

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Sockets](https://img.shields.io/badge/Sockets-TCP%2FUDP-informational?style=for-the-badge)
![Multithreading](https://img.shields.io/badge/Multithreading-Concurrent-orange?style=for-the-badge)
![Status](https://img.shields.io/badge/status-conclu%C3%ADdo-brightgreen?style=for-the-badge)

## Descrição

Ferramenta de benchmark de rede, no estilo de utilitários como o `iperf`, que satura a capacidade do link de rede enviando pacotes ininterruptamente por um período fixo, medindo taxa de transferência, pacotes por segundo e percentual de perda. Desenvolvido para a disciplina de **Redes de Computadores** (UEL), o mesmo código atua tanto como emissor (*sender*) quanto como receptor (*receiver*), sobre TCP ou UDP, permitindo comparar diretamente o comportamento dos dois protocolos sob a mesma carga de tráfego e em diferentes condições reais de rede (cabeada e sem fio).

## Conceitos de Computação e Decisões Técnicas

- **Paralelismo com múltiplos sockets (multithreading)**: o emissor abre 4 sockets simultâneos, cada um rodando em sua própria thread, todos enviando dados de forma independente durante a janela de teste. Essa abordagem multiplica a carga total gerada sobre a rede, aproximando o teste de um cenário de saturação de link em vez de medir apenas a capacidade de um único fluxo.
- **Sincronização de contadores compartilhados com `threading.Lock`**: como as 4 threads de envio (e, no TCP, as threads de recepção) escrevem simultaneamente nos mesmos contadores de pacotes e bytes, cada operação de incremento é protegida por um lock, evitando que atualizações concorrentes se percam ou sobrescrevam umas às outras.
- **Estimativa de perda de pacotes por número de sequência**: cada pacote carrega um identificador de socket (`sid`) e um número de sequência (`seq`). O receptor mantém o último número visto por socket e, a cada novo pacote, calcula quantos números foram "pulados" desde o último (`seq - último_visto - 1`) para estimar quantos pacotes se perderam no caminho — sem depender de confirmação (ACK) alguma, já que o objetivo aqui é medir throughput sob estresse, não garantir entrega.
- **TCP_NODELAY para desativar o algoritmo de Nagle**: por padrão, TCP agrupa pequenos pacotes antes de enviá-los, otimizando para uso de banda em vez de latência. Como o objetivo é medir a taxa de transferência real sob envio contínuo, essa opção é desativada para que os dados sejam transmitidos assim que disponíveis.
- **Paralelismo assimétrico entre TCP e UDP no lado da recepção**: no receptor TCP, cada conexão aceita roda em sua própria thread dedicada (uma por socket do emissor). No receptor UDP, por não haver conceito de conexão, um único socket recebe os datagramas de todos os 4 emissores simultâneos em um laço único. Essa diferença de arquitetura, somada à ausência de controle de fluxo nativo do UDP, é um fator relevante para a diferença de comportamento observada entre os dois protocolos sob rede instável (ver seção de resultados).
- **Buffers de socket ampliados (4 MB)**: tanto o lado de envio (`SO_SNDBUF`) quanto o de recepção (`SO_RCVBUF`) têm seus buffers do sistema operacional configurados para 4 MB, reduzindo a chance de descarte de pacotes por buffer cheio quando o processamento da aplicação não acompanha momentaneamente a taxa de chegada.

## Tecnologias Utilizadas

**Linguagens**
- Python 3

**Bibliotecas**
- `socket` (nativa) — comunicação via TCP (`SOCK_STREAM`) e UDP (`SOCK_DGRAM`)
- `threading` (nativa) — paralelização do envio e recepção em múltiplos sockets simultâneos
- `struct` (nativa) — empacotamento binário do cabeçalho de cada pacote (identificador de socket e número de sequência)
- `time` (nativa) — controle da janela de duração do teste e medição de taxas

**Protocolos**
- TCP/IP e UDP/IP

## Funcionalidades

- **Modo sender e modo receiver no mesmo script**, selecionáveis interativamente, permitindo que a mesma ferramenta seja usada nas duas pontas do teste.
- **Envio contínuo e paralelo** por 20 segundos, usando 4 sockets simultâneos por padrão, sobre TCP ou UDP.
- **Pacotes de tamanho fixo (500 bytes)**, com cabeçalho binário contendo identificador do socket de origem e número de sequência.
- **Estimativa de pacotes perdidos** no receptor, com percentual de perda calculado sobre o total de pacotes recebidos e perdidos.
- **Relatórios de execução** em ambos os lados, com contagem de pacotes, bytes trafegados, velocidade em pacotes/segundo e em bits/segundo (formatada automaticamente em bps, Kbps, Mbps ou Gbps conforme a magnitude), e duração real do teste.
- **Formatação numérica com separador de milhar**, facilitando a leitura de contagens grandes de pacotes.
- **Encerramento do receptor**, aguardando alguns segundos após o fim da janela de envio para permitir que os últimos pacotes em trânsito cheguem antes de fechar o relatório.

### Exemplo de execução

Resultados reais obtidos em uma bateria de testes comparando rede Wi-Fi (universidade) e rede cabeada, com 3 execuções por protocolo em cada tipo de rede:

**TCP em Wi-Fi (Teste 2) — relatório do receiver:**

```
Pacotes recebidos: 206.371
Pacotes perdidos: 0  (0.00%)
Bytes trafegados: 103.185.500
Velocidade (pkt/s): 8.559
Velocidade (bit/s): 34.24 Mbps
Duração real: 24.109 s
```

**UDP em Wi-Fi (Teste 2) — relatório do receiver:**

```
Pacotes recebidos: 28.534
Pacotes perdidos: 434.612  (93.84%)
Bytes trafegados: 14.267.000
Velocidade (pkt/s): 1.239
Velocidade (bit/s): 4.96 Mbps
Duração real: 23.018 s
```

Nos seis testes realizados em **rede cabeada**, tanto TCP quanto UDP apresentaram 0% de perda em todas as execuções. Já em **rede Wi-Fi**, o TCP manteve 0% de perda nos três testes, enquanto o UDP apresentou perdas de 89,09%, 93,84% e 60,36% nos três testes, respectivamente — evidenciando na prática que o controle de fluxo nativo do TCP absorve a instabilidade da rede sem fio, enquanto o UDP, por não ter esse mecanismo, expõe diretamente ao usuário a taxa real de descarte de pacotes da rede.

> Nota: nos testes em rede cabeada, a velocidade máxima observada foi limitada a aproximadamente 100 Mbps devido ao adaptador de rede utilizado, e não à capacidade da ferramenta.

## Instalação e Execução

### Pré-requisitos

- **Python 3** instalado (não há dependências externas — o projeto usa apenas bibliotecas nativas: `socket`, `struct`, `time` e `threading`).

### 1. Clonar o repositório

```bash
git clone https://github.com/seu-usuario/ferramenta-teste-desempenho-rede.git
cd ferramenta-teste-desempenho-rede
```

### 2. Instalar dependências

Não há dependências para instalar — todas as bibliotecas usadas já vêm com o Python.

### 3. Executar

Assim como um teste de banda tradicional, é necessário rodar o script em dois computadores (ou dois terminais, para testar localmente): um no papel de receiver e outro no papel de sender. O receiver deve estar em execução **antes** do sender iniciar o teste.

**No computador que vai medir a recepção (receiver):**

```bash
python3 trabalho2.py
```

Responda às perguntas:
- `Protocolo (TCP=1, UDP=2):` — escolha o protocolo a testar.
- `Porta:` — porta em que este nó vai escutar (ex: `5000`).
- `Este nó vai (S)ender ou (R)eceiver?` — digite `R`.

**No computador que vai gerar o tráfego (sender):**

```bash
python3 trabalho2.py
```

Responda às perguntas:
- `Protocolo (TCP=1, UDP=2):` — deve ser **o mesmo protocolo** escolhido no receiver.
- `Porta:` — deve ser **a mesma porta** em que o receiver está escutando.
- `Este nó vai (S)ender ou (R)eceiver?` — digite `S`.
- `IP do destino:` — endereço IP da máquina receptora (use `127.0.0.1` se estiver testando na mesma máquina).

O teste roda automaticamente por 20 segundos a partir do início do envio, usando 4 sockets paralelos. Ao final, ambos os lados exibem seus respectivos relatórios de desempenho. Para comparar TCP e UDP, ou rede cabeada e sem fio, repita o processo alterando o protocolo escolhido ou o meio físico de conexão entre as duas máquinas.

## Autores

Essa aplicação foi desenvolvida em conjunto com Marcela de Oliveira Dorigão.