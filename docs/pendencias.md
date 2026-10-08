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

## Infraestrutura

Hospedagem, servidor ASGI, proxy, entrega dos estáticos, HTTPS, CI e backup não estão definidos no repositório. Requisitos já conhecidos em [deploy](operacao/deploy.md).
