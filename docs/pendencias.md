# Pendências

Itens sem solução em 08/10/2026. O comportamento atual foi mantido em todos.

## Funcionalidades não concluídas

| Item | Situação |
|---|---|
| Redis como camada do Channels e para os limites de tentativas do allauth | Avaliação planejada, não feita |

## Código

| Item | Evidência |
|---|---|
| Tempo real limitado a um processo | `InMemoryChannelLayer`: notificações criadas pelo `import_worker` ou em outro processo web não atualizam o sino na hora |
| Limites de login por processo | O allauth usa o cache `default` (`LocMemCache`) |
| WebSocket sem teste de navegador | Origem e sessão comprovadas pelos testes com a pilha do `config/asgi.py` e, no servidor, só a recusa sem sessão (403). Falta conferir num navegador real e atrás do proxy de produção, que não existe |
| Container `tailwind` como root | Só o estágio Python roda como `app`. O `tailwind` grava `node_modules` num volume anônimo criado pela imagem |

## Infraestrutura

Hospedagem, servidor ASGI, proxy, entrega dos estáticos, HTTPS, CI e backup não estão definidos no repositório. Requisitos já conhecidos em [deploy](operacao/deploy.md).
