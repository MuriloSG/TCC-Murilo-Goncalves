## Context

O projeto não tem notificações. O que existe é a aparência delas: o `ui/templatetags/ui.py` define `SAMPLE_NOTIFICATIONS`, cinco itens fixos sobre reservas e espaços que ainda não existem, renderizados por `ui/components/notifications.html` no cabeçalho de todas as páginas autenticadas. O `ui/static/ui/js/notifications.js` filtra entre "Todas" e "Não lidas" e marca tudo como lido apenas no navegador, sem nada no servidor. Os testes `ui/tests/test_base.py` fixam esse painel de exemplo.

As peças de que a Change precisa já existem e são reaproveitadas:

| Peça | Onde | Uso aqui |
|---|---|---|
| Decisão de acesso | `login_required` na URL e `permission_required` lido pelo `PermissionMiddleware` | publicação restrita por `NOTIFICACAO.PUBLICAR` |
| Perfil (`Role`) | `accounts` | destino por perfil, sem agrupamento novo |
| Situação do usuário (`is_active`) | `accounts` | elegibilidade dos destinatários |
| Ação em várias etapas no modal | `ui.views.ModalView`, com `continues_in_modal` | criar → revisar → publicar |
| Componente de seleção com busca e rota de opções | `ui.views.OptionsView` (Change `selecionar-opcoes-com-busca`) | escolha do perfil e dos usuários específicos |
| Paginação | `ui.pagination` | página de notificações |
| Auditoria por catálogo | `audit.catalog` e o ponto único de gravação | ação `PUBLICAR`, módulo `NOTIFICACAO` |
| Tratadores registrados pelo app dono | `outbox` | eventos registrados pelo app dono da ação |

Não há Channels, Daphne, Redis nem qualquer canal de comunicação contínua: o `config/asgi.py` é o gerado pelo `startproject`, a aplicação roda por WSGI e o `compose.yaml` tem os containers `web`, `worker`, `db` e `tailwind`. Nenhum mecanismo assíncrono é usado hoje além do worker do outbox, que é um processo separado que lê o banco, e não um canal com o navegador. A biblioteca `django-notifications-hq` **não está instalada**: o `requirements.txt` tem Django, django-allauth, psycopg e django-htmx, e o `INSTALLED_APPS` não tem `notifications`.

A atualização do sino sem recarregar a página é requisito desta versão, e é a parte que exige infraestrutura nova (D11).

A referência visual da tela de publicação ainda não chegou. Esta Change define o comportamento; o desenho entra na implementação, conforme a seção 9.8 das convenções.

## Goals / Non-Goals

**Goals:**

- Um único mecanismo de notificação, que sirva à publicação manual e aos eventos, e que os módulos de espaços e reservas usem depois sem estrutura nova.
- Estado de leitura por usuário, sempre, inclusive num comunicado global.
- O sino do cabeçalho mostrando dados reais do usuário autenticado.
- O sino atualizado sem recarregar a página, com a persistência continuando a ser a fonte de verdade.

**Non-Goals:**

- Entregar por e-mail, push, SMS, WhatsApp ou qualquer canal fora do sistema.
- Transformar o canal de tempo real num mecanismo geral de atualização de telas.
- Recuperar eventos perdidos pelo canal: quem reconecta reconcilia pelo estado gravado.
- Preferências de notificação por usuário, agendamento, expiração e exclusão de notificações.
- Especificar os eventos dos módulos que ainda não existem.

## Decisions

### D1. App `notices`, e não `notifications`

O app se chama `notices`, em inglês como os demais (`accounts`, `audit`, `outbox`, `imports`, `ui`). O nome `notifications` é o rótulo do app da `django-notifications-hq` e colidiria com ele no `INSTALLED_APPS` se a biblioteca for adotada (D3). As rotas ficam em português: `notificacoes/`, `notificacoes/nova/`, `notificacoes/<id>/revisar/`.

### D2. Uma linha por destinatário, decidida na publicação

Não existe "notificação global" guardada uma vez e lida por muitos. A publicação resolve o conjunto de destinatários e grava uma notificação por usuário, com o título e a mensagem copiados para cada uma. É o que torna o estado de leitura individual um fato do esquema, e não uma regra a lembrar.

O preço é o espaço e o tempo de gravar N linhas numa publicação. Com a escala do campus (centenas de usuários), uma inserção em lote numa transação resolve. A alternativa, um conteúdo compartilhado com uma tabela de leitura por usuário, economizaria espaço e exigiria a linha de leitura de qualquer modo, com a consulta da lista ficando mais cara e o conteúdo variável por destinatário (o nome do perfil novo, por exemplo) sem lugar. Recusada.

Copiar o texto também resolve o objeto relacionado que deixa de existir: a notificação continua legível, porque descreve o fato do momento em que ele aconteceu, e não busca o objeto para se montar.

### D3. Model próprio, porque a biblioteca não roda neste ambiente

**Verificação feita em 24/09/2026, no container do projeto (Python 3.13.15, Django 5.2.17):**

- a última versão publicada da `django-notifications-hq` é a **1.8.3, de outubro de 2023**, e declara suporte até o **Django 4.1**;
- instalada no container, ela falha já no `import`, com `ModuleNotFoundError: No module named 'distutils'`, porque o `notifications/base/models.py` usa `distutils.version.StrictVersion` e o `distutils` saiu do Python 3.12;
- mesmo com isso resolvido, o `Meta.index_together` do model abstrato e a operação `AlterIndexTogether` da migration `0008` foram removidos no Django 5.1;
- ela ainda traz `jsonfield` e `pytz`, desnecessárias desde que o Django tem `JSONField` nativo (3.1) e suporte a fuso próprio (4.0).

**Decisão: a opção 2, o model próprio no `notices`**, com os campos da spec. Usar a biblioteca exigiria um fork mantido pelo projeto ou baixar o Python e o Django, o que contraria P1 da Constitution e o ambiente já especificado. A spec `notificacoes` foi escrita sem depender da API de biblioteca nenhuma, então nenhum requisito muda por causa desta decisão, e é por isso que ela coube na implementação.

O texto abaixo fica registrado como a avaliação que levou à decisão.

### D3.1. A persistência não depende da API de uma biblioteca

A intenção inicial era usar a `django-notifications-hq` como persistência e gerenciamento das notificações. Nada neste projeto depende da API dela, e a spec `notificacoes` descreve só o comportamento esperado do sistema: tipos do catálogo, destinatários, uma notificação por destinatário, leitura individual, publicação com revisão e eventos declarados pelo app dono.

**A biblioteca não resolve o tempo real.** Ela grava e gerencia notificações; a atualização do sino sem recarregar é outra camada, tratada em D11, e nenhuma decisão sobre a biblioteca dispensa essa infraestrutura. Versões dela chegaram a oferecer endpoints de consulta para o navegador buscar a contagem de tempos em tempos, o que é sondagem, e não entrega imediata. De todo modo, rota da biblioteca não é exposta aqui.

Duas saídas atendiam à spec:

1. **Adotar a biblioteca como persistência**, adaptando-a: o app `notices` expõe as operações do projeto (criar, publicar, marcar como lida, contar não lidas) e a biblioteca fica atrás delas. Nesse caso, DEVEM valer: nenhuma rota, view, template, API nem comando da biblioteca é exposto; o vocabulário dela (`verb`, `level`, `actor`, `target`) fica dentro do app, e o que aparece na interface é o catálogo de tipos do projeto, em português; a versão instalada é fixada no `requirements.txt`; e o que a biblioteca não oferecer (a resolução de destinatários, a revisão, a contagem de alcançados para a auditoria) é do projeto.
2. **Model próprio no `notices`**, com os campos da spec.

A verificação acima eliminou a opção 1, e o projeto segue com a opção 2.

Nas duas saídas vale a Constitution: acesso ao banco pelo ORM (P3), mudanças por migrations (P3) e regras de negócio no model (P2, seção 5 das convenções).

### D4. Catálogo de tipos, como o catálogo da auditoria

Cada tipo é um código em português gravado como dado, com rótulo, ícone (Lucide) e tom (`info`, `success`, `warning`, `error`) usados só na interface, e a indicação de ser publicável manualmente. Criar uma notificação de um tipo fora do catálogo é recusado, como na auditoria. Acrescentar um tipo é acrescentar a entrada, sem migration de esquema.

Nesta Change o catálogo tem o que a Change usa:

| Código | Publicável manualmente | Origem |
|---|---|---|
| `COMUNICADO` | sim | publicação manual |
| `PERFIL_ALTERADO` | não | evento da troca de perfil |

Os tipos dos módulos futuros (solicitação criada, reserva aprovada, recusada, cancelada) entram pelas Changes deles, o que é exatamente o teste de que o mecanismo é genérico.

### D5. Eventos declarados pelo app dono da ação

Como o `outbox` faz com os tratadores de e-mail: o `notices` oferece o registro e não importa app de domínio; o app dono da ação declara o evento com o tipo, o texto e a regra de destinatários. A notificação é criada dentro da transação da operação, na própria operação do model, e não por sinal do ORM: o sinal dispararia também em gravações que não são a operação de negócio, e a seção 5 das convenções põe a regra no model.

Um evento só é acrescentado quando existe a ação que o origina. Nesta Change, a troca de perfil (`accounts`), que notifica o usuário afetado. É o mesmo caso que o painel de exemplo do `ui` já mostrava.

### D6. Elegibilidade: ativo para publicação, sempre para o evento direcionado

A publicação manual alcança somente usuários com `is_active = True`, nas três formas de destinar, inclusive quando um inativo é escolhido um a um. Um usuário inativo não entra no sistema (spec `autenticacao`) e não tem permissão nenhuma (spec `controle-acesso`), então incluí-lo inflaria a contagem exibida na revisão e registrada na auditoria com destinatários que não leem nada. O inativo escolhido é excluído do conjunto, e não recusa a publicação, para não obrigar quem publica a saber a situação de cada um.

A notificação de um evento direcionada ao usuário afetado é criada mesmo se ele estiver inativo: ela diz respeito a ele, é consequência de uma operação que o sistema aceitou fazer com ele, e fica disponível se ele for reativado. Descartá-la faria a operação perder o aviso sem que ninguém soubesse.

### D7. Revisão informativa e resolução no momento da publicação

A revisão mostra a prévia e a quantidade de destinatários, e a publicação resolve o conjunto de novo ao ser confirmada. Não se exige que o conjunto seja idêntico ao da revisão, como a importação exige do plano: ali confirmar aplica mudanças linha a linha em dados existentes, e uma divergência silenciosa alteraria o que o usuário não revisou; aqui a divergência só significa que alguém entrou ou saiu da situação ativa no intervalo, e o comunicado deve ir para quem está ativo agora. A quantidade registrada na auditoria é a do conjunto alcançado, e não a exibida na revisão.

### D8. Marcar como lida é POST

Abrir a notificação altera dado, então é POST com CSRF, como a saída do sistema e as ações de situação. O item do painel e da página é um botão de um formulário; quando a notificação tem destino, a resposta leva a ele depois de marcar. Sem JavaScript funciona igual, porque é um formulário comum.

Não há marcar como não lida nem excluir notificação nesta versão: nada no pedido depende disso e a seção 1 das convenções manda não antecipar.

### D9. Leitura fora da auditoria, publicação dentro

A spec `auditoria` manda registrar toda operação que altere dados persistidos. A marcação de leitura altera dados e não é registrada, o que é uma exceção e por isso está escrita na spec, e não deixada ao critério da implementação. O motivo: o estado de leitura é do próprio usuário sobre a própria notificação, muda a cada abertura do painel, não afeta nenhum outro usuário e nenhum dado do domínio, e registrá-lo afogaria a consulta da auditoria, que hoje ainda nem pagina por volume, e cuja utilidade depende de os registros significarem alguma coisa.

A publicação manual é registrada, com um único registro por publicação, contendo a quantidade de destinatários alcançados: é o que responde "quem comunicou o quê, para quantas pessoas e quando". Um registro por destinatário multiplicaria por N sem acrescentar informação.

A notificação criada por um evento não gera registro próprio, porque a operação que a originou já é auditada.

### D10. Rota de opções por tela, e não por dado

A Change `selecionar-opcoes-com-busca` escreveu na spec `controle-acesso` que "a rota de opções de usuários exige `AUDITORIA.VISUALIZAR`, porque só a consulta da auditoria a usa". A escolha de destinatários específicos passa a ser um segundo consumidor de opções de usuários, com outra permissão, e a frase deixa de valer.

A regra geral daquela Change, a de que a permissão da rota é a da tela que consome as opções, continua, e o delta desta Change torna explícito o que ela implica: cada tela declara a própria rota, no app dono da tela. A de usuários do `audit` exige `AUDITORIA.VISUALIZAR`; a de usuários do `notices` exige `NOTIFICACAO.PUBLICAR`. Uma rota única compartilhada entre as duas teria de aceitar a união das permissões e daria a quem só publica notificações o mesmo acesso concedido a quem consulta a auditoria.

A escolha do perfil de destino usa a rota de opções de perfis, que exige só autenticação, pela razão já registrada naquela spec: a escolha de um perfil num formulário não exige `PERFIL.VISUALIZAR`.

### D11. Tempo real: gravar, confirmar, avisar, e a tela busca

O tempo real é requisito desta versão, e é a única parte que exige infraestrutura que o projeto não tem. A ordem é sempre a mesma, e a spec a fixa:

```text
criar → gravar a notificação e o destinatário → confirmar a transação → avisar o destinatário → a tela busca o estado e atualiza o sino
```

Três decisões seguram essa ordem:

1. **Avisar depois da confirmação.** O aviso é disparado no `transaction.on_commit` da operação que grava, e nunca dentro dela. Uma transação desfeita não avisa ninguém sobre uma notificação que não existe, e uma falha no aviso não desfaz a notificação nem recusa a publicação.
2. **O evento não carrega a notificação.** Ele diz apenas que as notificações daquele usuário mudaram. A interface então pede ao servidor o fragmento do sino, numa requisição autenticada comum, e mostra o que vier. Assim a autorização continua num único ponto, o navegador nunca fica com um conteúdo que o servidor não confirmou, e a reconexão é resolvida pelo mesmo caminho, sem fila de eventos perdidos nem numeração de mensagens.
3. **Um destino por usuário.** O evento vai para o destinatário, e a separação é do servidor: cada sessão autenticada escuta só o destino do próprio usuário, e o servidor nunca manda para um destino coletivo do qual o navegador teria de filtrar o que é seu.

**Tecnologia: WebSocket com Django Channels**, decidido com o autor em 24/09/2026. O que a spec exige do canal é alcançar só o destinatário, atualizar dentro do limite configurado e subir pelo mesmo `docker compose up`. As saídas consideradas:

| Saída | O que exige | Observação |
|---|---|---|
| **WebSocket com Django Channels** | servidor ASGI no lugar do WSGI, camada de canal (em memória num processo só, com um serviço de mensagens quando houver mais de um), consumer e rota de WebSocket | entrega imediata, canal nos dois sentidos, autenticação pela sessão que já existe |
| **Eventos enviados pelo servidor (SSE)** | servidor ASGI e uma forma de acordar a conexão quando houver aviso | protocolo mais simples, de mão única, que é o que o sino precisa; menos peças que o WebSocket |
| **Sondagem pelo htmx** | nada de novo | não é entrega imediata: o atraso é o intervalo escolhido, e cada usuário conectado gera requisições o tempo todo |

O escolhido foi o **WebSocket com Channels**, a saída com entrega imediata de verdade, servindo HTTP e WebSocket pelo mesmo container `web` em ASGI, com o destino por usuário.

**Como ficou:** `channels` e `daphne` no `requirements.txt`, `daphne` no início do `INSTALLED_APPS` (o que faz o `runserver` servir ASGI), o `config/asgi.py` roteando o HTTP do Django e o WebSocket autenticado pela sessão, o consumer em `notices/consumers.py` e o aviso em `notices/realtime.py`. O ambiente continua com os mesmos quatro containers: a camada de canal é a `InMemoryChannelLayer`, que basta enquanto a aplicação é um processo só, e é ela que o `docker compose up` sobe, sem serviço novo e sem passo manual. Uma implantação com mais de um processo precisará de uma camada compartilhada (`channels-redis` e um serviço de mensagens), que entra na Change da implantação, quando houver hospedagem definida. Não se antecipa aqui o que o ambiente ainda não usa. A sondagem pelo htmx fica registrada como o caminho de contingência se a infraestrutura de canal não puder ser mantida na hospedagem: ela atende ao requisito de não recarregar a página, com atraso, e nenhuma outra parte da Change muda, porque o que a interface faz ao ser avisada é sempre pedir o fragmento ao servidor.

**Melhoria progressiva.** Sem JavaScript não há canal, e o sino continua correto a cada renderização da página, como o resto do projeto faz com o componente de seleção e os modais. O tempo real é a camada de cima, e nunca a condição para a funcionalidade existir.

**Testes.** O comportamento é verificável sem navegador: que o aviso sai depois da confirmação da transação (`TransactionTestCase` com `serialized_rollback`, como as convenções já pedem para `on_commit`), que ele alcança o destino do destinatário e não o de outro usuário, que a publicação é concluída quando o canal falha, e que a rota do fragmento do sino devolve o estado gravado do usuário autenticado.

### D12. Arquivos

- `notices/catalog.py`: tipos, com rótulo, ícone, tom e publicável manualmente.
- `notices/models.py`: a notificação, o manager com a criação, a entrega e a marcação de leitura, e a resolução dos destinatários.
- `notices/events.py`: registro dos eventos, sem importar app de domínio.
- `notices/forms.py`, `notices/views.py`, `notices/urls.py`, `notices/templates/notices/`: o fluxo de publicação em modal, a página de notificações e a rota de opções de usuários.
- `notices/migrations/`: esquema.
- `accounts/permissions.py` e migration de dados: `NOTIFICACAO.PUBLICAR`, concedida ao perfil `ADMINISTRADOR`.
- `accounts/models.py`: a troca de perfil declarando o evento.
- `audit/catalog.py`: ação `PUBLICAR` e módulo `NOTIFICACAO`.
- `ui/templatetags/ui.py`, `ui/components/notifications.html`, `ui/static/ui/js/notifications.js`: os dados de exemplo saem, o painel passa a receber as notificações do usuário e o JavaScript passa a ouvir o canal e a pedir o fragmento do sino ao ser avisado e ao reconectar.
- `notices/realtime.py` (ou equivalente do canal escolhido) e a rota do fragmento do sino, com `login_required` e sem permissão.
- `config/asgi.py`, `config/settings.py`, `compose.yaml`, `Dockerfile` e `Makefile`: o servidor e os serviços que o canal exigir, e o limite de tempo da atualização em configuração.

### D13. Visual, a partir da referência do autor

A tela de publicação e a página de notificações são telas novas: a referência é pedida ao autor antes de desenhá-las, e o que for adaptado e o que for retirado dela fica registrado aqui na implementação, conforme a seção 9.8 das convenções. O painel do cabeçalho já tem forma definida e só troca a origem dos dados.

## Risks / Trade-offs

- **Publicação para muitos destinatários numa transação.** Com centenas de usuários é uma inserção em lote e não preocupa; se o sistema crescer muito além disso, a publicação passa a ser um trabalho em segundo plano, como o worker do `outbox`. A spec não impede essa mudança, porque exige a transação e não a requisição.
- **Leitura fora da auditoria.** Perde-se saber quando cada usuário leu o quê. É o preço de a auditoria continuar legível, e a decisão está registrada na spec `auditoria` para não parecer esquecimento.
- **Decisão da biblioteca adiada.** A implementação pode descobrir que a `django-notifications-hq` não se adapta sem expor a API dela. A spec continua válida nos dois caminhos, e o custo fica na implementação, não na especificação.
- **Infraestrutura nova só para o sino.** Passar a aplicação para ASGI e manter um canal aberto por usuário é a maior mudança de infraestrutura do projeto até aqui, para atender a um componente. O risco real é a hospedagem, que o TCC deixa dependente de articulação institucional (3.3.1): se o canal não puder ser mantido lá, a contingência é a sondagem pelo htmx (D11), que não muda nenhum requisito nem o resto do código.
- **Conexões abertas.** Cada usuário com o sistema aberto ocupa uma conexão. Na escala do campus isso é pequeno, e o limite aparece muito antes em outras partes; ainda assim, o canal serve só ao sino, e não vira um mecanismo geral de atualização de telas.
- **Dois assuntos numa Change.** As notificações e o canal de tempo real poderiam ser Changes separadas. Ficaram juntas porque o requisito do autor é o sino atualizado sem recarregar, e uma primeira versão que exigisse recarregar entregaria uma funcionalidade que ele já disse não querer. As tarefas mantêm a separação: o mecanismo e a publicação funcionam antes de o canal existir.

## Migration Plan

1. Permissão `NOTIFICACAO.PUBLICAR` no catálogo, por migration de dados, concedida ao perfil `ADMINISTRADOR` sem tocar nos demais perfis, conforme a regra de menor privilégio da spec `controle-acesso`.
2. Esquema das notificações, por migration.
3. Ação `PUBLICAR` e módulo `NOTIFICACAO` no catálogo da auditoria, sem migration de esquema.
4. Troca dos dados de exemplo do `ui` pelas notificações do usuário, com os testes do painel reescritos.
5. Infraestrutura do canal de tempo real no ambiente: servidor ASGI e os serviços que ele exigir no `compose.yaml`, com o limite de tempo da atualização em configuração. O ambiente continua subindo com um `docker compose up`.

Não há dado a migrar: nenhuma notificação existe hoje.

## Open Questions

- Referência visual da tela de publicação e da página de notificações (D13).
