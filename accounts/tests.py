from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from animals.models import Species

User = get_user_model()


class AuthApiTests(APITestCase):
    def test_register_citoyen_is_soft_and_returns_token(self):
        response = self.client.post(
            "/api/auth/register/",
            {"email": "citoyen@example.com", "password": "StrongPass123", "role": "citoyen"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["user"]["role"], "citoyen")
        self.assertEqual(response.data["user"]["profile"], {"address": ""})
        self.assertIn("access", response.data)

    def test_register_admin_is_rejected(self):
        response = self.client.post(
            "/api/auth/register/",
            {"email": "admin@example.com", "password": "StrongPass123", "role": "admin"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_login_with_email_and_patch_profile(self):
        self.client.post(
            "/api/auth/register/",
            {"email": "vet@example.com", "password": "StrongPass123", "role": "veterinaire"},
            format="json",
        )
        login = self.client.post(
            "/api/auth/token/",
            {"email": "vet@example.com", "password": "StrongPass123"},
            format="json",
        )
        self.assertEqual(login.status_code, 200)
        self.assertIsNotNone(User.objects.get(email="vet@example.com").last_login)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

        me = self.client.patch(
            "/api/auth/me/",
            {"phone": "20000000", "profile": {"license_number": "VET-1", "radius_km": 25}},
            format="json",
        )
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.data["phone"], "20000000")
        self.assertEqual(me.data["profile"]["license_number"], "VET-1")
        self.assertEqual(me.data["profile"]["radius_km"], 25)

    def test_refuge_profile_is_created_from_me(self):
        register = self.client.post(
            "/api/auth/register/",
            {"email": "refuge@example.com", "password": "StrongPass123", "role": "refuge"},
            format="json",
        )
        self.assertIsNone(register.data["user"]["profile"])
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {register.data['access']}")

        species = Species.objects.create(name="Chien")
        me = self.client.patch(
            "/api/auth/me/",
            {
                "profile": {
                    "name": "Refuge Tunis",
                    "latitude": 36.8,
                    "longitude": 10.18,
                    "accepted_species": [species.id],
                }
            },
            format="json",
        )
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.data["profile"]["name"], "Refuge Tunis")
        self.assertEqual(me.data["profile"]["accepted_species"], [species.id])
        self.assertTrue(User.objects.get(email="refuge@example.com").refuge)
