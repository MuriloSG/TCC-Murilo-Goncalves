## ADDED Requirements

### Requirement: Infraestrutura única de notificações
Toda notificação do sistema DEVE (MUST) ser criada por um único mecanismo da aplicação, e nenhum módulo DEVE (MUST) implementar a própria persistência de notificações, tabela própria nem aviso guardado em outro lugar. Cada notificação DEVE (MUST) ter um tipo, e o tipo DEVE (MUST) pertencer a um catálogo do sistema, com o código gravado como dado, no formato de um código em português, e com o rótulo, o ícone e o tom usados só na interface. Uma criação com um tipo fora do catálogo DEVE (MUST) ser recusada, e nenhuma notificação DEVE (MUST) ser gravada. Acrescentar um tipo NÃO DEVE (MUST NOT) exigir tabela nova nem alteração do esquema: DEVE (MUST) bastar acrescentar o código e os dados de exibição ao catálogo. O mecanismo NÃO DEVE (MUST NOT) importar código dos apps de domínio.

#### Scenario: Tabela única
- **GIVEN** uma instalação nova com as migrations aplicadas
- **WHEN** a estrutura do banco é consultada
- **THEN** as notificações de todos os módulos ficam na mesma estrutura
- **AND** não existe tabela de avisos específica de usuários, de perfis ou de comunicados

#### Scenario: Tipo fora do catálogo
- **WHEN** a criação de uma notificação é tentada com um tipo que não está no catálogo
- **THEN** a criação é recusada e nenhuma notificação é gravada

#### Scenario: Tipo novo sem estrutura nova
- **GIVEN** o catálogo de tipos com um tipo acrescentado
- **WHEN** uma notificação desse tipo é criada
- **THEN** ela é gravada na mesma estrutura, sem migration de esquema

#### Scenario: Mecanismo sem dependência de domínio
- **WHEN** os módulos do mecanismo de notificações são inspecionados
- **THEN** nenhum deles importa módulos de `accounts` ou de outro app de domínio

### Requirement: Notificação individual por destinatário
Uma notificação DEVE (MUST) pertencer a um único destinatário, e o conteúdo destinado a vários usuários DEVE (MUST) gerar uma notificação por destinatário. O estado de leitura DEVE (MUST) ser de cada notificação, e portanto de cada usuário, e NÃO DEVE (MUST NOT) existir estado de leitura compartilhado entre destinatários. Um usuário NÃO DEVE (MUST NOT) ver, contar nem marcar como lida a notificação de outro usuário, em nenhuma rota. Cada notificação DEVE (MUST) guardar o título, a mensagem, o tipo, a data e a hora da criação, o estado de leitura e, quando houver, o destino a que ela leva. A data e a hora DEVEM (MUST) ser definidas pelo sistema no momento da criação. As notificações de um usuário DEVEM (MUST) ser apresentadas da mais recente para a mais antiga.

#### Scenario: Uma notificação por destinatário
- **GIVEN** 100 usuários elegíveis
- **WHEN** um comunicado é publicado para todos eles
- **THEN** existem 100 notificações, uma para cada usuário, todas não lidas

#### Scenario: Leitura de um não é leitura de todos
- **GIVEN** o mesmo comunicado entregue a Ana e a Bruno, não lido pelos dois
- **WHEN** Ana marca a notificação dela como lida
- **THEN** a notificação de Ana fica lida e a de Bruno continua não lida

#### Scenario: Notificação de outro usuário
- **GIVEN** uma notificação de Bruno, não lida
- **WHEN** Ana, autenticada, acessa diretamente a rota dessa notificação
- **THEN** a requisição é recusada, a notificação continua não lida e o conteúdo dela não é exibido

#### Scenario: Ordem das notificações
- **GIVEN** três notificações de um usuário, criadas em dias diferentes
- **WHEN** a área de notificações dele é exibida
- **THEN** elas aparecem da mais recente para a mais antiga, com a data e a hora no formato dd/mm/aaaa e 24 horas

### Requirement: Destinatários e elegibilidade
Uma publicação DEVE (MUST) destinar a notificação de uma destas formas: a todos os usuários elegíveis, aos usuários de um perfil ou a usuários específicos escolhidos um a um. O perfil DEVE (MUST) ser o mesmo perfil da spec `gestao-perfis`, e NÃO DEVE (MUST NOT) existir agrupamento de destinatários próprio das notificações. Na publicação manual, DEVE (MUST) ser considerado elegível somente o usuário com `is_active = True`, nas três formas, inclusive quando um usuário inativo for escolhido um a um; um usuário inativo escolhido DEVE (MUST) ser apenas excluído dos destinatários, sem recusar a publicação. A resolução dos destinatários DEVE (MUST) acontecer num único ponto da aplicação, que recebe a forma de destinar e devolve o conjunto de usuários, e DEVE (MUST) ser aplicada no momento da publicação. Uma publicação cujo conjunto de destinatários fique vazio DEVE (MUST) ser recusada, sem criar nenhuma notificação e informando o motivo a quem publicou. Uma notificação já entregue NÃO DEVE (MUST NOT) alcançar usuários cadastrados depois dela.

#### Scenario: Destino a todos os usuários elegíveis
- **GIVEN** 8 usuários ativos e 2 inativos
- **WHEN** um comunicado é publicado para todos os usuários elegíveis
- **THEN** existem 8 notificações, uma para cada usuário ativo
- **AND** nenhum dos dois usuários inativos tem notificação

#### Scenario: Destino a um perfil
- **GIVEN** 5 usuários ativos com o perfil `DOCENTE` e 3 usuários ativos com outros perfis
- **WHEN** um comunicado é publicado para o perfil `DOCENTE`
- **THEN** existem 5 notificações, só para os usuários desse perfil

#### Scenario: Destino a usuários específicos
- **GIVEN** os usuários ativos Ana, Bruno e Carla
- **WHEN** um comunicado é publicado para Ana e Carla
- **THEN** existem duas notificações, uma de Ana e uma de Carla, e Bruno não tem notificação

#### Scenario: Usuário inativo escolhido um a um
- **GIVEN** Ana ativa e Bruno inativo
- **WHEN** um comunicado é publicado escolhendo os dois
- **THEN** a publicação é concluída com uma notificação, a de Ana
- **AND** a quantidade de destinatários alcançados registrada é 1

#### Scenario: Publicação sem nenhum destinatário
- **GIVEN** um perfil sem nenhum usuário ativo
- **WHEN** a publicação de um comunicado para esse perfil é enviada
- **THEN** a publicação é recusada, nenhuma notificação é criada e a mensagem informa que não há destinatários

#### Scenario: Usuário cadastrado depois da publicação
- **GIVEN** um comunicado publicado para todos os usuários elegíveis
- **WHEN** um usuário novo é cadastrado e acessa a área de notificações dele
- **THEN** ele não tem esse comunicado

### Requirement: Publicação manual de comunicado
Um usuário autorizado DEVE (MUST) poder publicar um comunicado do sistema, informando título, mensagem, tipo e destinatários. O título e a mensagem DEVEM (MUST) ser obrigatórios, com os limites de tamanho definidos num único ponto do código, e o texto DEVE (MUST) seguir a spec `texto-interface`. O tipo DEVE (MUST) ser escolhido entre os tipos do catálogo marcados como publicáveis manualmente; um tipo gerado por evento NÃO DEVE (MUST NOT) aparecer nessa escolha nem ser aceito no envio. A escolha do perfil e a escolha de usuários específicos DEVEM (MUST) usar o componente de seleção da spec `interface`, esta última na forma de vários valores, e a escolha de usuários DEVE (MUST) oferecer apenas usuários ativos. A publicação DEVE (MUST) ser feita somente por requisição POST com token CSRF válido, depois da revisão, e DEVE (MUST) guardar a publicação e criar todas as notificações numa única transação, de modo que uma falha não deixe parte dos destinatários notificados. A publicação guardada DEVE (MUST) conter o tipo, o título, a mensagem, a forma de destinar, a quantidade de destinatários alcançados, quem publicou e a data e a hora, e cada notificação entregue DEVE (MUST) apontar para ela. Uma notificação gerada por evento NÃO DEVE (MUST NOT) ter publicação. Uma publicação recusada por validação ou por regra de negócio NÃO DEVE (MUST NOT) criar nenhuma notificação. A publicação NÃO DEVE (MUST NOT) enviar e-mail nem qualquer outra mensagem fora do sistema.

#### Scenario: Comunicado publicado
- **GIVEN** um usuário autorizado e 8 usuários ativos
- **WHEN** ele publica o comunicado "Nova versão do sistema", com a mensagem sobre a atualização, para todos os usuários elegíveis
- **THEN** cada um dos 8 usuários passa a ter uma notificação não lida com esse título, essa mensagem e esse tipo
- **AND** a tela de origem é exibida com a mensagem de sucesso informando a quantidade de destinatários

#### Scenario: Publicação sem título
- **WHEN** a publicação é enviada sem o título
- **THEN** o formulário é exibido com o erro no campo e nenhuma notificação é criada

#### Scenario: Tipo gerado por evento na publicação manual
- **WHEN** a publicação é enviada com um tipo que o catálogo não marca como publicável manualmente
- **THEN** a publicação é recusada e nenhuma notificação é criada

#### Scenario: Publicação sem token CSRF
- **GIVEN** um usuário autorizado
- **WHEN** uma publicação é enviada por POST sem token CSRF válido
- **THEN** a requisição é recusada com 403 e nenhuma notificação é criada

#### Scenario: Publicação por GET
- **GIVEN** um usuário autorizado
- **WHEN** ele acessa a rota de publicação por GET
- **THEN** o formulário é exibido e nenhuma notificação é criada

#### Scenario: Falha no meio da entrega
- **GIVEN** uma publicação para 100 destinatários que falha depois de criar parte das notificações
- **WHEN** a transação é desfeita
- **THEN** nenhum dos 100 usuários tem a notificação

#### Scenario: Publicação guardada
- **GIVEN** um usuário autorizado e 8 usuários ativos
- **WHEN** ele publica um comunicado para todos os usuários elegíveis
- **THEN** existe uma publicação com o título, a mensagem, o tipo, a forma de destinar, a quantidade 8, ele como quem publicou e a data e a hora
- **AND** as 8 notificações entregues apontam para essa publicação

#### Scenario: Notificação de evento sem publicação
- **WHEN** a notificação da troca de perfil é criada
- **THEN** ela não tem publicação

#### Scenario: Publicação não gera e-mail
- **WHEN** um comunicado é publicado para todos os usuários elegíveis
- **THEN** nenhum envio de e-mail é registrado no outbox

### Requirement: Revisão antes da publicação
A publicação manual DEVE (MUST) acontecer no fluxo criar, revisar, publicar e sucesso, em duas páginas completas, e NÃO DEVE (MUST NOT) abrir em modal: são duas etapas com conteúdo extenso, como a prévia da importação de planilhas, e não uma ação de gestão de um registro da tela atual. As duas páginas DEVEM (MUST) indicar em qual etapa o usuário está e quais são as etapas do fluxo. A etapa de revisão DEVE (MUST) receber o que foi preenchido na etapa anterior sem gravar nada, e nenhuma notificação DEVE (MUST) existir antes da publicação. A revisão DEVE (MUST) exibir a prévia da notificação como o destinatário vai vê-la, com o título, a mensagem, o ícone e o tom do tipo escolhido, e DEVE (MUST) informar a quantidade de destinatários que serão alcançados e a forma de destinar. A revisão DEVE (MUST) oferecer o controle para voltar e corrigir os dados, sem perdê-los, e o controle que publica. A quantidade exibida na revisão DEVE (MUST) ser informativa: a publicação DEVE (MUST) resolver os destinatários de novo no momento em que é confirmada, e a quantidade registrada DEVE (MUST) ser a do conjunto alcançado.

#### Scenario: Etapas do fluxo
- **WHEN** o usuário autorizado abre a criação de uma notificação
- **THEN** a página mostra a etapa atual e as etapas do fluxo, com "Criar" como a atual e "Revisar" como a seguinte
- **AND** ao avançar, a revisão mostra "Criar" como concluída e "Revisar" como a atual

#### Scenario: Prévia e quantidade na revisão
- **GIVEN** 12 usuários ativos com o perfil `DOCENTE`
- **WHEN** o usuário autorizado preenche o comunicado para o perfil `DOCENTE` e avança para a revisão
- **THEN** a revisão mostra a notificação como o destinatário vai vê-la e informa que 12 destinatários serão alcançados

#### Scenario: Revisão não grava nada
- **WHEN** a revisão de um comunicado é exibida
- **THEN** nenhuma notificação existe ainda

#### Scenario: Voltar da revisão para corrigir
- **GIVEN** a revisão de um comunicado
- **WHEN** o usuário aciona o controle de voltar
- **THEN** o formulário é exibido de novo com o título, a mensagem, o tipo e os destinatários que ele informou

#### Scenario: Revisão abandonada
- **GIVEN** a revisão de um comunicado exibida
- **WHEN** o usuário sai da página sem publicar
- **THEN** nenhuma notificação é criada

#### Scenario: Destinatários mudam entre a revisão e a publicação
- **GIVEN** a revisão de um comunicado para o perfil `DOCENTE`, que informou 12 destinatários
- **AND** que um desses usuários é desativado em seguida
- **WHEN** o comunicado é publicado
- **THEN** existem 11 notificações e a quantidade registrada é 11

#### Scenario: Fluxo sem JavaScript
- **WHEN** as duas páginas são usadas com o JavaScript desligado
- **THEN** o formulário, a revisão e a publicação funcionam pelos envios comuns do formulário

### Requirement: Lista das notificações publicadas
A funcionalidade de notificações DEVE (MUST) abrir numa lista das notificações publicadas, e a criação de uma notificação DEVE (MUST) ser alcançada a partir dela. A lista DEVE (MUST) exibir somente as publicações destinadas a todos os usuários elegíveis, que são os comunicados do sistema; as publicações direcionadas a um perfil ou a usuários específicos NÃO DEVEM (MUST NOT) aparecer nela, e continuam registradas na auditoria, conforme a spec `auditoria`. A lista DEVE (MUST) exibir, de cada publicação, o título, a mensagem, o tipo, a quantidade de destinatários alcançados, quem publicou e a data e a hora, da mais recente para a mais antiga, paginada conforme a spec `interface`. Quando não houver nenhuma publicação global, a lista DEVE (MUST) informar isso em texto, sem ilustração. A lista NÃO DEVE (MUST NOT) alterar dados, e o acesso a ela DEVE (MUST) ser auditado como o das demais funcionalidades.

#### Scenario: Lista antes da criação
- **WHEN** um usuário autorizado abre as notificações pela navegação
- **THEN** ele vê a lista das notificações publicadas e o controle que leva à criação de uma notificação

#### Scenario: Só as publicações globais
- **GIVEN** um comunicado publicado para todos os usuários elegíveis, um publicado para um perfil e um publicado para usuários específicos
- **WHEN** a lista é exibida
- **THEN** só o comunicado publicado para todos aparece

#### Scenario: Conteúdo de cada linha
- **GIVEN** um comunicado publicado por Ana para 8 usuários elegíveis
- **WHEN** a lista é exibida
- **THEN** a linha mostra o título, a mensagem, o tipo, "8 usuários", Ana e a data e a hora no formato dd/mm/aaaa e 24 horas

#### Scenario: Lista vazia
- **GIVEN** nenhuma publicação global
- **WHEN** a lista é exibida
- **THEN** ela informa em texto que não há notificação publicada para todos os usuários

#### Scenario: Lista paginada
- **GIVEN** 6 publicações globais
- **WHEN** a lista é acessada sem o parâmetro de página
- **THEN** ela mostra as 5 mais recentes, com o rodapé de paginação da spec `interface`

### Requirement: Autorização da publicação de notificações
A lista das notificações publicadas e a publicação manual DEVEM (MUST) exigir autenticação e a permissão `NOTIFICACAO.PUBLICAR`, conforme a spec `controle-acesso`, em todas as etapas do fluxo e em todos os métodos HTTP. Um visitante não autenticado DEVE (MUST) ser redirecionado para o login, e um usuário autenticado sem a permissão DEVE (MUST) receber 403, inclusive nas rotas de opções que alimentam a escolha dos destinatários. O item de navegação e os controles que levam à publicação DEVEM (MUST) aparecer somente para quem tem a permissão, sem que isso substitua a verificação no servidor. A área de notificações do próprio usuário DEVE (MUST) exigir somente autenticação, e NÃO DEVE (MUST NOT) depender de nenhuma permissão.

#### Scenario: Visitante não autenticado
- **WHEN** um visitante acessa diretamente a URL da lista ou a da publicação
- **THEN** ele é redirecionado para a página de login com a indicação da página solicitada

#### Scenario: Usuário sem a permissão
- **GIVEN** um usuário ativo autenticado, sem superadmin, cujo perfil não concede `NOTIFICACAO.PUBLICAR`
- **WHEN** ele acessa a lista, a criação, a revisão ou envia o POST da publicação
- **THEN** a requisição é recusada com 403 em todas elas e nenhuma notificação é criada
- **AND** a navegação não mostra o controle de publicar

#### Scenario: Usuário com a permissão
- **GIVEN** um usuário ativo autenticado, sem superadmin, cujo perfil concede somente `NOTIFICACAO.PUBLICAR`
- **WHEN** ele acessa a publicação
- **THEN** o acesso é concedido
- **AND** o acesso à lista de usuários continua recusado com 403

#### Scenario: Área do próprio usuário sem permissão específica
- **GIVEN** um usuário ativo autenticado, sem superadmin, com o perfil `DOCENTE`, que não concede nenhuma permissão
- **WHEN** ele abre a área de notificações dele
- **THEN** o acesso é concedido e ele vê somente as próprias notificações

### Requirement: Notificações geradas por eventos do sistema
Uma ação do sistema DEVE (MUST) poder gerar notificações automaticamente. Cada evento DEVE (MUST) ser declarado pelo app dono da ação, informando o tipo da notificação, o texto e a regra que define os destinatários a partir do que aconteceu, e o mecanismo de notificações NÃO DEVE (MUST NOT) conhecer os eventos nem os apps que os declaram. As notificações do evento DEVEM (MUST) ser criadas na mesma transação da operação que o origina, de modo que uma operação desfeita não deixe notificação e uma operação aplicada não fique sem ela. Uma operação recusada por regra de negócio ou por validação NÃO DEVE (MUST NOT) gerar notificação. Acrescentar um evento novo NÃO DEVE (MUST NOT) exigir alteração do mecanismo, do esquema nem das telas: DEVE (MUST) bastar acrescentar o tipo ao catálogo e declarar o evento no app dono da ação. Nesta versão, DEVE (MUST) existir o evento da troca de perfil de um usuário, que notifica o usuário afetado, e a notificação dele DEVE (MUST) ser criada mesmo quando o usuário estiver inativo, por dizer respeito a ele e ficar disponível quando ele voltar a entrar.

#### Scenario: Troca de perfil notifica o usuário
- **GIVEN** o usuário Bruno com o perfil `DOCENTE`
- **WHEN** alguém com a permissão de alterar o perfil o troca para `ADMINISTRADOR`
- **THEN** Bruno passa a ter uma notificação não lida informando o perfil novo
- **AND** nenhum outro usuário recebe notificação por essa troca

#### Scenario: Operação desfeita não deixa notificação
- **GIVEN** uma troca de perfil que falha depois de gravar
- **WHEN** a transação é desfeita
- **THEN** nem o perfil novo nem a notificação permanecem

#### Scenario: Operação recusada não notifica
- **GIVEN** uma troca de perfil recusada pela regra de continuidade administrativa da spec `gestao-usuarios`
- **WHEN** a recusa é informada a quem executou
- **THEN** nenhuma notificação é criada

#### Scenario: Evento para usuário inativo
- **GIVEN** um usuário inativo
- **WHEN** o perfil dele é trocado
- **THEN** a notificação é criada para ele
- **AND** ele a vê como não lida quando voltar a entrar

#### Scenario: Evento novo sem alterar o mecanismo
- **GIVEN** um app que declara um evento novo, com o tipo acrescentado ao catálogo
- **WHEN** a ação desse app acontece
- **THEN** as notificações são criadas pelo mesmo mecanismo, sem migration de esquema e sem alteração nas telas de notificação

### Requirement: Área de notificações do usuário
Toda página autenticada DEVE (MUST) dar acesso às notificações do usuário autenticado pelo painel do cabeçalho, definido na spec `interface`, e DEVE (MUST) existir uma página com o histórico completo das notificações dele, paginada conforme a spec `interface`. A contagem de não lidas DEVE (MUST) ser a das notificações não lidas do próprio usuário no momento da requisição, DEVE (MUST) aparecer junto do sino quando for maior que zero e NÃO DEVE (MUST NOT) aparecer quando for zero. O painel DEVE (MUST) permitir ver todas as notificações ou somente as não lidas, e DEVE (MUST) informar em texto quando não houver nenhuma a mostrar. Cada notificação DEVE (MUST) indicar se está não lida por texto e por forma, e não somente pela cor. Abrir uma notificação não lida DEVE (MUST) marcá-la como lida para aquele usuário e DEVE (MUST) atualizar a contagem de não lidas, na própria resposta e nas requisições seguintes; quando a notificação tiver destino, abrir DEVE (MUST) levar a ele. Marcar como lida DEVE (MUST) ser feito por POST com token CSRF válido, individualmente ou para todas as não lidas do usuário de uma vez, e DEVE (MUST) funcionar sem JavaScript. Marcar como lida uma notificação já lida NÃO DEVE (MUST NOT) alterar nada. NÃO DEVE (MUST NOT) existir operação que marque como não lida nem que exclua uma notificação nesta versão.

#### Scenario: Contagem de não lidas
- **GIVEN** um usuário com 2 notificações não lidas e 3 lidas
- **WHEN** ele abre qualquer página autenticada
- **THEN** o sino mostra a contagem 2 e o nome acessível informa 2 não lidas

#### Scenario: Sem notificações não lidas
- **GIVEN** um usuário sem nenhuma notificação não lida
- **WHEN** ele abre qualquer página autenticada
- **THEN** o sino não mostra contagem

#### Scenario: Abertura de uma notificação não lida
- **GIVEN** um usuário com 2 notificações não lidas
- **WHEN** ele abre uma delas
- **THEN** essa notificação fica lida para ele e a contagem exibida passa a 1, sem que ele recarregue a página

#### Scenario: Abertura de notificação com destino
- **GIVEN** uma notificação não lida com destino
- **WHEN** o usuário a abre
- **THEN** ela fica lida e a resposta leva ao destino

#### Scenario: Marcar todas como lidas
- **GIVEN** um usuário com 4 notificações não lidas
- **WHEN** ele marca todas como lidas
- **THEN** as 4 ficam lidas, a contagem passa a zero e as notificações de outros usuários não mudam

#### Scenario: Marcação sem token CSRF
- **WHEN** uma marcação como lida é enviada por POST sem token CSRF válido
- **THEN** a requisição é recusada com 403 e a notificação continua não lida

#### Scenario: Marcação de notificação já lida
- **GIVEN** uma notificação já lida
- **WHEN** a marcação como lida é enviada de novo para ela
- **THEN** nada é alterado e a contagem continua a mesma

#### Scenario: Sem notificações
- **GIVEN** um usuário sem nenhuma notificação
- **WHEN** ele abre o painel e a página de notificações
- **THEN** as duas informam em texto que não há notificações, sem ilustração

#### Scenario: Histórico paginado
- **GIVEN** um usuário com 57 notificações
- **WHEN** ele abre a página de notificações
- **THEN** ela mostra a primeira página, da mais recente para a mais antiga, com o rodapé de paginação da spec `interface`

### Requirement: Conteúdo das notificações
O título, a mensagem e os rótulos dos tipos DEVEM (MUST) seguir a spec `texto-interface`, inclusive nos textos gerados por evento. O sistema NÃO DEVE (MUST NOT) gravar senha, token, credencial nem qualquer outro segredo no título, na mensagem ou no destino de uma notificação. Uma notificação gerada por evento DEVE (MUST) descrever o fato com os dados do momento em que ele aconteceu, e NÃO DEVE (MUST NOT) depender de o objeto relacionado continuar existindo para ser exibida. Notificações de exemplo, texto de preenchimento e dados fictícios NÃO DEVEM (MUST NOT) existir no código nem nas telas.

#### Scenario: Texto do evento
- **WHEN** a notificação da troca de perfil é criada
- **THEN** o título e a mensagem estão em português, no tom da spec `texto-interface`, com o nome do perfil novo

#### Scenario: Notificação sem segredo
- **WHEN** as notificações criadas pelo sistema são consultadas
- **THEN** nenhuma delas contém senha, resumo de senha nem token

#### Scenario: Objeto relacionado ausente
- **GIVEN** uma notificação de um fato cujo objeto relacionado não existe mais
- **WHEN** a área de notificações do usuário é exibida
- **THEN** a notificação continua sendo exibida com o título e a mensagem gravados, sem erro

#### Scenario: Ausência de dados de exemplo
- **WHEN** o painel de notificações é exibido para um usuário sem notificações
- **THEN** nenhum título, mensagem ou data de exemplo aparece

### Requirement: Persistência como fonte de verdade
Toda notificação DEVE (MUST) ser gravada no banco de dados antes de qualquer entrega, e a gravação DEVE (MUST) incluir o destinatário, o estado de leitura dele, o tipo, o título, a mensagem, o destino quando houver e a data e a hora da criação, de modo que a exibição não dependa de nenhum dado mantido fora do banco. Uma notificação NÃO DEVE (MUST NOT) existir somente em memória, na sessão do usuário, no navegador nem numa mensagem de um canal de tempo real. A lista de notificações e a contagem de não lidas DEVEM (MUST) ser obtidas sempre do estado gravado, e um evento de tempo real NÃO DEVE (MUST NOT) ser tratado como fonte de dados nem substituir a gravação. A entrega em tempo real DEVE (MUST) acontecer somente depois de a transação que grava a notificação ser confirmada, e a falha dessa entrega NÃO DEVE (MUST NOT) desfazer a notificação, recusar a publicação nem alterar o estado de leitura. A notificação DEVE (MUST) continuar disponível depois de sair e entrar de novo no sistema, de recarregar a página, de fechar e reabrir o navegador e de reiniciar a aplicação, com o mesmo estado de leitura.

#### Scenario: Gravação antes da entrega
- **WHEN** uma notificação é criada
- **THEN** ela está gravada no banco e pode ser consultada por qualquer requisição seguinte do destinatário
- **AND** a entrega em tempo real acontece somente depois de a transação ser confirmada

#### Scenario: Notificação sobrevive à sessão e ao navegador
- **GIVEN** um usuário com uma notificação não lida
- **WHEN** ele sai do sistema, fecha o navegador, abre de novo e entra
- **THEN** a notificação continua existindo e continua não lida

#### Scenario: Notificação sobrevive ao reinício da aplicação
- **GIVEN** um usuário com 3 notificações, 2 delas não lidas
- **WHEN** a aplicação é reiniciada e ele abre qualquer página autenticada
- **THEN** as 3 notificações continuam existindo e a contagem de não lidas é 2

#### Scenario: Entrega em tempo real falha
- **GIVEN** um comunicado publicado para 8 destinatários
- **WHEN** a entrega em tempo real falha para todos eles
- **THEN** a publicação é concluída, as 8 notificações continuam gravadas e não lidas
- **AND** cada destinatário as encontra ao abrir a área de notificações

#### Scenario: Evento não substitui a gravação
- **WHEN** a área de notificações de um usuário é exibida
- **THEN** o conteúdo e a contagem vêm do estado gravado, e não de eventos recebidos pelo navegador

### Requirement: Atualização do sino em tempo real
Uma notificação criada para um usuário que está com o sistema aberto DEVE (MUST) aparecer no sino sem que ele recarregue a página: a contagem de não lidas DEVE (MUST) ser atualizada e a notificação nova DEVE (MUST) aparecer na lista ao abrir o painel. A atualização DEVE (MUST) acontecer dentro do limite de tempo definido em configuração, num único ponto do código. A entrega DEVE (MUST) alcançar somente o destinatário: um usuário NÃO DEVE (MUST NOT) receber o evento de notificação de outro usuário, e a separação DEVE (MUST) ser feita no servidor, e não pelo navegador. O evento entregue NÃO DEVE (MUST NOT) ser a origem do que a interface mostra: ele DEVE (MUST) apenas informar que as notificações daquele usuário mudaram, e a interface DEVE (MUST) buscar a contagem e a lista atualizadas no servidor, numa requisição autenticada, de modo que a autorização continue decidida num único ponto. A infraestrutura de tempo real DEVE (MUST) subir com o ambiente do projeto, conforme a spec `ambiente-desenvolvimento`. Sem JavaScript, NÃO DEVE (MUST NOT) haver atualização sem recarregar, e o sino DEVE (MUST) mostrar a contagem correta a cada renderização da página.

#### Scenario: Contagem sobe sem recarregar
- **GIVEN** a usuária Ana com o sistema aberto e 3 notificações não lidas
- **WHEN** um comunicado é publicado para todos os usuários elegíveis
- **THEN** o sino de Ana passa a mostrar 4 sem que ela recarregue a página

#### Scenario: Notificação nova na lista
- **GIVEN** o mesmo comunicado recebido em tempo real
- **WHEN** Ana abre o painel do sino, sem recarregar a página
- **THEN** o comunicado aparece na lista dela, como não lido

#### Scenario: Contagem desce ao ler
- **GIVEN** Ana com 4 notificações não lidas
- **WHEN** ela abre uma delas
- **THEN** a notificação fica lida e o sino passa a mostrar 3

#### Scenario: Evento restrito ao destinatário
- **GIVEN** Ana e Bruno com o sistema aberto
- **WHEN** uma notificação é criada somente para Ana
- **THEN** o sino de Ana é atualizado
- **AND** nenhum evento dessa notificação alcança a sessão de Bruno

#### Scenario: Conteúdo buscado no servidor
- **WHEN** a interface recebe o evento de que as notificações mudaram
- **THEN** ela busca a contagem e a lista numa requisição autenticada
- **AND** o que é exibido é o estado gravado do usuário autenticado

#### Scenario: Sem JavaScript
- **GIVEN** um usuário com o JavaScript desligado e uma notificação criada para ele
- **WHEN** ele carrega qualquer página autenticada
- **THEN** o sino mostra a contagem atualizada, e nada mais é exigido dele

### Requirement: Perda de conexão e reconciliação
A interface NÃO DEVE (MUST NOT) depender do canal de tempo real para conhecer as notificações do usuário. Uma notificação criada enquanto o usuário está sem conexão, com o sistema fechado ou com o canal indisponível DEVE (MUST) continuar gravada e não lida, e DEVE (MUST) aparecer na contagem e na lista assim que ele voltar, pela consulta comum ao estado gravado. Ao restabelecer a conexão, a interface DEVE (MUST) reconciliar o estado pelo servidor, e NÃO DEVE (MUST NOT) tentar recuperar eventos perdidos nem manter no navegador um estado que o servidor não tenha. Enquanto o canal estiver indisponível, todas as funcionalidades das notificações DEVEM (MUST) continuar disponíveis pela navegação comum: a contagem, o painel, a página, a abertura e a marcação como lida. A indisponibilidade do canal NÃO DEVE (MUST NOT) impedir nem recusar a publicação de notificações.

#### Scenario: Notificação criada com o usuário fora do sistema
- **GIVEN** um usuário sem sessão aberta
- **WHEN** um comunicado é publicado para ele
- **THEN** a notificação fica gravada e não lida
- **AND** ele a vê na contagem e na lista quando entrar

#### Scenario: Conexão perdida no momento da publicação
- **GIVEN** um usuário com a página aberta e sem conexão com o canal de tempo real
- **WHEN** uma notificação é criada para ele e, em seguida, a conexão volta
- **THEN** a contagem e a lista passam a mostrar a notificação, obtidas do servidor
- **AND** nenhum evento perdido precisa ser reenviado para isso

#### Scenario: Canal indisponível
- **GIVEN** o canal de tempo real fora do ar
- **WHEN** um usuário abre o painel, abre uma notificação e marca outra como lida
- **THEN** todas as operações funcionam pela navegação comum
- **AND** a contagem exibida continua sendo a do estado gravado

#### Scenario: Publicação com o canal fora do ar
- **GIVEN** o canal de tempo real fora do ar
- **WHEN** um usuário autorizado publica um comunicado
- **THEN** a publicação é concluída, as notificações são gravadas e a auditoria registra a publicação
