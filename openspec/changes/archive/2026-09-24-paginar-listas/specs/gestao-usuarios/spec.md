## MODIFIED Requirements

### Requirement: Busca e filtro na lista de usuários
A lista de usuários DEVE (MUST) aceitar uma busca por trecho do nome ou do e-mail, sem diferenciar maiúsculas de minúsculas, e um filtro por situação com as opções todas, ativos e inativos. Busca e filtro DEVEM (MUST) valer juntos e ser recebidos como parâmetros da URL da lista (`busca` e `situacao`), de modo que o mesmo endereço reproduza o mesmo resultado. Um valor de `situacao` fora das opções DEVE (MUST) ser tratado como todas. A lista DEVE (MUST) manter a ordem por nome e ser paginada conforme a spec `interface`, com a página combinada à busca e ao filtro. Mudar a busca ou o filtro DEVE (MUST) voltar para a primeira página. O título do cartão DEVE (MUST) informar quantos usuários existem no total, e o rodapé DEVE (MUST) informar o intervalo exibido dentro do resultado da busca. Quando nenhum usuário atender à busca, a lista DEVE (MUST) informar isso em texto e oferecer um link para limpar a busca. A busca, o filtro e a paginação NÃO DEVEM (MUST NOT) alterar dados nem mudar quem pode acessar a lista.

#### Scenario: Busca por trecho do nome
- **GIVEN** os usuários "Ana Souza", "Bruno Lima" e "Carla Mendes"
- **WHEN** a lista é acessada com `busca=SOU`
- **THEN** só "Ana Souza" é exibida, o título informa 3 usuários e o rodapé informa "Exibindo 1 a 1 de 1 usuário"

#### Scenario: Busca por trecho do e-mail
- **GIVEN** o usuário "Bruno Lima" com o e-mail `bruno.lima@ifnmg.edu.br`
- **WHEN** a lista é acessada com `busca=bruno.lima`
- **THEN** "Bruno Lima" é exibido

#### Scenario: Filtro por situação
- **GIVEN** dois usuários ativos e um inativo
- **WHEN** a lista é acessada com `situacao=inativos`
- **THEN** só o usuário inativo é exibido

#### Scenario: Busca e filtro combinados
- **GIVEN** "Ana Souza" ativa e "Ana Clara" inativa
- **WHEN** a lista é acessada com `busca=ana&situacao=ativos`
- **THEN** só "Ana Souza" é exibida

#### Scenario: Situação inválida
- **WHEN** a lista é acessada com `situacao=qualquer`
- **THEN** todos os usuários são exibidos

#### Scenario: Busca sem resultado
- **WHEN** a lista é acessada com uma busca que não corresponde a nenhum usuário
- **THEN** a lista mostra "Nenhum usuário encontrado para a busca." e um link "Limpar busca" para a lista sem parâmetros

#### Scenario: Busca paginada
- **GIVEN** 11 usuários com "Silva" no nome
- **WHEN** a lista é acessada com `busca=silva&pagina=2`
- **THEN** são exibidos os usuários 6 a 10 do resultado e o link "Próxima" leva a `?busca=silva&pagina=3`

#### Scenario: Atualização pelo htmx
- **WHEN** a lista recebe um GET com `busca=ana` e o cabeçalho `HX-Request` vindo do formulário de filtros ou da navegação entre páginas
- **THEN** a resposta contém só o fragmento da tabela e do rodapé com o resultado filtrado

#### Scenario: Busca sem a permissão
- **GIVEN** um usuário ativo autenticado sem a permissão de visualizar usuários
- **WHEN** ele acessa a lista com `busca=ana`
- **THEN** a requisição é recusada com 403
