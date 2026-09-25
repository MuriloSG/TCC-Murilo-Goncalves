from django.test import SimpleTestCase

from schedule.similarity import similar_names


class SimilarNamesTests(SimpleTestCase):
    def test_real_similar_names(self):
        cases = [
            ('HV5', ['HV 5', 'HV 4'], ['HV 5']),
            ('HV1', ['HV 1', 'HV 2', 'HV 3'], ['HV 1']),
            ('Lab.3 - Info', ['Lab. 3 - Info', 'Lab. 4 - Info'], ['Lab. 3 - Info']),
            ('Sala 01', ['Sala 1', 'Sala 10'], ['Sala 1']),
            ('Lab. Química', ['Lab. Química I', 'Lab. Química II', 'Lab. Redes'], ['Lab. Química I', 'Lab. Química II']),
            ('Lab. Química I', ['Lab. Química'], ['Lab. Química']),
            ('Lab.  Paras. Vet.', ['Lab. Paras. Vet'], ['Lab. Paras. Vet']),
        ]
        for name, known, expected in cases:
            with self.subTest(name=name):
                self.assertEqual(similar_names(name, known), expected)

    def test_names_that_are_not_similar(self):
        cases = [
            ('1/1', ['1/10', '11']),
            ('Lab. Análise Alim.', ['Sl. Análise Alim.']),
            ('1/10', ['Sala 10 do Bloco 1']),
            ('Lab. Química I', ['Lab. Química II']),
            ('Zoo I', ['Zoo II', 'Zoo III']),
            ('HV5', ['HV 4', 'Clínica do HV']),
            ('2/41', ['2/4', '2/1']),
        ]
        for name, known in cases:
            with self.subTest(name=name):
                self.assertEqual(similar_names(name, known), [])

    def test_same_name_is_recognition_and_not_similarity(self):
        self.assertEqual(similar_names('HV 5', ['hv 5', 'HV5']), ['HV5'])

    def test_repeated_known_names_appear_once(self):
        self.assertEqual(similar_names('HV5', ['HV 5', 'hv 5']), ['HV 5'])
