from __future__ import unicode_literals

from django.apps import apps
from django.apps.registry import Apps
from django.conf import settings
from django.contrib.sites import models
from django.contrib.sites.management import create_default_site
from django.contrib.sites.middleware import CurrentSiteMiddleware
from django.contrib.sites.models import Site, clear_site_cache
from django.contrib.sites.requests import RequestSite
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db.models.signals import post_migrate
from django.http import HttpRequest, HttpResponse
from django.test import TestCase, modify_settings, override_settings
from django.test.utils import captured_stdout


@modify_settings(INSTALLED_APPS={'append': 'django.contrib.sites'})
class SitesFrameworkTests(TestCase):
    multi_db = True

    def setUp(self):
        self.site = Site(
            id=settings.SITE_ID,
            domain="example.com",
            name="example.com",
        )
        self.site.save()

    def tearDown(self):
        Site.objects.clear_cache()

    def test_site_manager(self):
        # Make sure that get_current() does not return a deleted Site object.
        s = Site.objects.get_current()
        self.assertIsInstance(s, Site)
        s.delete()
        with self.assertRaises(ObjectDoesNotExist):
            Site.objects.get_current()

    def test_site_cache(self):
        # After updating a Site object (e.g. via the admin), we shouldn't return a
        # bogus value from the SITE_CACHE.
        site = Site.objects.get_current()
        self.assertEqual("example.com", site.name)
        s2 = Site.objects.get(id=settings.SITE_ID)
        s2.name = "Example site"
        s2.save()
        site = Site.objects.get_current()
        self.assertEqual("Example site", site.name)

    def test_delete_all_sites_clears_cache(self):
        # When all site objects are deleted the cache should also
        # be cleared and get_current() should raise a DoesNotExist.
        self.assertIsInstance(Site.objects.get_current(), Site)
        Site.objects.all().delete()
        with self.assertRaises(Site.DoesNotExist):
            Site.objects.get_current()

    @override_settings(ALLOWED_HOSTS=['example.com'])
    def test_get_current_site(self):
        # Test that the correct Site object is returned
        request = HttpRequest()
        request.META = {
            "SERVER_NAME": "example.com",
            "SERVER_PORT": "80",
        }
        site = get_current_site(request)
        self.assertIsInstance(site, Site)
        self.assertEqual(site.id, settings.SITE_ID)

        # Test that an exception is raised if the sites framework is installed
        # but there is no matching Site
        site.delete()
        with self.assertRaises(ObjectDoesNotExist):
            get_current_site(request)

        # A RequestSite is returned if the sites framework is not installed
        with self.modify_settings(INSTALLED_APPS={'remove': 'django.contrib.sites'}):
            site = get_current_site(request)
            self.assertIsInstance(site, RequestSite)
            self.assertEqual(site.name, "example.com")

    @override_settings(SITE_ID='', ALLOWED_HOSTS=['example.com'])
    def test_get_current_site_no_site_id(self):
        request = HttpRequest()
        request.META = {
            "SERVER_NAME": "example.com",
            "SERVER_PORT": "80",
        }
        del settings.SITE_ID
        site = get_current_site(request)
        self.assertEqual(site.name, "example.com")

    @override_settings(SITE_ID='', ALLOWED_HOSTS=['example.com', 'example.net'])
    def test_get_current_site_no_site_id_and_handle_port_fallback(self):
        request = HttpRequest()
        s1 = self.site
        s2 = Site.objects.create(domain='example.com:80', name='example.com:80')

        # Host header without port
        request.META = {'HTTP_HOST': 'example.com'}
        site = get_current_site(request)
        self.assertEqual(site, s1)

        # Host header with port - match, no fallback without port
        request.META = {'HTTP_HOST': 'example.com:80'}
        site = get_current_site(request)
        self.assertEqual(site, s2)

        # Host header with port - no match, fallback without port
        request.META = {'HTTP_HOST': 'example.com:81'}
        site = get_current_site(request)
        self.assertEqual(site, s1)

        # Host header with non-matching domain
        request.META = {'HTTP_HOST': 'example.net'}
        with self.assertRaises(ObjectDoesNotExist):
            get_current_site(request)

        # Ensure domain for RequestSite always matches host header
        with self.modify_settings(INSTALLED_APPS={'remove': 'django.contrib.sites'}):
            request.META = {'HTTP_HOST': 'example.com'}
            site = get_current_site(request)
            self.assertEqual(site.name, 'example.com')

            request.META = {'HTTP_HOST': 'example.com:80'}
            site = get_current_site(request)
            self.assertEqual(site.name, 'example.com:80')

    def test_domain_name_with_whitespaces(self):
        # Regression for #17320
        # Domain names are not allowed contain whitespace characters
        site = Site(name="test name", domain="test test")
        with self.assertRaises(ValidationError):
            site.full_clean()
        site.domain = "test\ttest"
        with self.assertRaises(ValidationError):
            site.full_clean()
        site.domain = "test\ntest"
        with self.assertRaises(ValidationError):
            site.full_clean()

    @override_settings(ALLOWED_HOSTS=['example.com'])
    def test_clear_site_cache(self):
        request = HttpRequest()
        request.META = {
            "SERVER_NAME": "example.com",
            "SERVER_PORT": "80",
        }
        self.assertEqual(models.SITE_CACHE, {})
        get_current_site(request)
        expected_cache = {self.site.id: self.site}
        self.assertEqual(models.SITE_CACHE, expected_cache)

        with self.settings(SITE_ID=''):
            get_current_site(request)

        expected_cache.update({self.site.domain: self.site})
        self.assertEqual(models.SITE_CACHE, expected_cache)

        clear_site_cache(Site, instance=self.site, using='default')
        self.assertEqual(models.SITE_CACHE, {})

    @override_settings(SITE_ID='', ALLOWED_HOSTS=['example2.com'])
    def test_clear_site_cache_domain(self):
        site = Site.objects.create(name='example2.com', domain='example2.com')
        request = HttpRequest()
        request.META = {
            "SERVER_NAME": "example2.com",
            "SERVER_PORT": "80",
        }
        get_current_site(request)  # prime the models.SITE_CACHE
        expected_cache = {site.domain: site}
        self.assertEqual(models.SITE_CACHE, expected_cache)

        # Site exists in 'default' database so using='other' shouldn't clear.
        clear_site_cache(Site, instance=site, using='other')
        self.assertEqual(models.SITE_CACHE, expected_cache)
        # using='default' should clear.
        clear_site_cache(Site, instance=site, using='default')
        self.assertEqual(models.SITE_CACHE, {})

    def test_unique_domain(self):
        site = Site(domain=self.site.domain)
        msg = 'Site with this Domain name already exists.'
        with self.assertRaisesMessage(ValidationError, msg):
            site.validate_unique()

    def test_site_natural_key(self):
        self.assertEqual(Site.objects.get_by_natural_key(self.site.domain), self.site)
        self.assertEqual(self.site.natural_key(), (self.site.domain,))

    @override_settings(ALLOWED_HOSTS=['example.com'])
    def test_requestsite_save_notimplemented_msg(self):
        # Test response msg for RequestSite.save NotImplementedError
        request = HttpRequest()
        request.META = {
            "HTTP_HOST": "example.com",
        }
        msg = 'RequestSite cannot be saved.'
        with self.assertRaisesMessage(NotImplementedError, msg):
            RequestSite(request).save()

    @override_settings(ALLOWED_HOSTS=['example.com'])
    def test_requestsite_delete_notimplemented_msg(self):
        # Test response msg for RequestSite.delete NotImplementedError
        request = HttpRequest()
        request.META = {
            "HTTP_HOST": "example.com",
        }
        msg = 'RequestSite cannot be deleted.'
        with self.assertRaisesMessage(NotImplementedError, msg):
            RequestSite(request).delete()


class JustOtherRouter(object):
    def allow_migrate(self, db, app_label, **hints):
        return db == 'other'


@modify_settings(INSTALLED_APPS={'append': 'django.contrib.sites'})
class CreateDefaultSiteTests(TestCase):
    multi_db = True

    def setUp(self):
        self.app_config = apps.get_app_config('sites')
        # Delete the site created as part of the default migration process.
        Site.objects.all().delete()

    def test_basic(self):
        """
        #15346, #15573 - create_default_site() creates an example site only if
        none exist.
        """
        with captured_stdout() as stdout:
            create_default_site(self.app_config)
        self.assertEqual(Site.objects.count(), 1)
        self.assertIn("Creating example.com", stdout.getvalue())

        with captured_stdout() as stdout:
            create_default_site(self.app_config)
        self.assertEqual(Site.objects.count(), 1)
        self.assertEqual("", stdout.getvalue())

    @override_settings(DATABASE_ROUTERS=[JustOtherRouter()])
    def test_multi_db_with_router(self):
        """
        #16353, #16828 - The default site creation should respect db routing.
        """
        create_default_site(self.app_config, using='default', verbosity=0)
        create_default_site(self.app_config, using='other', verbosity=0)
        self.assertFalse(Site.objects.using('default').exists())
        self.assertTrue(Site.objects.using('other').exists())

    def test_multi_db(self):
        create_default_site(self.app_config, using='default', verbosity=0)
        create_default_site(self.app_config, using='other', verbosity=0)
        self.assertTrue(Site.objects.using('default').exists())
        self.assertTrue(Site.objects.using('other').exists())

    def test_save_another(self):
        """
        #17415 - Another site can be created right after the default one.

        On some backends the sequence needs to be reset after saving with an
        explicit ID. Test that there isn't a sequence collisions by saving
        another site. This test is only meaningful with databases that use
        sequences for automatic primary keys such as PostgreSQL and Oracle.
        """
        create_default_site(self.app_config, verbosity=0)
        Site(domain='example2.com', name='example2.com').save()

    def test_signal(self):
        """
        #23641 - Sending the ``post_migrate`` signal triggers creation of the
        default site.
        """
        post_migrate.send(sender=self.app_config, app_config=self.app_config, verbosity=0)
        self.assertTrue(Site.objects.exists())

    @override_settings(SITE_ID=35696)
    def test_custom_site_id(self):
        """
        #23945 - The configured ``SITE_ID`` should be respected.
        """
        create_default_site(self.app_config, verbosity=0)
        self.assertEqual(Site.objects.get().pk, 35696)

    @override_settings()  # Restore original ``SITE_ID`` afterwards.
    def test_no_site_id(self):
        """
        #24488 - The pk should default to 1 if no ``SITE_ID`` is configured.
        """
        del settings.SITE_ID
        create_default_site(self.app_config, verbosity=0)
        self.assertEqual(Site.objects.get().pk, 1)

    def test_unavailable_site_model(self):
        """
        #24075 - A Site shouldn't be created if the model isn't available.
        """
        apps = Apps()
        create_default_site(self.app_config, verbosity=0, apps=apps)
        self.assertFalse(Site.objects.exists())


class MiddlewareTest(TestCase):

    def test_old_style_request(self):
        """ Makes sure that the request has correct `site` attribute. """
        middleware = CurrentSiteMiddleware()
        request = HttpRequest()
        middleware.process_request(request)
        self.assertEqual(request.site.id, settings.SITE_ID)

    def test_request(self):
        def get_response(request):
            return HttpResponse(str(request.site.id))
        response = CurrentSiteMiddleware(get_response)(HttpRequest())
        self.assertContains(response, settings.SITE_ID)
