## ADDED Requirements

### Requirement: Paginação das listas
As listas de registros da interface DEVEM (MUST) ser paginadas: a lista de usuários, a lista de perfis, o histórico de importações e as linhas da prévia e do detalhe de uma importação. A página DEVE (MUST) ser escolhida pelo parâmetro `pagina` da URL, que DEVE (MUST) se combinar com os demais parâmetros da lista, e os links de navegação DEVEM (MUST) manter esses parâmetros. Um valor de `pagina` inválido DEVE (MUST) mostrar a primeira página, e um número além da última DEVE (MUST) mostrar a última, sem erro. As listas DEVEM (MUST) exibir 20 registros por página, e as linhas de uma importação, 50. O rodapé de cada lista DEVE (MUST) informar o intervalo exibido e a quantidade de registros da lista, no formato "Exibindo 21 a 40 de 57 usuários", e oferecer os controles "Anterior" e "Próxima" e a indicação "Página X de Y". Na primeira e na última página, o controle sem destino DEVE (MUST) aparecer desabilitado, e não como link. Com uma só página, o rodapé DEVE (MUST) mostrar só o intervalo, e com a lista vazia o rodapé NÃO DEVE (MUST NOT) aparecer. A navegação DEVE (MUST) funcionar sem JavaScript e a partir de 360 px de largura.

#### Scenario: Primeira página
- **GIVEN** 57 perfis cadastrados
- **WHEN** a lista de perfis é acessada sem o parâmetro `pagina`
- **THEN** os 20 primeiros perfis são exibidos e o rodapé informa "Exibindo 1 a 20 de 57 perfis" e "Página 1 de 3"
- **AND** o controle "Anterior" aparece desabilitado e "Próxima" leva a `?pagina=2`

#### Scenario: Última página
- **GIVEN** 57 perfis cadastrados
- **WHEN** a lista de perfis é acessada com `pagina=3`
- **THEN** os perfis 41 a 57 são exibidos e o controle "Próxima" aparece desabilitado

#### Scenario: Página inválida ou além do fim
- **WHEN** uma lista é acessada com `pagina=abc` ou com `pagina=99` numa lista de 3 páginas
- **THEN** a resposta mostra, respectivamente, a primeira e a última página, sem erro

#### Scenario: Uma só página
- **GIVEN** 5 perfis cadastrados
- **WHEN** a lista de perfis é acessada
- **THEN** o rodapé informa "Exibindo 1 a 5 de 5 perfis" e não mostra os controles de navegação

#### Scenario: Parâmetros mantidos
- **GIVEN** uma importação com 120 linhas com erro
- **WHEN** a prévia é acessada com `linhas=erros`
- **THEN** o link "Próxima" leva a `?linhas=erros&pagina=2`

#### Scenario: Linhas de uma importação
- **GIVEN** uma importação com 120 linhas
- **WHEN** a prévia é acessada
- **THEN** são exibidas as linhas 1 a 50 do arquivo e o resumo continua contando as 120 linhas
