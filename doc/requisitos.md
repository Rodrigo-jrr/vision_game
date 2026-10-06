# Requisitos — Controlador de jogo por visão computacional

## 1. Visão geral

O projeto consiste em um aplicativo Python que usa uma webcam para reconhecer
gestos da mão e convertê-los em comandos de teclado para controlar um jogo em
execução no computador. O primeiro objetivo é oferecer uma alternativa simples
ao teclado ou controle físico, com resposta em tempo real e comandos
configuráveis.

Este documento define os requisitos do produto mínimo viável (MVP). A
integração inicial com o jogo deve funcionar por meio de teclas simuladas,
permitindo uso com jogos ou emuladores que aceitem entrada de teclado.

## 2. Objetivos

- Capturar imagens de uma webcam e localizar uma mão no quadro.
- Reconhecer um conjunto pequeno de gestos ou posições da mão.
- Traduzir os gestos reconhecidos em comandos de jogo configuráveis.
- Enviar os comandos ao jogo sem exigir modificação do jogo ou do emulador.
- Permitir que a pessoa veja o vídeo e o estado dos comandos durante o uso.
- Encerrar a captura e liberar a câmera de forma segura.

## 3. Escopo do MVP

### Incluído

- Execução local em computador com Python e webcam compatível.
- Rastreamento de uma mão.
- Mapeamento de gestos para teclas direcionais e ações configuráveis.
- Pré-visualização da câmera com indicação do gesto/comando detectado.
- Configuração básica de câmera, limiar de confiança e mapeamento de comandos.
- Atalho para encerrar o aplicativo e liberar os recursos.

### Fora do escopo inicial

- Controle por voz, corpo inteiro ou múltiplas mãos.
- Treinamento de modelos próprios ou coleta de dados para treinamento.
- Suporte a controles físicos ou comunicação direta com hardware de console.
- Compatibilidade garantida com todo jogo, emulador ou sistema operacional.
- Armazenamento, transmissão ou gravação de vídeo.

## 4. Requisitos funcionais

| ID | Requisito |
| --- | --- |
| RF-01 | O aplicativo deve permitir selecionar a câmera disponível, usando a câmera padrão quando nenhuma seleção for informada. |
| RF-02 | O aplicativo deve iniciar a captura de vídeo e informar claramente quando a câmera não puder ser aberta. |
| RF-03 | O aplicativo deve detectar e rastrear uma mão no vídeo em tempo real. |
| RF-04 | O aplicativo deve reconhecer pelo menos os gestos configurados para mover para esquerda, direita, cima e baixo, além de uma ação. |
| RF-05 | O mapeamento entre gestos e teclas deve ser configurável sem alterar o código-fonte, por meio de um arquivo de configuração. |
| RF-06 | O aplicativo deve enviar ao jogo a tecla associada ao gesto reconhecido e liberar a tecla quando o gesto deixar de ser reconhecido. |
| RF-07 | O aplicativo deve aplicar um limiar de confiança configurável e não deve emitir comando quando a detecção estiver abaixo desse limiar. |
| RF-08 | A janela de pré-visualização deve mostrar a imagem capturada e o gesto/comando atual, ou indicar que nenhum gesto válido foi detectado. |
| RF-09 | O aplicativo deve permitir encerrar a execução por meio de um atalho de teclado e liberar todas as teclas pressionadas e a câmera ao sair. |
| RF-10 | O aplicativo deve apresentar mensagens úteis para falhas de inicialização, câmera indisponível e configuração inválida. |

## 5. Requisitos não funcionais

| ID | Requisito |
| --- | --- |
| RNF-01 | O processamento deve ocorrer localmente; os quadros da câmera não devem ser enviados pela rede nem gravados em disco. |
| RNF-02 | Em condições normais no equipamento-alvo, o aplicativo deve buscar uma taxa mínima de 20 quadros por segundo e uma latência de resposta inferior a 150 ms. Esses valores devem ser verificados em testes no equipamento definido para a entrega. |
| RNF-03 | A perda temporária da mão não deve travar o aplicativo nem deixar uma tecla de movimento pressionada indefinidamente. |
| RNF-04 | O encerramento normal ou causado por erro deve liberar a câmera e qualquer tecla virtual ainda pressionada. |
| RNF-05 | O código deve ser organizado em componentes separáveis para captura, reconhecimento de gestos, mapeamento de comandos e interface. |
| RNF-06 | As dependências e instruções de instalação e execução devem ser documentadas. |
| RNF-07 | Os limiares e mapeamentos devem ser ajustáveis sem recompilar ou modificar a lógica principal do programa. |

## 6. Gestos e controles iniciais

O MVP deve usar gestos simples, distinguíveis e configuráveis. A implementação
deve documentar quais gestos foram escolhidos e como realizá-los. Sugestão
inicial de mapeamento:

| Comando | Tecla padrão | Gesto |
| --- | --- | --- |
| Esquerda | `LEFT` | Mão deslocada para o lado esquerdo da área de controle |
| Direita | `RIGHT` | Mão deslocada para o lado direito da área de controle |
| Cima | `UP` | Mão deslocada para a parte superior da área de controle |
| Baixo | `DOWN` | Mão deslocada para a parte inferior da área de controle |
| Ação | `Z` | Gesto de ação configurado, por exemplo, fechar a mão |

Os nomes das teclas são exemplos; a configuração deve permitir substituí-los
pelas teclas esperadas pelo jogo ou emulador. O comando neutro, quando não há
gesto válido, deve liberar as teclas direcionais mantidas pelo aplicativo.

## 7. Interface e operação

1. A pessoa instala as dependências e configura o mapeamento, se necessário.
2. Inicia o programa e seleciona a câmera, quando houver mais de uma.
3. Posiciona a mão dentro da área visível e confirma na pré-visualização que o
   rastreamento está funcionando.
4. Coloca o jogo ou emulador em foco. A aplicação deve deixar claro que o jogo
   precisa estar apto a receber as teclas simuladas.
5. Usa os gestos para enviar comandos e encerra pelo atalho indicado na
   interface.

## 8. Requisitos técnicos e proposta de implementação

- Linguagem: Python 3.
- Captura e exibição de vídeo: OpenCV.
- Detecção de mão: biblioteca de rastreamento de mãos compatível com Python
  (a seleção da biblioteca deve ser confirmada durante a implementação).
- Emissão de teclas: biblioteca de entrada de teclado compatível com o sistema
  operacional de destino.
- Configuração: arquivo legível, como TOML ou YAML, contendo câmera,
  confiança mínima, gestos e teclas.
- Organização sugerida: módulos independentes para captura, reconhecimento,
  mapeamento/saída de comandos, configuração e aplicação/interface.

A escolha final das bibliotecas deve considerar licença, compatibilidade com a
versão de Python adotada e suporte ao sistema operacional de destino. O
aplicativo não deve depender de acesso à memória do jogo ou do emulador.

## 9. Critérios de aceitação

- Com uma webcam funcional, o aplicativo inicia e apresenta a pré-visualização.
- Gestos reconhecidos produzem as teclas configuradas, e gestos neutros ou
  detecções abaixo do limiar não produzem comandos.
- Ao deixar de reconhecer um gesto direcional, o aplicativo libera a tecla
  correspondente.
- A pessoa consegue alterar ao menos uma tecla no arquivo de configuração e
  confirmar que o novo mapeamento é aplicado na execução seguinte.
- Se a câmera estiver indisponível ou a configuração for inválida, o aplicativo
  exibe uma mensagem útil e termina sem deixar recursos ocupados.
- Ao encerrar o programa, a câmera é liberada e nenhuma tecla virtual
  permanece pressionada.
- Em um teste no equipamento-alvo, o desempenho é medido e comparado às metas
  de taxa de quadros e latência definidas em RNF-02.
- Os quadros da câmera são processados localmente e não são gravados nem
  transmitidos.

## 10. Riscos e decisões pendentes

- **Sistema operacional de destino:** permissões de câmera e formas de
  simular teclas variam. Deve ser definido antes de escolher a biblioteca de
  entrada.
- **Jogo/emulador de referência:** a recepção de teclas simuladas depende do
  jogo, do emulador e do modo de execução. É necessário validar a combinação
  escolhida.
- **Gestos definitivos:** os exemplos desta especificação precisam ser
  avaliados quanto à ergonomia e à distinção entre comandos.
- **Desempenho:** iluminação, câmera, distância e capacidade do computador
  afetam a detecção e a latência; as metas devem ser testadas no equipamento
  de referência.
- **Foco da janela:** algumas tecnologias de entrada só enviam teclas à janela
  ativa. A interface deve explicar esse requisito e evitar indicar sucesso
  quando não for possível confirmar a entrega ao jogo.

## 11. Evoluções possíveis

- Calibração da área de controle e dos gestos por pessoa.
- Opção de usar duas mãos e combinações de comandos.
- Interface para editar mapeamentos sem alterar o arquivo manualmente.
- Perfis de configuração por jogo ou emulador.
- Testes automatizados para reconhecimento/mapeamento com quadros de exemplo
  não sensíveis e sem captura de dados pessoais.
