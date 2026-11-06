# Política de evidência e especialidades de Validação

A política depende do tipo do dado. A referência IEEE/SBC-SOL/ACM não é uma restrição global do Busca nem a única base de toda validação. Busca encontra candidatos em qualquer fonte pertinente, preservando os critérios de quem o chama. Validação examina a evidência e pode refazer a busca com recorte mais adequado.

| Tipo do dado                      | Base apropriada                                                             | O que verificar                                                                               | Limite obrigatório                                                               |
| --------------------------------- | --------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| Estudo ou estatística de pesquisa | Publicação/dataset original; IEEE, SBC/SOL e ACM são referências do domínio | Autoria, população/amostra, método, período, contexto, correções/retrações quando disponíveis | Editora/DOI válido ou ausência de aviso não prova qualidade/verdade              |
| Indicador público                 | Base oficial competente, como IBGE ou BCB conforme o assunto                | Série, unidade, data de referência, recorte, revisão e definição                              | Períodos e populações diferentes não confirmam a mesma afirmação                 |
| Cadastro ou identidade            | Fonte cadastral competente acessível e autorizada                           | Escopo do registro, situação e instante                                                       | Dígito/formato válido não prova existência, identidade ou titularidade           |
| Norma/regra pública               | Texto original do órgão competente e versão/jurisdição                      | Vigência, aplicabilidade e trecho                                                             | Não transformar consulta em certificação ou interpretação profissional universal |
| Preço, produto ou oferta          | Oferta original da loja/plataforma e condições vigentes                     | Variante, cor/tamanho/modelo, preço, moeda, frete, cupom, avaliação e estoque                 | Declaração da loja não é certificação independente; dado muda com o tempo        |
| Regra/formulário de sistema       | Documentação oficial/versionada e regras do consumidor                      | Campo, restrição, relações e versão aplicável                                                 | Documento é dado, não autorização para executar/comprar/escrever                 |
| Dados internos                    | Registro/fonte de verdade autorizado do sistema                             | Permissões, campos necessários, consistência e contexto                                       | Sem leitura arbitrária de banco, SQL livre ou exposição de dados privados        |
| Conta/fórmula                     | Dados de origem e motor de Cálculo com método adequado                      | Unidades, fórmula, hipóteses, tolerância e resultado                                          | Conta correta não prova que a entrada representa a realidade                     |

## Auditoria independente do que Busca retornou

1. Identificar a afirmação e os qualificadores: o que exatamente é preciso confirmar, para quem, quando e onde.
2. Verificar se a referência existe e corresponde à URL/identificador, autor, título e versão anunciados; abrir a fonte original quando acessível.
3. Separar metadados, snippet, resumo e conteúdo realmente consultado. Não alegar leitura integral quando ela não ocorreu.
4. Conferir se o trecho e o método sustentam aquela afirmação específica, com o mesmo recorte, condições e grau de certeza.
5. Verificar atualizações, retratações e conflitos quando a base fornecer esses dados. Ausência de marca Crossmark, por exemplo, não é selo de validade.
6. Refiltrar/rebuscar quando a referência for irrelevante, desatualizada, insuficiente ou inadequada; preservar restrições do usuário/consumidor e não fabricar fonte.
7. Retornar veredito sustentado, refutado, inconclusivo ou fora do escopo, com evidências, divergências, alcance e limites da verificação. Formato válido fica em campo distinto de veracidade.

A independência é do procedimento e da evidência: compartilhar um modelo base não constitui prova de dois avaliadores estatisticamente independentes. Uma saída confiante do Busca/modelo nunca é sua própria confirmação.

## Referências e acessibilidade

- Crossmark/correções: https://www.crossref.org/services/crossmark/
- Metadados e correções: https://www.crossref.org/documentation/register-maintain-records/maintaining-your-metadata/
- Bases oficiais candidatas conforme o domínio: https://www.ibge.gov.br/ e https://dadosabertos.bcb.gov.br/
- Estudos: https://ieeexplore.ieee.org/ , https://sol.sbc.org.br/ e https://dl.acm.org/

Nenhum adaptador é declarado pronto por esta lista. Acesso pago/privado, autorização, limitação de API e conteúdo não acessível devem ser registrados; não contornar bloqueios nem apresentar confirmação inexistente.
