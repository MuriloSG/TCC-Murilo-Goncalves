## ADDED Requirements

### Requirement: Abrangência e tom do texto exibido
As regras desta spec DEVEM (MUST) valer para todo texto exibido ao usuário: conteúdo visível e atributos `placeholder`, `title`, `alt`, `aria-label` e `value` de botões nos templates HTML; templates de texto de e-mail e de mensagens; strings passadas a `django.contrib.messages` e a `ValidationError`; rótulos, ajudas, opções vazias e mensagens de erro de formulários; e mensagens do Django e do allauth mostradas nas rotas expostas. O texto DEVE (MUST) ser impessoal, com o imperativo nas instruções e a terceira pessoa nos fatos, e NÃO DEVE (MUST NOT) usar "você", "vocês", "nós" nem verbos na primeira pessoa do plural. O possessivo que indica o que pertence ao usuário ("seu perfil", "sua senha") é permitido.

#### Scenario: Página de acesso negado
- **WHEN** um usuário autenticado sem a permissão acessa uma rota protegida e recebe a página 403
- **THEN** o texto informa que a página exige uma permissão que o perfil não concede e indica procurar um administrador do sistema, sem a palavra "você"

#### Scenario: Solicitação de recuperação de senha
- **WHEN** um visitante envia o formulário de recuperação de senha
- **THEN** a página seguinte informa, na terceira pessoa, que o link é enviado se o e-mail pertencer a um usuário ativo, sem "enviaremos" nem "você receberá"

#### Scenario: Mensagem do allauth ao sair
- **WHEN** um usuário autenticado faz logout
- **THEN** a mensagem exibida não contém "Você saiu"

### Requirement: Expressões e símbolos proibidos
O texto exibido NÃO DEVE (MUST NOT) conter: ponto de exclamação; emoji; travessão (— ou –); reticências; interjeições ("Ops", "Oops", "Opa", "Eba", "Uau"); saudações ("Olá", "Bem-vindo", "Bem-vinda", "Que bom"); mensagens vagas ("Algo deu errado", "Parece que", "Ocorreu um erro"); "por favor"; "com sucesso"; e as palavras de marketing jornada, experiência, potencialize, descubra, incrível, simples, facilmente, simplesmente, perfeito, poderoso e intuitivo, com as flexões. Texto de preenchimento, lorem ipsum e dados fictícios NÃO DEVEM (MUST NOT) aparecer em templates. Uma célula ou um campo sem valor DEVE (MUST) mostrar um texto explícito ("Sem descrição").

#### Scenario: Perfil sem descrição
- **GIVEN** um perfil personalizado criado sem descrição
- **WHEN** a página de detalhe do perfil é exibida
- **THEN** o campo Descrição mostra "Sem descrição", e não um travessão

#### Scenario: Página inicial
- **WHEN** um usuário autenticado acessa a página inicial
- **THEN** a página não contém "Olá" nem ponto de exclamação

#### Scenario: Cadastro de usuário concluído
- **WHEN** um usuário com a permissão cadastra outro usuário
- **THEN** a mensagem de sucesso não contém "com sucesso" nem ponto de exclamação

### Requirement: Botões, títulos e maiúsculas
Todo botão e todo link que executa ou inicia uma ação DEVE (MUST) começar por um verbo no infinitivo, com o objeto quando o verbo sozinho for ambíguo na tela ("Cadastrar usuário", "Desativar usuário", "Excluir perfil"). Num botão só com ícone, essa regra vale para o `aria-label` e para a dica. Os gatilhos de menu "Menu" e "Mais ações" são a exceção, porque não executam ação. Títulos, botões, rótulos e cabeçalhos de tabela DEVEM (MUST) ter maiúscula só na primeira palavra, em nomes próprios e em siglas. Títulos NÃO DEVEM (MUST NOT) ter dois-pontos seguidos de complemento.

#### Scenario: Botão da confirmação de desativação
- **WHEN** a confirmação de desativação de um usuário é exibida
- **THEN** o botão que executa a ação tem o texto "Desativar usuário"

#### Scenario: Título com nome próprio
- **WHEN** um template contém o título "Cadastrar Usuário"
- **THEN** a verificação automática aponta a maiúscula em "Usuário"

### Requirement: Mensagens de sucesso e de erro
A mensagem de sucesso DEVE (MUST) informar o fato no particípio e identificar o objeto ("Usuário ana@ifnmg.edu.br desativado."). A mensagem de erro de uma operação recusada ou de um campo inválido DEVE (MUST) dizer o que aconteceu e o que fazer para prosseguir, com o termo do domínio, sempre que existir uma ação possível para o usuário.

#### Scenario: Exclusão de perfil com usuários vinculados
- **GIVEN** um perfil personalizado com usuários vinculados
- **WHEN** um superadmin tenta excluí-lo
- **THEN** a mensagem informa que o perfil tem usuários vinculados e orienta trocar o perfil desses usuários antes de excluí-lo

#### Scenario: E-mail inválido no cadastro
- **WHEN** o formulário de cadastro de usuário é enviado com um e-mail em formato inválido
- **THEN** a mensagem do campo usa o termo "e-mail", com hífen, e orienta informar um e-mail válido

#### Scenario: Credenciais incorretas no login
- **WHEN** um visitante informa e-mail ou senha incorretos
- **THEN** a mensagem informa que o e-mail ou a senha não conferem e orienta conferir os dados ou usar "Esqueci minha senha"

### Requirement: Confirmação de ações
Toda confirmação, em página ou em modal, DEVE (MUST) ter como título a pergunta com o nome do objeto ("Desativar Ana Souza?"), trazer a consequência da ação em até duas frases, oferecer um botão com o verbo específico da ação e oferecer o controle "Fechar" para sair sem executar. A palavra "Cancelar" NÃO DEVE (MUST NOT) ser usada para sair de uma confirmação nem de um formulário.

#### Scenario: Confirmação de exclusão de perfil
- **WHEN** um superadmin abre a confirmação de exclusão de um perfil personalizado
- **THEN** o título é "Excluir o perfil <nome>?", o texto explica a consequência, e há o botão "Excluir perfil" e o controle "Fechar"

#### Scenario: Saída da confirmação
- **WHEN** o usuário aciona "Fechar" numa confirmação
- **THEN** nenhum dado é alterado e ele volta para a tela de origem

### Requirement: Glossário único
O texto exibido DEVE (MUST) usar um único termo para cada conceito, conforme o glossário do design: desativar e reativar (nunca bloquear, suspender ou inativar), rejeitar e rejeitada (nunca reprovar, reprovada, negar ou negada), excluir (nunca apagar, deletar ou remover), entrar e sair (nunca logar, deslogar ou logout) e e-mail (nunca email). Os estados do usuário DEVEM (MUST) ser "Ativo" e "Inativo".

#### Scenario: Situação na lista de usuários
- **WHEN** a lista de usuários mostra um usuário desativado
- **THEN** a coluna Situação mostra "Inativo" e a ação oferecida é "Reativar"

#### Scenario: Sinônimo proibido em template
- **WHEN** um template contém a palavra "Bloquear"
- **THEN** a verificação automática falha e indica o termo do glossário "desativar"

### Requirement: Formatos brasileiros de data, hora e número
Datas DEVEM (MUST) ser exibidas como dd/mm/aaaa, horas no formato de 24 horas com dois dígitos (hh:mm) e números com ponto como separador de milhar e vírgula decimal. Esses formatos DEVEM (MUST) vir da localização configurada no projeto, de modo que os filtros e a renderização padrão do Django os produzam sem formato escrito no template.

#### Scenario: Data renderizada
- **WHEN** a data 18 de setembro de 2026 é renderizada num template com o filtro `date` sem argumento
- **THEN** o texto exibido é "18/09/2026"

#### Scenario: Hora e número renderizados
- **WHEN** a hora 10:00 e o número 1234,5 são renderizados num template
- **THEN** os textos exibidos são "10:00" e "1.234,5"

### Requirement: Verificação automática do texto
A suíte de testes DEVE (MUST) percorrer todos os templates do projeto (HTML e texto) e as strings literais dos módulos Python dos apps do projeto, exceto docstrings, testes e migrations, e falhar ao encontrar qualquer violação das regras de expressões proibidas, de glossário e de maiúsculas em títulos e botões, informando o arquivo, a linha e o trecho. A verificação DEVE (MUST) considerar só o texto exibido, ignorando tags e comentários do Django, a declaração `<!DOCTYPE>`, comentários HTML e expressões como `!=` dentro de tags de template. A verificação DEVE (MUST) cobrir também as mensagens do allauth sobrescritas pelo projeto.

#### Scenario: Exclamação em texto visível
- **WHEN** um template contém "Usuário cadastrado!"
- **THEN** o teste falha indicando o arquivo, a linha e o trecho

#### Scenario: Operador em tag de template
- **WHEN** um template contém `{% if a != b %}` e a declaração `<!DOCTYPE html>`
- **THEN** o teste não aponta violação por causa desses trechos

#### Scenario: Palavra proibida em mensagem Python
- **WHEN** uma view passa a `messages.success` o texto "Perfil criado com sucesso."
- **THEN** o teste falha indicando o módulo e a linha

#### Scenario: Palavra em docstring
- **WHEN** uma docstring contém a palavra "simples"
- **THEN** o teste não aponta violação
