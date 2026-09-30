import io

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework.test import APITestCase

from animals.models import Species
from shelters.models import Refuge

User = get_user_model()


def jpeg_file(name="dog.jpg"):
    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), color="red").save(buffer, format="JPEG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/jpeg")


class ReportApiTests(APITestCase):
    def setUp(self):
        self.chien = Species.objects.create(name="Chien")
        self.chat = Species.objects.create(name="Chat")
        self.citizen = User.objects.create_user(
            username="sara",
            email="sara@test.tn",
            password="StrongPass123",
            role=User.Role.CITOYEN,
        )
        self.other = User.objects.create_user(
            username="other",
            email="other@test.tn",
            password="StrongPass123",
            role=User.Role.CITOYEN,
        )
        self.refuge_user = User.objects.create_user(
            username="refuge",
            email="refuge@test.tn",
            password="StrongPass123",
            role=User.Role.REFUGE,
        )
        self.refuge = Refuge.objects.create(
            user=self.refuge_user,
            name="Refuge Tunis",
            latitude=36.8,
            longitude=10.18,
        )
        self.refuge.accepted_species.add(self.chien)
        far_user = User.objects.create_user(
            username="far",
            email="far@test.tn",
            password="StrongPass123",
            role=User.Role.REFUGE,
        )
        self.far_refuge = Refuge.objects.create(
            user=far_user,
            name="Refuge Sfax",
            latitude=34.74,
            longitude=10.76,
        )
        self.far_refuge.accepted_species.add(self.chat)
        self.benevole = User.objects.create_user(
            username="karim",
            email="karim@test.tn",
            password="StrongPass123",
            role=User.Role.BENEVOLE,
        )

    def login(self, email):
        response = self.client.post(
            "/api/auth/token/",
            {"email": email, "password": "StrongPass123"},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")

    def test_citizen_creates_report_and_assigns_nearest_refuge(self):
        self.login("sara@test.tn")
        response = self.client.post(
            "/api/reports/",
            {
                "type": "stray",
                "species": self.chien.id,
                "description": "Chien errant",
                "latitude": 36.81,
                "longitude": 10.19,
                "photos": jpeg_file(),
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["assigned_refuge"], self.refuge.id)
        self.assertEqual(response.data["status"], "assigned")
        self.assertEqual(response.data["reporter"], self.citizen.id)
        self.assertEqual(len(response.data["photos"]), 1)
        self.assertEqual(response.data["nearest_refuges"][0]["id"], self.refuge.id)

    def test_injured_report_requires_severity(self):
        self.login("sara@test.tn")
        response = self.client.post(
            "/api/reports/",
            {
                "type": "injured",
                "latitude": 36.81,
                "longitude": 10.19,
                "photos": jpeg_file(),
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("severity", response.data)

    def test_lists_are_scoped_to_the_caller(self):
        self.login("sara@test.tn")
        created = self.client.post(
            "/api/reports/",
            {
                "type": "stray",
                "latitude": 36.81,
                "longitude": 10.19,
                "photos": jpeg_file(),
            },
            format="multipart",
        )
        report_id = created.data["id"]

        own_list = self.client.get("/api/reports/")
        self.assertEqual(own_list.status_code, 200)
        self.assertEqual([item["id"] for item in own_list.data], [report_id])

        self.login("other@test.tn")
        self.assertEqual(self.client.get("/api/reports/").data, [])
        self.assertEqual(self.client.get(f"/api/reports/{report_id}/").status_code, 404)

        self.login("refuge@test.tn")
        refuge_list = self.client.get("/api/reports/")
        self.assertEqual([item["id"] for item in refuge_list.data], [report_id])
        self.assertEqual(self.client.get(f"/api/reports/{report_id}/").status_code, 200)

    def test_benevole_cannot_create_but_can_search_nearby(self):
        self.login("sara@test.tn")
        self.client.post(
            "/api/reports/",
            {
                "type": "injured",
                "severity": "critical",
                "latitude": 36.81,
                "longitude": 10.19,
                "photos": jpeg_file(),
            },
            format="multipart",
        )
        self.login("karim@test.tn")
        denied = self.client.post(
            "/api/reports/",
            {
                "type": "stray",
                "latitude": 36.81,
                "longitude": 10.19,
                "photos": jpeg_file(),
            },
            format="multipart",
        )
        self.assertEqual(denied.status_code, 403)

        nearby = self.client.get(
            "/api/reports/nearby/",
            {"latitude": 36.8, "longitude": 10.18, "radius_km": 5},
        )
        self.assertEqual(nearby.status_code, 200)
        self.assertEqual(len(nearby.data), 1)
        self.assertLess(nearby.data[0]["distance_km"], 5)

        far = self.client.get(
            "/api/reports/nearby/",
            {"latitude": 33.8, "longitude": 10.1, "radius_km": 5},
        )
        self.assertEqual(far.data, [])
