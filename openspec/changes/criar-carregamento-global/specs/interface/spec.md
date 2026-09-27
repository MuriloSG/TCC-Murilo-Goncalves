## ADDED Requirements

### Requirement: Carregamento global
Toda página DEVE (MUST) ter uma única instância do carregamento global, declarada no `base.html` e oculta ao abrir a página. Qualquer script DEVE (MUST) poder ativá-lo com `IFAgenda.loading.show`, com mensagem opcional, e desativá-lo com `IFAgenda.loading.hide`. Ativo, o carregamento DEVE (MUST) cobrir toda a tela com um spinner centralizado, sem rolagem, e NENHUMA interação do usuário DEVE (MUST) chegar à página abaixo, inclusive a modais abertos. O envio de qualquer formulário e toda requisição htmx feita por um formulário, inclusive os filtros, DEVEM (MUST) ativar o carregamento, exceto quando o formulário declara `data-loading="false"`, e o carregamento DEVE (MUST) ser desativado ao fim dessa requisição htmx, salvo quando a resposta redireciona. `IFAgenda.loading.run` DEVE (MUST) desativar o carregamento ao fim da operação, com sucesso ou com erro.

#### Scenario: Estado inicial
- **WHEN** qualquer página é aberta
- **THEN** o carregamento está oculto e a página responde normalmente

#### Scenario: Ativação bloqueia a interação
- **GIVEN** o carregamento ativado com a mensagem "Processando..."
- **WHEN** o usuário clica num link, num botão ou tenta enviar um formulário
- **THEN** nenhuma ação é executada e o spinner e a mensagem continuam visíveis

#### Scenario: Desativação libera a interação
- **GIVEN** o carregamento ativo
- **WHEN** ele é desativado
- **THEN** o carregamento some e a página volta a responder

#### Scenario: Envio de formulário
- **WHEN** o usuário envia o formulário de importação de planilha
- **THEN** o carregamento é ativado com a mensagem "Importando a planilha" até a resposta

#### Scenario: Formulário recusado no modal
- **GIVEN** um formulário de modal enviado pelo htmx com um campo inválido
- **WHEN** a resposta chega com o erro
- **THEN** o carregamento é desativado e o modal com o erro volta a responder

#### Scenario: Filtro
- **WHEN** o usuário digita "ana" na busca da lista de usuários
- **THEN** o carregamento é ativado durante a requisição do filtro e desativado ao fim dela, com o foco de volta na busca

#### Scenario: Operação com erro
- **WHEN** uma operação executada com `IFAgenda.loading.run` falha
- **THEN** o carregamento é desativado
