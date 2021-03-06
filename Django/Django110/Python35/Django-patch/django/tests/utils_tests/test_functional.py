# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

import unittest

from django.utils import six
from django.utils.functional import cached_property, lazy, lazy_property


class FunctionalTestCase(unittest.TestCase):
    def test_lazy(self):
        t = lazy(lambda: tuple(range(3)), list, tuple)
        for a, b in zip(t(), range(3)):
            self.assertEqual(a, b)

    def test_lazy_base_class(self):
        """Test that lazy also finds base class methods in the proxy object"""

        class Base(object):
            def base_method(self):
                pass

        class Klazz(Base):
            pass

        t = lazy(lambda: Klazz(), Klazz)()
        self.assertIn('base_method', dir(t))

    def test_lazy_base_class_override(self):
        """Test that lazy finds the correct (overridden) method implementation"""

        class Base(object):
            def method(self):
                return 'Base'

        class Klazz(Base):
            def method(self):
                return 'Klazz'

        t = lazy(lambda: Klazz(), Base)()
        self.assertEqual(t.method(), 'Klazz')

    def test_lazy_property(self):

        class A(object):

            def _get_do(self):
                raise NotImplementedError

            def _set_do(self, value):
                raise NotImplementedError
            do = lazy_property(_get_do, _set_do)

        class B(A):
            def _get_do(self):
                return "DO IT"

        with self.assertRaises(NotImplementedError):
            A().do
        self.assertEqual(B().do, 'DO IT')

    def test_lazy_object_to_string(self):

        class Klazz(object):
            if six.PY3:
                def __str__(self):
                    return "Î am ā Ǩlâzz."

                def __bytes__(self):
                    return b"\xc3\x8e am \xc4\x81 binary \xc7\xa8l\xc3\xa2zz."
            else:
                def __unicode__(self):
                    return "Î am ā Ǩlâzz."

                def __str__(self):
                    return b"\xc3\x8e am \xc4\x81 binary \xc7\xa8l\xc3\xa2zz."

        t = lazy(lambda: Klazz(), Klazz)()
        self.assertEqual(six.text_type(t), "Î am ā Ǩlâzz.")
        self.assertEqual(six.binary_type(t), b"\xc3\x8e am \xc4\x81 binary \xc7\xa8l\xc3\xa2zz.")

    def test_cached_property(self):
        """
        Test that cached_property caches its value,
        and that it behaves like a property
        """

        class A(object):

            @cached_property
            def value(self):
                """Here is the docstring..."""
                return 1, object()

            def other_value(self):
                return 1

            other = cached_property(other_value, name='other')

        # docstring should be preserved
        self.assertEqual(A.value.__doc__, "Here is the docstring...")

        a = A()

        # check that it is cached
        self.assertEqual(a.value, a.value)

        # check that it returns the right thing
        self.assertEqual(a.value[0], 1)

        # check that state isn't shared between instances
        a2 = A()
        self.assertNotEqual(a.value, a2.value)

        # check that it behaves like a property when there's no instance
        self.assertIsInstance(A.value, cached_property)

        # check that overriding name works
        self.assertEqual(a.other, 1)
        self.assertTrue(callable(a.other_value))

    def test_lazy_equality(self):
        """
        Tests that == and != work correctly for Promises.
        """

        lazy_a = lazy(lambda: 4, int)
        lazy_b = lazy(lambda: 4, int)
        lazy_c = lazy(lambda: 5, int)

        self.assertEqual(lazy_a(), lazy_b())
        self.assertNotEqual(lazy_b(), lazy_c())

    def test_lazy_repr_text(self):
        original_object = 'Lazy translation text'
        lazy_obj = lazy(lambda: original_object, six.text_type)
        self.assertEqual(repr(original_object), repr(lazy_obj()))

    def test_lazy_repr_int(self):
        original_object = 15
        lazy_obj = lazy(lambda: original_object, int)
        self.assertEqual(repr(original_object), repr(lazy_obj()))

    def test_lazy_repr_bytes(self):
        original_object = b'J\xc3\xbcst a str\xc3\xadng'
        lazy_obj = lazy(lambda: original_object, bytes)
        self.assertEqual(repr(original_object), repr(lazy_obj()))
