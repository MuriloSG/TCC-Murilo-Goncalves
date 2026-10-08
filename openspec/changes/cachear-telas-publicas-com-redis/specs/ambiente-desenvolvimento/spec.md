## ADDED Requirements

### Requirement: Serviço Redis de cache
O Docker Compose DEVE (MUST) ter um serviço `redis`, com a imagem oficial e a versão maior fixada, usado somente como cache. O serviço NÃO DEVE (MUST NOT) publicar porta no host e DEVE (MUST) ser alcançável só pela rede interna do Compose. O Redis NÃO DEVE (MUST NOT) gravar dados em disco e DEVE (MUST) ter limite de memória com remoção das chaves menos usadas. Os containers `web`, `worker` e `import_worker` DEVEM (MUST) receber a URL de conexão pela variável `DJANGO_REDIS_URL` e DEVEM (MUST) iniciar mesmo com o Redis fora do ar. Sem `DJANGO_REDIS_URL`, a aplicação DEVE (MUST) funcionar sem cache público. A suíte de testes NÃO DEVE (MUST NOT) usar o Redis do ambiente.

#### Scenario: Redis só na rede interna
- **WHEN** o ambiente é iniciado com `make up`
- **THEN** o container `redis` está em execução e nenhuma porta dele é publicada no host

#### Scenario: Aplicação sem o Redis
- **GIVEN** o ambiente em execução
- **WHEN** o container `redis` é parado
- **THEN** o calendário público continua respondendo com o mesmo conteúdo

#### Scenario: Cache reiniciado vazio
- **WHEN** o container `redis` é reiniciado
- **THEN** nenhuma entrada de cache anterior continua existindo
