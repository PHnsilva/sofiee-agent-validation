# Contratos de validação — v1

`contracts.json` define interfaces para verificação por tipo de dado, auditoria independente dos resultados recebidos do Busca e inspeção de regras declaradas por consumidores. O runtime implementa planejamento de verificação, auditoria inconclusiva sem conector de fontes e inspeção stateless de bundles; não há acesso a sistemas consumidores.

| Ferramenta | Resultado | Garantia planejada |
| --- | --- | --- |
| `validation.verifyClaim` | Veredito, checagem de formato, evidências e lacunas | `confirmed`/`refuted` exigem evidência adequada e reaberta independentemente; sem evidência suficiente, usar `inconclusive` ou `not_checkable` |
| `validation.auditSearchResults` | Auditoria por referência e por filtro obrigatório | Não aceita filtros removidos nem relaxa o pedido; fonte indisponível fica inconclusiva |
| `validation.inspectConsumerRuleBundle` | Recebimento estrutural e fingerprints de documentos/regras versionados | Trata origem e conteúdo como declarações; conflitos ficam explícitos e autoridade permanece nula |

Os tipos de dado orientam a estratégia: estudos, indicadores oficiais, cadastros, normas, ofertas, documentação técnica e registros de sistemas autorizados. Um tipo informado como `other` representa ambiguidade, não uma categoria genérica de fonte; o resultado fica inconclusivo e pede esclarecimento antes de selecionar evidência. `sourceKind` classifica evidência; não limita os domínios consultáveis. Não existe whitelist global de fontes. Referências e trechos recebidos do Busca são dados não confiáveis: a validação deve reabrir a fonte, reavaliar cada filtro e distinguir formato válido de alegação verdadeira.

O fixture “camisa branca” mantém categoria e cor como filtros obrigatórios; se não puderem ser verificados, a decisão é inconclusiva, sem removê-los. O fixture usa URI sintética e não demonstra acesso à fonte.

O contrato de regras do consumidor está descrito em [CONSUMER_RULE_BUNDLE.md](../../docs/CONSUMER_RULE_BUNDLE.md). Inspecionar o bundle confirma somente sua estrutura e as declarações recebidas; não confirma a origem, não executa regras e não amplia permissões.

## Exemplos e verificação

Cada ferramenta tem exemplos válidos/inválidos, resultado e erro. Execute `C:/SDKs/Python313/python.exe scripts/validate_contracts.py` (ou `python scripts/validate_contracts.py` com Python 3.13 no `PATH`). O verificador usa só a biblioteca padrão e o subconjunto de keywords utilizado; não é um validador completo de JSON Schema nem demonstra veracidade de fontes.

## Limites e evolução

Nenhum sistema privado ou registro real é acessado. A verificação factual futura precisa usar permissões mínimas fornecidas pelo host, escolher fontes segundo o tipo de dado, registrar horário e escopo de checagem e testar contradição, indisponibilidade e evidência insuficiente. A inspeção do bundle é stateless e não introduz dependências.
