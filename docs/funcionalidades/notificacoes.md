# Notificações

Avisos dentro do sistema, por destinatário. Não há envio por e-mail. Implementação: app `notices`.

## Modelo

- `Notification`: uma linha por destinatário, com tipo, título (até 120 caracteres), mensagem (até 240), destino (`target_url`) e `read_at`. O texto é copiado no momento do evento, para continuar legível depois.
- `Notice`: registro de uma publicação manual (tipo, título, mensagem, destino e quantidade alcançada). Notificações geradas por evento não têm `Notice`.
- Tipos em `notices/catalog.py`. Um tipo fora do catálogo é recusado (`UnknownNoticeType`). O tom (cor) vem do tipo.

| Tipo | Origem |
|---|---|
| `INFORMACAO`, `SUCESSO`, `AVISO` | Publicação manual |
| `PERFIL_ALTERADO` | Troca de perfil (`accounts/notifications.py`) |
| `AGENDA_SOLICITADA`, `AGENDA_APROVADA`, `AGENDA_REJEITADA`, `AGENDA_ALTERNATIVA`, `AGENDA_ALTERNATIVA_ACEITA`, `AGENDA_ALTERNATIVA_RECUSADA`, `AGENDA_CANCELADA` | Transições da Agenda. Destinatários em [agenda](agenda.md#notificações) |

## Sino

Disponível em toda tela autenticada, sem permissão própria.

| Ação | Rota | Método |
|---|---|---|
| Fragmento com a contagem de não lidas e as 10 mais recentes | `/notificacoes/sino/` | GET |
| Abrir (marca como lida e redireciona ao destino) | `/notificacoes/<pk>/abrir/` | POST |
| Marcar todas como lidas | `/notificacoes/lidas/` | POST |

Uma notificação de outro usuário responde 404. O redirecionamento sem destino só aceita endereços do próprio host.

Tempo real: o navegador abre `ws/notificacoes/`. Depois do commit de uma operação que cria notificações, `notices/realtime.py` avisa o grupo `notificacoes-<user_id>` e o navegador busca o fragmento do sino. Ver as limitações do `InMemoryChannelLayer` em [arquitetura](../arquitetura/visao-geral.md#tempo-real).

Origem e autenticação do canal (`config/asgi.py`), em duas etapas independentes:

1. Origem: o `AllowedHostsOriginValidator` do Channels compara o cabeçalho `Origin` do handshake com `ALLOWED_HOSTS` e recusa com 403 a origem fora da lista e o handshake sem `Origin` (todo navegador o envia). O `Host` não é usado como substituto. Com `DEBUG` e a lista vazia, aceita só `localhost`, `127.0.0.1` e `[::1]`; sem `DEBUG` e com a lista vazia, recusa tudo. A lista é lida uma vez, quando a aplicação ASGI é montada.
2. Sessão: o `NotificationsConsumer` recusa visitante e usuário inativo.

Atrás de um proxy, o `Origin` é o endereço público digitado no navegador, que precisa estar em `DJANGO_ALLOWED_HOSTS`. Um `*` na lista aceitaria qualquer origem e não deve ser usado em produção.

## Publicação manual

Permissão `NOTIFICACAO.PUBLICAR`.

| Tela | Rota |
|---|---|
| Comunicados publicados para todos os usuários | `/notificacoes/` |
| Nova publicação (formulário e revisão) | `/notificacoes/nova/` |
| Publicar | `/notificacoes/publicar/` (POST) |
| Opções do campo de usuários, paginadas no servidor | `/notificacoes/opcoes/usuarios/` |

- Destino: todos os usuários, usuários de um perfil ou usuários escolhidos. Só usuários ativos recebem, inclusive quando escolhidos um a um.
- Os destinatários são resolvidos no momento da publicação. A publicação, as notificações e um único registro de auditoria (`PUBLICAR`, módulo `NOTIFICACAO`, com a quantidade alcançada) ficam na mesma transação.
- A lista em `/notificacoes/` mostra só as publicações para todos. As direcionadas a perfil ou a usuários ficam só na auditoria.
- Ler uma notificação não é auditado.

## Não implementado

A página com todas as notificações do próprio usuário não existe. O usuário vê só as 10 mais recentes no sino.

## Testes

`notices/tests/`: `test_models.py`, `test_events.py`, `test_views.py`, `test_publication.py`, `test_publish_views.py`, `test_options.py`, `test_realtime.py`.
