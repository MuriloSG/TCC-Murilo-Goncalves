# Testes do app `outbox`

Fila de envio de e-mails e worker. Comportamento descrito em [e-mails e servidor SMTP](../../funcionalidades/emails.md). Regras para escrever testes em [testes](../testes.md#regras-para-escrever-testes).

## Módulos

### `test_queue.py`

`EnqueueTests`: enfileira entrada pendente com referência em texto. Repetir mantém uma só pendente e as tentativas, também garantido pelo banco. Depois do envio, pode haver entrada nova. A mesma referência de outro tipo é independente.

### `test_worker.py`

| Classe | O que garante |
|---|---|
| `ProcessTests` | Envia e marca como enviada; nada a processar; tentativa futura espera; falha temporária agenda a próxima, com atrasos crescentes e o último repetido; no limite, marca falha e registra no log; falha não é retomada; descarte; tipo sem handler falha na hora; erro de banco no handler é falha; o lote respeita o tamanho |
| `HandlerRegistryTests` | Um handler por tipo |
| `IsolationTests` | O outbox não importa apps de domínio |
| `ConcurrencyTests` | Entrada travada é pulada |
| `SmtpSettingsTests` | O registro não depende da configuração; sem ela ou inválida, as entradas esperam e saem uma vez quando configurada; usa credenciais e remetente gravados; falha do SMTP segue a política de tentativas sem expor a senha; o comando registra o motivo uma vez |
