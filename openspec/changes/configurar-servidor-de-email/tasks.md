## 1. Configuração persistida

- [x] 1.1 Declarar `cryptography` no `requirements.txt` e a chave `DJANGO_CREDENTIALS_KEY` no `settings.py` e no `compose.yaml` (D3)
- [x] 1.2 Criar o app `system_settings` com o model `SystemSetting`, o tipo `smtp` e a migration (D1, D2)
- [x] 1.3 Criar `SmtpSettings` com o esquema, as regras, a cifra da senha e a conexão (D3, D4)
- [x] 1.4 Testar persistência, unicidade, validação, cifra e senha mantida

## 2. Permissão, auditoria e tela

- [x] 2.1 Acrescentar `CONFIGURACAO.EDITAR` ao catálogo e a migration que a concede ao `ADMINISTRADOR` (D9)
- [x] 2.2 Acrescentar o módulo `CONFIGURACAO` e os rótulos dos campos ao catálogo da auditoria (D9)
- [x] 2.3 Criar o formulário, a página, o modal, as rotas e o item do menu "Configurações" (D9, D10)
- [x] 2.4 Incluir as rotas na matriz de proteção e testar cadastro, atualização, erro, auditoria e ausência da senha

## 3. Worker e recuperação de senha

- [x] 3.1 Carregar a configuração por lote no worker e reter os envios sem configuração válida (D5, D6)
- [x] 3.2 Registrar no comando `process_outbox` o motivo da retenção quando mudar (D5)
- [x] 3.3 Enviar a recuperação de senha pública pela configuração (D8)
- [x] 3.4 Retirar as variáveis de credenciais do ambiente e atualizar o README (D7)
- [x] 3.5 Testar retenção, liberação, credenciais usadas, troca entre lotes, falha do SMTP e a recuperação sem configuração; ajustar os testes existentes que enviam e-mail
