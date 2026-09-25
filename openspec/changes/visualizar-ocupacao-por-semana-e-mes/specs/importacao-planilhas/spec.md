## ADDED Requirements

### Requirement: Validação conjunta e exibição dos campos próprios do envio
Uma importação específica PODE (MAY) declarar uma validação que recebe os valores de todos os seus campos próprios do envio, já limpos, para regras que envolvem mais de um campo. O motor DEVE (MUST) chamá-la antes de ler o arquivo, e uma recusa DEVE (MUST) ser erro do formulário de envio, sem criar importação. A regra DEVE (MUST) continuar na operação do model, e o motor NÃO DEVE (MUST NOT) conhecê-la. Uma importação específica PODE (MAY) também declarar como exibir o valor de um campo próprio, e o resumo da importação DEVE (MUST) mostrar o valor exibido quando ele existir, mantendo o valor gravado nas linhas como dado. Uma importação que não declara nenhuma das duas DEVE (MUST) continuar funcionando como antes.

#### Scenario: Campos próprios recusados juntos
- **GIVEN** uma importação específica que declara dois campos próprios de data e a validação conjunta deles
- **WHEN** o envio tem a data final anterior à inicial
- **THEN** o formulário de envio mostra o erro da validação e nenhuma importação é criada

#### Scenario: Data exibida formatada
- **GIVEN** uma importação cujo campo próprio de data foi gravado nas linhas como `2026-08-03`
- **WHEN** o resumo da importação é exibido
- **THEN** o valor aparece como `03/08/2026`, e as linhas continuam com `2026-08-03`

#### Scenario: Importação sem os ganchos
- **WHEN** uma importação de usuários é enviada e exibida
- **THEN** o envio, a prévia e o resumo se comportam como antes
