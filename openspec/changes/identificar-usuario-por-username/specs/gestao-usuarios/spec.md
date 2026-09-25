## ADDED Requirements

### Requirement: Identificador de domínio do usuário (`username`)
Todo usuário PODE (MAY) ter um `username`: um identificador textual, único no sistema, usado para reconhecê-lo em dados vindos de fora da aplicação, como a planilha de ensalamento. Ele NÃO DEVE (MUST NOT) ser usado como credencial de autenticação, conforme a spec `autenticacao`, e NÃO DEVE (MUST NOT) substituir o nome do usuário, que continua sendo o dado exibido na interface.

O `username` DEVE (MUST) aceitar qualquer texto, incluindo espaços, letras acentuadas, pontos e abreviações, com no máximo 150 caracteres. Valores como `Aldo Gomes`, `Maria Silva`, `João da Silva`, `Érica` e `Gera Jr.` DEVEM (MUST) ser aceitos. O sistema NÃO DEVE (MUST NOT) exigir formato, separador nem ausência de espaços.

O valor DEVE (MUST) ser gravado exatamente como informado quanto a maiúsculas, minúsculas e acentuação, com os espaços das bordas removidos e os espaços internos repetidos reduzidos a um. Um valor em branco DEVE (MUST) ser gravado como ausente, e não como texto vazio.

O `username` DEVE (MUST) ser opcional. Mais de um usuário PODE (MAY) estar sem `username`, e a ausência dele NÃO DEVE (MUST NOT) impedir nenhuma operação do sistema.

NÃO DEVE (MUST NOT) existir dois usuários com o mesmo `username`, sem diferenciar maiúsculas de minúsculas. Acentos DEVEM (MUST) ser considerados na comparação: `Erica` e `Érica` são valores distintos. A unicidade DEVE (MUST) ser garantida também pelo banco de dados, e um `username` pertencente a um usuário inativo continua indisponível para outro usuário. A recusa por duplicidade DEVE (MUST) aparecer como erro do próprio campo, no cadastro e na edição, como acontece com o e-mail.

#### Scenario: Valor com espaços e acentos
- **GIVEN** um usuário autenticado com a permissão de cadastrar usuários
- **WHEN** ele cadastra um usuário com o `username` `Aldo Gomes`
- **THEN** o valor é gravado como `Aldo Gomes`

#### Scenario: Abreviação com ponto
- **WHEN** um usuário é cadastrado com o `username` `Gera Jr.`
- **THEN** o valor é gravado como `Gera Jr.`, sem recusa de formato

#### Scenario: Caixa preservada
- **WHEN** um usuário é cadastrado com o `username` `Érica`
- **THEN** o valor é gravado como `Érica`, e não em minúsculas

#### Scenario: Espaços aparados
- **WHEN** um usuário é cadastrado com o `username` `  Aldo   Gomes  `
- **THEN** o valor é gravado como `Aldo Gomes`

#### Scenario: Valor em branco
- **GIVEN** dois usuários cadastrados sem `username`
- **WHEN** os dois são gravados
- **THEN** ambos ficam sem `username` e nenhuma recusa por duplicidade acontece

#### Scenario: Duplicata exata
- **GIVEN** um usuário existente com o `username` `Aldo Gomes`
- **WHEN** alguém com a permissão de cadastrar usuários tenta cadastrar outro usuário com `Aldo Gomes`
- **THEN** nenhum usuário é criado e o formulário indica, no campo do `username`, que o valor já pertence a outro usuário

#### Scenario: Duplicata que difere só em maiúsculas e minúsculas
- **GIVEN** um usuário existente com o `username` `Aldo Gomes`
- **WHEN** alguém com a permissão de cadastrar usuários tenta cadastrar outro usuário com `ALDO GOMES`
- **THEN** nenhum usuário é criado e o formulário indica, no campo do `username`, que o valor já pertence a outro usuário

#### Scenario: Valores que diferem por acento são distintos
- **GIVEN** um usuário existente com o `username` `Érica`
- **WHEN** alguém com a permissão de cadastrar usuários cadastra outro usuário com `Erica`
- **THEN** os dois usuários existem, com `username` diferentes

#### Scenario: `username` de usuário inativo
- **GIVEN** um usuário com `is_active = False` e o `username` `Aldo Gomes`
- **WHEN** alguém com a permissão de cadastrar usuários tenta cadastrar outro usuário com `Aldo Gomes`
- **THEN** nenhum usuário é criado e o formulário indica que o valor já pertence a outro usuário

#### Scenario: Gravação direta com `username` duplicado
- **GIVEN** um usuário existente com o `username` `Aldo Gomes`
- **WHEN** uma gravação que não passa pelo formulário tenta criar outro usuário com `aldo gomes`
- **THEN** o banco de dados recusa a gravação

#### Scenario: Usuários existentes sem o valor
- **GIVEN** usuários cadastrados antes de o `username` existir
- **WHEN** a alteração que acrescenta o campo é aplicada
- **THEN** todos continuam cadastrados, sem `username`, e nenhum valor é atribuído automaticamente a partir do nome

## MODIFIED Requirements

### Requirement: Cadastro de usuário
O cadastro DEVE (MUST) exigir nome, e-mail e exatamente um perfil, escolhido entre os perfis existentes no sistema, do sistema ou personalizados. Esta spec não define restrição sobre quais perfis o executor pode escolher em relação às suas próprias permissões: esse ponto (escalonamento de privilégio na atribuição de perfis) está pendente de decisão no design. O cadastro DEVE (MUST) aceitar também o `username`, de preenchimento opcional, conforme o requisito "Identificador de domínio do usuário (`username`)". O usuário cadastrado DEVE (MUST) ser gravado ativo, com `is_superadmin = False`, sem senha utilizável e vinculado ao perfil informado. O cadastro DEVE (MUST) aceitar só e-mails do domínio institucional `@ifnmg.edu.br`, sem diferenciar maiúsculas e minúsculas. Um cadastro que não seja concluído NÃO DEVE (MUST NOT) deixar gravado usuário sem perfil. O envio do link para o novo usuário definir a própria senha segue a spec `autenticacao`.

#### Scenario: Cadastro válido
- **GIVEN** um usuário autenticado com a permissão de cadastrar usuários
- **WHEN** ele cadastra o nome `Maria Souza`, o e-mail `maria@ifnmg.edu.br` e o perfil `DOCENTE`
- **THEN** o usuário é gravado com esse nome e esse e-mail, com `is_active = True` e `is_superadmin = False`
- **AND** ele tem exatamente um perfil, `DOCENTE`
- **AND** ele não tem senha que permita autenticação

#### Scenario: Cadastro com `username`
- **GIVEN** um usuário autenticado com a permissão de cadastrar usuários
- **WHEN** ele cadastra o nome `Aldo Gomes da Silva`, o e-mail `aldo@ifnmg.edu.br`, o perfil `DOCENTE` e o `username` `Aldo Gomes`
- **THEN** o usuário é gravado com o nome `Aldo Gomes da Silva` e o `username` `Aldo Gomes`

#### Scenario: Cadastro sem `username`
- **GIVEN** um usuário autenticado com a permissão de cadastrar usuários
- **WHEN** ele envia um cadastro válido com o campo do `username` vazio
- **THEN** o usuário é criado sem `username`

#### Scenario: Nome ausente
- **GIVEN** um usuário autenticado com a permissão de cadastrar usuários
- **WHEN** ele envia o cadastro sem nome
- **THEN** nenhum usuário é criado e o formulário indica que o nome é obrigatório

#### Scenario: E-mail ausente
- **GIVEN** um usuário autenticado com a permissão de cadastrar usuários
- **WHEN** ele envia o cadastro sem e-mail
- **THEN** nenhum usuário é criado e o formulário indica que o e-mail é obrigatório

#### Scenario: E-mail em formato inválido
- **GIVEN** um usuário autenticado com a permissão de cadastrar usuários
- **WHEN** ele envia o cadastro com o e-mail `maria.ifnmg.edu.br`
- **THEN** nenhum usuário é criado e o formulário indica que o e-mail é inválido

#### Scenario: E-mail fora do domínio institucional
- **GIVEN** um usuário autenticado com a permissão de cadastrar usuários
- **WHEN** ele envia o cadastro com o e-mail `maria@gmail.com`
- **THEN** nenhum usuário é criado e o formulário indica que o e-mail deve terminar em `@ifnmg.edu.br`

#### Scenario: Perfil ausente
- **GIVEN** um usuário autenticado com a permissão de cadastrar usuários
- **WHEN** ele envia o cadastro sem perfil
- **THEN** nenhum usuário é criado e o formulário indica que o perfil é obrigatório

#### Scenario: Mais de um perfil
- **GIVEN** um usuário autenticado com a permissão de cadastrar usuários
- **WHEN** ele tenta cadastrar um usuário com os perfis `ADMINISTRADOR` e `DOCENTE` ao mesmo tempo
- **THEN** nenhum usuário é criado

#### Scenario: Superadmin enviado no cadastro
- **GIVEN** um usuário autenticado com a permissão de cadastrar usuários
- **WHEN** ele envia um cadastro válido acrescentando `is_superadmin = true` aos dados da requisição
- **THEN** o usuário é criado com `is_superadmin = False`

### Requirement: Edição dos dados do usuário
Um usuário com a permissão de editar usuários DEVE (MUST) poder alterar o nome, o e-mail e o `username` de outro usuário, ativo ou inativo, respeitando a obrigatoriedade dos campos, a unicidade do e-mail, a unicidade do `username` e a proteção do e-mail de superadmin. O `username` DEVE (MUST) poder ser definido, alterado e apagado pela edição, e apagá-lo DEVE (MUST) deixar o usuário sem `username`, sem afetar o seu acesso ao sistema. A proteção do e-mail de superadmin NÃO DEVE (MUST NOT) se estender ao `username`. A edição de nome, e-mail e `username` NÃO DEVE (MUST NOT) alterar o perfil, a situação, a senha nem `is_superadmin`. Depois da troca de e-mail, o login passa a aceitar só o novo endereço e os links de senha já emitidos deixam de valer, conforme a spec `autenticacao`.

#### Scenario: Alteração do nome
- **GIVEN** um usuário com o nome `Maria Sousa`
- **WHEN** alguém com a permissão de editar usuários altera o nome para `Maria Souza`
- **THEN** o nome `Maria Souza` é gravado
- **AND** o e-mail, o `username`, o perfil, a situação e a senha do usuário não mudam

#### Scenario: Alteração do e-mail
- **GIVEN** um usuário que não é superadmin, com o e-mail `maria@ifnmg.edu.br`
- **WHEN** alguém com a permissão de editar usuários altera o e-mail para `Maria.Souza@ifnmg.edu.br`
- **THEN** o e-mail `maria.souza@ifnmg.edu.br` é gravado
- **AND** o usuário continua com o mesmo perfil, a mesma situação e a mesma senha

#### Scenario: Definição do `username` na edição
- **GIVEN** um usuário sem `username`
- **WHEN** alguém com a permissão de editar usuários informa o `username` `Aldo Gomes`
- **THEN** o valor `Aldo Gomes` é gravado e os demais dados do usuário não mudam

#### Scenario: `username` apagado na edição
- **GIVEN** um usuário com o `username` `Aldo Gomes`
- **WHEN** alguém com a permissão de editar usuários envia a edição com o campo do `username` vazio
- **THEN** o usuário fica sem `username` e continua podendo se autenticar normalmente

#### Scenario: `username` de outro usuário na edição
- **GIVEN** dois usuários com os `username` `Ana Souza` e `Bruno Lima`
- **WHEN** alguém com a permissão de editar usuários tenta alterar o `username` de Bruno para `ANA SOUZA`
- **THEN** a alteração é recusada, o formulário indica o erro no campo do `username` e os dois valores permanecem como estavam

#### Scenario: `username` de superadmin
- **GIVEN** um superadmin e um executor com a permissão de editar usuários que não é superadmin
- **WHEN** o executor altera o `username` do superadmin
- **THEN** o novo valor é gravado, e a proteção que impede a troca do e-mail do superadmin continua valendo só para o e-mail

#### Scenario: Nome apagado na edição
- **GIVEN** um usuário existente
- **WHEN** alguém com a permissão de editar usuários envia a edição com o nome vazio
- **THEN** a alteração é recusada e o nome anterior permanece

#### Scenario: Edição de usuário inativo
- **GIVEN** um usuário com `is_active = False`
- **WHEN** alguém com a permissão de editar usuários altera o nome dele
- **THEN** o novo nome é gravado e o usuário continua inativo

#### Scenario: Superadmin enviado na edição
- **GIVEN** um usuário com `is_superadmin = False`
- **WHEN** alguém com a permissão de editar usuários envia a edição acrescentando `is_superadmin = true` aos dados da requisição
- **THEN** o usuário continua com `is_superadmin = False`

### Requirement: Busca e filtro na lista de usuários
A lista de usuários DEVE (MUST) aceitar uma busca por trecho do nome, do e-mail ou do `username`, sem diferenciar maiúsculas de minúsculas, e um filtro por situação com as opções todas, ativos e inativos. Busca e filtro DEVEM (MUST) valer juntos e ser recebidos como parâmetros da URL da lista (`busca` e `situacao`), de modo que o mesmo endereço reproduza o mesmo resultado. Um valor de `situacao` fora das opções DEVE (MUST) ser tratado como todas. A lista DEVE (MUST) manter a ordem por nome e ser paginada conforme a spec `interface`, com a página combinada à busca e ao filtro. Mudar a busca ou o filtro DEVE (MUST) voltar para a primeira página. O título do cartão DEVE (MUST) informar quantos usuários existem no total, e o rodapé DEVE (MUST) informar o intervalo exibido dentro do resultado da busca. Quando nenhum usuário atender à busca, a lista DEVE (MUST) informar isso em texto e oferecer um link para limpar a busca. A coluna que identifica o usuário DEVE (MUST) exibir o e-mail, e NÃO DEVE (MUST NOT) exibir o nome nem o `username`, que continuam alcançáveis pela busca. A busca, o filtro e a paginação NÃO DEVEM (MUST NOT) alterar dados nem mudar quem pode acessar a lista.

#### Scenario: Busca por trecho do nome
- **GIVEN** os usuários "Ana Souza", "Bruno Lima" e "Carla Mendes"
- **WHEN** a lista é acessada com `busca=SOU`
- **THEN** só o e-mail de "Ana Souza" é exibido, o título informa 3 usuários e o rodapé informa "Exibindo 1 a 1 de 1 usuário"

#### Scenario: Busca por trecho do e-mail
- **GIVEN** o usuário "Bruno Lima" com o e-mail `bruno.lima@ifnmg.edu.br`
- **WHEN** a lista é acessada com `busca=bruno.lima`
- **THEN** o e-mail `bruno.lima@ifnmg.edu.br` é exibido

#### Scenario: Busca por trecho do `username`
- **GIVEN** o usuário `aldo@ifnmg.edu.br`, com o nome "Aldo Gomes da Silva" e o `username` `Aldo Gomes`
- **WHEN** a lista é acessada com `busca=aldo gomes`
- **THEN** o e-mail `aldo@ifnmg.edu.br` é exibido, embora o `username` não apareça na lista

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

### Requirement: Importação de usuários por planilha
Um usuário ativo autenticado com a permissão `USUARIO.IMPORTAR`, ou superadmin ativo, DEVE (MUST) poder cadastrar e atualizar usuários em lote por meio de um arquivo CSV, conforme a spec `importacao-planilhas`, com o tipo `USUARIO`. O arquivo DEVE (MUST) ter as colunas obrigatórias `E-mail`, `Nome`, `Perfil` e `Nome de usuário`. O e-mail DEVE (MUST) ser a coluna identificadora, normalizado como no cadastro (sem espaços nas bordas e em minúsculas). O perfil DEVE (MUST) ser informado pelo código, sem espaços nas bordas e convertido para maiúsculas, e resolvido entre os perfis existentes. Um código sem perfil correspondente DEVE (MUST) ser um erro na coluna `Perfil`, e a importação NÃO DEVE (MUST NOT) criar perfis.

A coluna `Nome de usuário` DEVE (MUST) ser obrigatória no cabeçalho, como as demais, e a célula PODE (MAY) vir vazia, porque o `username` é opcional. Uma célula vazia DEVE (MUST) ser tratada como ausência de informação: no cadastro o usuário é criado sem `username`, e na atualização o valor atual do usuário DEVE (MUST) ser mantido. Uma célula vazia NÃO DEVE (MUST NOT) apagar um `username` já gravado; apagá-lo é feito pela tela de edição. O valor preenchido DEVE (MUST) ser normalizado e validado pela mesma regra do cadastro pela tela, e uma duplicidade DEVE (MUST) receber erro na coluna `Nome de usuário`, com a mesma mensagem da tela.

Para cada linha, a importação DEVE (MUST) decidir:
- `create`, quando não existe usuário com o e-mail, cadastrando-o pela mesma operação do cadastro, com o nome, o perfil e o `username` da linha;
- `update`, quando o usuário existe e o nome, o perfil ou o `username` são diferentes, alterando só o que difere, pelas mesmas operações da edição e da troca de perfil, sem exigir o domínio institucional do e-mail de um usuário já existente;
- `unchanged`, quando o usuário existe e nada difere, sem executar nenhuma operação.

A importação NÃO DEVE (MUST NOT) alterar o e-mail, a senha, a situação nem `is_superadmin` de nenhum usuário, e nenhuma coluna do arquivo DEVE (MUST) definir esses dados. Um superadmin DEVE (MUST) ser tratado como qualquer outro usuário. Um usuário inativo presente no arquivo DEVE (MUST) ser atualizado normalmente, continuar inativo e receber o aviso de usuário inativo na prévia.

#### Scenario: Cadastro de usuário novo
- **GIVEN** que não existe usuário com o e-mail `ana@ifnmg.edu.br`
- **AND** um arquivo com a linha `ana@ifnmg.edu.br;Ana Souza;DOCENTE;Ana Souza`
- **WHEN** a importação é confirmada
- **THEN** a usuária é cadastrada, ativa, sem senha utilizável, com exatamente o perfil `DOCENTE` e o `username` `Ana Souza`

#### Scenario: Cadastro com a coluna do `username` vazia
- **GIVEN** que não existe usuário com o e-mail `ana@ifnmg.edu.br`
- **AND** um arquivo com a linha `ana@ifnmg.edu.br;Ana Souza;DOCENTE;`
- **WHEN** a importação é confirmada
- **THEN** a usuária é cadastrada sem `username`

#### Scenario: Atualização do `username`
- **GIVEN** o usuário `aldo@ifnmg.edu.br`, com o nome "Aldo Gomes da Silva", o perfil `DOCENTE` e sem `username`
- **AND** um arquivo com a linha `aldo@ifnmg.edu.br;Aldo Gomes da Silva;DOCENTE;Aldo Gomes`
- **WHEN** a prévia é gerada
- **THEN** a linha tem a ação `update` com a mudança do `username` de vazio para `Aldo Gomes` e nenhuma mudança de nome ou de perfil

#### Scenario: Célula vazia não apaga o valor atual
- **GIVEN** o usuário `aldo@ifnmg.edu.br`, com o `username` `Aldo Gomes`
- **AND** um arquivo com a linha `aldo@ifnmg.edu.br;Aldo Gomes da Silva;DOCENTE;`
- **WHEN** a importação é confirmada
- **THEN** o `username` continua `Aldo Gomes`

#### Scenario: `username` duplicado no arquivo
- **GIVEN** um arquivo com duas linhas de e-mails diferentes e o mesmo `username` `Aldo Gomes`
- **WHEN** a prévia é gerada
- **THEN** a segunda linha recebe erro na coluna `Nome de usuário` e a importação fica `COM_ERROS`

#### Scenario: `username` já pertencente a outro usuário
- **GIVEN** o usuário `aldo@ifnmg.edu.br` com o `username` `Aldo Gomes`
- **WHEN** a prévia de um arquivo que atribui `ALDO GOMES` a `bruno@ifnmg.edu.br` é gerada
- **THEN** a linha de Bruno recebe erro na coluna `Nome de usuário`, com a mesma mensagem da tela

#### Scenario: Cabeçalho sem a coluna do `username`
- **WHEN** é enviado um arquivo com o cabeçalho `E-mail;Nome;Perfil`
- **THEN** o envio é recusado informando que a coluna `Nome de usuário` está ausente

#### Scenario: Troca de perfil pela importação
- **GIVEN** o usuário `bruno@ifnmg.edu.br`, com o nome "Bruno Lima", o perfil `DOCENTE` e o `username` `Bruno Lima`
- **AND** um arquivo com a linha `bruno@ifnmg.edu.br;Bruno Lima;ADMINISTRADOR;Bruno Lima`
- **WHEN** a prévia é gerada
- **THEN** a linha tem a ação `update` com a mudança de perfil de `DOCENTE` para `ADMINISTRADOR` e nenhuma mudança de nome ou de `username`

#### Scenario: Linha sem alteração
- **GIVEN** o usuário `carla@ifnmg.edu.br`, com o nome "Carla Mendes", o perfil `DOCENTE` e o `username` `Carla Mendes`
- **WHEN** a prévia de um arquivo com a linha ` Carla@IFNMG.edu.br ;Carla Mendes;docente;Carla Mendes` é gerada
- **THEN** a linha tem a ação `unchanged`

#### Scenario: Perfil inexistente
- **WHEN** a prévia de um arquivo com a linha `davi@ifnmg.edu.br;Davi Rocha;COORDENACAO;Davi Rocha` é gerada, sem existir o perfil `COORDENACAO`
- **THEN** a linha recebe erro na coluna `Perfil` e a importação fica `COM_ERROS`

#### Scenario: E-mail inválido
- **WHEN** a prévia de um arquivo com a linha `davi-ifnmg;Davi Rocha;DOCENTE;Davi Rocha` é gerada
- **THEN** a linha recebe erro na coluna `E-mail`, com a mesma mensagem do cadastro pela tela

#### Scenario: E-mail fora do domínio institucional na importação
- **GIVEN** que não existe usuário com o e-mail `davi@gmail.com`
- **WHEN** a prévia de um arquivo com a linha `davi@gmail.com;Davi Rocha;DOCENTE;Davi Rocha` é gerada
- **THEN** a linha recebe erro na coluna `E-mail`, com a mesma mensagem do cadastro pela tela, e ninguém é cadastrado

#### Scenario: Usuário inativo
- **GIVEN** o usuário inativo `eva@ifnmg.edu.br`, com o perfil `DOCENTE`
- **AND** um arquivo que troca o perfil dele para `ADMINISTRADOR`
- **WHEN** a importação é confirmada
- **THEN** o perfil passa a `ADMINISTRADOR`, o usuário continua inativo e a prévia mostrou o aviso de usuário inativo

#### Scenario: Superadmin no arquivo
- **GIVEN** um superadmin com o perfil `ADMINISTRADOR`
- **AND** um arquivo que altera o nome dele e troca o perfil para `DOCENTE`
- **WHEN** a importação é confirmada por quem tem as permissões dessas ações
- **THEN** o nome e o perfil mudam e ele continua com `is_superadmin = True`
