import unittest
from tempfile import NamedTemporaryFile

from clips import Environment, Symbol, LoggingRouter, ImpliedFact


DEFRULE_FACT = """
(defrule fact-rule
   ?fact <- (test-fact)
   =>
   (python-function python_method ?fact))
"""

DEFRULE_INSTANCE = """
(defrule instance-rule
   ?instance <- (object (is-a TEST))
   =>
   (python-function python_method ?instance))
"""

DEFFUNCTION = """
(deffunction test-fact-function ()
   (bind ?facts (python-function python_fact_method))
   (python-function python_method ?facts))
"""

DEFCLASS = """(defclass TEST (is-a USER))"""


def python_function(*value):
    return value


class TestEnvironment(unittest.TestCase):
    def setUp(self):
        self.value = None
        self.env = Environment()
        router = LoggingRouter()
        router.add_to_environment(self.env)
        self.env.build(DEFCLASS)
        self.env.build(DEFFUNCTION)
        self.env.build(DEFRULE_FACT)
        self.env.build(DEFRULE_INSTANCE)
        self.env.define_function(python_function)
        self.env.define_function(self.python_method)
        self.env.define_function(self.python_fact_method)

    def python_method(self, *value):
        self.value = value

    def python_fact_method(self):
        """Returns a list with one fact."""
        template = self.env.facts.find_template('test-fact')
        fact = template.new_fact()
        fact.append(5)

        return [fact]

    def test_eval_python_function(self):
        """Python function is evaluated correctly."""
        expected = [0, 1.1, "2", Symbol('three')]

        ret = self.env.eval('(python-function python_function 0 1.1 "2" three)')

        self.assertEqual(ret, expected)

    def test_eval_python_method(self):
        """Python method is evaluated correctly."""
        expected = 0, 1.1, "2", Symbol('three')

        ret = self.env.eval('(python-function python_method 0 1.1 "2" three)')

        self.assertEqual(ret, Symbol('nil'))
        self.assertEqual(self.value, expected)

    def test_rule_python_fact(self):
        """Facts are forwarded to Python functions."""
        fact = self.env.facts.assert_string('(test-fact)')
        self.env.agenda.run()

        self.assertEqual(self.value[0], fact)

    def test_rule_python_instance(self):
        """Instances are forwarded to Python functions."""
        cl = self.env.classes.find_class('TEST')
        inst = cl.new_instance('test')
        self.env.agenda.run()

        self.assertEqual(self.value[0], inst)

    def test_facts_function(self):
        """Python functions can return list of facts."""
        function = self.env.functions.find_function('test-fact-function')
        function()

        self.assertTrue(isinstance(self.value[0][0], ImpliedFact))

    def test_save_load(self):
        """Constructs are saved and loaded."""
        with NamedTemporaryFile() as tmp:
            self.env.save(tmp.name)
            self.env.clear()
            self.env.load(tmp.name)

            self.assertTrue('fact-rule' in
                            (r.name for r in self.env.agenda.rules()))

        with NamedTemporaryFile() as tmp:
            self.env.save(tmp.name, binary=True)
            self.env.clear()
            self.env.load(tmp.name)

            self.assertTrue('fact-rule' in
                            (r.name for r in self.env.agenda.rules()))