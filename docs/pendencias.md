# Pendências

Itens sem solução em 08/10/2026. O comportamento atual foi mantido em todos.

## Funcionalidades não concluídas

| Item | Situação |
|---|---|
| Camada do Channels compartilhada entre processos | A definir com a arquitetura de execução. O `import_worker` já é um processo separado do web, então a camada precisa alcançar os dois. Opção conhecida: Redis |
| Cache compartilhado para os limites do allauth | Só necessário com mais de um processo web. Opções: Redis (o mesmo serviço do Channels, se adotado, com configuração e política de descarte próprias para contadores) ou `DatabaseCache`. Com um processo, o `LocMemCache` basta |

## Código

| Item | Evidência |
|---|---|
| Tempo real limitado a um processo | `InMemoryChannelLayer`: notificações criadas pelo `import_worker` ou em outro processo web não atualizam o sino na hora |
| Limites de login dependem da implantação | O allauth usa o cache `default` (`LocMemCache`), com contadores por processo: com vários processos ou instâncias, o limite efetivo pode se multiplicar. Sem `ALLAUTH_TRUSTED_PROXY_COUNT` ou `ALLAUTH_TRUSTED_CLIENT_IP_HEADER`, atrás de um proxy reverso os limites por IP passam a valer para o IP do proxy, compartilhados por todos; a configuração depende do proxy escolhido |

## Infraestrutura

Hospedagem, servidor ASGI, proxy, entrega dos estáticos, HTTPS, CI e backup não estão definidos no repositório. Requisitos já conhecidos em [deploy](operacao/deploy.md).
