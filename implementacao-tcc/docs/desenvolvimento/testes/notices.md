# Testes do app `notices`

Notificações no sistema: sino, tempo real e publicação manual. Comportamento descrito em [notificações](../../funcionalidades/notificacoes.md). Regras para escrever testes em [testes](../testes.md#regras-para-escrever-testes).

## Mecanismo

### `test_models.py`

| Classe | O que garante |
|---|---|
| `CatalogTests` | Tipos com rótulo, ícone e tom; os tipos manuais são os três da publicação |
| `MechanismIndependenceTests` | O mecanismo não importa apps de domínio |
| `DeliveryTests` | Uma notificação por destinatário, com leitura individual; tipo fora do catálogo e publicação sem destinatários recusados; mais recentes primeiro |
| `RecipientResolutionTests` | "Todos" são os ativos; perfil alcança só seus ativos; usuários escolhidos, sem os inativos; destino fora do catálogo recusado |
| `ReadingTests` | Contagem de não lidas; marcar como lida uma vez; marcar todas |

### `test_events.py`

| Classe | O que garante |
|---|---|
| `RegistryTests` | Evento sem gerador ou com dois geradores recusado |
| `RoleChangeEventTests` | Troca de perfil notifica o usuário afetado, mesmo inativo; mesmo perfil, operação recusada ou transação desfeita não notificam |

### `test_publication.py`

`PublicationAuditTests`: a publicação grava uma entrada de auditoria com a quantidade alcançada e resolve os destinatários no momento da publicação; recusa, tipo não manual, entrega sem publicação e leitura não são auditados.

## Tempo real

### `test_realtime.py`

| Classe | O que garante |
|---|---|
| `ChannelTests` | O usuário autenticado recebe só os próprios eventos; visitante e inativo recusados; desativar fecha a conexão aberta |
| `OriginTests` | Pela pilha real do `config.asgi`, só origem permitida e com sessão conecta |
| `EmptyAllowedHostsTests` | Lista vazia fora do `DEBUG` recusa toda origem |
| `AnnounceTests` | O aviso sai só depois do commit, para cada destinatário e não para outros; transação desfeita não avisa; falha do canal não desfaz a notificação |

### `test_channel_layer.py`

| Classe | O que garante |
|---|---|
| `LayerSettingsTests` | Com URL do Redis, camada compartilhada com prefixo próprio e sem timeout de leitura menor que a espera; sem URL ou nos testes, camada em memória |
| `LayerCheckTests` | Camada em memória gera aviso, exceto nos testes |
| `CrossProcessTests` | Evento enviado por outro processo pelo Redis chega a quem escuta o grupo |

## Telas

### `test_views.py`

| Classe | O que garante |
|---|---|
| `OpenTests` | Abrir marca como lida e vai ao destino ou volta à origem, ignorando origem fora do sistema; notificação de outro recusada; já lida não muda |
| `ReadAllTests` | Marca só as notificações do usuário |
| `PanelTests` | Fragmento do sino com as notificações do usuário, voltando à tela aberta e nunca a si mesmo ou para fora; estado vazio; não conta como acesso |

### `test_publish_views.py`

| Classe | O que garante |
|---|---|
| `AccessTests` | Abre com a permissão |
| `CreateStepTests` | Mostra a quantidade de ativos; perfil e usuários obrigatórios conforme o destino |
| `ReviewStepTests` | A revisão mostra a prévia e a estimativa só de ativos, sem criar nada, carrega os valores adiante e mantém o preenchido ao voltar |
| `PublishStepTests` | Publica para todos os ativos; sem destinatários mostra a recusa; tipo gerado por evento recusado |
| `ListTests` | Lista só avisos globais publicados; estado vazio; acesso registrado |

### `test_options.py`

`UserOptionsTests`: opções de usuário paginadas de 10 em 10, com busca no servidor por nome e e-mail, sem inativos; o formulário não carrega todos os usuários e mantém os escolhidos depois de um erro.
