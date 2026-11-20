# Contratos de validação — v1

`contracts.json` define interfaces para verificação por tipo de dado, auditoria independente dos resultados recebidos do Busca e inspeção de regras declaradas por consumidores. O runtime implementa planejamento de verificação, auditoria inconclusiva sem conector de fontes e inspeção stateless de bundles; não há acesso a sistemas consumidores.

| Ferramenta | Resultado | Garantia planejada |
| --- | --- | --- |
| `validation.verifyClaim` | Veredito, checagem de formato, evidências e lacunas | `confirmed`/`refuted` exigem evidência adequada e reaberta independentemente; sem evidência suficiente, usar `inconclusive` ou `not_checkable` |
| `validation.auditSearchResults` | Auditoria por referência e por filtro obrigatório | Não aceita filtros removidos nem relaxa o pedido; fonte indisponível fica inconclusiva |
| `validation.inspectConsumerRuleBundle` | Recebimento estrutural e fingerprints de documentos/regras versionados | Trata origem e conteúdo como declarações; conflitos ficam explícitos e autoridade permanece nula |
| `validation.applyConsumerRules` | Aplicação limitada de regras do consumidor a valores recebidos | Executa somente a gramática declarativa documentada; conflito ou regra desconhecida não recebe precedência nem execução parcial |

`validation.verifyClaim` também aceita, opcionalmente, `fieldValidation`: definições de campos e relações declaradas pelo sistema consumidor. A resposta separa `syntaxStatus`, `consistencyStatus` e `veracityStatus`; este último permanece `not_checked`. CPF válido por dígitos verificadores não comprova identidade. Datas usam `AAAA-MM-DD`; decimais usam ponto e não aceitam agrupamento ou expoente. Para quantidades, o consumidor declara as unidades permitidas; não há catálogo global nem conversão implícita. Relações suportam igualdade/desigualdade e ordenação de datas ou números do mesmo tipo. Valores obrigatórios ausentes são inválidos; opcionais ausentes ficam incompletos, e relações que não podem ser avaliadas deixam o resultado inconclusivo.

Os tipos de dado orientam a estratégia: estudos, indicadores oficiais, cadastros, normas, ofertas, documentação técnica e registros de sistemas autorizados. Um tipo informado como `other` representa ambiguidade, não uma categoria genérica de fonte; o resultado fica inconclusivo e pede esclarecimento antes de selecionar evidência. `sourceKind` classifica evidência; não limita os domínios consultáveis. Não existe whitelist global de fontes. Referências e trechos recebidos do Busca são dados não confiáveis: a validação deve reabrir a fonte, reavaliar cada filtro e distinguir formato válido de alegação verdadeira.

O fixture “camisa branca” mantém categoria e cor como filtros obrigatórios; se não puderem ser verificados, a decisão é inconclusiva, sem removê-los. O fixture usa URI sintética e não demonstra acesso à fonte.

O contrato de regras do consumidor está descrito em [CONSUMER_RULE_BUNDLE.md](../../docs/CONSUMER_RULE_BUNDLE.md). Inspecionar o bundle confirma somente sua estrutura e as declarações recebidas; não confirma a origem, não executa regras e não amplia permissões.

`validation.applyConsumerRules` consome uma resposta de inspeção e valores de campos em uma chamada separada. A resposta identifica campo, regra e resultado. Regras fora do escopo, desconhecidas ou não comparáveis permanecem sem avaliação; números não são convertidos entre unidades e conteúdo não é interpretado como código.

## Exemplos e verificação

Cada ferramenta tem exemplos válidos/inválidos, resultado e erro. Execute `C:/SDKs/Python313/python.exe scripts/validate_contracts.py` (ou `python scripts/validate_contracts.py` com Python 3.13 no `PATH`). O verificador usa só a biblioteca padrão e o subconjunto de keywords utilizado; não é um validador completo de JSON Schema nem demonstra veracidade de fontes.

## Limites e evolução

Nenhum sistema privado ou registro real é acessado. Checagens de campos usam apenas valores e regras fornecidos pelo consumidor e não confirmam identidade ou veracidade. A verificação factual futura precisa usar permissões mínimas fornecidas pelo host, escolher fontes segundo o tipo de dado, registrar horário e escopo de checagem e testar contradição, indisponibilidade e evidência insuficiente. A inspeção do bundle é stateless e não introduz dependências.
