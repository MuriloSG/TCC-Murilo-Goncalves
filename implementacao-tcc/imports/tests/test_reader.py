from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, override_settings

from imports.definitions import Column, ImportDefinition, RowError, errors_from_validation
from imports.reader import FileRejected, read_csv


class PeopleImport(ImportDefinition):
    kind = 'TESTE'
    columns = (Column('E-mail'), Column('Nome'), Column('Perfil'))
    identifier = 'E-mail'

    def normalize_identifier(self, value):
        return value.strip().lower()


def upload(text, encoding='utf-8'):
    return SimpleUploadedFile('pessoas.csv', text.encode(encoding), content_type='text/csv')


def read(text, **kwargs):
    return read_csv(upload(text, **kwargs), PeopleImport())


class FileTests(SimpleTestCase):
    def assertRejected(self, text, message, **kwargs):
        with self.assertRaises(FileRejected) as context:
            read(text, **kwargs)
        self.assertIn(message, context.exception.message)

    def test_reads_rows_by_column_label_without_the_bom(self):
        with self.subTest('por rótulo'):
            rows = read('E-mail;Nome;Perfil\nana@ifnmg.edu.br;Ana Souza;DOCENTE\n')
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].line_number, 2)
            self.assertEqual(rows[0].values, {'E-mail': 'ana@ifnmg.edu.br', 'Nome': 'Ana Souza', 'Perfil': 'DOCENTE'})
            self.assertEqual(rows[0].errors, [])
        with self.subTest('BOM'):
            rows = read('﻿E-mail;Nome;Perfil\nana@ifnmg.edu.br;Ana;DOCENTE\n')
            self.assertEqual(rows[0].values['E-mail'], 'ana@ifnmg.edu.br')

    def test_refused_files(self):
        with self.subTest('fora do UTF-8'):
            self.assertRejected(
                'E-mail;Nome;Perfil\njoao@ifnmg.edu.br;João;DOCENTE\n',
                'O arquivo não está em UTF-8. No Excel, salve como "CSV UTF-8 (delimitado por vírgulas)".',
                encoding='cp1252',
            )
        with self.subTest('acima do tamanho'):
            with override_settings(IMPORT_MAX_FILE_SIZE=1024):
                self.assertRejected('E-mail;Nome;Perfil\n' + 'a;b;c\n' * 400, 'O limite é 1 KB.')
        with self.subTest('acima das linhas'):
            with override_settings(IMPORT_MAX_ROWS=2):
                self.assertRejected(
                    'E-mail;Nome;Perfil\n' + ''.join(f'p{index}@ifnmg.edu.br;P;DOCENTE\n' for index in range(3)),
                    'O arquivo tem 3 linhas. O limite é 2. Divida o arquivo e importe em partes.',
                )
        with self.subTest('vazio e só cabeçalho'):
            for text in ('', 'E-mail;Nome;Perfil\n', 'E-mail;Nome;Perfil\n;;\n\n'):
                with self.subTest(text=text):
                    self.assertRejected(text, 'O arquivo não tem linhas de dados.')
        with self.subTest('vírgula'):
            self.assertRejected('E-mail,Nome,Perfil\na@ifnmg.edu.br,A,DOCENTE\n', 'como separador')


class HeaderTests(SimpleTestCase):
    def assertRejected(self, header, message):
        with self.assertRaises(FileRejected) as context:
            read(header + '\nana@ifnmg.edu.br;Ana;DOCENTE\n')
        self.assertEqual(context.exception.message, message)

    def test_order_case_accents_and_spaces_do_not_matter(self):
        rows = read('perfil;NOME; e-mail \nDOCENTE;Ana;ana@ifnmg.edu.br\n')
        self.assertEqual(rows[0].values, {'E-mail': 'ana@ifnmg.edu.br', 'Nome': 'Ana', 'Perfil': 'DOCENTE'})
        rows = read('E-mail;Nóme;Pérfil\nana@ifnmg.edu.br;Ana;DOCENTE\n')
        self.assertEqual(rows[0].values['Nome'], 'Ana')

    def test_unknown_missing_or_repeated_column(self):
        with self.subTest('desconhecida'):
            self.assertRejected(
                'E-mail;Nome;Perfl',
                'Coluna "Perfl" não reconhecida. Use as colunas do modelo: E-mail, Nome, Perfil.',
            )
        with self.subTest('ausente'):
            self.assertRejected('E-mail;Nome', 'Falta a coluna "Perfil". Use as colunas do modelo: E-mail, Nome, Perfil.')
        with self.subTest('repetida'):
            self.assertRejected('E-mail;Nome;Perfil;e-mail', 'A coluna "E-mail" aparece mais de uma vez. Deixe só uma.')


class RowTests(SimpleTestCase):
    def codes(self, row):
        return [(error.column, error.code) for error in row.errors]

    def test_row_parsing(self):
        with self.subTest('linhas vazias'):
            rows = read(
                'E-mail;Nome;Perfil\na@ifnmg.edu.br;A;DOCENTE\nb@ifnmg.edu.br;B;DOCENTE\n;;\n'
                'c@ifnmg.edu.br;C;DOCENTE\n\n  ;  ;\n'
            )
            self.assertEqual([row.line_number for row in rows], [2, 3, 5])
        with self.subTest('aspas'):
            rows = read('E-mail;Nome;Perfil\na@ifnmg.edu.br;"Ana; da\nSilva";DOCENTE\nb@ifnmg.edu.br;B;DOCENTE\n')
            self.assertEqual(rows[0].values['Nome'], 'Ana; da\nSilva')
            self.assertEqual([row.line_number for row in rows], [2, 4])
        with self.subTest('valores brutos'):
            rows = read('E-mail;Nome;Perfil\n Ana@IFNMG.edu.br ;Ana;docente\n')
            self.assertEqual(rows[0].values['E-mail'], ' Ana@IFNMG.edu.br ')
        with self.subTest('células ausentes'):
            rows = read('E-mail;Nome;Perfil\na@ifnmg.edu.br;Ana\n')
            self.assertEqual(rows[0].values['Perfil'], '')
            self.assertEqual(self.codes(rows[0]), [('Perfil', 'required')])
        with self.subTest('células a mais'):
            rows = read('E-mail;Nome;Perfil\na@ifnmg.edu.br;Ana;DOCENTE;sobra\nb@ifnmg.edu.br;B;DOCENTE;\n')
            self.assertEqual(self.codes(rows[0]), [(None, 'extra_cells')])
            self.assertEqual(rows[1].errors, [])

    def test_required_and_optional_cells(self):
        with self.subTest('obrigatória só com espaços'):
            rows = read('E-mail;Nome;Perfil\na@ifnmg.edu.br;   ;DOCENTE\n')
            self.assertEqual(rows[0].errors, [RowError('Nome', 'required', 'Preencha a coluna Nome.')])
        with self.subTest('opcional vazia'):
            class WithOptional(PeopleImport):
                columns = (Column('E-mail'), Column('Nome'), Column('Apelido', required=False))

            rows = read_csv(upload('E-mail;Nome;Apelido\na@ifnmg.edu.br;Ana;\n'), WithOptional())
            self.assertEqual(rows[0].errors, [])
            self.assertEqual(rows[0].values['Apelido'], '')
        with self.subTest('opcional no cabeçalho'):
            class WithOptional(PeopleImport):
                columns = (Column('E-mail'), Column('Nome'), Column('Apelido', required=False))

            with self.assertRaises(FileRejected) as context:
                read_csv(upload('E-mail;Nome\na@ifnmg.edu.br;Ana\n'), WithOptional())
            self.assertIn('"Apelido"', context.exception.message)

    def test_repeated_identifier_with_different_spelling(self):
        rows = read(
            'E-mail;Nome;Perfil\nana@ifnmg.edu.br;A;DOCENTE\nb@ifnmg.edu.br;B;DOCENTE\n ANA@ifnmg.edu.br;A;DOCENTE\n'
        )
        message = 'E-mail repetido nas linhas 2 e 4.'
        self.assertEqual(rows[0].errors, [RowError('E-mail', 'duplicate', message)])
        self.assertEqual(rows[2].errors, [RowError('E-mail', 'duplicate', message)])
        self.assertEqual(rows[1].errors, [])


class ValidationTranslationTests(SimpleTestCase):
    def test_errors_go_to_their_columns(self):
        with self.subTest('erros de campo'):
            error = ValidationError({
                'email': ValidationError('Informe um e-mail válido.', code='invalid'),
                'is_active': ValidationError('Outro campo.', code='other'),
            })
            self.assertEqual(
                errors_from_validation(error, {'email': 'E-mail'}),
                [RowError('E-mail', 'invalid', 'Informe um e-mail válido.'), RowError(None, 'other', 'Outro campo.')],
            )
        with self.subTest('erro geral'):
            error = ValidationError('Operação recusada.', code='refused')
            self.assertEqual(errors_from_validation(error, {}), [RowError(None, 'refused', 'Operação recusada.')])
