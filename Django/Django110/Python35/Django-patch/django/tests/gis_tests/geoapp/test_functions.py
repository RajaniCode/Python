from __future__ import unicode_literals

import re
from decimal import Decimal

from django.contrib.gis.db.models import functions
from django.contrib.gis.geos import LineString, Point, Polygon, fromstr
from django.contrib.gis.measure import Area
from django.db import connection
from django.db.models import Sum
from django.test import TestCase, skipUnlessDBFeature
from django.utils import six

from ..utils import mysql, oracle, postgis, spatialite
from .models import City, Country, CountryWebMercator, State, Track


@skipUnlessDBFeature("gis_enabled")
class GISFunctionsTests(TestCase):
    """
    Testing functions from django/contrib/gis/db/models/functions.py.
    Several tests are taken and adapted from GeoQuerySetTest.
    Area/Distance/Length/Perimeter are tested in distapp/tests.

    Please keep the tests in function's alphabetic order.
    """
    fixtures = ['initial']

    def test_asgeojson(self):
        # Only PostGIS and SpatiaLite support GeoJSON.
        if not connection.ops.geojson:
            with self.assertRaises(NotImplementedError):
                list(Country.objects.annotate(json=functions.AsGeoJSON('mpoly')))
            return

        pueblo_json = '{"type":"Point","coordinates":[-104.609252,38.255001]}'
        houston_json = (
            '{"type":"Point","crs":{"type":"name","properties":'
            '{"name":"EPSG:4326"}},"coordinates":[-95.363151,29.763374]}'
        )
        victoria_json = (
            '{"type":"Point","bbox":[-123.30519600,48.46261100,-123.30519600,48.46261100],'
            '"coordinates":[-123.305196,48.462611]}'
        )
        chicago_json = (
            '{"type":"Point","crs":{"type":"name","properties":{"name":"EPSG:4326"}},'
            '"bbox":[-87.65018,41.85039,-87.65018,41.85039],"coordinates":[-87.65018,41.85039]}'
        )
        if spatialite:
            victoria_json = (
                '{"type":"Point","bbox":[-123.305196,48.462611,-123.305196,48.462611],'
                '"coordinates":[-123.305196,48.462611]}'
            )

        # Precision argument should only be an integer
        with self.assertRaises(TypeError):
            City.objects.annotate(geojson=functions.AsGeoJSON('point', precision='foo'))

        # Reference queries and values.
        # SELECT ST_AsGeoJson("geoapp_city"."point", 8, 0)
        # FROM "geoapp_city" WHERE "geoapp_city"."name" = 'Pueblo';
        self.assertEqual(
            pueblo_json,
            City.objects.annotate(geojson=functions.AsGeoJSON('point')).get(name='Pueblo').geojson
        )

        # SELECT ST_AsGeoJson("geoapp_city"."point", 8, 2) FROM "geoapp_city"
        # WHERE "geoapp_city"."name" = 'Houston';
        # This time we want to include the CRS by using the `crs` keyword.
        self.assertEqual(
            houston_json,
            City.objects.annotate(json=functions.AsGeoJSON('point', crs=True)).get(name='Houston').json
        )

        # SELECT ST_AsGeoJson("geoapp_city"."point", 8, 1) FROM "geoapp_city"
        # WHERE "geoapp_city"."name" = 'Houston';
        # This time we include the bounding box by using the `bbox` keyword.
        self.assertEqual(
            victoria_json,
            City.objects.annotate(
                geojson=functions.AsGeoJSON('point', bbox=True)
            ).get(name='Victoria').geojson
        )

        # SELECT ST_AsGeoJson("geoapp_city"."point", 5, 3) FROM "geoapp_city"
        # WHERE "geoapp_city"."name" = 'Chicago';
        # Finally, we set every available keyword.
        self.assertEqual(
            chicago_json,
            City.objects.annotate(
                geojson=functions.AsGeoJSON('point', bbox=True, crs=True, precision=5)
            ).get(name='Chicago').geojson
        )

    @skipUnlessDBFeature("has_AsGML_function")
    def test_asgml(self):
        # Should throw a TypeError when trying to obtain GML from a
        # non-geometry field.
        qs = City.objects.all()
        with self.assertRaises(TypeError):
            qs.annotate(gml=functions.AsGML('name'))
        ptown = City.objects.annotate(gml=functions.AsGML('point', precision=9)).get(name='Pueblo')

        if oracle:
            # No precision parameter for Oracle :-/
            gml_regex = re.compile(
                r'^<gml:Point srsName="SDO:4326" xmlns:gml="http://www.opengis.net/gml">'
                r'<gml:coordinates decimal="\." cs="," ts=" ">-104.60925\d+,38.25500\d+ '
                r'</gml:coordinates></gml:Point>'
            )
        else:
            gml_regex = re.compile(
                r'^<gml:Point srsName="EPSG:4326"><gml:coordinates>'
                r'-104\.60925\d+,38\.255001</gml:coordinates></gml:Point>'
            )

        self.assertTrue(gml_regex.match(ptown.gml))

        if postgis:
            self.assertIn(
                '<gml:pos srsDimension="2">',
                City.objects.annotate(gml=functions.AsGML('point', version=3)).get(name='Pueblo').gml
            )

    @skipUnlessDBFeature("has_AsKML_function")
    def test_askml(self):
        # Should throw a TypeError when trying to obtain KML from a
        # non-geometry field.
        with self.assertRaises(TypeError):
            City.objects.annotate(kml=functions.AsKML('name'))

        # Ensuring the KML is as expected.
        ptown = City.objects.annotate(kml=functions.AsKML('point', precision=9)).get(name='Pueblo')
        self.assertEqual('<Point><coordinates>-104.609252,38.255001</coordinates></Point>', ptown.kml)

    @skipUnlessDBFeature("has_AsSVG_function")
    def test_assvg(self):
        with self.assertRaises(TypeError):
            City.objects.annotate(svg=functions.AsSVG('point', precision='foo'))
        # SELECT AsSVG(geoapp_city.point, 0, 8) FROM geoapp_city WHERE name = 'Pueblo';
        svg1 = 'cx="-104.609252" cy="-38.255001"'
        # Even though relative, only one point so it's practically the same except for
        # the 'c' letter prefix on the x,y values.
        svg2 = svg1.replace('c', '')
        self.assertEqual(svg1, City.objects.annotate(svg=functions.AsSVG('point')).get(name='Pueblo').svg)
        self.assertEqual(svg2, City.objects.annotate(svg=functions.AsSVG('point', relative=5)).get(name='Pueblo').svg)

    @skipUnlessDBFeature("has_BoundingCircle_function")
    def test_bounding_circle(self):
        qs = Country.objects.annotate(circle=functions.BoundingCircle('mpoly')).order_by('name')
        self.assertAlmostEqual(qs[0].circle.area, 168.89, 2)
        self.assertAlmostEqual(qs[1].circle.area, 135.95, 2)

        qs = Country.objects.annotate(circle=functions.BoundingCircle('mpoly', num_seg=12)).order_by('name')
        self.assertAlmostEqual(qs[0].circle.area, 168.44, 2)
        self.assertAlmostEqual(qs[1].circle.area, 135.59, 2)

    @skipUnlessDBFeature("has_Centroid_function")
    def test_centroid(self):
        qs = State.objects.exclude(poly__isnull=True).annotate(centroid=functions.Centroid('poly'))
        tol = 1.8 if mysql else (0.1 if oracle else 0.00001)
        for state in qs:
            self.assertTrue(state.poly.centroid.equals_exact(state.centroid, tol))

        with self.assertRaisesMessage(TypeError, "'Centroid' takes exactly 1 argument (2 given)"):
            State.objects.annotate(centroid=functions.Centroid('poly', 'poly'))

    @skipUnlessDBFeature("has_Difference_function")
    def test_difference(self):
        geom = Point(5, 23, srid=4326)
        qs = Country.objects.annotate(diff=functions.Difference('mpoly', geom))
        # SpatiaLite and Oracle do something screwy with the Texas geometry.
        if spatialite or oracle:
            qs = qs.exclude(name='Texas')

        for c in qs:
            self.assertTrue(c.mpoly.difference(geom).equals(c.diff))

    @skipUnlessDBFeature("has_Difference_function", "has_Transform_function")
    def test_difference_mixed_srid(self):
        """Testing with mixed SRID (Country has default 4326)."""
        geom = Point(556597.4, 2632018.6, srid=3857)  # Spherical mercator
        qs = Country.objects.annotate(difference=functions.Difference('mpoly', geom))
        # SpatiaLite and Oracle do something screwy with the Texas geometry.
        if spatialite or oracle:
            qs = qs.exclude(name='Texas')
        for c in qs:
            self.assertTrue(c.mpoly.difference(geom).equals(c.difference))

    @skipUnlessDBFeature("has_Envelope_function")
    def test_envelope(self):
        countries = Country.objects.annotate(envelope=functions.Envelope('mpoly'))
        for country in countries:
            self.assertIsInstance(country.envelope, Polygon)

    @skipUnlessDBFeature("has_ForceRHR_function")
    def test_force_rhr(self):
        rings = (
            ((0, 0), (5, 0), (0, 5), (0, 0)),
            ((1, 1), (1, 3), (3, 1), (1, 1)),
        )
        rhr_rings = (
            ((0, 0), (0, 5), (5, 0), (0, 0)),
            ((1, 1), (3, 1), (1, 3), (1, 1)),
        )
        State.objects.create(name='Foo', poly=Polygon(*rings))
        st = State.objects.annotate(force_rhr=functions.ForceRHR('poly')).get(name='Foo')
        self.assertEqual(rhr_rings, st.force_rhr.coords)

    @skipUnlessDBFeature("has_GeoHash_function")
    def test_geohash(self):
        # Reference query:
        # SELECT ST_GeoHash(point) FROM geoapp_city WHERE name='Houston';
        # SELECT ST_GeoHash(point, 5) FROM geoapp_city WHERE name='Houston';
        ref_hash = '9vk1mfq8jx0c8e0386z6'
        h1 = City.objects.annotate(geohash=functions.GeoHash('point')).get(name='Houston')
        h2 = City.objects.annotate(geohash=functions.GeoHash('point', precision=5)).get(name='Houston')
        self.assertEqual(ref_hash, h1.geohash)
        self.assertEqual(ref_hash[:5], h2.geohash)

    @skipUnlessDBFeature("has_Intersection_function")
    def test_intersection(self):
        geom = Point(5, 23, srid=4326)
        qs = Country.objects.annotate(inter=functions.Intersection('mpoly', geom))
        for c in qs:
            if spatialite or (mysql and not connection.ops.uses_invalid_empty_geometry_collection) or oracle:
                # When the intersection is empty, some databases return None.
                expected = None
            else:
                expected = c.mpoly.intersection(geom)
            self.assertEqual(c.inter, expected)

    @skipUnlessDBFeature("has_IsValid_function")
    def test_isvalid(self):
        valid_geom = fromstr('POLYGON((0 0, 0 1, 1 1, 1 0, 0 0))')
        invalid_geom = fromstr('POLYGON((0 0, 0 1, 1 1, 1 0, 1 1, 1 0, 0 0))')
        State.objects.create(name='valid', poly=valid_geom)
        State.objects.create(name='invalid', poly=invalid_geom)
        valid = State.objects.filter(name='valid').annotate(isvalid=functions.IsValid('poly')).first()
        invalid = State.objects.filter(name='invalid').annotate(isvalid=functions.IsValid('poly')).first()
        self.assertIs(valid.isvalid, True)
        self.assertIs(invalid.isvalid, False)

    @skipUnlessDBFeature("has_Area_function")
    def test_area_with_regular_aggregate(self):
        # Create projected country objects, for this test to work on all backends.
        for c in Country.objects.all():
            CountryWebMercator.objects.create(name=c.name, mpoly=c.mpoly)
        # Test in projected coordinate system
        qs = CountryWebMercator.objects.annotate(area_sum=Sum(functions.Area('mpoly')))
        # Some backends (e.g. Oracle) cannot group by multipolygon values, so
        # defer such fields in the aggregation query.
        for c in qs.defer('mpoly'):
            result = c.area_sum
            # If the result is a measure object, get value.
            if isinstance(result, Area):
                result = result.sq_m
            self.assertAlmostEqual((result - c.mpoly.area) / c.mpoly.area, 0)

    @skipUnlessDBFeature("has_MakeValid_function")
    def test_make_valid(self):
        invalid_geom = fromstr('POLYGON((0 0, 0 1, 1 1, 1 0, 1 1, 1 0, 0 0))')
        State.objects.create(name='invalid', poly=invalid_geom)
        invalid = State.objects.filter(name='invalid').annotate(repaired=functions.MakeValid('poly')).first()
        self.assertIs(invalid.repaired.valid, True)
        self.assertEqual(invalid.repaired, fromstr('POLYGON((0 0, 0 1, 1 1, 1 0, 0 0))'))

    @skipUnlessDBFeature("has_MemSize_function")
    def test_memsize(self):
        ptown = City.objects.annotate(size=functions.MemSize('point')).get(name='Pueblo')
        self.assertTrue(20 <= ptown.size <= 40)  # Exact value may depend on PostGIS version

    @skipUnlessDBFeature("has_NumGeom_function")
    def test_num_geom(self):
        # Both 'countries' only have two geometries.
        for c in Country.objects.annotate(num_geom=functions.NumGeometries('mpoly')):
            self.assertEqual(2, c.num_geom)

        qs = City.objects.filter(point__isnull=False).annotate(num_geom=functions.NumGeometries('point'))
        for city in qs:
            # Oracle and PostGIS return 1 for the number of geometries on
            # non-collections, whereas MySQL returns None.
            if mysql:
                self.assertIsNone(city.num_geom)
            else:
                self.assertEqual(1, city.num_geom)

    @skipUnlessDBFeature("has_NumPoint_function")
    def test_num_points(self):
        coords = [(-95.363151, 29.763374), (-95.448601, 29.713803)]
        Track.objects.create(name='Foo', line=LineString(coords))
        qs = Track.objects.annotate(num_points=functions.NumPoints('line'))
        self.assertEqual(qs.first().num_points, 2)
        if spatialite or mysql:
            # SpatiaLite and MySQL can only count points on LineStrings
            return

        for c in Country.objects.annotate(num_points=functions.NumPoints('mpoly')):
            self.assertEqual(c.mpoly.num_points, c.num_points)

        if not oracle:
            # Oracle cannot count vertices in Point geometries.
            for c in City.objects.annotate(num_points=functions.NumPoints('point')):
                self.assertEqual(1, c.num_points)

    @skipUnlessDBFeature("has_PointOnSurface_function")
    def test_point_on_surface(self):
        # Reference values.
        if oracle:
            # SELECT SDO_UTIL.TO_WKTGEOMETRY(SDO_GEOM.SDO_POINTONSURFACE(GEOAPP_COUNTRY.MPOLY, 0.05))
            # FROM GEOAPP_COUNTRY;
            ref = {'New Zealand': fromstr('POINT (174.616364 -36.100861)', srid=4326),
                   'Texas': fromstr('POINT (-103.002434 36.500397)', srid=4326),
                   }
        else:
            # Using GEOSGeometry to compute the reference point on surface values
            # -- since PostGIS also uses GEOS these should be the same.
            ref = {'New Zealand': Country.objects.get(name='New Zealand').mpoly.point_on_surface,
                   'Texas': Country.objects.get(name='Texas').mpoly.point_on_surface
                   }

        qs = Country.objects.annotate(point_on_surface=functions.PointOnSurface('mpoly'))
        for country in qs:
            tol = 0.00001  # SpatiaLite might have WKT-translation-related precision issues
            self.assertTrue(ref[country.name].equals_exact(country.point_on_surface, tol))

    @skipUnlessDBFeature("has_Reverse_function")
    def test_reverse_geom(self):
        coords = [(-95.363151, 29.763374), (-95.448601, 29.713803)]
        Track.objects.create(name='Foo', line=LineString(coords))
        track = Track.objects.annotate(reverse_geom=functions.Reverse('line')).get(name='Foo')
        coords.reverse()
        self.assertEqual(tuple(coords), track.reverse_geom.coords)

    @skipUnlessDBFeature("has_Scale_function")
    def test_scale(self):
        xfac, yfac = 2, 3
        tol = 5  # The low precision tolerance is for SpatiaLite
        qs = Country.objects.annotate(scaled=functions.Scale('mpoly', xfac, yfac))
        for country in qs:
            for p1, p2 in zip(country.mpoly, country.scaled):
                for r1, r2 in zip(p1, p2):
                    for c1, c2 in zip(r1.coords, r2.coords):
                        self.assertAlmostEqual(c1[0] * xfac, c2[0], tol)
                        self.assertAlmostEqual(c1[1] * yfac, c2[1], tol)
        # Test float/Decimal values
        qs = Country.objects.annotate(scaled=functions.Scale('mpoly', 1.5, Decimal('2.5')))
        self.assertGreater(qs[0].scaled.area, qs[0].mpoly.area)

    @skipUnlessDBFeature("has_SnapToGrid_function")
    def test_snap_to_grid(self):
        # Let's try and break snap_to_grid() with bad combinations of arguments.
        for bad_args in ((), range(3), range(5)):
            with self.assertRaises(ValueError):
                Country.objects.annotate(snap=functions.SnapToGrid('mpoly', *bad_args))
        for bad_args in (('1.0',), (1.0, None), tuple(map(six.text_type, range(4)))):
            with self.assertRaises(TypeError):
                Country.objects.annotate(snap=functions.SnapToGrid('mpoly', *bad_args))

        # Boundary for San Marino, courtesy of Bjorn Sandvik of thematicmapping.org
        # from the world borders dataset he provides.
        wkt = ('MULTIPOLYGON(((12.41580 43.95795,12.45055 43.97972,12.45389 43.98167,'
               '12.46250 43.98472,12.47167 43.98694,12.49278 43.98917,'
               '12.50555 43.98861,12.51000 43.98694,12.51028 43.98277,'
               '12.51167 43.94333,12.51056 43.93916,12.49639 43.92333,'
               '12.49500 43.91472,12.48778 43.90583,12.47444 43.89722,'
               '12.46472 43.89555,12.45917 43.89611,12.41639 43.90472,'
               '12.41222 43.90610,12.40782 43.91366,12.40389 43.92667,'
               '12.40500 43.94833,12.40889 43.95499,12.41580 43.95795)))')
        Country.objects.create(name='San Marino', mpoly=fromstr(wkt))

        # Because floating-point arithmetic isn't exact, we set a tolerance
        # to pass into GEOS `equals_exact`.
        tol = 0.000000001

        # SELECT AsText(ST_SnapToGrid("geoapp_country"."mpoly", 0.1)) FROM "geoapp_country"
        # WHERE "geoapp_country"."name" = 'San Marino';
        ref = fromstr('MULTIPOLYGON(((12.4 44,12.5 44,12.5 43.9,12.4 43.9,12.4 44)))')
        self.assertTrue(
            ref.equals_exact(
                Country.objects.annotate(
                    snap=functions.SnapToGrid('mpoly', 0.1)
                ).get(name='San Marino').snap,
                tol
            )
        )

        # SELECT AsText(ST_SnapToGrid("geoapp_country"."mpoly", 0.05, 0.23)) FROM "geoapp_country"
        # WHERE "geoapp_country"."name" = 'San Marino';
        ref = fromstr('MULTIPOLYGON(((12.4 43.93,12.45 43.93,12.5 43.93,12.45 43.93,12.4 43.93)))')
        self.assertTrue(
            ref.equals_exact(
                Country.objects.annotate(
                    snap=functions.SnapToGrid('mpoly', 0.05, 0.23)
                ).get(name='San Marino').snap,
                tol
            )
        )

        # SELECT AsText(ST_SnapToGrid("geoapp_country"."mpoly", 0.5, 0.17, 0.05, 0.23)) FROM "geoapp_country"
        # WHERE "geoapp_country"."name" = 'San Marino';
        ref = fromstr(
            'MULTIPOLYGON(((12.4 43.87,12.45 43.87,12.45 44.1,12.5 44.1,12.5 43.87,12.45 43.87,12.4 43.87)))'
        )
        self.assertTrue(
            ref.equals_exact(
                Country.objects.annotate(
                    snap=functions.SnapToGrid('mpoly', 0.05, 0.23, 0.5, 0.17)
                ).get(name='San Marino').snap,
                tol
            )
        )

    @skipUnlessDBFeature("has_SymDifference_function")
    def test_sym_difference(self):
        geom = Point(5, 23, srid=4326)
        qs = Country.objects.annotate(sym_difference=functions.SymDifference('mpoly', geom))
        # Oracle does something screwy with the Texas geometry.
        if oracle:
            qs = qs.exclude(name='Texas')
        for country in qs:
            self.assertTrue(country.mpoly.sym_difference(geom).equals(country.sym_difference))

    @skipUnlessDBFeature("has_Transform_function")
    def test_transform(self):
        # Pre-transformed points for Houston and Pueblo.
        ptown = fromstr('POINT(992363.390841912 481455.395105533)', srid=2774)
        prec = 3  # Precision is low due to version variations in PROJ and GDAL.

        # Asserting the result of the transform operation with the values in
        #  the pre-transformed points.
        h = City.objects.annotate(pt=functions.Transform('point', ptown.srid)).get(name='Pueblo')
        self.assertEqual(2774, h.pt.srid)
        self.assertAlmostEqual(ptown.x, h.pt.x, prec)
        self.assertAlmostEqual(ptown.y, h.pt.y, prec)

    @skipUnlessDBFeature("has_Translate_function")
    def test_translate(self):
        xfac, yfac = 5, -23
        qs = Country.objects.annotate(translated=functions.Translate('mpoly', xfac, yfac))
        for c in qs:
            for p1, p2 in zip(c.mpoly, c.translated):
                for r1, r2 in zip(p1, p2):
                    for c1, c2 in zip(r1.coords, r2.coords):
                        # The low precision is for SpatiaLite
                        self.assertAlmostEqual(c1[0] + xfac, c2[0], 5)
                        self.assertAlmostEqual(c1[1] + yfac, c2[1], 5)

    # Some combined function tests
    @skipUnlessDBFeature(
        "has_Difference_function", "has_Intersection_function",
        "has_SymDifference_function", "has_Union_function")
    def test_diff_intersection_union(self):
        "Testing the `difference`, `intersection`, `sym_difference`, and `union` GeoQuerySet methods."
        geom = Point(5, 23, srid=4326)
        qs = Country.objects.all().annotate(
            difference=functions.Difference('mpoly', geom),
            sym_difference=functions.SymDifference('mpoly', geom),
            union=functions.Union('mpoly', geom),
        )

        # For some reason SpatiaLite does something screwy with the Texas geometry here.
        # Also, it doesn't like the null intersection.
        if spatialite:
            qs = qs.exclude(name='Texas')
        else:
            qs = qs.annotate(intersection=functions.Intersection('mpoly', geom))

        if oracle:
            # Should be able to execute the queries; however, they won't be the same
            # as GEOS (because Oracle doesn't use GEOS internally like PostGIS or
            # SpatiaLite).
            return
        for c in qs:
            self.assertTrue(c.mpoly.difference(geom).equals(c.difference))
            if not (spatialite or mysql):
                self.assertEqual(c.mpoly.intersection(geom), c.intersection)
            self.assertTrue(c.mpoly.sym_difference(geom).equals(c.sym_difference))
            self.assertTrue(c.mpoly.union(geom).equals(c.union))

    @skipUnlessDBFeature("has_Union_function")
    def test_union(self):
        geom = Point(-95.363151, 29.763374, srid=4326)
        ptown = City.objects.annotate(union=functions.Union('point', geom)).get(name='Dallas')
        tol = 0.00001
        # Undefined ordering
        expected1 = fromstr('MULTIPOINT(-96.801611 32.782057,-95.363151 29.763374)', srid=4326)
        expected2 = fromstr('MULTIPOINT(-95.363151 29.763374,-96.801611 32.782057)', srid=4326)
        self.assertTrue(expected1.equals_exact(ptown.union, tol) or expected2.equals_exact(ptown.union, tol))
