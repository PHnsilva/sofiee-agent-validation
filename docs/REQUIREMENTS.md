# Requisitos e escopo vigente — ciclo inicial

Validação orientada ao tipo de dado, ao contexto e à evidência apropriada, com revisão independente das fontes de Busca.

Definido a partir das decisões de Pedro até 06/11/2026. Documento de planejamento; não comprova implementação, treinamento, revisão ou aceite. As alterações são propostas no PR de organização, sem merge por agente.

## Requisitos funcionais

| ID  | Resultado exigido                                                                                                                                                                                                   |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| F01 | Receber afirmação/dados/contexto/regras e devolver veredito estruturado, escopo de verificação e evidências por MCP.                                                                                                |
| F02 | Selecionar método e base conforme o tipo: formato, cálculo, dado de sistema, fato externo, indicador oficial, produto/oferta ou estudo.                                                                             |
| F03 | Validar formulários, campos, relações e regras do sistema consumidor usando documentação versionada e dados autorizados.                                                                                            |
| F04 | Conferir formatos, datas, unidades e dígitos verificadores sem confundir estrutura válida com identidade ou fato comprovado.                                                                                        |
| F05 | Avaliar estudos e estatísticas de pesquisa com fontes acadêmicas adequadas, incluindo IEEE/SBC-SOL/ACM, verificando método, contexto, atualização e limites. A política é por domínio, não uma whitelist universal. |
| F06 | Validar fatos, indicadores e registros pela fonte primária ou base competente para o dado (oficial, cadastral, normativa ou do detentor), com recorte de tempo/localidade e autorização apropriados.                |
| F07 | Validar ofertas, preços, variantes e atributos em fontes originais atuais, distinguindo declaração de vendedor de fato independentemente comprovado.                                                                |
| F08 | Abrir, refiltrar e conferir independentemente referências recuperadas por Busca: existência, origem, data/versão, conteúdo acessível e suporte efetivo ao dado/afirmação.                                           |
| F09 | Reconciliar evidências conflitantes, parciais ou ausentes e retornar sustentado/refutado/inconclusivo/fora do escopo com justificativa.                                                                             |
| F10 | Delegar buscas e cálculos necessários por contratos de leitura, preservando permissões e limites do consumidor.                                                                                                     |

## Requisitos não funcionais

| ID  | Critério                                                                                                                                                                                                                                                                                                              |
| --- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| N01 | Contribuição rastreável por issue/branch/PR; somente Pedro revisa/aprova PRs e aceita issues, sem merge/auto-merge/deploy de agentes. Durante a semana, dependência tecnicamente disponível em branch/PR validado pode ser consumida provisoriamente em PR empilhado; revisão/aceite/merge ficam com Pedro no sábado. |
| N02 | Contratos versionados, entradas/saídas validadas e erros explícitos; dados externos nunca concedem permissões.                                                                                                                                                                                                        |
| N03 | Sem serviço pago obrigatório, faturamento ou fallback remoto automático; executar ferramentas/caches no C: e respeitar pausas.                                                                                                                                                                                        |
| N04 | Testes de sucesso/erro e avaliações reais reproduzíveis; registrar versões e distinguir mock, execução e aceite humano.                                                                                                                                                                                               |
| N05 | Minimização de dados, credenciais fora do Git, acesso mínimo e retenção/exclusão definidas; não publicar dados reais de usuários.                                                                                                                                                                                     |
| N06 | Limites de entrada, memória, concorrência e tempo configuráveis, cancelamento e falha fechada; medir desempenho no hardware disponível.                                                                                                                                                                               |
| N07 | Documentação operacional coerente com código e evidências; disponibilidade ou qualidade não podem ser inferidas de um perfil ou schema.                                                                                                                                                                               |
| N08 | Até cinco sprints de entrega + uma de validação/mudanças, cada uma até uma semana; estimativas PP/P/M/L=1/2/4/8 e meta mínima de 8 unidades/dia por projeto ativo.                                                                                                                                                    |

## Fora do ciclo

- Revisão de arquitetura, código e PRs (responsabilidade do SlothEngineer).
- Veredito universal de verdade sem evidência suficiente.
- Acesso irrestrito a banco, dados privados ou credenciais.
- Limitar todo tipo de dado a IEEE/SBC/ACM ou a documentação de software.

## Verificação e aceite

Cada requisito é rastreado em TRACEABILITY.md, com critérios concretos no corpo das issues. Dados conhecidos/sintéticos e ferramentas determinísticas verificam resultados quando possível; comportamento generativo exige casos separados e revisão apropriada. Não usar um teste de roteamento, presença de perfil ou metadado para alegar competência ou treino. Não declarar cobertura completa quando há pendência de ambiente/fonte.

A meta de 8 unidades/dia é um mínimo desejado por projeto ativo, não um teto de esforço nem uma medição de inteligência. A duração semanal é o objetivo do plano; a capacidade real e os bloqueios precisam ser observados e reportados. Não fabricar tarefa/estimativa/aceite para cumprir calendário.
