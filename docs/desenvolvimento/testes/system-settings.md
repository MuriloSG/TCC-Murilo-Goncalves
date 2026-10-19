# Testes do app `system_settings`

Configuração do servidor SMTP no banco e checagens de deploy. Comportamento descrito em [e-mails e servidor SMTP](../../funcionalidades/emails.md) e em [configuração](../../operacao/configuracao.md). Regras para escrever testes em [testes](../testes.md#regras-para-escrever-testes).

## Auxiliares

- `base.py`: `configure_smtp` grava a configuração SMTP direto no banco, sem auditoria. É usado também pelos testes que enviam e-mail.

## Módulos

### `test_models.py`

| Classe | O que garante |
|---|---|
| `SaveSmtpTests` | Cria e atualiza uma configuração única por tipo; dados inválidos e senha sem usuário recusados; relay sem credenciais aceito; senha em branco mantém a gravada para o mesmo destino e é recusada para destino novo; remover o usuário apaga a senha; a auditoria não tem a senha |
| `EncryptionTests` | A senha fica cifrada no banco; outra chave torna a configuração inválida; o `repr` esconde a senha |
| `SchemaTests` | Campo desconhecido recusado; configuração ausente é `None` |
| `ClearSmtpTests` | Limpar é auditado sem a senha |

### `test_views.py`

`SmtpViewTests`: administrador que não é superadmin é recusado; página sem configuração; cadastro pelo formulário; senha em branco mantida na edição e recusada no campo para servidor novo; recusas aparecem no campo; a senha nunca chega à tela; a página mostra configuração inválida e e-mails pendentes; limpar pela confirmação, com 404 sem configuração.

### `test_checks.py`

`DeploymentCheckTests`: valores de produção passam; padrões de desenvolvimento são recusados; Redis sem senha gera aviso; sem Redis, nada é dito sobre ele.
