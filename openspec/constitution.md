# Constitution do Projeto

**Sistema Web para Agendamento de Espaços Físicos no IFNMG – Campus Salinas**

Revisão 2 · 14/09/2026 · Fonte: `sources/TCC_REVISADO (1).pdf`

Princípios permanentes do desenvolvimento do sistema no TCC 2, extraídos exclusivamente do TCC. Cada regra indica entre parênteses a seção ou o requisito que a fundamenta (páginas conforme a numeração do PDF).

---

## 1. Arquitetura e organização

### P1. Tecnologias definidas no TCC

- O sistema é desenvolvido como aplicação web, em Python, com o framework Django. (3.3.1, p. 23)
- A camada de dados usa o PostgreSQL como sistema gerenciador de banco de dados relacional. (3.3.1, p. 23)
- A camada de apresentação é construída com os templates do Django combinados ao Tailwind CSS. (3.3.1, p. 24)

### P2. Separação entre dados, lógica e apresentação (MTV)

- O sistema adota o padrão MTV do Django, que garante separação clara entre as camadas de dados, lógica e apresentação. (3.3.1, p. 23; RNF06)
- Responsabilidades no padrão adotado (2.3.6, p. 11–12):
  - **Model:** representa as entidades de dados e encapsula as regras de negócio associadas ao banco de dados;
  - **View:** recebe a requisição HTTP, aciona os Models necessários e seleciona o Template adequado para compor a resposta;
  - **Template:** ocupa-se exclusivamente da renderização da interface;
  - **Roteamento de URLs:** o mecanismo do Django mapeia cada endereço recebido para a View correspondente.
- Essa separação permite que cada parte do sistema seja mantida e evoluída de forma independente. (2.3.6, p. 13)

### P3. Acesso aos dados

- O acesso ao banco é feito exclusivamente por meio do ORM, mantendo consistência entre o código Python e o esquema relacional. (3.3.1, p. 24)
- As mudanças nos Models são controladas pelo sistema de migrations do Django, aplicadas de forma incremental e rastreável. (2.3.7, p. 14; 3.3.1, p. 23)

---

## 2. Qualidade e manutenibilidade

### P4. Manutenibilidade

- O sistema deve ser manutenível, de modo a permitir sua evolução após a implantação, com separação clara entre as camadas de dados, lógica e apresentação. (RNF06; 3.2.2, p. 20–21)
- O princípio DRY, que integra o funcionamento do Django adotado no projeto, orienta o reaproveitamento de código e a centralização de lógicas que, se duplicadas, aumentariam o custo de manutenção. (2.3.7, p. 13; 3.3.1, p. 23)

---

## 3. Segurança

### P5. Controle de acesso e proteção dos dados

- O sistema deve controlar o acesso com base em papéis, conforme o modelo RBAC, restringindo cada funcionalidade ao perfil correspondente. (RNF01)
- O sistema deve proteger os dados dos usuários contra acessos indevidos, incluindo proteções contra CSRF, XSS e injeção de SQL. (RNF02)
- O Django, adotado no projeto, oferece essas proteções ativas por padrão (2.3.7, p. 14; 3.3.1, p. 23):
  - **CSRF:** middleware que exige um token válido em todas as requisições que modificam dados no servidor;
  - **XSS:** o sistema de templates escapa automaticamente todo conteúdo dinâmico antes de inseri-lo no HTML;
  - **Injeção de SQL:** o ORM parametriza as consultas, de modo que dados fornecidos pelo usuário nunca são interpolados diretamente no SQL.

---

## 4. Desempenho

### P6. Desempenho nas consultas de disponibilidade

- O sistema deve apresentar tempo de resposta adequado nas consultas de disponibilidade, mesmo em períodos de pico de uso. (RNF03; 3.2.2, p. 20)

---

## 5. Usabilidade

### P7. Adequação ao público do campus

- O sistema deve ser acessível por meio de navegador web, sem exigir instalação de software nos dispositivos dos usuários. Os docentes do campus utilizam dispositivos variados. (RNF04; 2.3.5, p. 11)
- O sistema deve apresentar usabilidade compatível com o perfil tecnológico dos docentes do campus, que têm familiaridade tecnológica variada, dispensando treinamento extensivo. (RNF05; 2.3.8, p. 15)
- Heurísticas de Nielsen às quais o TCC atribui peso particular no sistema proposto (2.3.8, p. 15):
  - **visibilidade do estado do sistema:** manter o usuário informado sobre o que está acontecendo;
  - **correspondência com o mundo real:** usar termos como "laboratório", "reserva" e "disponível" em vez de jargões técnicos;
  - **prevenção de erros:** projetar para evitar que erros ocorram.

### P8. Consistência visual

- O sistema deve manter consistência visual entre suas telas. (RNF05)
- Os templates do Django combinados ao Tailwind CSS foram escolhidos para manter a consistência visual entre as telas e reduzir o custo de manutenção, permitindo ajustes visuais sem alteração nas Views ou nos Models. (3.3.1, p. 24)

---

## 6. Testabilidade

### P9. Verificação por testes

- A conformidade do sistema com os requisitos especificados é verificada por testes unitários e de integração, cobrindo as regras de negócio centrais indicadas na Seção 3.3.1 do TCC. (3.3.1, p. 25)
- Testes unitários verificam o comportamento de unidades individuais de código de forma isolada; testes de integração verificam se os componentes interagem corretamente entre si. (2.3.9, p. 16)
- Não estão previstas no TCC a validação com usuários, a avaliação de usabilidade em ambiente real nem a homologação institucional do sistema. (3.3.1, p. 25)

---

## 7. Independência e autonomia

### P10. Autonomia em relação à infraestrutura de horários

- O sistema deve operar de forma autônoma em relação à infraestrutura de horários do campus, sem depender de consultas em tempo real a sistemas externos. (RNF07)
- A atualização da ocupação institucional ocorre mediante ação administrativa, conduzida pelo responsável. (3.2.1, p. 20)
- O sistema evita dependência de integrações automáticas com sistemas de terceiros. (3.2.1, p. 20)
- A planilha institucional de horários permanece como fonte da ocupação decorrente das aulas regulares, mas não substitui o banco de dados do sistema. (2.3.3, p. 9)

---

## 8. Modelagem

### P11. Modelagem com UML

- A modelagem do sistema adota a UML. (3.3, p. 22)
- O diagrama de casos de uso, elaborado no TCC 1, delimita o escopo funcional do sistema. (3.3, p. 22)
- Os diagramas de classes e de sequência, que representam respectivamente a estrutura estática e o comportamento dinâmico do sistema, são elaborados no TCC 2, na fase de implementação, a partir desse escopo. (2.3.2, p. 8; 3.3, p. 22)
- Os relacionamentos do diagrama de classes definem as regras de integridade que orientam a estrutura do banco de dados. (3.3, p. 23)

---

## 9. Consistência com os requisitos

### P12. Escopo e requisitos do TCC

- A implementação compreende a codificação das funcionalidades especificadas, a elaboração dos diagramas de classes e de sequência e a realização dos testes. (3.2, p. 17)
- Os requisitos do sistema são os requisitos funcionais da Tabela 2 e os não funcionais da Tabela 3 do TCC. (3.2.2, p. 21–22)
- O trabalho compreende o desenvolvimento e a disponibilização de uma versão funcional do sistema em ambiente acessível por navegador. A implantação definitiva na infraestrutura institucional fica a cargo da direção do campus e dos setores envolvidos. (3.3.1, p. 24)

---

## Uso desta Constitution

*Convenção interna do projeto para uso com o OpenSpec; não provém do TCC.*

- As specs e changes do OpenSpec devem estar em conformidade com os princípios acima.
- Em caso de divergência entre esta Constitution e o TCC, prevalece o TCC.

---

## Decisões fora da Constitution

*Convenção interna do projeto; não provém do TCC.*

Esta Constitution não define o que cada funcionalidade faz nem como ela é implementada. Os itens abaixo são definidos nas specs e changes do OpenSpec, dentro do escopo e dos requisitos do TCC:

- **Funcionalidades e regras de negócio:** comportamento de cada funcionalidade prevista nos requisitos funcionais.
- **Interfaces:** páginas, telas, navegação e componentes.
- **Fluxos:** sequência de passos de cada funcionalidade, incluindo rotas.
- **Entidades e dados:** entidades, atributos, relacionamentos e classes.
- **Autenticação e autorização:** login, cadastro de usuários, recuperação de senha, sessões, papéis e permissões de cada funcionalidade.
- **Configuração das tecnologias:** forma concreta de uso das tecnologias previstas no TCC, inclusive as de autenticação e de envio de e-mail.
- **Hospedagem:** infraestrutura de hospedagem, que o TCC deixa dependente de uma articulação institucional ainda não concretizada. (3.3.1, p. 24)
- **Demais decisões de implementação** que o TCC não define.
