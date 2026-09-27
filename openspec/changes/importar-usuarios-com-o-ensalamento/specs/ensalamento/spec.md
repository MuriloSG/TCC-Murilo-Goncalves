## MODIFIED Requirements

### Requirement: Importação do ensalamento por planilha
Um usuário ativo autenticado com a permissão `ENSALAMENTO.IMPORTAR`, ou superadmin ativo, DEVE (MUST) poder carregar um semestre de ensalamento a partir da planilha institucional, conforme a spec `importacao-planilhas`, com o tipo `ENSALAMENTO`. O sistema NÃO DEVE (MUST NOT) exigir nenhuma alteração na planilha: NÃO DEVE (MUST NOT) exigir coluna, aba, identificador, código ou marcação criados para ele, e NÃO DEVE (MUST NOT) alterar o arquivo enviado.

O envio DEVE (MUST) receber o arquivo da planilha e o código do semestre, porque nenhuma aba da planilha traz o semestre. O código DEVE (MUST) ser obrigatório e validado no formato do semestre, e o semestre DEVE (MUST) ser criado quando ainda não existir. Um envio sem o código, ou com um código fora do formato, DEVE (MUST) ser recusado no formulário de envio, sem criar importação. A importação inteira DEVE (MUST) ficar vinculada ao semestre informado, e todas as alocações e faixas de horário dela DEVEM (MUST) pertencer a ele. O código DEVE (MUST) ser gravado nos valores de cada linha, e a confirmação DEVE (MUST) usar o código gravado, e não um informado de novo.

Depois da importação, os dados carregados DEVEM (MUST) ser dados do sistema. Nenhuma funcionalidade DEVE (MUST) consultar a planilha em tempo de execução para saber a ocupação de um espaço, e a ocupação DEVE (MUST) ser respondida a partir das alocações gravadas. O sistema NÃO DEVE (MUST NOT) guardar o arquivo enviado depois da leitura, e NÃO DEVE (MUST NOT) manter nenhuma sincronização automática com a planilha ou com serviço externo.

A importação DEVE (MUST) criar usuário só a partir da aba opcional `usuários - sistema`, conforme o requisito "Usuários do sistema na planilha do ensalamento", e NÃO DEVE (MUST NOT) alterar nem desativar usuário existente. Sem essa aba, a importação NÃO DEVE (MUST NOT) criar usuário. A ausência de um usuário correspondente a um docente NÃO DEVE (MUST NOT) impedir a importação do docente nem da alocação, e a importação NÃO DEVE (MUST NOT) criar a partir do catálogo de docentes nenhum usuário que não esteja na aba de usuários.

#### Scenario: Carga de um semestre
- **GIVEN** um usuário com `ENSALAMENTO.IMPORTAR` e a planilha institucional
- **WHEN** ele envia o arquivo com o semestre `2026/1` e confirma a importação
- **THEN** o semestre, os espaços, os cursos, as disciplinas, os docentes, as turmas, as faixas de horário e as alocações da planilha existem no banco
- **AND** todas as faixas de horário e alocações criadas pertencem a `2026/1`

#### Scenario: Envio sem o semestre
- **WHEN** o arquivo é enviado sem o código do semestre
- **THEN** o formulário de envio mostra o erro, nenhuma importação é criada e nada é efetivado

#### Scenario: Código de semestre fora do formato
- **WHEN** o arquivo é enviado com o código `2026` no campo do semestre
- **THEN** o formulário de envio mostra o erro e nenhuma importação é criada

#### Scenario: Semestre criado no envio
- **GIVEN** que não existe o semestre `2027/1`
- **WHEN** o arquivo é enviado com o código `2027/1`
- **THEN** o semestre passa a existir e a importação fica vinculada a ele

#### Scenario: Semestre da confirmação é o da prévia
- **GIVEN** uma importação `VALIDADA` enviada com o semestre `2026/1`
- **WHEN** ela é confirmada
- **THEN** os dados são aplicados a `2026/1`, a partir do código gravado nas linhas, e quem confirma não informa o semestre de novo

#### Scenario: Ocupação respondida pelo banco
- **GIVEN** uma importação concluída de `2026/1`
- **WHEN** a ocupação de um espaço no semestre é consultada
- **THEN** a resposta vem das alocações gravadas, sem nenhuma leitura do arquivo da planilha

#### Scenario: Arquivo não guardado
- **GIVEN** uma importação de ensalamento concluída
- **WHEN** os dados gravados da importação são consultados
- **THEN** o arquivo enviado não está guardado, e restam o nome do arquivo, os valores lidos de cada linha e o plano

#### Scenario: Nenhum usuário criado sem a aba de usuários
- **GIVEN** a planilha sem a aba `usuários - sistema`, com o docente `Aldo Gomes` e nenhum usuário com esse nome de usuário
- **WHEN** a importação é confirmada
- **THEN** o docente é criado, a alocação dele é criada e nenhum usuário é criado nem alterado

#### Scenario: Acesso sem a permissão
- **GIVEN** um usuário ativo autenticado sem `ENSALAMENTO.IMPORTAR`
- **WHEN** ele acessa qualquer rota da importação de ensalamento
- **THEN** o acesso é recusado com 403

#### Scenario: Visitante não autenticado
- **WHEN** um visitante não autenticado acessa qualquer rota da importação de ensalamento
- **THEN** ele é redirecionado para a página de login


## ADDED Requirements

### Requirement: Usuários do sistema na planilha do ensalamento
A importação do ensalamento DEVE (MUST) reconhecer a aba opcional `usuários - sistema`, pelo nome sem diferenciar maiúsculas de minúsculas, acentos e espaços nas bordas. A ausência dessa aba NÃO DEVE (MUST NOT) recusar o arquivo, gerar erro ou aviso, nem mudar em nada a leitura, o plano e a aplicação das demais abas.

Presente a aba, a primeira linha DEVE (MUST) ser o cabeçalho, com as colunas `E-mail`, `Nome`, `Perfil` e `Nome de usuário`, reconhecidas sem diferenciar maiúsculas de minúsculas e acentos. Faltar uma dessas colunas DEVE (MUST) recusar o arquivo inteiro, sem criar importação, informando a coluna e a aba. Coluna a mais NÃO DEVE (MUST NOT) recusar o arquivo. Cada linha seguinte com alguma célula preenchida DEVE (MUST) ser uma linha própria da importação, com a célula de origem, e as linhas de usuário DEVEM (MUST) vir antes das linhas dos catálogos e das atividades. A aba presente sem nenhuma linha de dado NÃO DEVE (MUST NOT) gerar linha nem erro.

`E-mail`, `Nome` e `Perfil` DEVEM (MUST) ser obrigatórios na linha, e `Nome de usuário` DEVE (MUST) ser opcional. O usuário DEVE (MUST) ser identificado pelo e-mail, normalizado como no cadastro e comparado sem diferenciar maiúsculas de minúsculas. O perfil DEVE (MUST) ser o código de um perfil existente, sem diferenciar maiúsculas de minúsculas, e a importação NÃO DEVE (MUST NOT) criar perfil.

Para o e-mail sem usuário, a linha DEVE (MUST) cadastrar o usuário pelas mesmas regras e pela mesma operação do cadastro de usuário da spec `gestao-usuarios`: ativo, sem senha utilizável, com o perfil informado e com o link para definir a senha enviado conforme a spec `autenticacao`. A importação NÃO DEVE (MUST NOT) ler, gerar nem guardar senha. O cadastro DEVE (MUST) exigir que quem gera a prévia e quem confirma tenha a permissão de cadastrar usuários, ou seja superadmin ativo.

Para o e-mail que já pertence a um usuário, a linha NÃO DEVE (MUST NOT) alterar o usuário, qualquer que seja a situação dele, e DEVE (MUST) ficar sem alteração. Quando o nome, o nome de usuário ou o perfil da planilha diferirem do cadastro, ou o usuário estiver inativo, a linha DEVE (MUST) receber um aviso. Importar de novo a mesma planilha NÃO DEVE (MUST NOT) criar usuário duplicado.

DEVEM (MUST) ser erro da linha: célula obrigatória vazia, e-mail inválido ou fora do domínio institucional no cadastro, perfil inexistente, e-mail ou nome de usuário repetido em outra linha da aba, nome de usuário que já pertence a outro usuário e a falta da permissão de cadastrar usuários. Um erro numa linha de usuário DEVE (MUST) deixar a importação com erros, como um erro de qualquer outra linha, e NÃO DEVE (MUST NOT) deixar nenhum usuário, espaço, docente ou alocação gravado.

Os usuários DEVEM (MUST) ser cadastrados na mesma unidade da importação do ensalamento: a prévia e a atualização da prévia DEVEM (MUST) desfazê-los junto com o resto, sem enviar o link, e a confirmação DEVE (MUST) gravá-los só quando gravar o ensalamento. Se a confirmação não aplicar o ensalamento, por plano diferente ou por erro inesperado, nenhum usuário DEVE (MUST) ficar gravado. O usuário cadastrado NÃO DEVE (MUST NOT) ganhar vínculo gravado com o docente: a correspondência continua pelo nome de usuário.

#### Scenario: Planilha sem a aba de usuários
- **GIVEN** a planilha do ensalamento sem a aba `usuários - sistema`
- **WHEN** a importação é enviada e confirmada
- **THEN** o arquivo é aceito, nenhuma linha é do tipo usuário, o ensalamento é aplicado como antes e nenhum usuário é criado

#### Scenario: Usuário novo cadastrado na confirmação
- **GIVEN** a aba de usuários com `adailton@ifnmg.edu.br`, `Adailton`, `DOCENTE` e `Adailton`, e nenhum usuário com esse e-mail
- **WHEN** a importação é confirmada por quem tem `ENSALAMENTO.IMPORTAR` e a permissão de cadastrar usuários
- **THEN** o usuário existe, ativo, com o perfil `DOCENTE`, o nome de usuário `Adailton` e sem senha utilizável, e o envio do link para definir a senha está no outbox

#### Scenario: Prévia não grava usuário
- **GIVEN** a aba de usuários com um e-mail sem usuário
- **WHEN** a prévia é gerada
- **THEN** a linha planeja o cadastro, e nenhum usuário nem envio de link fica gravado

#### Scenario: Reimportação sem duplicar
- **GIVEN** uma importação concluída que cadastrou `adailton@ifnmg.edu.br`
- **WHEN** a mesma planilha é importada e confirmada de novo
- **THEN** a linha do usuário fica sem alteração, existe um único usuário com esse e-mail e nenhum novo link é enviado

#### Scenario: Usuário existente com outros dados
- **GIVEN** um usuário `adailton@ifnmg.edu.br` com o nome `Adailton Souza`
- **WHEN** a planilha traz o nome `Adailton` para esse e-mail
- **THEN** a linha fica sem alteração, com aviso, e o nome do usuário continua `Adailton Souza`

#### Scenario: Perfil inexistente
- **WHEN** a aba de usuários traz o perfil `COORDENADOR`, que não existe
- **THEN** a linha tem erro na coluna `Perfil`, a importação fica com erros e nenhum perfil é criado

#### Scenario: E-mail repetido na aba
- **WHEN** duas linhas da aba de usuários trazem o mesmo e-mail, com caixas diferentes
- **THEN** as duas linhas têm erro de duplicidade e a importação fica com erros

#### Scenario: Coluna faltando na aba de usuários
- **WHEN** a aba de usuários não tem a coluna `Perfil`
- **THEN** o envio é recusado informando a coluna e a aba, e nenhuma importação é criada

#### Scenario: Sem permissão de cadastrar usuários
- **GIVEN** quem importa tem `ENSALAMENTO.IMPORTAR` e não tem a permissão de cadastrar usuários
- **WHEN** a aba de usuários traz um e-mail sem usuário
- **THEN** a linha tem erro de permissão e a importação fica com erros

#### Scenario: Ensalamento recusado na confirmação desfaz os usuários
- **GIVEN** uma importação `VALIDADA` com um usuário a cadastrar
- **WHEN** a confirmação encontra o plano diferente ou falha por erro inesperado
- **THEN** nenhum usuário, espaço, docente ou alocação fica gravado
