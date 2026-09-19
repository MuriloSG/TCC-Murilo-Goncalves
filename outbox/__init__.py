"""Outbox dos e-mails disparados pelo sistema.

A intenção de envio é gravada na transação da operação que a origina, e o
comando process_outbox faz o envio depois (Change enviar-emails-por-outbox).
"""
