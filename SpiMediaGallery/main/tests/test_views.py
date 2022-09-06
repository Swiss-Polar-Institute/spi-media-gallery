from django.test import Client, TestCase


class ViewsTest(TestCase):
    fixtures = ["test_basic_data.yaml"]

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_homepage(self):
        c = Client()

        response = c.get("/")

        self.assertEqual(response.status_code, 200)

        self.assertContains(response, "landscape")

        self.assertNotContains(response, "this is not a tag")

    def test_medium_not_found(self):
        c = Client()

        response = c.get("/media/9999999")

        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "Media not found", status_code=404)

    def test_medium(self):
        c = Client()

        response = c.get("/media/1")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SPI-1.jpg")
        self.assertContains(response, "Copyright EPFL")

    def test_search_invalid_parameters(self):
        c = Client()

        response = c.get("/media/?invalid_parameter=1")

        self.assertEqual(response.status_code, 400)

    def test_search(self):
        c = Client()

        response = c.get("/media/?tags=1")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "tag: landscape (1 results)")
