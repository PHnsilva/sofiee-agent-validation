# Casos e protocolo de avaliação — Validação

Os arquivos development/cases.json e regression/cases.json são públicos, sintéticos e versionados v1.0.0. Cobrem alegação de estudo, formato de data, auditoria independente de oferta, indicador oficial e registro de sistema autorizado. Cada caso exige revisão humana e distingue formato de veracidade.

O compartimento reserve tem política v1.0.0, com custódia de Pedro fora do repositório. Está definido, mas ainda não populado nesta entrega; nenhum caso privado foi criado ou publicado. Os casos públicos de regressão não são reserva oculta.

Apenas estrutura e regras de seleção/inconclusão dos fixtures são verificadas localmente. Nenhuma fonte real foi consultada, nenhum registro de sistema foi acessado e nenhum fato foi declarado verdadeiro. O verificador não é um agente de validação nem demonstra acurácia.

## Execução

Na raiz do repositório, execute scripts/validate_eval_cases.py com CPython 3.13.15. O programa valida versão, separação, cobertura de ferramentas, critérios e invariantes determinísticas aplicáveis. Um caso aprovado pelo validador de fixtures significa apenas que seus dados/rubricas são coerentes; não representa avaliação do agente, execução, baseline ou aceite humano.
