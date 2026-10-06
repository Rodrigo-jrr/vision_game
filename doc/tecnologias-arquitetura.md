# Tecnologias e arquitetura

## 1. Objetivo

Este documento define a stack e a arquitetura propostas para o MVP do
controlador de jogo por visão computacional. A solução será um aplicativo
desktop local em Python: captura imagens da webcam, reconhece gestos de uma
mão e os converte em teclas simuladas para o jogo ou emulador em foco.

Os requisitos funcionais e os critérios de aceitação estão em
[requisitos.md](./requisitos.md). A biblioteca de entrada de teclado e o
comportamento com o jogo de referência precisam ser validados no sistema
operacional de destino antes de considerar a integração concluída.

## 2. Tecnologias

| Área | Tecnologia proposta | Uso |
| --- | --- | --- |
| Linguagem | Python 3.10 ou superior | Aplicativo e módulos do projeto. |
| Captura e imagem | OpenCV (`opencv-contrib-python`) | Acesso à webcam, conversão e exibição dos quadros; é também a distribuição requerida pelo MediaPipe. |
| Rastreamento da mão | MediaPipe Tasks (Hand Landmarker) | Localização dos pontos de referência da mão em cada quadro. |
| Entrada de teclado | `pynput` | Pressionar e liberar teclas mapeadas para comandos. |
| Configuração | JSON, usando o módulo `json` da biblioteca padrão | Câmera, limiar de confiança, parâmetros dos gestos e teclas. |
| Testes automatizados | `pytest` | Testes unitários e de integração com câmera e entrada simuladas. |
| Controle de qualidade | `ruff` | Formatação e análise estática do código Python. |
| Ambiente e dependências | `venv` e `requirements.txt` | Isolamento do ambiente e instalação reproduzível das bibliotecas. |

As versões diretas das dependências estão fixadas em `requirements.txt` com
base no ambiente Python 3.10 validado. A compatibilidade ainda deve ser
confirmada nos sistemas operacionais oficialmente escolhidos. O modelo do MediaPipe deve
ser obtido conforme as instruções oficiais da versão adotada e distribuído ou
baixado de forma documentada. A licença e as condições de distribuição do
modelo e das dependências também devem ser verificadas antes de publicar o
aplicativo.

### Justificativas

- **OpenCV** oferece captura de vídeo e uma pré-visualização suficiente para
  o MVP, sem exigir uma interface gráfica adicional.
- **MediaPipe Hand Landmarker** fornece pontos de referência da mão que
  permitem classificar gestos sem treinar um modelo próprio.
- **`pynput`** separa a emissão de teclas do reconhecimento visual e permite
  substituir ou adaptar a camada de entrada caso o sistema de destino exija
  outra tecnologia.
- **JSON** é legível, suportado pela biblioteca padrão e suficiente para os
  parâmetros e mapeamentos iniciais.
- **`pytest` e `ruff`** permitem validar a lógica de forma automatizada e
  consistente durante a evolução do projeto.

## 3. Arquitetura

O aplicativo será organizado em módulos com responsabilidades separadas. O
fluxo principal é síncrono no MVP para manter a implementação simples; a
captura, o reconhecimento e o mapeamento serão executados em sequência para
cada quadro.

```text
Webcam
  |
  v
Captura de vídeo (OpenCV)
  |
  v
Reconhecimento da mão (MediaPipe)
  |
  v
Classificação e estabilização do gesto
  |
  v
Mapeamento gesto -> comando -> tecla
  |
  v
Saída de teclado (pynput)
  |
  v
Jogo ou emulador em foco

Configuração JSON ---> Aplicação / parâmetros dos módulos
Pré-visualização <--- Captura + estado do gesto/comando
```

### Componentes

1. **Aplicação (`app`)**
   - Inicializa os componentes e coordena o ciclo de execução.
   - Apresenta a pré-visualização e o estado do gesto.
   - Trata o atalho de encerramento e garante a liberação dos recursos.

2. **Configuração (`config`)**
   - Lê o arquivo JSON e valida campos, tipos, limites e teclas.
   - Mantém valores padrão documentados para câmera e limiar de confiança.
   - Informa erros de configuração com mensagens que identifiquem o campo
     inválido; não deve ocultar erros usando valores substitutos silenciosos.

3. **Captura (`camera`)**
   - Abre a câmera configurada e fornece quadros ao ciclo principal.
   - Informa falhas de abertura ou leitura.
   - Libera o dispositivo ao encerrar, inclusive em caso de exceção.

4. **Reconhecimento (`hand_tracking`)**
   - Recebe um quadro e retorna os pontos da mão e a confiança da detecção.
   - Não decide quais teclas devem ser pressionadas.
   - Processa os quadros localmente; não persiste nem transmite imagens.

5. **Gestos (`gestures`)**
   - Interpreta os pontos da mão e classifica os gestos suportados.
   - Aplica limiar de confiança e, se necessário, estabilização temporal para
     reduzir alternância causada por detecção instável.
   - Retorna um gesto conhecido ou o estado neutro.

6. **Controles (`controls`)**
   - Converte o gesto em um comando lógico e o comando em uma tecla configurada.
   - Acompanha as teclas mantidas pressionadas e libera as que não correspondem
     mais ao estado atual.
   - Garante liberação de todas as teclas ainda pressionadas ao encerrar.

7. **Entrada de teclado (`keyboard`)**
   - Encapsula a biblioteca `pynput` atrás de operações simples, como
     pressionar, liberar e liberar todas.
   - Mantém dependências específicas de sistema operacional fora da lógica de
     gestos e comandos.

8. **Interface (`preview`)**
   - Usa a janela do OpenCV para mostrar o quadro e a indicação de gesto,
     comando ou ausência de detecção.
   - Exibe instruções de uso e o atalho de saída.
   - A interface não deve afirmar que o jogo recebeu uma tecla; a aplicação
     não tem confirmação confiável da janela que a recebeu.

## 4. Organização de código sugerida

```text
vision_game/
├── doc/
│   ├── requisitos.md
│   └── tecnologias-arquitetura.md
├── src/
│   └── vision_game/
│       ├── __init__.py
│       ├── app.py
│       ├── config.py
│       ├── camera.py
│       ├── hand_tracking.py
│       ├── gestures.py
│       ├── controls.py
│       ├── keyboard.py
│       └── preview.py
├── tests/
│   ├── test_config.py
│   ├── test_gestures.py
│   └── test_controls.py
├── config.example.json
├── requirements.txt
└── README.md
```

Essa estrutura é uma proposta para orientar a implementação; arquivos e
módulos devem ser criados conforme o desenvolvimento começar. Arquivos de
configuração pessoais não devem conter dados sensíveis nem ser necessários
para os testes automatizados.

## 5. Contratos entre componentes

- A captura entrega um quadro ou sinaliza uma falha explícita.
- O reconhecedor retorna os pontos e a confiança detectada, ou informa que
  nenhuma mão foi encontrada.
- O classificador retorna um identificador de gesto ou estado neutro.
- O mapeador converte apenas gestos válidos em comandos configurados.
- A camada de teclado recebe comandos lógicos/teclas e gerencia transições
  entre pressionado e liberado, evitando repetir indefinidamente o evento de
  pressionar a cada quadro.
- A interface recebe dados já calculados e não controla diretamente a câmera,
  o classificador ou a biblioteca de teclado.

Esses contratos permitem testar a classificação e o mapeamento sem webcam
real e sem enviar entradas ao sistema operacional.

## 6. Ciclo de execução e tratamento de falhas

1. Carregar e validar a configuração.
2. Inicializar o reconhecedor e abrir a câmera.
3. Para cada quadro, detectar a mão, classificar o gesto, atualizar as teclas
   e desenhar o estado da execução.
4. Se a detecção deixar de ser válida, mudar para o estado neutro e liberar as
   teclas direcionais mantidas.
5. Ao solicitar saída ou ao ocorrer uma falha, liberar teclas pressionadas,
   fechar a janela e liberar a câmera e o reconhecedor.

A limpeza deve ser feita em bloco de finalização (`try/finally` ou mecanismo
equivalente), de modo que falhas em uma etapa não deixem a câmera aberta nem
teclas virtuais pressionadas. Erros de inicialização devem ser apresentados
com contexto e encerrar a execução com estado de falha.

## 7. Estratégia de testes

- **Unitários:** validação da configuração, classificação de gestos a partir
  de pontos de referência conhecidos e mapeamento de gesto para tecla.
- **Transições de controle:** verificar pressionar, manter, trocar, neutralizar
  e liberar comandos, usando uma implementação de teclado simulada.
- **Falhas:** câmera indisponível, configuração inválida, perda de detecção e
  encerramento durante uma tecla pressionada.
- **Integração manual:** testar webcam, permissões do sistema operacional e
  recepção de teclas pelo jogo/emulador de referência.
- **Desempenho:** medir quadros por segundo e latência no equipamento-alvo e
  comparar com RNF-02 em [requisitos.md](./requisitos.md).

Os testes automatizados não devem depender de webcam física, janela gráfica,
permissões de acessibilidade nem de um jogo em execução. Esses casos pertencem
à validação manual de integração.

## 8. Premissas e validações antes da implementação

- O desenvolvimento começa em um computador macOS, mas o sistema operacional
  oficialmente suportado ainda precisa ser definido.
- O jogo ou emulador receberá teclas simuladas e estará em foco durante o
  controle.
- Permissões de câmera e, no macOS, permissões de acessibilidade podem ser
  necessárias para a captura e a emissão de teclas.
- A combinação MediaPipe + OpenCV + `pynput` deve ser instalada e testada no
  sistema-alvo antes de fixar as versões no arquivo de dependências.
- O jogo/emulador de referência deve ser escolhido para validar se aceita
  entrada sintetizada. Alguns jogos podem ignorar esse tipo de entrada.
- Se a combinação de sistema operacional e jogo não aceitar `pynput`, somente
  o adaptador de entrada deve ser substituído, mantendo as interfaces e a
  lógica de reconhecimento e mapeamento.
