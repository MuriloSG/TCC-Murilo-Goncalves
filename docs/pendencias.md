# Pendências

Itens sem solução em 08/10/2026. O comportamento atual foi mantido em todos.

## Funcionalidades não concluídas

| Item | Situação |
|---|---|
| Página com todas as notificações do usuário | Planejada e não implementada. O usuário vê só as 10 mais recentes no sino |
| Comando de estatísticas do cache público (geração atual, hits, misses, chaves removidas) | Planejado e não implementado |
| Redis como camada do Channels e para os limites de tentativas do allauth | Avaliação planejada, não feita |
| Conferência visual no navegador (360 a 1280 px, teclado, sem JavaScript) | Não registrada para a Grade do ensalamento, o cadastro e o encerramento de aula e o acompanhamento das importações em segundo plano. A última tentativa falhou por falta de acesso ao PyPI no container do Playwright |
| Imagem de referência das telas da Agenda | A convenção da seção 9.8 pede uma imagem de referência antes de cada tela nova; a da Agenda não foi registrada |

## Código

| Item | Evidência |
|---|---|
| Consulta de e-mails sem uso no calendário público | `schedule.public.entries_of` ainda chama `teacher_emails` (uma consulta por requisição), mas os templates não mostram e-mail desde o commit `bbf8044` |
| `flush` sem trava de ambiente | O comando nativo do Django apaga todas as tabelas. Não foi travado como `clear_data`, porque o `TransactionTestCase` o chama a cada teste. Nenhum alvo do `Makefile` ou script o chama |
| Tempo real limitado a um processo | `InMemoryChannelLayer`: notificações criadas pelo `import_worker` ou em outro processo web não atualizam o sino na hora |
| Limites de login por processo | O allauth usa o cache `default` (`LocMemCache`) |
| Agendamento em choque após reimportação | A importação não detecta conflito com agendamentos aprovados; o painel lista o caso como "choque". Risco aceito quando a Agenda foi criada |
| Logs `INFO` perdidos | Sem `LOGGING` |
| Container como root | `Dockerfile` sem `USER` |
| WebSocket sem validação de origem | `config/asgi.py` não usa `AllowedHostsOriginValidator`. O canal só avisa que as notificações mudaram, sem conteúdo, e exige sessão; outro site poderia saber quando o usuário recebe notificações |

## Infraestrutura

Hospedagem, servidor ASGI, proxy, entrega dos estáticos, HTTPS, CI e backup não estão definidos no repositório. Requisitos já conhecidos em [deploy](operacao/deploy.md).
