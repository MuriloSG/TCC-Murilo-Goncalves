## 1. Referência visual e decisões de tecnologia

- [ ] 1.1 Receber do autor a imagem de referência da tela de publicação e da página de notificações (D13)
- [x] 1.2 Verificar a versão da `django-notifications-hq` compatível com o Django 5.2, o que ela exige de `INSTALLED_APPS` e de migrations, como ela trata destinatário e leitura e se ela convive com o servidor ASGI (D3)
- [x] 1.3 Decidir entre adotar a biblioteca como persistência e usar model próprio, e registrar a decisão no `design.md` (D3)
- [x] 1.4 Decidir a tecnologia do canal de tempo real e a camada de mensagens, com o WebSocket por Channels como recomendação, e registrar a decisão no `design.md` (D11)
- [ ] 1.5 Registrar no `design.md` o que foi adaptado e o que foi retirado da referência visual (seção 9.8 das convenções)

## 2. Persistência e mecanismo de notificações

- [x] 2.1 Criar o app `notices` e o `notices/catalog.py` com os tipos `COMUNICADO` e `PERFIL_ALTERADO`, com rótulo, ícone, tom e publicável manualmente (D1, D4)
- [x] 2.2 Criar o model da notificação e a migration de esquema, com destinatário, tipo, título, mensagem, destino, estado de leitura e data (D2, D3)
- [x] 2.3 Criar as operações do model: criar para um destinatário, publicar para um conjunto, marcar como lida, marcar todas como lidas e contar não lidas, cada uma numa transação (D2)
- [x] 2.4 Criar a resolução dos destinatários, com as três formas de destinar e a elegibilidade pela situação do usuário (D6)
- [x] 2.5 Recusar tipo fora do catálogo e publicação sem destinatários, com `ValidationError` (D4)
- [x] 2.6 Testar a entrega por destinatário, a leitura individual, a elegibilidade, a recusa por tipo e por conjunto vazio, a transação desfeita e a notificação continuando disponível depois de sair, entrar e reiniciar a aplicação
- [x] 2.7 Commit

## 3. Permissão e auditoria

- [ ] 3.1 Acrescentar `NOTIFICACAO.PUBLICAR` ao `accounts/permissions.py` e a migration de dados que a concede ao perfil `ADMINISTRADOR` sem alterar os demais perfis
- [ ] 3.2 Acrescentar a ação `PUBLICAR` e o módulo `NOTIFICACAO` ao `audit/catalog.py`, sem migration de esquema (D9)
- [ ] 3.3 Registrar a publicação na auditoria, com o título, o tipo, a forma de destinar e a quantidade de destinatários alcançados, num único registro (D9)
- [ ] 3.4 Testar o catálogo de permissões instalado, a migration sobre instalação existente, o registro da publicação e a ausência de registro na marcação de leitura e nas notificações de evento
- [ ] 3.5 Commit

## 4. Publicação manual

- [ ] 4.1 Criar o formulário da publicação, com título, mensagem, tipo publicável manualmente e destinatários, com os limites de tamanho num único ponto do código
- [ ] 4.2 Criar as views de criar, revisar e publicar sobre a `ModalView`, com a revisão em `continues_in_modal` e a publicação por POST com CSRF (D7)
- [ ] 4.3 Criar as rotas em `notices/urls.py`, com `login_required`, e a permissão `NOTIFICACAO.PUBLICAR` declarada em cada view
- [ ] 4.4 Criar a rota de opções de usuários do `notices`, com a permissão `NOTIFICACAO.PUBLICAR`, e usar o componente de seleção na escolha do perfil e dos usuários (D10)
- [ ] 4.5 Criar os templates da criação, da revisão com a prévia e a quantidade de destinatários, e a mensagem de sucesso
- [ ] 4.6 Testar cada rota nas quatro situações de acesso, o fluxo com e sem htmx, a volta da revisão sem perder os dados, a mudança de destinatários entre a revisão e a publicação e a ausência de envio de e-mail
- [ ] 4.7 Commit

## 5. Notificação gerada por evento

- [ ] 5.1 Criar o registro de eventos no `notices`, sem importar app de domínio (D5)
- [ ] 5.2 Declarar o evento da troca de perfil no `accounts`, notificando o usuário afetado na mesma transação da operação (D5, D6)
- [ ] 5.3 Testar a notificação criada na troca, a ausência dela na operação recusada, a transação desfeita e o evento para usuário inativo
- [ ] 5.4 Commit

## 6. Área de notificações do usuário

- [ ] 6.1 Passar o sino e o painel do `ui` a receber as notificações e a contagem do usuário autenticado, e retirar o `SAMPLE_NOTIFICATIONS` e os testes dele (D12)
- [ ] 6.2 Criar a página de notificações, paginada conforme a spec `interface`, com o estado vazio em texto
- [ ] 6.3 Criar as rotas de abrir e de marcar como lida, por POST com CSRF, e a de marcar todas como lidas, só com `login_required` (D8)
- [ ] 6.4 Criar a rota que devolve o fragmento do sino com a contagem e a lista do usuário autenticado, só com `login_required` (D11)
- [ ] 6.5 Ajustar o `notifications.js` para o filtro entre todas e não lidas sobre os dados reais, mantendo o funcionamento sem JavaScript
- [ ] 6.6 Testar a contagem, a abertura marcando como lida, o destino, a marcação de todas, a notificação de outro usuário recusada, a marcação sem CSRF e o comportamento sem JavaScript
- [ ] 6.7 Rodar `make test` com a suíte inteira passando
- [ ] 6.8 Commit

## 7. Tempo real

- [ ] 7.1 Acrescentar a infraestrutura do canal escolhida em 1.4, com o servidor ASGI e a camada de mensagens configurados por variável de ambiente (D11)
- [ ] 7.2 Acrescentar ao `compose.yaml`, ao `Dockerfile` e ao `Makefile` o que o canal exigir, mantendo o ambiente subindo com um `docker compose up`
- [ ] 7.3 Criar o destino por usuário e a autenticação da conexão pela sessão, de modo que um usuário só receba os eventos dele (D11)
- [ ] 7.4 Disparar o aviso no `transaction.on_commit` da operação que grava a notificação, com o evento informando só que as notificações do usuário mudaram (D11)
- [ ] 7.5 Fazer o `notifications.js` pedir o fragmento do sino ao ser avisado e ao reconectar, e definir o limite de tempo da atualização em configuração (D11)
- [ ] 7.6 Testar o aviso depois da confirmação da transação, o evento restrito ao destinatário, a publicação concluída com o canal falhando e o fragmento do sino devolvendo o estado gravado
- [ ] 7.7 Rodar `make test` com a suíte inteira passando
- [ ] 7.8 Commit

## 8. Documentação e verificação

- [ ] 8.1 Acrescentar ao glossário da seção 9.4 das convenções os termos de notificação, comunicado, destinatário e lida/não lida
- [ ] 8.2 Documentar as notificações, o canal de tempo real e os comandos do ambiente no `README.md`
- [ ] 8.3 Conferir no navegador, no banco `visual_check`, em 360 e 1280 px, com teclado, com e sem JavaScript, e com duas janelas para ver o sino atualizar sem recarregar
- [ ] 8.4 Validar a Change com `openspec validate notificar-usuarios --strict`
- [ ] 8.5 Commit
