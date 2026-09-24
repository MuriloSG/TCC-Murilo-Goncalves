## MODIFIED Requirements

### Requirement: Paginação das listas
As listas de registros da interface DEVEM (MUST) ser paginadas: a lista de usuários, a lista de perfis, o histórico de importações, as linhas da prévia e do detalhe de uma importação e a lista de registros de auditoria. A página DEVE (MUST) ser escolhida pelo parâmetro `pagina` da URL, que DEVE (MUST) se combinar com os demais parâmetros da lista, e os links de navegação DEVEM (MUST) manter esses parâmetros. Um valor de `pagina` inválido DEVE (MUST) mostrar a primeira página, e um número além da última DEVE (MUST) mostrar a última, sem erro. As listas DEVEM (MUST) exibir 5 registros por página, e as linhas de uma importação, 20, valores definidos num único ponto do código. O rodapé de cada lista DEVE (MUST) informar o intervalo exibido e a quantidade de registros da lista, no formato "Exibindo 6 a 10 de 57 usuários", e oferecer os controles "Anterior" e "Próxima" e a indicação "Página X de Y". Na primeira e na última página, o controle sem destino DEVE (MUST) aparecer desabilitado, e não como link. Com uma só página, o rodapé DEVE (MUST) mostrar só o intervalo, e com a lista vazia o rodapé NÃO DEVE (MUST NOT) aparecer. A navegação DEVE (MUST) funcionar sem JavaScript e a partir de 360 px de largura.

#### Scenario: Primeira página
- **GIVEN** 57 perfis cadastrados
- **WHEN** a lista de perfis é acessada sem o parâmetro `pagina`
- **THEN** os 5 primeiros perfis são exibidos e o rodapé informa "Exibindo 1 a 5 de 57 perfis" e "Página 1 de 12"
- **AND** o controle "Anterior" aparece desabilitado e "Próxima" leva a `?pagina=2`

#### Scenario: Última página
- **GIVEN** 57 perfis cadastrados
- **WHEN** a lista de perfis é acessada com `pagina=12`
- **THEN** os perfis 56 e 57 são exibidos e o controle "Próxima" aparece desabilitado

#### Scenario: Página inválida ou além do fim
- **WHEN** uma lista é acessada com `pagina=abc` ou com `pagina=99` numa lista de 3 páginas
- **THEN** a resposta mostra, respectivamente, a primeira e a última página, sem erro

#### Scenario: Uma só página
- **GIVEN** 4 perfis cadastrados
- **WHEN** a lista de perfis é acessada
- **THEN** o rodapé informa "Exibindo 1 a 4 de 4 perfis" e não mostra os controles de navegação

#### Scenario: Parâmetros mantidos
- **GIVEN** uma importação com 50 linhas com erro
- **WHEN** a prévia é acessada com `linhas=erros`
- **THEN** o link "Próxima" leva a `?linhas=erros&pagina=2`

#### Scenario: Linhas de uma importação
- **GIVEN** uma importação com 50 linhas
- **WHEN** a prévia é acessada
- **THEN** são exibidas as 20 primeiras linhas do arquivo e o resumo continua contando as 50 linhas

#### Scenario: Lista de auditoria paginada
- **GIVEN** 57 registros de auditoria
- **WHEN** a lista de auditoria é acessada com `acao=LOGIN&pagina=2`
- **THEN** são exibidos os registros 6 a 10 do resultado filtrado e o link "Próxima" leva a `?acao=LOGIN&pagina=3`
