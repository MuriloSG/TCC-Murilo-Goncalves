## MODIFIED Requirements

### Requirement: Calendário público no celular
A página DEVE (MUST) usar a mesma Grade em qualquer largura e NÃO DEVE (MUST NOT) ter uma representação do calendário só para o celular. O cabeçalho DEVE (MUST) ser uma barra única e discreta, com a marca "IFAgenda" e o link "Entrar", discreto e com borda verde clara, sem outro conteúdo. O cabeçalho, os filtros e o calendário DEVEM (MUST) ficar centralizados, com a largura máxima das páginas do sistema. Os filtros DEVEM (MUST) ficar num card com a mesma borda do calendário, sem título visível e sem linha de resumo. Abaixo de 640 px, os filtros DEVEM (MUST) ficar empilhados na largura toda, com a data inicial e a final lado a lado. Valores longos DEVEM (MUST) ser cortados com reticências dentro do próprio campo, sem alargar a coluna nem a página, e a lista de opções aberta DEVE (MUST) aparecer inteira, sem ser cortada pelo card. Os controles DEVEM (MUST) ter alvo de toque de pelo menos 44x44 px, as datas DEVEM (MUST) usar o seletor nativo, e Sala, Docente e Curso DEVEM (MUST) usar o campo de seleção com busca. A Grade DEVE (MUST) rolar na horizontal só dentro da própria área, rotulada e focável, com a coluna de horários e a linha dos dias fixas, e a página NÃO DEVE (MUST NOT) rolar na horizontal a partir de 360 px. Abaixo de 640 px, a coluna de dia DEVE (MUST) ter largura mínima que mantenha o card legível, e a área DEVE (MUST) abrir rolada até "Hoje" quando ele está no intervalo.

#### Scenario: Celular com três semanas
- **GIVEN** uma tela de 360 px
- **WHEN** o calendário da sala 10 é aberto de 14/09/2026 a 02/10/2026
- **THEN** o calendário é a Grade com 15 dias, rolando na horizontal só dentro da própria área
- **AND** a página não rola na horizontal

#### Scenario: Lista de opções inteira
- **WHEN** o campo "Docente" é aberto
- **THEN** a lista de opções aparece inteira sobre o calendário, sem ser cortada pelo card de filtros
