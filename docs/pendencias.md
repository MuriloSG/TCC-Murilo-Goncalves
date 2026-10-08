# Pendências

Itens sem solução em 08/10/2026. O comportamento atual foi mantido em todos.

## Funcionalidades não concluídas

| Item | Situação |
|---|---|
| Comando de estatísticas do cache público (geração atual, hits, misses, chaves removidas) | Planejado e não implementado |
| Redis como camada do Channels e para os limites de tentativas do allauth | Avaliação planejada, não feita |

## Código

| Item | Evidência |
|---|---|
| Tempo real limitado a um processo | `InMemoryChannelLayer`: notificações criadas pelo `import_worker` ou em outro processo web não atualizam o sino na hora |
| Limites de login por processo | O allauth usa o cache `default` (`LocMemCache`) |
| Trava de ambiente identifica a instalação, não o banco | Com `DJANGO_ENVIRONMENT=local` apontando para o banco errado, `flush`, `clear_data`, `delete_users` e `set_passwords` rodam |
| `--parallel` nos testes | A suíte falha com `cannot pickle 'traceback' object`, independentemente das mudanças de 08/10/2026; só a execução sequencial (`make test`) é suportada |
| WebSocket sem teste de navegador | Origem e sessão comprovadas pelos testes com a pilha do `config/asgi.py` e, no servidor, só a recusa sem sessão (403). Falta conferir num navegador real e atrás do proxy de produção, que não existe |
| Container `tailwind` como root | Só o estágio Python roda como `app`. O `tailwind` grava `node_modules` num volume anônimo criado pela imagem |
| uid do container fixo em 1000 | Em host Linux com outro uid, é preciso construir com `--build-arg APP_UID=$(id -u)`; não validado em Linux, só no macOS |
| Agendamento em choque após reimportação | A importação não detecta conflito com agendamentos aprovados; o painel lista o caso como "choque". Risco aceito quando a Agenda foi criada |

## Infraestrutura

Hospedagem, servidor ASGI, proxy, entrega dos estáticos, HTTPS, CI e backup não estão definidos no repositório. Requisitos já conhecidos em [deploy](operacao/deploy.md).
