## MODIFIED Requirements

### Requirement: Calendário público no celular
A página DEVE (MUST) usar a mesma Grade em qualquer largura e NÃO DEVE (MUST NOT) ter uma representação do calendário só para o celular. O cabeçalho DEVE (MUST) ser uma barra única e discreta, com a marca "IFAgenda" e o botão de trocar o modo de exibição, sem outro conteúdo. O cabeçalho, os filtros e o calendário DEVEM (MUST) ficar centralizados, com a largura máxima das páginas do sistema. Os filtros DEVEM (MUST) ficar num card com a mesma borda do calendário, sem título visível. Abaixo de 640 px, os filtros DEVEM (MUST) ficar empilhados na largura toda, com a data inicial e a final lado a lado. Abaixo de 640 px, ao aplicar qualquer filtro, a página DEVE (MUST) descer até o calendário com rolagem suave, ou sem animação quando o sistema pede movimento reduzido, e os filtros DEVEM (MUST) continuar abertos. Valores longos DEVEM (MUST) ser cortados com reticências dentro do próprio campo, sem alargar a coluna nem a página, e a lista de opções aberta DEVE (MUST) aparecer inteira, sem ser cortada pelo card. Os controles DEVEM (MUST) ter alvo de toque de pelo menos 44x44 px, as datas DEVEM (MUST) usar o seletor nativo, e Sala, Docente e Curso DEVEM (MUST) usar o campo de seleção com busca. A Grade DEVE (MUST) rolar na horizontal só dentro da própria área, rotulada e focável, com a coluna de horários e a linha dos dias fixas, e a página NÃO DEVE (MUST NOT) rolar na horizontal a partir de 360 px. Abaixo de 640 px, a área DEVE (MUST) mostrar dois dias inteiros por vez, com a rolagem encaixando no início de cada dia, o cabeçalho do dia abreviado com o nome completo para a tecnologia assistiva, e o card com o mesmo conteúdo das demais larguras; a área DEVE (MUST) abrir rolada até "Hoje" quando ele está no intervalo.

#### Scenario: Celular com três semanas
- **GIVEN** uma tela de 360 px
- **WHEN** o calendário da sala 10 é aberto de 14/09/2026 a 02/10/2026
- **THEN** o calendário é a Grade com 15 dias, rolando na horizontal só dentro da própria área, com dois dias inteiros visíveis por vez
- **AND** a página não rola na horizontal

#### Scenario: Rolagem até o calendário depois do filtro
- **GIVEN** uma tela de 360 px com o calendário aberto sem filtro
- **WHEN** o curso Informática é escolhido
- **THEN** a página desce com rolagem suave até o calendário, que fica no topo da tela
- **AND** os filtros continuam abertos acima dele

#### Scenario: Calendário largo sem rolagem automática
- **GIVEN** uma tela de 1280 px
- **WHEN** o curso Informática é escolhido
- **THEN** a página não rola sozinha

#### Scenario: Cabeçalho do dia no celular
- **GIVEN** uma tela de 360 px
- **WHEN** o calendário da sala 10 é aberto em 23/09/2026
- **THEN** o cabeçalho da coluna mostra "Hoje", "Qua" e "23/09", e o nome acessível é "Hoje, Quarta-feira, 23/09/2026"

#### Scenario: Lista de opções inteira
- **WHEN** o campo "Docente" é aberto
- **THEN** a lista de opções aparece inteira sobre o calendário, sem ser cortada pelo card de filtros
