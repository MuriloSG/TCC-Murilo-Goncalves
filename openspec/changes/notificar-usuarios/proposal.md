## Why

O cabeçalho de todas as páginas autenticadas já mostra o sino e o painel de notificações, mas com dados fixos escritos no `ui/templatetags/ui.py`: cinco notificações de exemplo, sobre reservas e espaços que ainda não existem, iguais para todo usuário e com um estado de leitura que só vive no navegador. Isso contraria a seção 9.2 das convenções, que proíbe texto de preenchimento e dados fictícios, e a seção 9.8, que manda deixar de fora da tela o que não existe no sistema. Nenhuma spec descreve hoje o que uma notificação é.

Ao mesmo tempo, o sistema já tem ações que o usuário só descobre por acaso: quem tem o perfil trocado não é avisado, e a administração não tem como comunicar nada a quem usa o sistema. Os módulos de espaços e reservas, por vir, precisarão avisar sobre solicitação criada, reserva aprovada, recusada e cancelada.

Esta Change especifica a infraestrutura de notificações do sistema: um único lugar onde uma notificação é criada, gravada, entregue a cada destinatário e lida, servindo tanto à publicação manual de um comunicado quanto às notificações geradas por eventos, e preparada para receber os eventos dos módulos futuros sem estrutura nova. As notificações são internas ao sistema e aparecem no sino da interface, que passa a mostrar uma notificação nova sem que o usuário recarregue a página.

## What Changes

- **Capability nova `notificacoes`**, com o app `notices`: catálogo de tipos, criação da notificação, resolução dos destinatários, entrega por destinatário e estado de leitura individual.
- **Uma notificação por destinatário.** Um comunicado global recebido por 100 usuários vira 100 notificações, cada uma com o próprio estado de leitura, e nunca um estado de leitura compartilhado.
- **Três formas de destinar:** todos os usuários elegíveis, os usuários de um perfil e usuários específicos. O perfil é o `Role` que já existe, e não um agrupamento novo.
- **Elegibilidade pela situação do usuário:** uma publicação manual alcança somente usuários ativos, em qualquer das três formas.
- **Publicação manual de comunicado**, em modal, no fluxo criar → revisar → publicar → sucesso, com prévia da notificação e a quantidade de destinatários antes de publicar.
- **Notificação gerada por evento:** o app dono do evento registra o tipo e a regra de destinatários, e o `notices` não importa código de app de domínio, como o `outbox` faz com os tratadores de e-mail. Esta Change usa esse mecanismo na troca de perfil de um usuário, que passa a notificar o usuário afetado.
- **Permissão `NOTIFICACAO.PUBLICAR`**, concedida ao perfil `ADMINISTRADOR` pela migration que a acrescenta. A área de notificações do próprio usuário exige só autenticação.
- **Auditoria da publicação:** um registro com a ação `PUBLICAR`, o módulo `NOTIFICACAO` e a quantidade de destinatários alcançados, no mecanismo de auditoria que já existe. A marcação de leitura não é auditada.
- **Sino e painel com dados reais**, com a contagem de não lidas do usuário autenticado, a abertura de uma notificação, a marcação individual como lida e a página com o histórico paginado. Os dados de exemplo do `ui` saem.
- **Persistência como fonte de verdade:** a notificação é gravada antes de qualquer entrega, e a contagem e a lista sempre vêm do banco. Um evento de tempo real nunca é a origem do que a tela mostra.
- **Atualização do sino em tempo real**, sem recarregar a página: uma notificação criada para quem está com o sistema aberto atualiza a contagem e aparece na lista. O canal alcança só o destinatário e informa apenas que as notificações dele mudaram; a interface busca a contagem e a lista numa requisição autenticada.
- **Infraestrutura de comunicação em tempo real**, que o projeto ainda não tem: ela é introduzida por esta Change e sobe pelo mesmo `docker compose up`. A tecnologia é decidida no design da implementação (D11).
- **Reconciliação pelo servidor:** quem estiver sem conexão quando a notificação for criada a encontra ao voltar, pela consulta comum. Com o canal fora do ar, tudo continua funcionando pela navegação normal.

### Fora do escopo

- Qualquer canal fora do sistema: e-mail, push, WhatsApp, SMS e aplicativo. Esta versão tem só a notificação interna, no sino da interface. O envio de e-mails continua sendo o do `outbox`, e nenhuma notificação desta Change gera e-mail.
- Entrega em tempo real de qualquer outra coisa além das notificações do usuário. O canal criado aqui atende ao sino, e não vira um mecanismo geral de atualização de telas.
- Recuperação de eventos perdidos pelo canal, histórico de entregas e confirmação de recebimento. A reconciliação é feita pela consulta ao estado gravado.
- Agendamento da publicação, preferências de notificação por usuário, templates de conteúdo, campanhas, indicadores de leitura e exclusão ou expiração automática das notificações.
- Os eventos dos módulos de espaços e reservas, que ainda não existem. Eles entram pelas Changes desses módulos, acrescentando tipo e regra de destinatários ao mecanismo desta.

### Dependência

Esta Change depende da Change `selecionar-opcoes-com-busca`, que cria o componente de seleção e as rotas de opções paginadas usadas pela escolha de perfil e de usuários específicos na publicação. O delta da spec `controle-acesso` parte do texto dela, e ela DEVE ser arquivada antes desta.

## Capabilities

### New Capabilities

- `notificacoes`: infraestrutura de notificações do sistema, com tipos, destinatários, entrega por destinatário, estado de leitura individual, publicação manual e notificação gerada por evento.

### Modified Capabilities

- `controle-acesso`: a permissão `NOTIFICACAO.PUBLICAR` entra no catálogo, com a configuração padrão para o perfil `ADMINISTRADOR`, e a publicação entra na correspondência entre operações e permissões.
- `auditoria`: a publicação manual passa a ser uma alteração auditada, e a marcação de leitura e a entrega de uma notificação gerada por evento ficam explicitamente fora da auditoria.
- `interface`: o sino de notificações e o painel passam a fazer parte do layout base com dados do usuário autenticado, atualizados sem recarregar a página.
- `ambiente-desenvolvimento`: o canal de tempo real e os serviços que ele exigir sobem com o ambiente, pelo mesmo `docker compose up`.

## Impact

- **`notices` (app novo):** catálogo de tipos, model da notificação, operações de criação e de leitura, resolução dos destinatários, registro dos eventos, views, rotas, templates e migrations.
- **`accounts`:** a permissão nova no catálogo e na migration de dados, e a troca de perfil registrando o evento.
- **`ui`:** o sino e o painel passam a receber os dados do usuário; os exemplos fixos do `ui/templatetags/ui.py` e os testes deles saem.
- **`audit`:** a ação `PUBLICAR` e o módulo `NOTIFICACAO` no catálogo, sem migration de esquema.
- **Tempo real:** o canal, a rota do fragmento do sino consultado depois do evento e a configuração do limite de tempo; o `ui` passa a ouvir o canal e a reconciliar na reconexão.
- **Ambiente:** o `compose.yaml`, o `Dockerfile` e o `Makefile` acompanham o servidor e os serviços que o canal exigir.
- **Dependências novas:** as do canal de tempo real (D11). A persistência fica num model do próprio projeto: a `django-notifications-hq` foi verificada e não roda com o Python 3.13 e o Django 5.2 deste ambiente (D3). A spec descreve o comportamento esperado do sistema, e não a API de nenhuma biblioteca.

## Alinhamento com o TCC

- **RNF06 e P2:** a criação da notificação e a resolução dos destinatários são operações do model, e as views só as acionam.
- **P4 e P8:** um único mecanismo de notificação para todos os módulos, em vez de um aviso por tela, e a mesma área de notificações em todas as páginas.
- **P7, visibilidade do estado do sistema:** o usuário passa a saber o que aconteceu com o que lhe diz respeito sem precisar procurar na tela certa, e sem precisar recarregar a página para descobrir.
- **RNF01:** a publicação é restrita por permissão, pelo mesmo mecanismo das demais funcionalidades, e a leitura é sempre do próprio usuário.
