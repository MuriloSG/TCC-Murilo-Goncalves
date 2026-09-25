## MODIFIED Requirements

### Requirement: Conferência do cabeçalho
A primeira linha do arquivo DEVE (MUST) ser o cabeçalho. Cada cabeçalho DEVE (MUST) ser reconhecido pelo rótulo da coluna declarada pela importação específica, sem diferenciar maiúsculas de minúsculas nem letras acentuadas das não acentuadas e ignorando espaços nas bordas. A ordem das colunas NÃO DEVE (MUST NOT) importar. O motor DEVE (MUST) recusar o arquivo quando houver coluna desconhecida, coluna declarada ausente ou cabeçalho repetido, informando as colunas envolvidas e as colunas esperadas.

Toda coluna declarada DEVE (MUST) estar presente no cabeçalho, inclusive a coluna cuja célula é opcional. A importação específica PODE (MAY) declarar uma coluna como opcional, e essa escolha vale para a célula, e não para o cabeçalho: numa coluna opcional, a célula vazia DEVE (MUST) ser entregue à importação específica como texto vazio, sem gerar erro da linha, e cabe à importação específica dizer o que uma célula vazia significa. Numa coluna obrigatória, a célula vazia continua gerando erro, conforme o requisito "Linhas do arquivo".

#### Scenario: Colunas em outra ordem e com outra grafia
- **GIVEN** uma importação que declara as colunas `E-mail`, `Nome` e `Perfil`
- **WHEN** é enviado um arquivo com o cabeçalho `perfil;NOME; e-mail `
- **THEN** as três colunas são reconhecidas

#### Scenario: Coluna desconhecida
- **WHEN** é enviado um arquivo com o cabeçalho `E-mail;Nome;Perfl`
- **THEN** o envio é recusado com a mensagem "Coluna "Perfl" não reconhecida. Use as colunas do modelo: E-mail, Nome, Perfil."

#### Scenario: Coluna obrigatória ausente
- **WHEN** é enviado um arquivo com o cabeçalho `E-mail;Nome`
- **THEN** o envio é recusado informando que a coluna `Perfil` está ausente

#### Scenario: Coluna opcional ausente do cabeçalho
- **GIVEN** uma importação que declara as colunas `E-mail`, `Nome` e `Apelido`, esta última com a célula opcional
- **WHEN** é enviado um arquivo com o cabeçalho `E-mail;Nome`
- **THEN** o envio é recusado informando que a coluna `Apelido` está ausente

#### Scenario: Célula vazia numa coluna opcional
- **GIVEN** uma importação que declara a coluna `Apelido` com a célula opcional
- **WHEN** é enviado um arquivo cuja linha 2 tem a célula de `Apelido` vazia
- **THEN** a linha 2 não recebe erro nessa coluna e a importação específica recebe o valor como texto vazio

#### Scenario: Cabeçalho repetido
- **WHEN** é enviado um arquivo com o cabeçalho `E-mail;Nome;Perfil;E-mail`
- **THEN** o envio é recusado informando que a coluna `E-mail` está repetida
