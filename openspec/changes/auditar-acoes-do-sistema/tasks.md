## 1. Mecanismo de auditoria

- [x] 1.1 Criar o app `audit`, com `catalog.py` (ações, recursos, origens e rótulos) e registrá-lo em `INSTALLED_APPS` (D4)
- [x] 1.2 Criar o model `AuditLog`, com os campos, a ordenação e os índices, e a migration inicial (D1)
- [x] 1.3 Criar `AuditLog.objects.record`, com a recusa de código fora do catálogo e a retirada dos campos sensíveis (D2, D8)
- [x] 1.4 Criar `audit/context.py` com o ator, o padrão do sistema e os gerenciadores de contexto (D3)
- [x] 1.5 Recusar alteração e exclusão de registros no model e no queryset (D10)
- [x] 1.6 Testar o mecanismo: campos gravados, ator padrão, código inválido, campo sensível descartado, alteração e exclusão recusadas
- [x] 1.7 Commit

## 2. Ator da requisição e acesso às funcionalidades

- [x] 2.1 Criar `AuditMiddleware`, que define o ator da requisição e registra `ACESSO` (D3, D5) e registrá-lo no fim de `MIDDLEWARE` (D13)
- [x] 2.2 Declarar `audit_resource` nas views de usuários, perfis e importações (D5)
- [x] 2.3 Testar o acesso: registro no GET da lista, ausência de registro nas requisições do htmx, no 403, no POST e na página inicial, e IP e cliente gravados
- [x] 2.4 Commit

## 3. Autenticação

- [x] 3.1 Ligar os sinais de login e de logout no `ready()` do app `audit` (D6)
- [x] 3.2 Registrar a recusa de login no `AccountAdapter.authenticate`, com o e-mail informado (D6)
- [x] 3.3 Registrar a solicitação de recuperação no `PasswordResetForm` e a redefinição pelo sinal do allauth (D6)
- [x] 3.4 Testar login, recusa por senha errada, recusa de usuário inativo, logout, solicitação de recuperação com e sem conta e redefinição, e a ausência de senha e de token nos registros
- [x] 3.5 Commit

## 4. Alterações de dados

- [ ] 4.1 Registrar as operações de `User`: cadastro, edição, troca de perfil, desativação e reativação (D7, D9)
- [ ] 4.2 Registrar as operações de `Role`: criação, edição, alteração de permissões e exclusão (D7, D9)
- [ ] 4.3 Registrar a prévia, a confirmação, o descarte e o download do modelo nas importações, e trocar a origem para `IMPORTACAO` na execução das linhas (D3, D7)
- [ ] 4.4 Registrar o envio e a falha definitiva no worker do outbox (D11)
- [ ] 4.5 Testar cada operação: valores anteriores e posteriores só com os campos alterados, operação sem mudança e operação recusada sem registro, prévia sem registro das linhas, confirmação com registro por usuário e origem `IMPORTACAO`, envio e falha do worker sem usuário responsável
- [ ] 4.6 Rodar `make test` com a suíte inteira passando
- [ ] 4.7 Commit

## 5. Consulta

- [ ] 5.1 Acrescentar `AUDITORIA.VISUALIZAR` ao catálogo de permissões e o rótulo do recurso, com a migration de dados que a concede ao `ADMINISTRADOR` (D12)
- [ ] 5.2 Criar o formulário de filtros e a consulta com os parâmetros da URL, a ordem e a paginação (D12)
- [ ] 5.3 Criar a lista de auditoria com o cartão, a tabela, o estado vazio e o rodapé de paginação, e a rota com `login_required` (D12)
- [ ] 5.4 Criar o detalhe do registro em modal, somente leitura (D12)
- [ ] 5.5 Acrescentar o item "Auditoria" à navegação e o ícone do Lucide (D12)
- [ ] 5.6 Testar as rotas nas quatro situações (anônimo, sem permissão, com permissão e POST sem CSRF), cada filtro, a combinação de filtros com a página, o filtro inválido, a ordem e o estado vazio
- [ ] 5.7 Rodar `make test` com a suíte inteira passando
- [ ] 5.8 Commit

## 6. Documentação e verificação

- [ ] 6.1 Documentar a auditoria no `README.md`: o que é registrado, quem consulta e a permissão nova
- [ ] 6.2 Conferir a tela de auditoria no navegador, no banco `visual_check`, em 360 e 1280 px, com e sem JavaScript
- [ ] 6.3 Validar a Change com `openspec validate auditar-acoes-do-sistema --strict`
- [ ] 6.4 Commit
