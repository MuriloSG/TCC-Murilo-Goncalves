## ADDED Requirements

### Requirement: Escopo do cache público
O cache público DEVE (MUST) ser usado só pelo calendário público e pelo horário original, e só para as opções dos filtros do semestre e, quando a medição justificar, para a Grade montada. Ele NÃO DEVE (MUST NOT) guardar a resposta HTTP inteira, dado de sessão, de cookie, de usuário autenticado, de permissão, token CSRF ou mensagem. O conteúdo guardado DEVE (MUST) ser só o que a tela mostra a qualquer visitante. As telas autenticadas e as do login, da saída e da recuperação de senha NÃO DEVEM (MUST NOT) usar o cache público. O PostgreSQL DEVE (MUST) continuar como a fonte de verdade.

#### Scenario: Visitante autenticado recebe o mesmo conteúdo
- **GIVEN** a Grade da sala 10 está no cache público
- **WHEN** um administrador autenticado e um visitante anônimo abrem o calendário da sala 10
- **THEN** os dois recebem a mesma Grade, sem dado do administrador

#### Scenario: Login fora do cache
- **WHEN** a página de login é aberta duas vezes
- **THEN** nenhuma entrada é gravada no cache público

### Requirement: Chave do cache público
A chave DEVE (MUST) ser montada por uma única função, a partir do recurso, da geração atual e do hash dos parâmetros já normalizados contra o cadastro, e nunca a partir da query string, de cabeçalhos ou de cookies. Parâmetros que não correspondem a nenhum registro DEVEM (MUST) ser descartados antes de compor a chave. A chave DEVE (MUST) ter tamanho fixo, qualquer que seja a URL. A chave da Grade DEVE (MUST) incluir a data de hoje. As respostas de estado vazio e de erro de data NÃO DEVEM (MUST NOT) ser cacheadas.

#### Scenario: Grafias diferentes, mesma chave
- **WHEN** o calendário é aberto com `sala=sala 10` e depois com `sala=SALA 10`
- **THEN** as duas requisições usam a mesma entrada de cache

#### Scenario: Parâmetro inexistente não cria chave
- **WHEN** o calendário é aberto com `sala=` seguido de 5.000 caracteres aleatórios
- **THEN** a sala é descartada e nenhuma entrada de Grade é gravada

#### Scenario: Troca de dia
- **GIVEN** a Grade da sala 10 em cache no dia 06/10/2026
- **WHEN** o calendário da sala 10 é aberto no dia 07/10/2026
- **THEN** a Grade é montada de novo a partir do banco

### Requirement: Invalidação depois do commit
Toda escrita confirmada num modelo cujo dado aparece nas telas públicas DEVE (MUST) invalidar o cache público, incrementando a geração global, e a invalidação DEVE (MUST) acontecer só depois do commit da transação, por `transaction.on_commit`. Uma transação desfeita NÃO DEVE (MUST NOT) alterar o cache. Uma gravação que só altera campos que nenhuma tela pública mostra NÃO DEVE (MUST NOT) invalidar. Toda escrita que não dispara `post_save` ou `post_delete` nesses modelos, como as escritas em massa e a troca dos docentes de uma alocação sem gravá-la, DEVE (MUST) chamar a invalidação explicitamente. Uma falha da invalidação NÃO DEVE (MUST NOT) desfazer nem recusar a operação que escreveu.

#### Scenario: Alteração confirmada aparece na próxima requisição
- **GIVEN** o calendário da sala 10 está em cache
- **WHEN** um administrador renomeia a sala 10 para "Sala 10 A" e a operação é confirmada
- **THEN** a próxima requisição do calendário mostra "Sala 10 A"

#### Scenario: Rollback mantém o cache anterior
- **GIVEN** o calendário da sala 10 está em cache
- **WHEN** uma operação altera uma alocação da sala 10 e a transação é desfeita
- **THEN** a geração não muda e a próxima requisição usa a entrada em cache

#### Scenario: Prévia da importação não invalida
- **WHEN** a prévia de uma importação de ensalamento é gerada e desfeita
- **THEN** a geração do cache público não muda

#### Scenario: Confirmação da importação invalida uma vez
- **WHEN** o worker confirma uma importação de ensalamento com centenas de alocações
- **THEN** a geração do cache público é incrementada depois do commit, uma vez

#### Scenario: Agendamento aprovado
- **GIVEN** o calendário da sala 10 em cache
- **WHEN** uma solicitação de agendamento na sala 10 é aprovada
- **THEN** a próxima requisição do calendário da sala 10 mostra o agendamento

#### Scenario: Login não invalida
- **WHEN** um usuário entra no sistema e o Django grava o último acesso
- **THEN** a geração do cache público não muda

### Requirement: TTL do cache público
Cada recurso do cache público DEVE (MUST) ter o seu TTL, definido e justificado no `design.md`: 1 hora para as opções do semestre, 10 minutos para a Grade do calendário público e 30 minutos para a Grade do horário original. O contador de geração NÃO DEVE (MUST NOT) expirar. O TTL DEVE (MUST) ser só uma proteção adicional, e a consistência DEVE (MUST) vir da invalidação. Se o contador de geração não existir, ele DEVE (MUST) ser recriado com um valor que não repete nenhuma geração anterior.

#### Scenario: Contador removido
- **GIVEN** entradas em cache na geração atual
- **WHEN** o contador de geração é removido do Redis
- **THEN** a próxima requisição recria o contador com um valor novo e não lê as entradas anteriores

### Requirement: Funcionamento sem o Redis
O cache público DEVE (MUST) ser uma otimização: com o Redis indisponível, lento ou sem configuração, as telas públicas DEVEM (MUST) consultar o PostgreSQL e responder com o mesmo conteúdo, sem erro. O tempo limite de conexão e de leitura DEVE (MUST) ser curto, e depois de uma falha o processo DEVE (MUST) deixar de chamar o Redis por um intervalo, para que a indisponibilidade não atrase toda requisição. Um valor ilegível no cache DEVE (MUST) ser tratado como ausente.

#### Scenario: Redis parado
- **GIVEN** o Redis está parado
- **WHEN** um visitante abre o calendário da sala 10
- **THEN** a página mostra a Grade da sala 10 consultada no banco, com o cabeçalho `X-Public-Cache: bypass`

#### Scenario: Redis volta
- **GIVEN** o Redis voltou depois de uma falha
- **WHEN** termina o intervalo de pausa
- **THEN** as requisições voltam a ler e gravar o cache

### Requirement: Diagnóstico do cache público
As telas públicas DEVEM (MUST) responder com o cabeçalho `X-Public-Cache` com o valor `hit`, `miss` ou `bypass`, sem expor chave, geração nem dado, e com `Cache-Control: no-cache`. A consistência NÃO DEVE (MUST NOT) depender do `Cache-Control`. A aplicação DEVE (MUST) registrar em log cada invalidação confirmada, uma vez por transação, e as falhas de conexão com o Redis, no máximo uma vez por intervalo de pausa por processo. Hits e misses NÃO DEVEM (MUST NOT) ser registrados em log por padrão. Nenhum log DEVE (MUST) conter a URL ou a senha do Redis.

#### Scenario: Hit e miss pelo cabeçalho
- **WHEN** o calendário da sala 10 é aberto duas vezes seguidas
- **THEN** a primeira resposta tem `X-Public-Cache: miss` e a segunda `X-Public-Cache: hit`
- **AND** as duas respostas têm `Cache-Control: no-cache`

#### Scenario: Invalidação registrada
- **WHEN** uma importação é confirmada
- **THEN** o log registra uma linha `CACHE INVALIDATED` com a nova geração
