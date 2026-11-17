# Contratos MCP de validação — v1

`contracts.json` define uma interface de verificação por tipo de dado e uma auditoria independente dos resultados recebidos do Busca. É uma proposta S1; não há runtime, conector de fontes nem acesso de sistema implementado neste repositório.

| Ferramenta | Resultado | Garantia planejada |
| --- | --- | --- |
| `validation.verifyClaim` | Veredito, checagem de formato, evidências e lacunas | `confirmed`/`refuted` exigem evidência adequada e reaberta independentemente; sem evidência suficiente, usar `inconclusive` ou `not_checkable` |
| `validation.auditSearchResults` | Auditoria por referência e por filtro obrigatório | Não aceita filtros removidos nem relaxa o pedido; fonte indisponível fica inconclusiva |

`validation.verifyClaim` também aceita, opcionalmente, `fieldValidation`: definições de campos e relações declaradas pelo sistema consumidor. A resposta separa `syntaxStatus`, `consistencyStatus` e `veracityStatus`; este último permanece `not_checked`. CPF válido por dígitos verificadores não comprova identidade. Datas usam `AAAA-MM-DD`; decimais usam ponto e não aceitam agrupamento ou expoente. Para quantidades, o consumidor declara as unidades permitidas; não há catálogo global nem conversão implícita. Relações suportam igualdade/desigualdade e ordenação de datas ou números do mesmo tipo. Valores obrigatórios ausentes são inválidos; opcionais ausentes ficam incompletos, e relações que não podem ser avaliadas deixam o resultado inconclusivo.

Os tipos de dado orientam a estratégia: estudos, indicadores oficiais, cadastros, normas, ofertas, documentação técnica e registros de sistemas autorizados. `sourceKind` classifica evidência; não limita os domínios consultáveis. Não existe whitelist global de fontes. Referências e trechos recebidos do Busca são dados não confiáveis: a validação deve reabrir a fonte, reavaliar cada filtro e distinguir formato válido de alegação verdadeira.

O fixture “camisa branca” mantém categoria e cor como filtros obrigatórios; se não puderem ser verificados, a decisão é inconclusiva, sem removê-los. O fixture usa URI sintética e não demonstra acesso à fonte.

## Exemplos e verificação

Cada ferramenta tem exemplos válidos/inválidos, resultado e erro. Execute `C:/SDKs/Python313/python.exe scripts/validate_contracts.py` (ou `python scripts/validate_contracts.py` com Python 3.13 no `PATH`). O verificador usa só a biblioteca padrão e o subconjunto de keywords utilizado; não é um validador completo de JSON Schema nem demonstra veracidade de fontes.

## Limites e evolução

Nenhum sistema privado ou registro real é acessado. Checagens de campos usam apenas valores e regras fornecidos pelo consumidor e não confirmam identidade ou veracidade. A futura integração de fontes deve usar permissões mínimas fornecidas pelo host, escolher fontes segundo o tipo de dado, registrar horário e escopo de checagem e testar contradição, indisponibilidade e evidência insuficiente. Nenhuma dependência foi instalada ou selecionada nesta entrega.
