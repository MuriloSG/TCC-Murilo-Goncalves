## Why

O sistema ainda não tem identidade nem controle de acesso. Sem isso, não há como distinguir o Administrador do Docente nem restringir cada funcionalidade às permissões do perfil atribuído, como exigem o RF04 ("Gerenciar usuários e seus perfis de acesso") e o RNF01 (controle de acesso baseado em papéis, modelo RBAC). Todos os módulos seguintes dependem dessa base: espaços físicos, importação de horários, reservas, notificações e relatórios. Por isso ela precisa existir antes deles.

## What Changes

- **Usuário próprio do sistema** (`Usuario`), identificado por e-mail e sem nome de usuário (*username*). O e-mail é único, sem diferenciar maiúsculas de minúsculas.
- **Perfis** (`Perfil`) configuráveis. Os perfis iniciais `ADMINISTRADOR` e `DOCENTE` são criados pela carga do sistema e marcados como **perfis do sistema**, que não podem ser excluídos. Os demais perfis são **personalizados** e criados pelo Superadmin. Todo perfil tem um código informado na criação, único e imutável depois, e um nome obrigatório e único, sem diferenciar maiúsculas de minúsculas.
- **Permissões granulares** (`Permissao`) no padrão `RECURSO.ACAO`. São definidas pelo sistema e sincronizadas com o banco por migrations, sem cadastro manual. Ninguém cria permissões pela interface, nem o Superadmin.
- **Relacionamentos:** `Usuario ↔ Perfil` N:N no modelo, com a regra de que **cada usuário tem exatamente um perfil** nesta versão. `Perfil ↔ Permissao` também é N:N.
- **Autorização por permissão:** o acesso a cada funcionalidade protegida depende das **permissões efetivas** do usuário, que são as permissões concedidas pelos seus perfis. Nenhuma regra verifica o código ou o nome do perfil.
- **Superadmin:** o `Usuario` tem a flag `is_superadmin`. Com `is_superadmin = true`, o usuário acessa todas as funcionalidades do sistema, qualquer que seja a permissão atribuída ao seu perfil. O superadmin é uma característica do usuário para a administração e a manutenção do sistema, e é também o responsável por configurar os perfis. **Não é um perfil nem uma permissão.** A regra fica na camada de autorização da aplicação e não depende do `is_superuser` do Django.
- **Gestão de perfis pelo Superadmin:** listar e consultar, criar, editar nome e descrição, definir as permissões concedidas e excluir perfis. As operações são protegidas pelas permissões do recurso `PERFIL` e passam pela mesma camada de autorização por permissão das demais funcionalidades.
- **Permissões reservadas ao Superadmin:** as permissões `PERFIL.*` fazem parte do catálogo, mas não podem ser concedidas a nenhum perfil. Por isso, na prática, só o superadmin ativo as possui.
- **Menor privilégio nos perfis:** um perfil novo não tem nenhuma permissão, exceto as escolhidas explicitamente na criação.
- **Exclusão de perfil:** só é possível para perfis personalizados sem nenhum usuário vinculado, ativo ou inativo.
- **Autenticação com django-allauth:** login por e-mail e senha, e logout.
- **Sem cadastro público:** o fluxo de registro do allauth fica desligado, e só o administrador cadastra usuários.
- **Criação da própria senha:** o usuário cadastrado recebe um e-mail com um link para definir a senha. O administrador nunca define nem conhece a senha.
- **Gestão de usuários pelo administrador:** cadastrar, editar, atribuir perfil, desativar e reativar.
- **Desativação lógica:** não há exclusão física de usuários pela interface, e o histórico é preservado. Um usuário inativo não autentica e não executa funcionalidades protegidas.
- **Regra de continuidade:** deve existir sempre pelo menos um usuário ativo com capacidade administrativa para gerenciar usuários. Tem capacidade administrativa o usuário ativo com `is_superadmin = true` ou com um perfil que conceda as permissões de gestão de usuários (`USUARIO.*`), sem incluir as permissões `PERFIL.*`. Fica bloqueada qualquer alteração que deixe o sistema sem nenhum usuário nessa condição: remover o `is_superadmin`, desativar o usuário, trocar o seu perfil ou retirar permissões do perfil dele. Não existe a regra de sempre haver um superadmin ativo.
- **Superadmin inativo:** segue a mesma regra dos demais usuários inativos. Não autentica, não acessa funcionalidades protegidas e não conta para a regra de continuidade.
- **Catálogo inicial de permissões** restrito aos recursos `USUARIO` e `PERFIL`, que são os que esta Change usa. As permissões dos demais recursos entram nas Changes dos respectivos módulos.
- Testes unitários e de integração das regras de autenticação, da checagem de permissões por perfil e da gestão de perfis.

### Fora do escopo

- **Acesso público de consulta (Visualizador):** a rota pública de disponibilidade (RF11) será criada na Change de consulta de disponibilidade. Esta Change só define que o acesso público do Visualizador não depende de perfil nem de autenticação.
- **Permissões de outros módulos:** `ESPACO`, `HORARIO`, `AGENDA`, `RESERVA`, `RELATORIO` e demais recursos. Até essas Changes existirem, a configuração inicial do perfil `DOCENTE` não libera nenhuma funcionalidade.
- **Mais de um perfil por usuário:** o modelo já suporta, mas a regra desta versão limita a um perfil.
- **Cadastro, edição ou exclusão de permissões** pela interface.
- **Delegação da gestão de perfis** a usuários que não são superadmin.
- **Hierarquia de perfis** (RBAC1) e **separação de obrigações** (RBAC2).
- **Auditoria** das alterações de usuários e de perfis.
- Cadastro público de usuários e login por provedores externos.
- Notificações de reservas (RF09, RF10), espaços, horários, reservas e relatórios.
- Configuração de hospedagem ou de produção.

### Pontos em aberto (a fechar em `design.md` e specs)

- **Primeiro administrador:** como ele é criado na primeira instalação, já que não há cadastro público.
- **Recuperação de senha:** se entra nesta Change. O TCC a cita entre os fluxos do django-allauth, e ela reaproveitaria o mecanismo de criação de senha.
- **Concessão de superadmin:** quem pode marcar ou desmarcar `is_superadmin` em um usuário, e por qual meio.
- **Papel do `/admin` do Django:** se ele é mantido e como convive com a autorização da aplicação, já que o `is_superuser` do Django não é usado nas regras de negócio.
- **Detalhes de autenticação:** mensagens de erro no login (usuário inativo, credenciais inválidas), limite de tentativas, duração da sessão e validade do link de criação de senha.
- **Configuração de envio de e-mail** para o link de criação de senha.
- **Estilização das telas:** se o Tailwind CSS é configurado nesta Change ou numa Change própria.
- **Escalonamento de privilégio na atribuição de perfis (pendente):** quem tem permissão para cadastrar usuários ou trocar o perfil de um usuário pode, hoje, atribuir qualquer perfil, inclusive um que conceda permissões que ele mesmo não tem. Ainda não está decidido se isso continua permitido ou se haverá alguma restrição. Ver `design.md`, Open Questions.
- **Alinhamento com o texto do TCC sobre "dois papéis" (pendente, depende dos orientadores):** ver a seção seguinte.

## Alinhamento com o TCC

- **RF04 e casos de uso:** o Administrador cadastra usuários e atribui seus perfis de acesso. A configuração dos perfis (quais existem e quais permissões concedem) fica com o Superadmin. Por isso não há cadastro público.
- **RNF01 e Seção 2.3.4:** adota o **RBAC0** de Sandhu et al. (1996), sem hierarquia. No RBAC0, as permissões ficam ligadas aos papéis e o usuário as adquire pelo papel atribuído. Checar permissões granulares, e não o nome do perfil, é a aplicação direta desse modelo, e o acesso a cada funcionalidade continua dependendo do perfil atribuído, como pede o RNF01. Os papéis Administrador e Docente descritos no TCC correspondem aos perfis do sistema, que existem em toda instalação.
- **Seção 3.3.1 ("associando cada usuário a um dos dois perfis autenticados"):** a regra de exatamente um perfil por usuário continua atendida. O relacionamento N:N segue a definição geral do RBAC na Seção 2.3.4 ("um ou mais papéis") e evita alterar o esquema se essa regra mudar.
- **Ponto pendente de decisão dos orientadores:** o TCC (2.3.4 e 3.3.1) descreve **dois papéis autenticados**, e esta Change permite que o Superadmin crie perfis personalizados além deles. A Constitution determina que o TCC prevalece em caso de divergência. Esta proposal não altera o texto do TCC nem decide como essa diferença será tratada. A decisão fica com os orientadores.
- **Superadmin:** é um atributo do usuário, fora da estrutura de papéis, que serve à manutenção e à evolução do sistema (RNF06) e à configuração dos perfis. Não é um papel do RBAC0.
- **Visualizador:** o TCC o descreve como acesso público sem autenticação, por rota aberta, sem expor dados pessoais (2.3.4, casos de uso, RF11). Por isso o acesso dele não depende de perfil nem de autenticação.
- **Seção 3.3.1 (django-allauth):** a autenticação usa a biblioteca definida no TCC. O fluxo de registro que ela oferece fica desligado, em respeito ao RF04.
- **RNF02:** senhas guardadas só como hash, verificação de acesso no servidor e proteções nativas do Django (CSRF, XSS, injeção de SQL).
- **Seção 3.3.1 (testes):** a "checagem de permissões por perfil" é uma das regras de negócio centrais a serem cobertas por testes unitários e de integração (P9).
- **Seção 3.3 e P11:** `Usuario`, `Perfil` e `Permissao` passam a fazer parte do diagrama de classes. `Usuario` já está entre as entidades centrais previstas.

## Decisões arquiteturais

- **Modelos próprios de identidade**, em vez de `User`, `Group` e `Permission` do Django. Os códigos `RECURSO.ACAO` não correspondem ao CRUD de um model (por exemplo, aprovar uma reserva ou gerar um relatório). Os modelos próprios evitam as permissões `add/change/delete/view` geradas automaticamente para cada model e deixam as entidades explícitas no diagrama de classes. A integração com o mecanismo de autenticação do Django e do allauth continua existindo.
- **Modelo de usuário personalizado definido antes da primeira migration de autenticação.** O Django exige isso, e mudar depois é muito custoso.
- **Catálogo de permissões definido no código** e sincronizado por migration. Uma permissão só faz efeito se o código a verifica, então não faz sentido criá-la pela interface. O Superadmin **combina** permissões existentes em perfis, mas não cria permissões.
- **Perfis do sistema e perfis personalizados.** `ADMINISTRADOR` e `DOCENTE` são criados pela carga, marcados como perfis do sistema e protegidos contra exclusão. Os perfis personalizados são criados pelo Superadmin. Em todos eles, nome, descrição e permissões podem ser alterados pelo Superadmin, e o código é imutável. O código serve para a carga, para as migrations localizarem os perfis do sistema e para a interface, nunca para decisões de autorização.
- **Gestão de perfis protegida por permissões reservadas.** As operações de perfil exigem permissões `PERFIL.*`, verificadas pelo mesmo mecanismo das demais funcionalidades. Essas permissões não podem ser concedidas a nenhum perfil e só o superadmin ativo as possui. Assim, nenhuma view decide acesso pelo `is_superadmin`.
- **Permissões efetivas calculadas a cada requisição.** Um usuário inativo não tem nenhuma permissão, mesmo que tenha perfil. Uma alteração nas permissões de um perfil vale para todos os usuários dele a partir da próxima requisição.
- **Superadmin na camada de autorização da aplicação.** A verificação de acesso considera `is_superadmin` antes das permissões efetivas. O `is_superuser` do Django fica fora das regras de negócio, para que exista um único ponto de decisão de acesso, controlado pela aplicação.
- **Regra de continuidade como invariante do sistema,** verificada em toda alteração que possa retirar a capacidade administrativa de um usuário (flag de superadmin, desativação, troca de perfil e retirada de permissões de um perfil). Isso evita que o sistema fique sem ninguém capaz de gerenciar usuários.
- **Desativação lógica** para manter a integridade do histórico que os módulos de reservas e relatórios vão referenciar.
- **Crescimento progressivo:** esta Change cria só as entidades, permissões e dependências que usa. Cada módulo seguinte acrescenta suas permissões por migration e pode conceder uma configuração padrão **somente aos perfis do sistema**, uma única vez, na própria Change. Perfis personalizados nunca recebem permissões automaticamente: o Superadmin decide.

## Capabilities

### New Capabilities

- `autenticacao`: login por e-mail e senha, logout, criação da senha pelo próprio usuário via link enviado por e-mail, bloqueio de autenticação de usuários inativos e ausência de cadastro público.
- `gestao-usuarios`: cadastro, edição, desativação e reativação de usuários pelo administrador, unicidade do e-mail, atribuição de exatamente um perfil por usuário, preservação do histórico sem exclusão física e regra de continuidade administrativa (pelo menos um usuário ativo com capacidade administrativa, via superadmin ou perfil).
- `gestao-perfis`: listagem, consulta, criação, edição, definição das permissões e exclusão de perfis pelo Superadmin, perfis do sistema protegidos, código imutável, nome único, bloqueio da exclusão de perfis com usuários vinculados, permissões reservadas e continuidade administrativa na retirada de permissões.
- `controle-acesso`: catálogo de permissões definido pelo sistema, padrão `RECURSO.ACAO`, permissões reservadas ao superadmin, cálculo das permissões efetivas, acesso irrestrito do superadmin ativo, autorização baseada em permissões, menor privilégio e comportamento diante de acesso sem autenticação ou sem permissão.

### Modified Capabilities

Nenhuma. Não há specs existentes em `openspec/specs/`.

## Impact

- **Código novo:** a primeira app de domínio do projeto, com os models `Usuario` (incluindo a flag `is_superadmin`), `Perfil` (incluindo a marca `sistema`) e `Permissao`, suas migrations (incluindo a carga dos perfis do sistema e das permissões iniciais), as views, rotas e templates de autenticação, de gestão de usuários e de gestão de perfis, e os testes.
- **Configuração:** `AUTH_USER_MODEL` aponta para `Usuario`. Entram as configurações do django-allauth (login por e-mail, registro desligado) e de envio de e-mail.
- **Dependências:** `django-allauth` é adicionado ao `requirements.txt`.
- **Banco de desenvolvimento:** se já tiver recebido `migrate` com o usuário padrão do Django, precisará ser recriado (`make reset-db`), porque o modelo de usuário muda antes da primeira migration de autenticação. Não há dados de produção afetados.
- **Módulos futuros:** espaços, horários, reservas, notificações e relatórios passam a declarar suas permissões no padrão `RECURSO.ACAO`, a proteger suas funcionalidades por elas e, se quiserem, a conceder uma configuração padrão aos perfis do sistema. Depois de cada módulo novo, o Superadmin precisa revisar os perfis personalizados. As notificações por e-mail já terão uma configuração de envio para reaproveitar.
- **Constitution:** concretiza P5 (RBAC e proteção dos dados). Aplica P3 (ORM e migrations), P2 (separação MTV) e P9 (testes da checagem de permissões por perfil).
