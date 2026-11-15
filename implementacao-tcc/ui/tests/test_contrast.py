from django.test import SimpleTestCase

from ui import contrast


class ContrastTests(SimpleTestCase):
    def setUp(self):
        self.css = contrast.STYLES.read_text(encoding='utf-8')

    def test_pares_atingem_o_minimo_nos_dois_temas(self):
        with self.subTest('pares'):
            failures = contrast.all_contrast_failures(self.css)
            self.assertEqual(failures, [], '\n'.join(failures))
        with self.subTest('tema escuro'):
            light = contrast.read_colors(self.css)
            dark = contrast.read_colors(self.css, 'dark')
            self.assertNotEqual(dark['page'], light['page'])
            self.assertNotEqual(dark['text'], light['text'])
            self.assertGreater(contrast.luminance(dark['text']), contrast.luminance(dark['page']))

    def test_todo_token_de_cor_tem_par_ou_esta_isento(self):
        self.assertEqual(contrast.uncovered_tokens(self.css), [])

    def test_falhas_sao_apontadas(self):
        with self.subTest('texto secundário escuro'):
            css = self.css.replace('--color-text-muted: var(--palette-dark-200);', '--color-text-muted: #595E61;')
            self.assertNotEqual(css, self.css)
            failures = contrast.all_contrast_failures(css)
            self.assertEqual(contrast.contrast_failures(css), [])
            self.assertTrue(any(failure.startswith('tema escuro:') for failure in failures), failures)
        with self.subTest('texto secundário'):
            css = self.css.replace('--color-text-muted: var(--palette-neutral-700);', '--color-text-muted: #7B7677;')
            self.assertNotEqual(css, self.css)
            failures = contrast.contrast_failures(css)
            self.assertTrue(any('text-muted #7B7677 sobre surface #FFFFFF): 4,47:1, mínimo 4,50:1' in failure
                                for failure in failures), failures)
        with self.subTest('token sem par'):
            css = self.css.replace('--color-page:', '--color-highlight: var(--palette-green-100);\n  --color-page:')
            self.assertEqual(contrast.uncovered_tokens(css), ['highlight'])
